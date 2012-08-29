'''
Module for connecting Python code to the OpenMinds API.

Adapted from Adam's version by Ram Narasimhan
'''

import oauth2
import time
import httplib
import sys
from libraries.python.web_util import encode_json, decode_json

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

