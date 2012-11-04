import bson
import json
from datetime import datetime
import re
import time
import web
import copy

def encode_json(json_object):

  json_str = json.dumps(json_object, separators=(',', ':'))
  # TODO: revisit how to escape unicode. I commented this out for now
  # because it unescapes quotes and causes invalid json.
  #json_str = unicode(json_str, 'unicode-escape')
  return json_str.encode('ascii', 'xmlcharrefreplace')


def decode_json(json_str):
  return json.loads(json_str)


def get_current_time():
  '''
  Returns the current datetime object, with milliseconds set to 0.
  '''
  now = datetime.now()
  return datetime(
      now.year, now.month, now.day, now.hour, now.minute, now.second)


def error_response(status):
  if status == 400:
    web.ctx.status = '400 Bad Request'
    return encode_json({'error': 'Input is malformed.'});
  elif status == 401:
    web.ctx.status = '401 Unauthorized'
    return encode_json({'error': 'Use is not authorized for this request.'})
  elif status == 404:
    web.ctx.status = '404 No Content'
    return encode_json({'error': 'User does not exist.'})
  elif status == 500:
    web.ctx.status = '500 Internal Server Error'
    return encode_json({'error': 'Internal server error.'})
  else:
    return encode_json({'error': 'Generic error.'})

