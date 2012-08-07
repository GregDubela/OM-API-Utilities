from auth import public_api_auth
from bson.objectid import ObjectId
from backend import Assignment, Class, User, List, Item, Event
from libraries.python.cors_util import add_cors_headers
from libraries.python.web_util import encode_json
from libraries.python.web_util import parse_int_param, parse_int_param_as_bool
from libraries.python.util import error_response
from api_util import OpenMindsAPIHandler
import adaptive_model
import json
import logging
import oauth
import pymongo
import web
import math

urls =(
  '/standards/?', 'StandardsHandler',
  '/lists/?', 'ListsHandler',
  '/lists/([^/]+)/?', 'ListHandler',
  '/samplings/([^/]+)/([^/]+)/?', 'SamplingsHandler',
  '/assignments/([^/]+)/?', 'AssignmentHandler',
  #'/classes/?', 'ClassesHandler',
  #'/classes/([^/]+)/?', 'ClassHandler',
)
app = web.application(urls, locals())

DEFAULT_NUM = 20
DEFAULT_PAGE = 1
SORT_OPTIONS = set(['total', 'avg', 'vol', 'dur', 'standards', 'lists', 'items'])
DEFAULT_SORT = 'items'
SORT_DIR_OPTIONS = set(['asc', 'desc'])
DEFAULT_SORT_DIR = 'desc'
FILTER_OPTIONS = set(['all', 'mastered', 'unmastered', 'struggling'])
DEFAULT_FILTER = 'all'


def parse_page_params(params):
  num_items = parse_int_param(params.num, DEFAULT_NUM)
  page = max(1, parse_int_param(params.page, DEFAULT_PAGE))
  skip_num = (page-1) * num_items
  return num_items, page, skip_num


def parse_sort_params(params):
  if not params.sort in SORT_OPTIONS:
    return None

  if params.sort_dir == 'asc':
    sort_dir = pymongo.ASCENDING
  elif params.sort_dir == 'desc':
    sort_dir = pymongo.DESCENDING
  else:
    sort_dir = pymongo.DESCENDING

  if params.sort == 'total':
    sort = [('totalOutcomes', sort_dir)]
  elif params.sort == 'avg':
    sort = [('average', sort_dir)]
  elif params.sort == 'vol':
    sort = [('volatility', sort_dir)]
  elif params.sort == 'dur':
    sort = [('duration', sort_dir)]
  elif params.sort == 'standards':
    sort = [('standard', sort_dir)]
  elif params.sort == 'lists':
    sort = [('listId', sort_dir)]
  elif params.sort == 'items':
    sort = [('itemId', sort_dir)]
  else:
    sort = None
  return sort

def get_mastery_spec(mastery_param):
  if not mastery_param in FILTER_OPTIONS:
    return {
      'totalOutcomes': {'$gte': 0},
    }
  if mastery_param == 'all':
    spec = {
      'totalOutcomes': {'$gte': 0},
    }
  elif mastery_param == 'mastered':
    spec = {
      'totalOutcomes': {'$gte': adaptive_model.MIN_TOTAL_OUTCOMES_FOR_MASTERY},
      'average': {'$gte': adaptive_model.MIN_AVERAGE_FOR_MASTERY},
      'volatility': {'$lte': adaptive_model.MAX_VOLATILITY_FOR_MASTERY},
    }

  elif mastery_param == 'unmastered':
    spec = {
      'totalOutcomes': {'$gte': adaptive_model.MIN_TOTAL_OUTCOMES_FOR_MASTERY},
      '$or': [
        {'average': {'$lt': adaptive_model.MIN_AVERAGE_FOR_MASTERY}},
        {'volatility': {'$gt': adaptive_model.MAX_VOLATILITY_FOR_MASTERY}},
      ]
    }
  elif mastery_param == 'struggling':
    spec = {
      'totalOutcomes': {'$gte': 10},
      'average': {'$lt': 0.6},
      'volatility': {'$gte': adaptive_model.MAX_VOLATILITY_FOR_MASTERY},
    }
  else:
    spec = {}
  return spec


def create_response(
    num_items, has_next_page, page,
    sort, sort_dir,
    mastery_param, data):
  formatted_data = [i.formatted_dict(include_mastery_score=True) for i in data]
  
  meta_data = {
    'num': num_items,
    'page': page,
    'sort': sort,
    'sortDir': sort_dir,
    'mastery': mastery_param,
    'hasNextPage': has_next_page,
  }
  return meta_data, formatted_data


def get_standards_stats(auth_user, params):
  num_items, page, skip_num = parse_page_params(params)
  sort = parse_sort_params(params)

  spec = {'userId': auth_user._id}
  spec.update(get_mastery_spec(params.mastery))
  stats = list(adaptive_model.UserStandardInfo.collection.find(
      spec, limit=num_items+1, skip=skip_num, sort=sort))
  if len(stats) == num_items + 1:
    has_next_page = True
    # Trim list back to requested size.
    stats = stats[:num_items]
  else:
    has_next_page = False

  return create_response(
      num_items, has_next_page, page,
      params.sort, params.sort_dir,
      params.mastery, stats)


def get_lists_stats(auth_user, params):
  # Find lists that match the list filtering
  list_spec = {'deleted': False}
  grade = parse_int_param(params.grade, None)
  section = parse_int_param(params.section, None)
  if grade is not None:
    list_spec['grade'] = grade
  if params.standard is not None:
    list_spec['standard'] = params.standard
    # Only add the section to the spec if a standard is also defined.
    if params.section is not None:
      list_spec['section'] = section
  try:
    item_lists = List.collection.find(list_spec, {'_id': 1})
    list_ids = [l._id for l in item_lists]
  except Exception, e:
    logging.error(e)
    return error_response(500)

  # Find List stats for the appropriate lists.
  num_items, page, skip_num = parse_page_params(params)
  sort = parse_sort_params(params)
  spec = {'userId': auth_user._id, 'listId': {'$in': list_ids}}
  spec.update(get_mastery_spec(params.mastery))
  stats = list(adaptive_model.UserListInfo.collection.find(
      spec, limit=num_items+1, skip=skip_num, sort=sort))
  if len(stats) == num_items + 1:
    has_next_page = True
    # Trim list back to requested size.
    stats = item_stats[:num_items]
  else:
    has_next_page = False

  return create_response(
      num_items, has_next_page, page,
      params.sort, params.sort_dir,
      params.mastery, stats)


def get_items_stats(auth_user, item_ids, params):
  num_items, page, skip_num = parse_page_params(params)
  sort = parse_sort_params(params)

  spec = {'userId': auth_user._id, 'itemId': {'$in': item_ids}}
  spec.update(get_mastery_spec(params.mastery))

  item_stats = list(adaptive_model.UserItemInfo.collection.find(
      spec, limit=num_items+1, skip=skip_num, sort=sort))
  if len(item_stats) == num_items + 1:
    has_next_page = True
    # Trim list back to requested size.
    item_stats = item_stats[:num_items]
  else:
    has_next_page = False

  (meta_data, formatted_data) = create_response(
      num_items, has_next_page, page,
      params.sort, params.sort_dir,
      params.mastery, item_stats)

  return (meta_data, formatted_data)


def get_sampling_stats(auth_user, list_id, app_id, num_samples):
  spec = {'userId': auth_user._id,
          'listId': list_id,
          'appId': app_id}
  raw_data = list(adaptive_model.SamplingSummary.collection.find(
    spec, limit=num_samples, sort=[('timestamp',-1)]))
  # All of the samples have the same listId, appId, userId: we don't need
  # that info in each sample.
  formatted_data = \
    [i.formatted_dict(['listId', 'appId', 'userId']) for i in raw_data]
  return formatted_data


class StandardsHandler(OpenMindsAPIHandler):
  @add_cors_headers
  @public_api_auth
  def GET(self, auth_user=None, auth_app_id=None):
    params = web.input(
      num=DEFAULT_NUM,
      page=DEFAULT_PAGE,
      sort=DEFAULT_SORT,
      sort_dir=DEFAULT_SORT_DIR,
      mastery=DEFAULT_FILTER)
    meta_data, stats = get_standards_stats(auth_user, params)
    return encode_json(stats)


class ListsHandler(OpenMindsAPIHandler):
  @add_cors_headers
  @public_api_auth
  def GET(self, auth_user=None, auth_app_id=None):
    params = web.input(
      grade=None,
      standard=None,
      section=None,
      num=DEFAULT_NUM,
      page=DEFAULT_PAGE,
      sort=DEFAULT_SORT,
      sort_dir=DEFAULT_SORT_DIR,
      mastery=DEFAULT_FILTER)
    meta_data, stats = get_lists_stats(auth_user, params)
    return encode_json(stats)


class ListHandler(OpenMindsAPIHandler):
  @add_cors_headers
  @public_api_auth
  def GET(self, list_id, auth_user=None, auth_app_id=None):
    try:
      list_id = ObjectId(list_id)
    except Exception, e:
      logging.warn(e)
      return error_response(400, 'Not a valid list id')

    try:
      item_list = List.collection.find_one({'_id': list_id, 'deleted': False})
      if not item_list:
        message = 'List does not exist'
        logging.warn(message)
        return error_response(404, message)
      item_ids = [ObjectId(i) for i in item_list.get('items', [])]
    except Exception, e:
      logging.error(e)
      return error_response(500, 'Server Error')

    params = web.input(
      num=DEFAULT_NUM,
      page=DEFAULT_PAGE,
      sort=DEFAULT_SORT,
      sort_dir=DEFAULT_SORT_DIR,
      mastery=DEFAULT_FILTER)
    meta_data, stats = get_items_stats(auth_user, item_ids, params)
    return encode_json(stats)


class SamplingsHandler(OpenMindsAPIHandler):
  @add_cors_headers
  @public_api_auth
  def GET(self, raw_list_id, raw_app_id, auth_user=None, auth_app_id=None):
    try:
      list_id = ObjectId(raw_list_id)
    except Exception, e:
      logging.warn(e)
      return error_response(400, 'Not a valid list id')

    try:
      app_id = ObjectId(raw_app_id)
    except Exception, e:
      logging.warn(e)
      return error_response(400, 'Not a valid app id')

    try:
      params = web.input(num_samples=1)
      num_samples = parse_int_param(params.num_samples, 1)
      if num_samples <= 0:
        return error_response(400, 'Invalid num_samples param.')

      # We want the n most recent 'samplings' of this user in this
      # app with this list.
      samplings = get_sampling_stats(auth_user, list_id, app_id, num_samples)
      return encode_json(samplings)
    except Exception, e:
      logging.error(e)
      return error_response(500, 'Server Error')


class AssignmentHandler(OpenMindsAPIHandler):
  @add_cors_headers
  @public_api_auth
  def GET(self, assignment_id, auth_user=None, auth_app_id=None):
    try:
      assignment_id = ObjectId(assignment_id)
    except Exception, e:
      logging.warn(e)
      return error_response(400, 'Not a valid assignment id')

    try:
      assignment = Assignment.collection.find_one(
          {'_id': assignment_id, 'deleted': False})
      if not assignment:
        message = 'Assignment does not exist'
        logging.warn(message)
        return error_response(404, message)

      else:
        item_id_strs = assignment.get_item_ids()
      item_ids = [ObjectId(item_id_str) for item_id_str in item_id_strs]

    except Exception, e:
      logging.error(e)
      return error_response(500, 'Server Error')

    params = web.input(
      num=DEFAULT_NUM,
      page=DEFAULT_PAGE,
      sort=DEFAULT_SORT,
      sort_dir=DEFAULT_SORT_DIR,
      mastery=DEFAULT_FILTER)
    meta_data, stats = get_items_stats(auth_user, item_ids, params)
    return encode_json(stats)


class ClassesHandler(OpenMindsAPIHandler):
  @add_cors_headers
  @public_api_auth
  def GET(self, auth_user=None, auth_app_id=None):
    response = {'data': 'classes'}
    return encode_json(response)


class ClassHandler(OpenMindsAPIHandler):
  @add_cors_headers
  @public_api_auth
  def GET(self, class_id, auth_user=None, auth_app_id=None):
    response = {'data': 'class'}
    return encode_json(response)


class StudentHandler(OpenMindsAPIHandler):
  @add_cors_headers
  @public_api_auth
  def GET(self, class_id, student_id, auth_user=None, auth_app_id=None):
    response = {'data': 'student'}
    return encode_json(response)
