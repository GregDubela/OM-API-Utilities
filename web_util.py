import bson
import json
from datetime import datetime
import re
import time
import web
import copy

HEX_NUMBER_RE = re.compile('^[0-9a-fA-F]+$')

def parse_int_param(param, default):
  try:
    return int(param)
  except:
    return default


def parse_int_param_as_bool(param):
  '''
  Returns True if the param is defined and equal to 1. Otherwise, returns False.
  '''
  return parse_int_param(param, 0) == 1

def is_hex_number_string(test_string):
  """
  Return True if this is a legit hex number in string form.
  """
  if test_string is None:
    return False
  if not isinstance(test_string, str):
    if not isinstance(test_string, unicode):
      return False
  test_string = str(test_string)
  if HEX_NUMBER_RE.search(test_string):
    return True
  return False


def is_object_id(test_string):
  """
  Return True if this string is a legit object id.
  """
  try:
    id = bson.objectid.ObjectId(test_string)
    return True
  except:
    return False

def create_query_string(params, skip_list=None):
  '''
  Creates a query string from the given dictionary. Optionally skip
  certain parameters.

  Arguments:
    params -- Dictionary of param/values.
    skip_list -- List of params to leave out of the query stirng.
  '''
  params = copy.copy(params)
  if skip_list:
    for skip_param in skip_list:
      if skip_param in params:
        del params[skip_param]
  return '&'.join(['%s=%s' % (k, v) for k, v in params.iteritems() if v is not None])


def get_config_value(config_key, config, override_config_key='allow_overrides'):
  '''
  Returns the build config value for the given key. If the build
  config allows for overrides, and the key is specified as a query parameter,
  return the override value instead.
  '''
  params = web.input()
  allow_overrides = config[override_config_key]
  if allow_overrides and config_key in params:
    value = parse_int_param_as_bool(params[config_key])
  else:
    value = config[config_key]
  return value


def get_locales():
  """
  Returns a list of locales.  Each locale may be of the form:
    ln : two letter code for language.
    ln-lo: two letter code for language plus two letter code for locale.
  They will always be lowercase.
  The returned list is sorted by preference, from most to least preferred.
  """
  # FIXME(dbanks)
  # Later we could add cgi args to override this: for now, just use
  # the default language settings of the browser.
  if web.ctx.env.has_key('HTTP_ACCEPT_LANGUAGE'):
    locale_string = web.ctx.env['HTTP_ACCEPT_LANGUAGE'].lower()
    pieces = locale_string.split(',');
    scored_locales = []
    for piece in pieces:
      bits = piece.split(';')
      if len(bits) < 2:
        score = 1.0
      else:
        score = float(bits[1].split('=')[1])
      scored_locales.append([bits[0], score])
    sorted_locales = sorted(scored_locales, key=lambda scored_locale:-scored_locale[1])
    locales = []
    for sl in sorted_locales:
      locales.append(sl[0])
  else:
    locales = []

  params = web.input(use_locale=None)
  if params.use_locale:
    locales.insert(0, params.use_locale)

  return locales


def is_mobile_user_agent():
  return 'mobile' in web.ctx.env['HTTP_USER_AGENT'].lower()


def is_webkit():
 return 'webkit' in web.ctx.env['HTTP_USER_AGENT'].lower()


def is_ie():
 return 'MSIE' in web.ctx.env['HTTP_USER_AGENT']


def has_chromeframe():
  return 'chromeframe' in web.ctx.env['HTTP_USER_AGENT']


def is_ie_without_chromeframe():
  return is_ie() and (not has_chromeframe())


def encode_json(json_object):

  json_str = json.dumps(json_object, separators=(',', ':'))
  # TODO: revisit how to escape unicode. I commented this out for now
  # because it unescapes quotes and causes invalid json.
  #json_str = unicode(json_str, 'unicode-escape')
  return json_str.encode('ascii', 'xmlcharrefreplace')


def decode_json(json_str):
  return json.loads(json_str)


def to_timestamp(datetime_object):
  '''
  Returns a numeric timestamp for the given datetime object.
  Returned value is seconds-since-epoch.
  '''
  return int(time.mktime(datetime_object.timetuple()))


def now_timestamp():
  '''
  Returns a numeric timestamp for 'right now'
  Returned value is seconds-since-epoch.
  '''
  datetime_object = datetime.now()
  return to_timestamp(datetime_object)


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

