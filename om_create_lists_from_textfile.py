'''
A utility to CREATE OM Lists using the API
Reads all the csv files in a directory. Tries to create one list per file.

Adapted from Adam's version by Ram Narasimhan
'''

import logging
import oauth2
import os
import re
import time
import httplib
import sys
import csv
from libraries.python.web_util import encode_json, decode_json
import gflags
from om_utils import *
import cfg


logging.basicConfig(level=logging.DEBUG, filename='omapiUtils.log')
logging.basicConfig(level=logging.INFO, filename='omapiUtils.log')
logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)
# http://antonym.org/2005/03/a-real-python-logging-example.html is very good

#It is important to use the right severity levels when you write you log calls. I tend to use INFO for generally useful stuff that I like to see traced while developing, but not at runtime, while I reserve DEBUG for the extra detailed information that is only useful when something is going wrong. The WARNING and lower I always have on at runtime, and in production are sent to an operator console.


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
      return self._get_json('POST', '/api/lists/', info)

  # added by Ram. 
  def delete_list(self, list_id):
    return self._get_json('DELETE', '/api/data/lists/%s/' % list_id)



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


def   count_number_of_occurrences(reg,textlist):

    nummatch=0
    for r in textlist:
        str1 = ''.join(str(e) for e in r) #convert row to a string
        if re.match(reg,str1) != None:
            nummatch+= 1
    return nummatch


def create_OMList_from_file(fname):
    '''
    Read a CSV file. Create JSONs for the List Header
    Create JSONs for items. Create the list. Add the items.
    '''
    newList = []

    textlist = read_all_csv_lines(fname)
    print "Lists occurences:", count_number_of_occurrences('^[L|l]ist',textlist)
    print "Item occurences:", count_number_of_occurrences('^[I|i]tem',textlist)

    # one list dictionary for just the properties
    ld = create_list_dict(textlist) # in om utils

    try:
        listType = ld["format"]
        print "list of type: ", listType
        # one dictionary for each item
    except Exception, e:
        logging.warning('Format type not specified. Aborting this file. %s \n' % fname)
        return newList

    idictsList = create_item_dicts(textlist, listType, two_lines=False) #om_utils

    # create a new list
    print ld
    newList =  client.create_list(ld) # the actual list shell creation

    # test for "error"
    if isResponseErrorFree(newList)!=1:
        return []

    # double checking
    try:
        lid= newList["id"]
    except ValueError, e:
        logging.warning("new List ID is incorrect. Aborting this file %s \n" % fname)

    # create new items
    for iteminfo in idictsList:
        logging.info(iteminfo)
        it = client.create_item(lid,iteminfo)
        isResponseErrorFree(it) # will print if there is error

    return newList




if __name__ == '__main__':

  argv = cfg.FLAGS(sys.argv)
  print argv
  if cfg.FLAGS.om_access_token:
    client = OpenMindsThreeLeggedClient(cfg.FLAGS.om_access_token, cfg.FLAGS.om_host)
  else:
    client = OpenMindsTwoLeggedClient(cfg.FLAGS.om_key, cfg.FLAGS.om_secret, cfg.FLAGS.om_host)
  
  logging.info("Me: %s" % client.get_user('me'))

  #read the input directory path
  currdir =  os.getcwd()
  dirpath = os.path.join(currdir, cfg.FLAGS.directory)

  #print out all the csv files in that directory
  logging.info("Directory to Read...%s \n" % dirpath)

  #read the input directory path
  rawDirPath = r'C:\Documents and Settings\u163202\crossword\data\jeopardy\season27'
  filename = os.path.join(rawDirPath,"chemistry_1")
  f = open(filename)

  dirList=os.listdir(dirpath) #list of filenames
  for fname in dirList:
      if filenameendsin(fname,"csv"):
          filename = os.path.join(dirpath,fname)
          logging.info("Trying to create List from %s \n\n" % filename)
          newList = create_OMList_from_file(filename)
          if newList:
              print "Status of new List: OK"
              print
          else:
              print "Skipped"
              print


# Neat trick to switch between dev and prod from command line
# if len(sys.argv) > 2 and sys.argv[2] == 'dev':
#    web.config.debug = True
#    web.config.debug = False
