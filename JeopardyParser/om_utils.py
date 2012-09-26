import gflags
import oauth2
import time
import httplib
import logging
import sys
import csv
from cfg import *
from libraries.python.web_util import encode_json, decode_json
from codecs import decode
import re

TITLE = 'title'
DESCRIPTION = 'description'
FORMAT = 'format'
GRADE = 'grade'
SECTION = 'section'
STANDARD = 'standard'
SHARING = 'sharing'
TAGS = 'tags'
VALID_LIST_PROPERTIES = (TITLE, DESCRIPTION, FORMAT, SECTION, STANDARD, SHARING, TAGS)

WORD = 'word'
POS = 'pos'
DEFINITION = 'defn'
SENTENCE = 'sentence'
ROOTWORD= 'rootWord'
QUESTION = 'question'
CORRECTANSWER = 'correctAnswer'
INCORRECTANSWERS = 'incorrectAnswers'
VALID_VOCAB_PROPERTIES = (WORD, POS, DEFINITION, SENTENCE, ROOTWORD)



class HTTPError(Exception):
  '''
  Exception class used for server errors. Includes information to
  format a JSON error response.
  '''
  def __init__(self, *args):
    self.code = args[0]
    if len(args) > 1:
      self.message = args[1]
    else:
      self.message = None

  def error_response(self):
    return error_response(self.code, self.message)

  def __str__(self):
    return self.error_response()


# http://www.packtpub.com/article/python-when-to-use-object-oriented-programming
class Color:
  def __init__(self, rgb_value, name):
    self._rgb_value = rgb_value
    self._name = name
  def set_name(self, name):
    self._name = name
  def get_name(self):
    return self._name

class ResponseValidation:
  def __init__(self):
    pass



def isResponseErrorFree(newList):
  try:
    if newList["error"]:
      print "Response error:", newList["error"]
      return 0
  except Exception, e:
    return 1
  
def filenameendsin(fname,filext):
    m = re.search(r'csv$',fname)
    if m:
      return True
    return False


def  get_userid_given_username(listofusers,username):
  for u in listofusers:
    try:
      if u["username"] == username:
        return u["id"]
    except Exception, e:
      pass
      # logging.warning('User has no username %s' % u["id"])

  return("")  #no username match found


def validate_item_dictionary_for_format(f_type,idict):
  '''
  for each format, see if all the needed elements are in the dictionary
  '''
  CORRECTANSWER = 'correctAnswer'
  WORD = 'word'
  POS = 'pos'
  DEFINITION = 'defn'

  validity = True

  if f_type == "multipleChoice":
    # log("idict")
    # log(idict)
    if not CORRECTANSWER in idict:
      print("CORRECTANSWER property not specified in CSV. ITEM  cannot be created without this mandatory field")
      validity = False

  if f_type == "vocabulary":
    if not WORD in idict:
      print("WORD  property not specified in CSV. ITEM  cannot be created without this mandatory field")
    if not DEFINITION in idict:
      print("DEFN  property not specified in CSV. ITEM  cannot be created without this mandatory field")
  return validity



def   isValidUser(userid):
#  userid = "4fdf8ecfd6b77f037b0007fd"

  if len(userid)==24:
    return True
  return False


def isprintable(s, codec='utf8'):
  '''
  checks if the characters are in utf8.
  '''
  try: s.decode(codec)
  except UnicodeDecodeError: return False #not printable
  else: return True
  


def log(s):
  '''
  Just another way to make prints during debugging
  Usage: log("hello world") will print only when DEBUG is ON
  The right way to do this is to use the logging module in Python
  '''
  # DEBUG = True
  if cfg.DEBUG:
    print s


def  printList(li):
  for l in li:
    logging.info(l)


def create_users_dict(textlist):
  pass


def add_to_dict_as_int(ldict,keyword,row,index):
  '''
  INTEGER add items to the list dictionary
  '''
  
  try:
    ldict[keyword] = int(row[index+1])
  except ValueError:
    print row
    print("Incorrect kw %s  row %s index %d" % keyword, row, index)
    
#end of def

def add_to_dict(ldict,keyword,row,index):
  '''
  STRING add items to the list dictionary
  '''
  format_ok = True
  
  TO_BE_UNQUOTED = ('format', 'grade', 'section', 'standard','sharing')

  element = row[index+1]

  if keyword in TO_BE_UNQUOTED:   
    element = element.replace('"','')

  try:
    if keyword == "format":
      format_ok = validate_format_type(element)
      
    if format_ok:
      ldict[keyword] = element
  except ValueError:
    print("Incorrect %s Supplied" % keyword)
    
#end of def


def addElementToDict(listOrItem, dictionary, kw, el):

  format_ok = True
  valid_kw = True

  if kw == "format":
    format_ok = validate_format_type(el)
  
  valid_kw = validate_keyword(listOrItem, kw)

  if format_ok and valid_kw:
    dictionary[kw] = el
  else:
    print("Incorrect %s Supplied %s" % kw, el)    
      



def validate_keyword(listOrItem,kw):
  
  if listOrItem == "list":
    if kw in VALID_LIST_PROPERTIES:
      return True

  if listOrItem == "vocab":
    if kw in VALID_VOCAB_PROPERTIES:
      return True

  return False



def validate_format_type(f_type):
  
  PAIRS = 'pairs'
  MULTIPLECHOICE = 'multipleChoice'
  VOCAB = 'vocabulary'

  FORMAT_TYPES = (PAIRS, MULTIPLECHOICE,VOCAB)
  
  # print("f_type %s" % f_type)
  if f_type not in FORMAT_TYPES:	
    print('LIST FORMAT must be one of %s' % str(FORMAT_TYPES))
    return False
  
  return True


def read_all_csv_users(filename):
    '''
    read the file with the users
    '''
    # Each row read from the csv file is returned as a list of strings. No automatic data type conversion is performed.

    USER   =  "user"
    CONT   = "c"

    ENDLIST= "endlist"
    LISTEND = "listend"

    VALID_START_WORDS = (USER,CONT)
    LISTENDERS = (ENDLIST,LISTEND)

    allRows = csv.reader(open(filename, 'rb'), delimiter=',', quotechar='|')
    textlist = []

    for row in allRows:  
      logging.info(row)

      str1 = ''.join(str(e) for e in row) #convert row to a string

      if row and isprintable(str1):
        if row[0].rstrip(" ").lower() in LISTENDERS:
          return textlist

        if row[0].rstrip(" ").lower() in VALID_START_WORDS:
          textlist.append(row)

    return textlist



def read_all_csv_lines(filename):
    '''
    read the file with the list
    '''
# Each row read from the csv file is returned as a list of strings. No automatic data type conversion is performed.
    allRows = csv.reader(open(filename, 'rb'), delimiter=',', quotechar='|')
    textlist = []

    ITEM   =  "item"
    LIST   =  "list"
    CONT   =  "c"

    ENDLIST = "endlist"
    LISTEND = "listend"

    VALID_START_WORDS = (ITEM,LIST,CONT)
    LISTENDERS = (ENDLIST,LISTEND)

#    print "All Rows"

    for row in allRows:  
      # if not row.strip():  # a way to skip blank lines. row.strip() returns TRUE if blank
#      logging.info(row)

      str1 = ''.join(str(e) for e in row) #convert row to a string
      # print("can be printed:",isprintable(str1))
      
      if row and isprintable(str1):
        row[0] = row[0].replace('"','')
        if row[0].rstrip(" ").lower() in LISTENDERS:
          return textlist
        if row[0].rstrip(" ").lower() in VALID_START_WORDS:
          # print "Line with List params"
          textlist.append(row)
      
    print(len(textlist)) 
    return textlist
        
        
            

#given a username, the properties to be added.            
def create_user_properties_dicts(textlist):
  '''
  Each line in CSV file is a one user. 
  It has a list of properties that need to be updated.
  '''

  dictslist = []

  USERNAME = 'username'
  PASSWORD = 'password'
  EMAIL = 'email'
  NAME  =  'name'
  TYPE = 'type'
  USER_PROPERTIES = (EMAIL,PASSWORD, NAME, TYPE)

  for r in textlist:
    if r[0].rstrip(" ").lower() =="user":
      longdict = {} #the full line with one embedded dict
      jdict = {} #the actual json to be added via the API
      for index, el in enumerate(r):                
        if el in USERNAME:
          add_to_dict(longdict,el,r,index) #will add the token next to curr index        

        if el in USER_PROPERTIES:
          add_to_dict(jdict,el,r,index) #will add the token next to curr index        

      longdict["JSON"] = jdict      #example    {"JSON": {"email":"abc@r.com"} }

      if not USERNAME in longdict:
        logging.warning("USERNAME property not specified in CSV %s" % r)


      dictslist.append(longdict)

  return dictslist # a list of idicts




def create_list_dict(allRows):
    '''
    Read all lines that begin with List and if a format is found, store it.
    Return False if there is no format, or if format is unrecognized
    '''


# title || Name of the list || 
# description || Short list description.
# standard || String code representing the list standard. Example: "L.7.2".
# section || Numerical sub-section of the standard.

    LIST = 'list'
    Q_LIST = '"list"'
    LIST_IDENTIFIER  = (LIST, Q_LIST)


    Q_TITLE = '"title"'
    Q_DESCRIPTION = '"description"'
    Q_FORMAT = '"format"'
    Q_GRADE = '"grade"'
    Q_SECTION = '"section"'
    Q_STANDARD = '"standard"'
    Q_SHARING = '"sharing"'

    LIST_PROPERTIES = (TITLE, DESCRIPTION, FORMAT,SECTION,STANDARD,SHARING,Q_TITLE, Q_DESCRIPTION, Q_FORMAT,Q_SECTION,Q_STANDARD, Q_SHARING)
    LIST_INTEGER_PROPERTIES = (GRADE, Q_GRADE)

#    if not 'format' in row:
#        print('Format type must be specified for new lists.')
    
    ldict = {}
#    print("useful lines in List file",  len(allRows))
    for row in allRows:
#        print row
        if row[0].rstrip(" ").lower() in LIST_IDENTIFIER:
          for index, token in enumerate(row):                
              token = token.replace('"','')
              if token in LIST_PROPERTIES:
                add_to_dict(ldict, token.lower(),row,index) #will add the token next to curr index
                            
                # grade || Intended grade level of the list. Number between 0 (K) and 8.
              if token in LIST_INTEGER_PROPERTIES:
                # print("item %s" % item)
                add_to_dict_as_int(ldict, token.lower(),row,index)

    if not ("format" or '"format"') in ldict:
      logging.warning("Create List Dict -- List format property not specified in CSV. List cannot be created without this mandatory field")


    return ldict
                        

# word || The item word.
# pos|| The item part-of-speech.
# defn|| The item definition.
# sentence || An example sentence using the item word.
# otherWords || Alternate words. Array of strings, maximum number of words is 5.
# parts || The item word broken down into parts. Array of strings, maximum number if parts is 5.
def  create_item_dicts(textlist,f_type,two_lines=False):
  '''
  Each line in CSV file is a new item. It has to have its mandatory fields
  and optionally, any of the other item properties for that list format
  '''
  
  dictslist = []

  Q_WORD = '"word"'
  Q_POS = '"pos"'
  Q_DEFINITION = '"defn"'
  Q_SENTENCE = '"sentence"'
  Q_ROOTWORD= '"rootWord"'
  Q_QUESTION = '"question"'
  Q_CORRECTANSWER = '"correctAnswer"'
  Q_INCORRECTANSWERS = '"incorrectAnswers"'

  MULTIPLECHOICE_PROPERTIES = (WORD,CORRECTANSWER,INCORRECTANSWERS,DEFINITION,QUESTION, Q_WORD, Q_CORRECTANSWER,Q_INCORRECTANSWERS,Q_DEFINITION,Q_QUESTION)
  VOCAB_PROPERTIES = (WORD, POS, DEFINITION, SENTENCE, ROOTWORD, Q_WORD, Q_POS, Q_DEFINITION, Q_SENTENCE, Q_ROOTWORD)

  numitems = 0
  numrows  = len(textlist)
  for row_index, r in enumerate(textlist):
    if row_index < numrows-1:
      # print row_index, numrows
      nextrow = textlist[row_index+1]
      # print "row :",r
      # print "Nextrow :",nextrow

    if r[0].rstrip(" ").lower() == ("item" or '"item"'):
      idict = {}
      for index, element in enumerate(r):
        element = element.replace('"','')
        if f_type == "multipleChoice":
          if element in MULTIPLECHOICE_PROPERTIES:
            add_to_dict(idict,element,r,index) #will add the token next to curr index        
        if f_type == "vocabulary":
          if element in VOCAB_PROPERTIES:
            add_to_dict(idict,element,r,index) #will add the token next to curr index        
            
        if two_lines:      
          for ind, el in enumerate(nextrow):
            el = el.replace('"','')
            if f_type == "multipleChoice":
              if el in MULTIPLECHOICE_PROPERTIES:
                add_to_dict(idict,el,nextrow,ind) #will add the token next to curr index        
            if f_type == "vocabulary":
              if el in VOCAB_PROPERTIES:
                add_to_dict(idict,el,nextrow,ind) #will add the token next to curr index           
  
      if(validate_item_dictionary_for_format(f_type,idict)== 1):
        dictslist.append(idict)
        numitems+=1

  logging.info("Number of item dictionaries: %d" % numitems)
  return dictslist # a list of idicts



def createADictWithListMetadata(title, tags, desc, lformat = "vocabulary", sharing = "public"):

  ldict = {}
  newList = []
  
  # Usage addElementToDict(identifier, ldict,kw,el) in om_utils
  addElementToDict("list", ldict, "format", lformat)
  addElementToDict("list", ldict, "title", title)
  addElementToDict("list", ldict, "sharing", sharing)
  addElementToDict("list", ldict, "tags", tags)
  addElementToDict("list", ldict, "description", desc)

  # create a new list
  print ldict
  return ldict


def  write_to_file(fname, string):

  fo = open(fname, "a+") #append
  fo.write(string)
  fo.close()


def  write_object_to_file(fname, obj):

  fo = open(fname, "a+") #append
  fo.write("\n\n\n\n")
  for o in obj:
    #for k,v in o.items():
    try:
      fo.write(o["word"] + ": " + o["defn"] + "\n")
    except Exception, e:
      print "unprintable char", e


  fo.close()
