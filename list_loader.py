'''
Library for Accessing the OpenMinds API from Python.
Provides two methods of accessing the OpenMinds API:
- Using a user's API key and API secret. This is how
  an individual should access the API to get their own data.
- Using an oAuth access token. This is how an app should access
  the API on behalf of a user that has granted API access to the app.

Adapted from Adam's version by Ram Narasimhan
'''

import gflags
import oauth2
import time
import httplib
import sys
import csv
from libraries.python.web_util import encode_json, decode_json
import om_utils 

DEFAULT_HOST = 'openminds.io'

FLAGS = gflags.FLAGS
gflags.DEFINE_string('om_host', DEFAULT_HOST, 'OpenMinds Host')

gflags.DEFINE_string('om_key', '', 'OpenMinds API user key. Used by an individual to access the OpenMinds API.')
gflags.DEFINE_string('om_secret', '', 'OpenMinds API user secret. Used by an individual to access the OpenMinds API.')

gflags.DEFINE_string('om_access_token', '', 'OpenMindsAPI access token. Used by an app to access the OpenMinds API on behalf of a user. If this flag is defined, om_key and om_secret are ignored.')


class AbstractOpenMindsClient(object):
  '''
  Abstract OpenMindsClient class. Subclasses should implement the _api_response()
  method, which should return the response from an HTTPConnection object.
  '''

  def __init__(self, host=None):
    if host:
      self.host = host
    else:
      self.host = DEFAULT_HOST
    
  def _api_response(self, method, path, body={}):
    '''
    Implemented by subclasses. Should return a response
    from an HTTPConnection object.
    '''
    return None

  def _get_json(self, method, path, body={}, params={}):
    response = self._api_response(method, path, body, params).read()
    return decode_json(response)

  def get_users(self):
    return self._get_json('GET', '/api/data/users/')

  def get_user(self, user_id):
    return self._get_json('GET', '/api/data/users/%s/' % user_id)

  def update_user(self, user_id, info):
    return self._get_json('PUT', '/api/data/users/%s/' % user_id, info)

  def create_user(self, info):
    return self._get_json('POST', '/api/data/users/', info)

  def get_class(self, class_id):
    return self._get_json('GET', '/api/data/classes/%s/' % class_id)

  def update_class(self, class_id, info):
    return self._get_json('PUT', '/api/data/classes/%s/' % class_id, info)

  def create_class(self, info):
    return self._get_json('POST', '/api/data/classes/', info)

  def get_lists(self, params={}):
    return self._get_json('GET', '/api/data/lists/', params=params)

  def get_list(self, list_id):
    return self._get_json('GET', '/api/data/lists/%s/' % list_id)

  def update_list(self, list_id, info):
    return self._get_json('PUT', '/api/data/lists/%s/' % list_id, info)

  def create_list(self, info):
    return self._get_json('POST', '/api/data/lists/', info)

  def get_item(self, list_id, item_id):
    return self._get_json('GET', '/api/data/lists/%s/%s/' % (list_id, item_id))

  def update_item(self, list_id, item_id, info):
    return self._get_json('PUT', '/api/data/lists/%s/%s/' % (list_id, item_id), info)

  def create_item(self, list_id, info):
    return self._get_json('POST', '/api/data/lists/%s/' % list_id, info)

  def get_assignment(self, assignment_id):
    return self._get_json('GET', '/api/data/assignments/%s/' % (assignment_id))

  def update_assignment(self, assignment_id, info):
    return self._get_json(
        'PUT',
        '/api/data/assignments/%s/' % (assignment_id),
        info)

  def create_assignment(self, info):
    return self._get_json('POST', '/api/data/assignments/', info)

  def get_assignment_template(self, assignment_template_id):
    return self._get_json(
        'GET',
        '/api/data/assignment_templates/%s/' % (assignment_template_id))

  def update_assignment_template(self, assignment_template_id, info):
    return self._get_json(
        'PUT',
        '/api/data/assignment_templates/%s/' % (assignment_template_id),
        info)

  def create_assignment_template(self, info):
    return self._get_json('POST', '/api/data/assignment_templates/', info)


class OpenMindsTwoLeggedClient(AbstractOpenMindsClient):
  '''
  Client to access the OpenMinds API using oAuth two-legged authentication. The
  user provides an API key and API secret, which are used to securely sign the
  request.
  '''
  def __init__(self, key, secret, host=None):
    AbstractOpenMindsClient.__init__(self, host)
    self.key = key
    self.secret = secret

  def _get_request(self, method, path, body='', extra_params={}):
    consumer = oauth2.Consumer(self.key, self.secret)
    params = {
      'oauth_version': "1.0",
      'oauth_nonce': oauth2.generate_nonce(),
      'oauth_timestamp': int(time.time())
    }
    params.update(extra_params)

    if method == 'POST':
      params['data'] = body

    url = 'http://' + self.host + path
    req = oauth2.Request(method=method, url=url, body='', parameters=params)
    signature_method = oauth2.SignatureMethod_HMAC_SHA1()
    req.sign_request(signature_method, consumer, None)
    return req

  def _api_response(self, method, path, body={}, params={}):
    '''
    Signs the request using the oauth2 library.
    '''
    str_body = encode_json(body)
    req = self._get_request(method, path, str_body, extra_params=params)
    data = req.to_postdata()

    connection = httplib.HTTPConnection(self.host)
    if self.host.startswith('localhost') and method == 'POST':
      # Workaround for sending api POST requests to local server.
      connection.request(method, path, data)
    else:
      connection.request(method, path + '?' + data, str_body)
    return connection.getresponse()

  def get_game_url(self, game_id, list_id, params):
    path = '/game/%s/%s/' % (game_id, list_id)
    req = self._get_request('GET', path, extra_params=params)
    return '%s%s?%s' % (self.host, path, req.to_postdata())


class OpenMindsThreeLeggedClient(AbstractOpenMindsClient):
  '''
  Client to access the OpenMinds API using oAuth three-legged authentication.
  We assume the user has already obtained an API access token by granting
  an app access through the web interface. The access token is used by the app
  to get access to the API on behalf of the user.
  '''
  def __init__(self, access_token, host=None):
    AbstractOpenMindsClient.__init__(self, host)
    self.access_token = access_token

  def _api_response(self, method, path, body=None):
    '''
    Includes the access token as a header in the request.
    '''
    connection = httplib.HTTPConnection(self.host)
    if body:
      data = encode_json(body)
    else:
      data = None
    headers = {
      'X-OpenMinds-Access-Token': self.access_token
    }
    if method == 'GET':
      if data:
        path += '?' + data
      connection.request(method, path, None, headers)
    else:
      connection.request(method, path, data, headers)
    return connection.getresponse()



# word || The item word.
# pos|| The item part-of-speech.
# defn|| The item definition.
# sentence || An example sentence using the item word.
# otherWords || Alternate words. Array of strings, maximum number of words is 5.
# parts || The item word broken down into parts. Array of strings, maximum number if parts is 5.
def  create_item_dicts(textlist):
  '''
  Each line in CSV file is a new item. It has to have its mandatory fields
  and optionally, any of the other item properties for that list format
  '''

  dictslist = []


  WORD = 'word'
  POS = 'pos'
  DEFINITION = 'defn'
  SENTENCE = 'sentence'
  ITEM_PROPERTIES = (WORD,POS, DEFINITION,SENTENCE)

  for r in textlist:
    print r
    if r[0].rstrip(" ").lower() =="item":
      idict = {}
      for index, el in enumerate(r):                
        if el in ITEM_PROPERTIES:
          om_utils.add_to_dict(idict,el,r,index) #will add the token next to curr index        

      if not WORD in idict:
        print("WORD  property not specified in CSV. ITEM  cannot be created without this mandatory field")
      if not DEFINITION in idict:
        print("DEFN  property not specified in CSV. ITEM  cannot be created without this mandatory field")

      dictslist.append(idict)


  return dictslist # a list of idicts


def create_list_dict(allRows):
    '''
    Read all lines that begin with List and if a format is found, store it.
    Return False if there is no format, or if format is unrecognized
    '''
    ldict = {}
# title || Name of the list || 
# description || Short list description.
# standard || String code representing the list standard. Example: "L.7.2".
# section || Numerical sub-section of the standard.

    TITLE = 'title'
    DESCRIPTION = 'description'
    FORMAT = 'format'
    GRADE = 'grade'
    SECTION = 'section'
    STANDARD = 'standard'
    DUMMY = 'dummy12sger434'
    LIST_PROPERTIES = (TITLE, DESCRIPTION, FORMAT,SECTION,STANDARD)
    LIST_INTEGER_PROPERTIES = (GRADE, DUMMY)

#    if not 'format' in row:
#        print('Format type must be specified for new lists.')
    



#    print("useful lines in List file",  len(allRows))
    for row in allRows:
#        print row[0]
        if row[0].rstrip(" ").lower() == "list":
            for index, item in enumerate(row):                
                if item in LIST_PROPERTIES:
                  om_utils.add_to_dict(ldict,item.lower(),row,index) #will add the token next to curr index
                            
                # grade || Intended grade level of the list. Number between 0 (K) and 8.
                if item in LIST_INTEGER_PROPERTIES:
                  # print("item %s" % item)
                  om_utils.add_to_dict_as_int(ldict,item.lower(),row,index)

    if not "format" in ldict:
      print("List format property not specified in CSV. List cannot be created without this mandatory field")


    return ldict
                        



if __name__ == '__main__':
  '''
  Simple test for the API.
  '''
  argv = FLAGS(sys.argv)
  print argv
  print FLAGS.om_key, FLAGS.om_secret

  print FLAGS.om_host
  if FLAGS.om_access_token:
    client = OpenMindsThreeLeggedClient(FLAGS.om_access_token, FLAGS.om_host)
  else:
    client = OpenMindsTwoLeggedClient(FLAGS.om_key, FLAGS.om_secret, FLAGS.om_host)

#  print client.get_user('me')
  print client.get_users()
#  print(userinfo["username"])
  

#  print client.get_users()
#  print client.get_lists({"num":1})
#  print client.get_lists({"search":"created"})
#  print client.update_user("4fd1269037eaef23070024e7", {"name":"ramtestupdated"} )

  # read in the CSV File (skip header row)

  ld = {}

  textlist = om_utils.read_all_csv_lines()       

  #one list dictionary
  ld = create_list_dict(textlist)

  #one dictionary for each item
  idictsList = create_item_dicts(textlist)

  # create a new list
  newlist =  client.create_list(ld)
  print newlist

  # check if the list was successfully created.
  if "success" in newlist:
    print "List Creation failed"
    print "Exiting Script"
    sys.exit()


  print("New list successfully created")    
  #get the ID of the newly created List
  lid= newlist["id"]
    
#  iteminfo = {"word":"tuber"}

# /data/lists/4ec3c8642324d773c0000057/4f2c68a0d0ccd94e22000000
#create a new item


  for iteminfo in idictsList:
    print client.create_item(lid,iteminfo)




  # add each of the items to that list









## ------- notes follow

# gflags help http://python-gflags.googlecode.com/svn/trunk/gflags.py

# Any flags you don't feel like typing, throw them in a file, one flag per
# line, for instance:
#   --myflag=myvalue
#   --nomyboolean_flag
# You then specify your file with the special flag '--flagfile=somefile'.
# You CAN recursively nest flagfile= tokens OR use multiple files on the
# command line.  Lines beginning with a single hash '#' or a double slash
# '//' are comments in your flagfile.

