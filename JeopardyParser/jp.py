'''
A Python script to read Jeopardy J!Archive files
Parses the XML files using BeautifulSoup
Creates dictionaries
Then calls the OpenMinds API and creates Lists

Author: Ram Narasimhan
(Using OpenMinds API code authored by Adam Stepinski)
'''

import logging
import oauth2
import os
os.system("cls")    #Windows based systems us
import time
import httplib
import urllib
import sys

import string
import math

import gflags
#NLTK related imports
import re
import enchant
from nltk.corpus import wordnet as wn

from bs4 import BeautifulSoup
from unidecode import unidecode
from web_util import encode_json, decode_json


import cfg
from text_utils import *
from om_utils import *
from om_client import *
from webList_to_OM import *
#Steps:
#1. Read the relevant file(s)
#2. Parse XML Using BeautifulSoup
#3. Form Dicts of Lists and Items
#4. Create OM Lists
#5. Record the creations in a separate file

logging.basicConfig(level=logging.DEBUG, filename='jt.log')
logging.basicConfig(level=logging.INFO, filename='jt.log')
logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)
 
def  create_category_List(soup,catflag=None):
    categories = [None]*14
    categories[0]= "zero offset"
    ctemp = [] #just a "bag" of categories names
    index = 0
    # extract category names
    for index, catname in enumerate(soup(class_="category_name")):
        # print catname
        ctg = remove_italics_html_tag(catname.get_text())
        ctg = remove_backslash_apostrophe(ctg)
        ctemp.append(ctg)

    if catflag is None:
        categories = ctemp
    else:
        for c in xrange(1,14):        
            if catflag[c]==1:
                categories[c] = ctemp.pop(0)

        if catflag[13] == 1:
            categories[13] = "Final Jeopardy: " + str(categories[13])


    print index, "Categories found in soup"    
    return categories


def extract_jeopardy_items_from_soup(soup):
    '''
    
    Given a BeautifulSoup object that has read a JArchive file, this function extracts relevant fields such as: Question, Answer, Dollar Value of the question, and Category
    '''

    numResponses=0
    numQuestions=0
    divWithCorrectResponses = []
    divWithQuestions = []
  
    question=[]
    correctAnswer=[]
    clueIDstring=[]
    cat= [0]*61
    dv = [0]*61
    catflag = [0]*14

# d in the following is a tag with attrs.
# the attrs of interest are onmouseover and onmouseout. 
# we use regexes to snip out the useful bits, and create a list out of those


    for d in soup.findAll('div'):
        try:
            divWithCorrectResponses.append(d['onmouseover'])
            numResponses+= 1
        except:
            pass

        try:
            divWithQuestions.append(d['onmouseout'])
            numQuestions+= 1
        except:
            pass
          
    print numResponses, numQuestions
    if(numResponses != numQuestions):
        print "Q and A's don't line up!"

    numA=0
    numQ=0


    # Parse the Answers
    for cr in divWithCorrectResponses:
        clueID = re.match("toggle.\'(.*)', 'c" ,cr,re.IGNORECASE)
        ansSearch = re.search('toggle.*stuck.*_response.*">(.*)</em>', cr, re.IGNORECASE)
        if ansSearch:
            numA+=1
            # print clueID.group(1), "A..", ansSearch.group(1)
            ans = remove_italics_html_tag(ansSearch.group(1))
            ans = remove_backslash_apostrophe(ans)
            ans = remove_br_slash_tag(ans)
            correctAnswer.append(ans)
            clueIDstring.append(clueID.group(1))

    # Parse the questions
    for cr in divWithQuestions:
        clueID = re.match("toggle.\'(.*)', 'c" ,cr,re.IGNORECASE)
        qSearch = re.search("toggle.*stuck., .(.*)..$", cr, re.IGNORECASE)
        if qSearch:
            numQ+=1
          # print clueID.group(1), "Q...", qSearch.group(1)
            qu = remove_italics_html_tag(qSearch.group(1))
            qu = remove_backslash_apostrophe(qu)
            qu = remove_br_slash_tag(qu) #textutils get rid of <br />
            #print numQ, qu
            question.append(qu)


    # extract cat and dv from clue category (J 1-6, DJ 7-12, FJ=13) int
    for index, clstr in enumerate(clueIDstring):
        #print clstr
        fj = re.search("_FJ" ,clstr, re.IGNORECASE)     #_J_ _DJ_ _FJ
        if fj:
            cat[index] = 13 #FJ
            dv[index] = 5000
        else: 
            categ = re.search("_DJ_(\d)_(\d)" ,clstr, re.IGNORECASE)     #_DJ_
            if categ:
                cat[index] = 6 + int(categ.group(1))
                dv[index] = 400 * int(categ.group(2))
            else: 
                jcateg = re.search("_J_(\d)_(\d)" ,clstr, re.IGNORECASE)     #_DJ_
                if jcateg:
                    cat[index] = int(jcateg.group(1))
                    dv[index] = 200* int(jcateg.group(2))


    #catflag is a 0/1 array that indicates whether a categorynumber is present.
    # which category numbers (1-13) exist, and which ones don't                
    for c in cat:
        catflag[c] = 1
    catflag[0] = sum(catflag)-1 #store numcats in the 0th place

    #create the categories list
    categories = create_category_List(soup,catflag)

    print "A,Q ", numA, numQ
    if(numA != numQ):
        print "Q and A's don't match up!"

    # put it all together into one List of dicts
    idictsList = []
    for index, q in enumerate(question):                 
#        print index, clueIDstring[index], dv[index], categories[cat[index]].upper(), question[index], correctAnswer[index].upper()
#        qstr = question[index]+" $"+ str(dv[index]) + " [" + categories[cat[index]].upper() + "]"
        qstr = question[index]
        
        if dv[index] != 0:
            qstr = qstr + " $"+ str(dv[index]) 
        else:
            print "no dv found"

        if cat[index]:
            #print "idx, cat", index, cat[index], categories[cat[index]]
            qstr = qstr + " ["+ categories[cat[index]].upper() + "]"

        iDict = {}
        addElementToDict("vocab", iDict, "word", correctAnswer[index].upper())
        addElementToDict("vocab", iDict, "defn", qstr)        
        idictsList.append(iDict)
    return idictsList


# This is a J Archive specific function
def mediaPresentInItem(iteminfo):
    '''
    Returns 1 if it is a "media question"
    '''
    p = r'j-archive.com/media' #the pattern as compiled regex object    
    if re.search(p, iteminfo["defn"], re.IGNORECASE):
        print "Media found"
        print
        print
        print
        return 1
    if re.search(p, iteminfo["word"], re.IGNORECASE):
        print "Media found"
        print
        print
        print
        return 1
    return 0

def extract_jeopardy_title(tstring):
    '''
    J! Archive - Show #5976, aired 2010-09-13
    '''

    splitpattern = "aired "
    try:
        title = "Jeopardy! Aired on " + tstring.split(splitpattern)[1]
    except:
        title = tstring
    return title


#1 tag is already there. Add 11 more, since only 12 are allowed
def  add_jeopardy_categories_as_tags(soup, tags):
    categories = create_category_List(soup)
    for ctg in categories:  
        if "final jeopardy" in str(unidecode(ctg)).lower(): #want the Final Jep categ to be the 2nd tag
            tags.insert(1,ctg)
        else:
            tags.append(str(unidecode(ctg)))    

    if len(tags) > 10:
        return(tags[:10])
    else:
        return tags



def create_list_jarchive_files_for_this_run(rawDirPath,startfile=0, endfile=0):
    # read the input directory path
    fileList=os.listdir(rawDirPath) #list of filenames
    print len(fileList), "files in all."

    if endfile==0: #not specified, so run for all the files
        endfile = len(fileList)

    fList = fileList[startfile:endfile+1]
    return fList



if __name__ == '__main__':

  argv = cfg.FLAGS(sys.argv)
  print argv
  if cfg.FLAGS.om_access_token:
      client = OpenMindsThreeLeggedClient(cfg.FLAGS.om_access_token, cfg.FLAGS.om_host)
  else:
      client = OpenMindsTwoLeggedClient(cfg.FLAGS.om_key, cfg.FLAGS.om_secret, cfg.FLAGS.om_host)

#####################
  RECORD_THE_ITEMS = True
  #run this in chunks
  startfile = 0  #first file is 0
  endfile = 231

  rawDirPath = r'C:\Users\Ram\Root-1\source\data\jeopardy\season26'
  #filename = os.path.join(rawDirPath,"game_id_3576") #3576 has prblems. look into it.


  title_base = "Jeopardy! Show"
  desc = "Lists of Jeopardy Questions in one episode of the show"
  fname = "jlists_created.txt" #just a running count of List ID's
  jsonfname = "jepQuestions.txt"


####################
  
  #logging.info("Me: %s" % client.get_user('me'))

  # Step 1 Read in the relevant files
  fileList = create_list_jarchive_files_for_this_run(rawDirPath,startfile,endfile)

  for index, f in enumerate(fileList):
      filename = os.path.join(rawDirPath,f)
      print "index:", startfile+index
      print "Now reading ", filename 


      # step 1 open the file
      f = open(filename) #set above

      # Step 2. Parse XML Using BeautifulSoup
      soup = BeautifulSoup(f, "html5lib")

      # Step 3. Form Dicts of Items
      # Create a List of Items Dictionaries
      itemDictsList = extract_jeopardy_items_from_soup(soup)

      # Step 4. Create a shell list
      title = extract_jeopardy_title(soup.title.string)
      tags = ["jeopardy-2009"]
      tags = add_jeopardy_categories_as_tags(soup, tags)
      ldict = createADictWithListMetadata(title, tags, desc, lformat = "vocabulary", sharing = "public") #omutils

      # ######## OPEN MINDS ###########
      # Step 5. Create OM List Shell
      if (cfg.FLAGS.debug_lvl == False): #not debug means create OM Lists
          newList =  client.create_list(ldict) # the OM list shell creation
          if isResponseErrorFree(newList)!=1:
              logging.warning("new List creation had errors.")
          try:
              lid= newList["id"]
              print "Creating a new List with ID: ", lid
          except ValueError, e:
              logging.warning("new List ID is incorrect")


      # step 6: Add all the items to this new List    
      numI =0
      goodItems =0
      numItemsinList = 0
      for iteminfo in itemDictsList:
          numI += 1
          # print unidecode(iteminfo["word"]).upper(), " : ", unidecode(iteminfo["defn"])
          if not mediaPresentInItem(iteminfo): # media questions are not loaded to OM
              goodItems+=1
              if (cfg.FLAGS.debug_lvl == False): #not debug means create OM Lists      
                  try:
                      it = client.create_item(lid, iteminfo)
                      isResponseErrorFree(it) # will print out errors if any
                      numItemsinList += 1
                  except UnicodeDecodeError:
                      print("Bad character in item ", numI)

      print title, " is ready with ", goodItems, " items."
      print "-----------------------"

      # Step 6. Record the creations in two separate files
      if (cfg.FLAGS.debug_lvl == False): 
          print lid, title, numItemsinList
          string = lid + "| " + title + "| " + str(numItemsinList) + "\n"
          write_to_file(fname, string) #om_utils Store the ListIDs for later reference
         
      if RECORD_THE_ITEMS:
          write_object_to_file(jsonfname, itemDictsList) #om_utils Store the JSON for creating other lists




      





