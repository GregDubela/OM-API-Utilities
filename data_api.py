from backend import Class, User, List, Item, Event, AssignmentTemplate, Assignment
from bson.errors import InvalidId
from bson.objectid import ObjectId
from common_core import CommonCore
from datetime import datetime
from libraries.python import cookies
from libraries.python.cors_util import add_cors_headers
from libraries.python.db_models import create_generic_document_from_data
from libraries.python.db_models import get_generic_document, ValidationError
from libraries.python.util import permute_indices_by_weight
from libraries.python.web_util import encode_json, decode_json
from libraries.python.web_util import parse_int_param, parse_int_param_as_bool
import logging
import util

from pymongo.errors import DuplicateKeyError
from libraries.python.util import error_response, HTTPError
from api_util import OpenMindsAPIHandler
import adaptive_model
from auth import login_optional, login_required
from auth import public_api_auth, private_api_auth
from auth import get_user_cookie, set_user_cookie
import json
import pymongo
import web
import littlelives_info

urls =(
  # SEMI-PRIVATE APIS
  '/authenticate/?', 'AuthenticateHandler',

  '/classes/?', 'ClassesHandler',
  '/classes/([^/]+)/?', 'ClassHandler',
  '/users/?', 'UsersHandler',
  '/users/([^/]+)/?', 'UserHandler',
  '/lists/?', 'ListsHandler',
  '/lists/([^/]+)/?', 'ListHandler',
  '/lists/([^/]+)/([^/]+)/?', 'ItemHandler',

  # ASSIGNMENTS
  '/assignment_templates/?', 'AssignmentTemplatesHandler',
  '/assignment_templates/([^/]+)/?', 'AssignmentTemplateHandler',
  '/assignments/?', 'AssignmentsHandler',
  '/assignments/([^/]+)/?', 'AssignmentHandler',

  # PRIVATE APIS
  '/events/?', 'EventsHandler',
  '/common_core/([^/]+)/?', 'CommonCoreHandler',

  '/littlelives/auth/?', 'LittleLivesAuthenticateHandler',
  '/littlelives/user_info/?', 'LittleLivesUsersHandler',

  # TEMP APIS
  '/leaderboard/?', 'LeaderboardHandler',
)
app = web.application(urls, locals())

def can_see_student_data(auth_user, student_user_id):
  """
  Can the authenticated user view data for this student?
  Optimal answer: yes, if user is student, teacher of student, or parent of
  student.
  FIXME(dbanks)
  For now, just say yes.
  """
  return True

def can_see_class_data(auth_user, class_id):
  """
  Can the authenticated user see data about this class?
  Yes, if user is creator of class or instructor of class.
  """
  class_spec = {
    '_id': class_id,
    '$or': {
      'creator': auth_user._id,
      'instructor': str(auth_user.id)
    }
  }
  class_item = Class.collection.find_one(class_spec)
  return class_item is not None


def get_lists(auth_user, params):
  num = parse_int_param(params.num, 50)
  grade = parse_int_param(params.grade, None)
  section = parse_int_param(params.section, None)
  if params.search in ('all', 'created'):
    search = params.search
  else:
    search = 'all'

  spec = {'deleted': False}
  if search == 'created':
    spec['creator'] = auth_user._id
  if grade is not None:
    spec['grade'] = grade
  if params.standard is not None:
    spec['standard'] = params.standard
    # Only add the section to the spec if a standard is also defined.
    if params.section is not None:
      spec['section'] = section

  item_lists = List.collection.find(spec).limit(num)
  return item_lists


def adaptive_sort_item_list(json_item_list, auth_user):
  """
  Sort the items in this list by order of 'adaptive learning desirability':
  A < B if we think given user should practice on A instead of B.
  """
  # Get any stats for this user and these items.
  item_ids = [ObjectId(item['id']) for item in json_item_list]
  spec = {'userId': auth_user._id, 'itemId': {'$in': item_ids}}
  item_stats = list(adaptive_model.UserItemInfo.collection.find(spec))

  # Make an array tying item json (what we will be returning) to any
  # known stats or scores,
  item_blobs = []
  for json_item in json_item_list:
    item_blob = {}
    item_blob['json'] = json_item
    item_blob['stat'] = None
    item_blob['masteryScore'] = -1
    for item_stat in item_stats:
      if str(item_stat.itemId) == json_item['id']:
        item_blob['stat'] = item_stat
        item_blob['masteryScore'] = item_stat.calculate_mastery_score()
        item_blob['masteryThreshold'] = item_stat.get_mastery_threshold()
        break

    item_blobs.append(item_blob)

  weights = adaptive_model.get_adaptive_weights(item_blobs)
  indices = permute_indices_by_weight(weights)
  new_json_list = []
  for index in indices:
    new_json_list.append(item_blobs[index]['json'])
    logging.debug("  " + item_blobs[index]['json'].get('word', 'word'))
    logging.debug("    weight:" + str(weights[index]))
    logging.debug("    MasteryScore:" + str(item_blobs[index]['masteryScore']))

  return new_json_list


class AuthenticateHandler(object):
  '''
  Handler to authenticate a user based on a username and password.
  '''

  def GET(self):
    '''
    Authenticates the user based on a username and password. If the
    authentication is successful, returns a JSON object containing a user id
    and the auth token. The auth token should be written to a cookie that gets
    sent on subsequent requests.
    '''
    params = web.input(username=None, password=None)
    if params.username == None or params.password == None:
      logging.warn('Missing username or password.')
      return error_response(400)

    try:
      user = User.collection.find_one(
          {'username': params.username, 'deleted': False})
    except Exception, e:
      logging.error(e)
      return error_response(500, 'Server Error')

    if not user:
      return error_response(401, 'Incorrect username')

    if not user.check_password(params.password):
      return error_response(401, 'Incorrect password')

    user_id = str(user._id)
    auth_token = set_user_cookie(user_id)
    response = {
      'id': user_id,
      'authToken': auth_token
    }

    return encode_json(response)


class ClassesHandler(OpenMindsAPIHandler):
  '''
  Handler for retrieving basic information about classes and creating
  new classes.
  '''

  @add_cors_headers
  @public_api_auth
  def GET(self, auth_user=None, auth_app_id=None):
    '''
    Returns a JSON array of basic information about classes owned
    by the authenticated user.
    '''
    spec = {
      'creator': auth_user._id,
      'deleted': False,
    }
    try:
      classes = Class.collection.find(spec)
      formatted_classes = [c.formatted_dict() for c in classes]
      return encode_json(formatted_classes)
    except Exception, e:
      logging.error(e)
      return error_response(500, 'Server Error')

  @add_cors_headers
  @public_api_auth
  def POST(self, auth_user=None, auth_app_id=None):
    '''
    Creates a new class and returns a JSON object containing the
    id for the new class.
    '''
    params = web.input(data=None)
    try:
      if params.data:
        data = decode_json(params.data)
      else:
        data = decode_json(web.ctx.data)
      Class.validate(data)
    except ValueError, e:
      logging.warn(e)
      return error_response(400, 'Could not parse JSON')
    except ValidationError, e:
      logging.warn(e)
      return error_response(400, e.error)

    try:
      school_class = Class()
      school_class.update_class(data)
      school_class.reset_code()
      school_class.set_creator(auth_user)
      school_class.save()
      response = {
        'id': str(school_class._id),
        'code': school_class.code,
      }
      return encode_json(response)
    except Exception, e:
      return error_response(500, 'Server Error')


class ClassHandler(OpenMindsAPIHandler):
  '''
  Handler for retrieving extended information about a specific class,
  or updating/deleting a class' information.
  '''

  @add_cors_headers
  @public_api_auth
  def GET(self, class_id=None, auth_user=None, auth_app_id=None):
    '''
    Return a JSON object containing extended information about the
    specific class.
    '''
    try:
      school_class = get_generic_document(class_id, Class)
    except HTTPError, e:
      return e.error_response()
    formatted_dict = school_class.formatted_dict(extended=True)
    return encode_json(formatted_dict)

  @add_cors_headers
  @public_api_auth
  def PUT(self, class_id, auth_user=None, auth_app_id=None):
    '''
    Update the given class, and returns a JSON object containing the
    new timestamp.
    '''
    try:
      school_class = get_generic_document(class_id, Class)
    except HTTPError, e:
      return e.error_response()
    if not school_class.user_can_update(auth_user):
      message = 'Class cannot be modified by the user'
      logging.warn(message)
      return error_response(403, message)

    try:
      data = decode_json(web.ctx.data)
      Class.validate(data)
      # Convert string user ids to object ids. If an object id is not
      # valid, return an error response code.
      if 'instructor' in data:
        data['instructor'] = ObjectId(data['instructor'])
    except ValueError, e:
      logging.warn(e)
      return error_response(400, 'Could not parse JSON')
    except ValidationError, e:
      logging.warn(e)
      return error_response(400, e.error)

    try:
      school_class.update_class(data)
      school_class.save()
      update_json = {'updated': school_class.updated_timestamp()}
      if 'resetCode' in data:
        # Since the class code change happens on the server, we need
        # to send the new code in the response.
        update_json['code'] = school_class.code
      return encode_json(update_json)
    except Exception, e:
      logging.error(e)
      return error_response(500)

  @add_cors_headers
  @public_api_auth
  def DELETE(self, class_id, auth_user=None, auth_app_id=None):
    '''
    Delete the given class, and returns a JSON object containing a
    success notification.
    '''
    try:
      school_class = get_generic_document(class_id, Class)
    except HTTPError, e:
      return e.error_response()

    if not school_class.user_can_update(auth_user):
      message = 'Class cannot be modified by the user'
      logging.warn(message)
      return error_response(403, message)

    try:
      school_class.delete()
      school_class.save()
      # Delete all assignments associated with this class.
      Assignment.collection.update({
        'classId': class_id,
        'deleted': False,
      }, {
        '$set': {
          'deleted': True
        }
      }, multi=True)

      update_json = {'success': True}
      return encode_json(update_json)
    except Exception, e:
      logging.error(e)
      return error_response(500)


class UsersHandler(OpenMindsAPIHandler):
  '''
  Handler for retrieving basic information about users and creating
  new users.
  '''

  @add_cors_headers
  @public_api_auth
  def GET(self, auth_user=None, auth_app_id=None):
    '''
    Returns a JSON array of basic information about users.
    '''
    params = web.input(assignment_id=None, class_id=None)

    class_id = None
    if params.class_id is not None:
      try:
        class_id = ObjectId(params.class_id)
      except Exception, e:
        logging.warn(e)
        return error_response(400)

    if class_id is None:
      # Just find all users created by authenticated user.
      users_spec = {
        'creator': auth_user._id,
        'deleted': False,
      }
    else:
      cspec = {'_id': class_id}
      try:
        class_obj = Class.collection.find_one(cspec)
      except Exception, e:
        logging.error(e)
        return error_response(500)

      if class_obj is None:
        return error_response(404)

      user_id_str_set = set()
      if 'students' in class_obj:
        for user_id_str in class_obj['students']:
          user_id_str_set.add(user_id_str)
      try:
        user_ids = [ObjectId(user_id_str) for user_id_str in user_id_str_set]
        users_spec = {
          'deleted': False,
          '_id': {'$in': user_ids},
        }
      except Exception, e:
        logging.error(e)
        return error_response(500)

    try:
      users = User.collection.find(users_spec)
      # Return private data iff we're looking at users created by
      # authenticated user.
      formatted_users = [
          u.formatted_dict(private_data=(class_id is None)) for u in users]
      return encode_json(formatted_users)
    except Exception, e:
      logging.error(e)
      return error_response(500)


  @add_cors_headers
  @public_api_auth
  def POST(self, auth_user=None, auth_app_id=None):
    '''
    Creates a new user and returns a JSON object containing the
    id and auth token for the new user.
    '''
    params = web.input(data=None)
    try:
      if params.data:
        data = decode_json(params.data)
      else:
        data = decode_json(web.ctx.data)
      User.validate(data)
    except ValueError, e:
      logging.warn(e)
      return error_response(400, 'Could not parse JSON')
    except ValidationError, e:
      logging.warn(e)
      return error_response(400, e.error)

    try:
      user = User()
      user.update_user(data)
      user.set_creator(auth_user)
      token = data.get('token', None)
      if auth_user:
        user.add_to_acl(auth_user, token)
      user.reset_oauth()
      user.save()
      auth_token = get_user_cookie(user._id)
      response = {
        'id': str(user._id),
        'authToken': auth_token
      }
      return encode_json(response)
    except DuplicateKeyError, e:
      logging.error(e)
      return error_response(400, 'That username already exists.')
    except Exception, e:
      logging.error(e)
      return error_response(500, 'Server Error')


class UserHandler(OpenMindsAPIHandler):
  '''
  Handler for retrieving extended information about a specific user,
  or updating/deleting a user's information.
  '''

  def parse_user_id(self, user_id, auth_user):
    if user_id == 'me':
      return 'id', auth_user._id
    elif user_id.startswith('token:'):
      return 'token', user_id[6:]
    else:
      return 'id', ObjectId(user_id)

  @add_cors_headers
  @public_api_auth
  def GET(self, user_id, auth_user=None, auth_app_id=None):
    '''
    Return a JSON object containing extended information about the
    specific user.
    '''

    try:
      id_type, user_id = self.parse_user_id(user_id, auth_user)
    except Exception, e:
      logging.warn(e)
      return error_response(400, 'Not a valid user id')

    if user_id == auth_user._id:
      # User is accessing own information.
      user = auth_user
      user_dict = auth_user.formatted_dict()
    else:
      # User is accessing another user's information.
      if id_type == 'id':
        # Accessing another user by id.
        # NOTE(adam): Perhaps this should be forbidden for now?
        user = User.collection.find_one({'_id': user_id, 'deleted': False})
      else:
        # Accessing another user with a token.
        auth_user_key = 'acl.%s.token' % str(auth_user._id)
        user = User.collection.find_one({
          auth_user_key: user_id,
          'deleted': False,
        })
      if not user:
        message = 'User does not exist'
        logging.warn(message)
        return error_response(404, message)
      user_dict = user.formatted_dict()

    try:
      num_mastered_words = adaptive_model.UserItemInfo.collection.find({
          'userId': user._id,
          'totalOutcomes': {
            '$gte': adaptive_model.MIN_TOTAL_OUTCOMES_FOR_MASTERY
          },
          'average': {
            '$gte': adaptive_model.MIN_AVERAGE_FOR_MASTERY
          },
          'volatility': {
            '$lte': adaptive_model.MAX_VOLATILITY_FOR_MASTERY
          }
          }).count()
    except Exception, e:
      logging.error(e)
      return error_response(500)

    user_dict['numMastered'] = num_mastered_words
    return encode_json(user_dict)

  @add_cors_headers
  @public_api_auth
  def PUT(self, user_id, auth_user=None, auth_app_id=None):
    '''
    Updates the given user, and returns a JSON object containing
    the new timestamp.
    '''
    try:
      id_type, user_id = self.parse_user_id(user_id, auth_user)
    except Exception, e:
      logging.warn(e)
      return error_response(400, 'Not a valid user id')

    try:
      data = decode_json(web.ctx.data)
      User.validate(data)
    except ValueError, e:
      logging.warn(e)
      return error_response(400, 'Could not parse JSON')
    except ValidationError, e:
      logging.warn(e)
      return error_response(400, e.error)

    user = None
    try:
      if user_id == auth_user._id:
        # User is modifying itself.
        user = auth_user
      else:
        # User is attempting to modify other user.
        if id_type == 'id':
          # Accessing another user by id.
          user = User.collection.find_one({'_id': user_id, 'deleted': False})
        else:
          # Accessing another user with a token.
          auth_user_key = 'acl.%s.token' % str(auth_user._id)
          user = User.collection.find_one({
            auth_user_key: user_id
          })
    except Exception, e:
      logging.error(e)
      return error_response(500, 'Server Error')

    if not user:
      message = 'User does not exist'
      logging.warn(message)
      return error_response(404, message)
    if not user.user_can_update(auth_user):
      message = 'Forbidden'
      logging.warn(message)
      return error_response(403, message)

    try:
      user.update_user(data)
      user.save()
      update_json = {'updated': user.updated_timestamp()}
      return encode_json(update_json)
    except DuplicateKeyError, e:
      logging.error(e)
      return error_response(500, 'That username already exists.')
    except Exception, e:
      logging.error(e)
      return error_response(500, 'Server Error')

  @add_cors_headers
  @public_api_auth
  def DELETE(self, user_id, auth_user=None, auth_app_id=None):
    '''
    Delete the given user, and returns a JSON object containing
    a success notification.
    '''
    try:
      id_type, user_id = self.parse_user_id(user_id, auth_user)
    except Exception, e:
      logging.warn(e)
      return error_response(400, 'Not a valid user id')

    user = None
    try:
      if user_id == auth_user._id:
        # User is modifying itself.
        user = auth_user
      else:
        # User is attempting to modify other user.
        if id_type == 'id':
          # Accessing another user by id.
          user = User.collection.find_one({'_id': user_id, 'deleted': False})
        else:
          # Accessing another user with a token.
          auth_user_key = 'acl.%s.token' % str(auth_user._id)
          user = User.collection.find_one({
            auth_user_key: user_id,
            'deleted': False,
          })
    except Exception, e:
      logging.error(e)
      return error_response(500, 'Server Error')

    if not user:
      message = 'User does not exist'
      logging.warn(message)
      return error_response(404, message)
    if not user.user_can_update(auth_user):
      message = 'Forbidden'
      logging.warn(message)
      return error_response(403, message)

    try:
      user.delete()
      user.save()
      update_json = {'success': True}
      return encode_json(update_json)
    except Exception, e:
      logging.error(e)
      return error_response(500, 'Server Error')


class AssignmentTemplatesHandler(OpenMindsAPIHandler):
  '''
  Handler for retrieving basic information about assignment templates and
  creating new assignment template.
  '''

  @add_cors_headers
  @public_api_auth
  def GET(self, auth_user=None, auth_app_id=None):
    '''
    Returns a JSON array of basic information about assignment templates.
    FIXME(dbanks)
    Right now you get all assignment templates.
    We may want to control that somehow so that some templates (created
    by us) are public-domain.  Others, auth_user has to be on acl for that
    template.
    '''
    params = web.input(num=50)
    depth = parse_int_param(util.get_header('X-OpenMinds-Depth'), 0)
    try:
      num = parse_int_param(params.num, 50)
      spec = {'deleted': False}
      templates = AssignmentTemplate.collection.find(spec).limit(num)
      formatted_templates = \
        [template.formatted_dict(depth=depth) for template in templates]
      return encode_json(formatted_templates)
    except Exception, e:
      logging.error(e)
      return error_response(500)

  @add_cors_headers
  @public_api_auth
  def POST(self, auth_user=None, auth_app_id=None):
    '''
    Creates a new AssignmentTemplate and returns a JSON object containing the
    id for the new AssignmentTemplate.
    '''
    params = web.input(data=None)
    depth = parse_int_param(util.get_header('X-OpenMinds-Depth'), 0)
    try:
      if params.data:
        data = decode_json(params.data)
      else:
        data = decode_json(web.ctx.data)
      AssignmentTemplate.validate(data)
    except ValueError, e:
      logging.warn(e)
      return error_response(400, 'Could not parse JSON')
    except ValidationError, e:
      logging.warn(e)
      return error_response(400, e.error)

    try:
      convert_assignment_data_to_db_format(data)
      assignment_template = AssignmentTemplate(data)
      assignment_template.set_creator(auth_user)
      assignment_template.save()
      formatted_dict = assignment_template.formatted_dict(depth=depth)
      return encode_json(formatted_dict)
    except:
      return error_response(500, 'Server Error')


class AssignmentTemplateHandler(OpenMindsAPIHandler):
  """
  Handler for getting and updating AssignmentTemplates
  """

  @add_cors_headers
  @public_api_auth
  def GET(self, assignment_template_id, auth_user=None, auth_app_id=None):
    '''
    Return a JSON object containing information about the
    specific AssignmentTemplate.
    '''
    try:
      assignment_template = get_generic_document(
          assignment_template_id, AssignmentTemplate)
    except HTTPError, e:
      return e.error_response()

    depth = parse_int_param(util.get_header('X-OpenMinds-Depth'), 0)
    formatted_dict = assignment_template.formatted_dict(depth=depth)
    return encode_json(formatted_dict)

  @add_cors_headers
  @public_api_auth
  def PUT(self, assignment_template_id, auth_user=None, auth_app_id=None):
    '''
    Update existing AssignmentTemplate.
    '''
    try:
      assignment_template = get_generic_document(
          assignment_template_id, AssignmentTemplate)
    except HTTPError, e:
      return e.error_response()

    params = web.input(data=None)
    try:
      if params.data:
        data = decode_json(params.data)
      else:
        data = decode_json(web.ctx.data)
      AssignmentTemplate.validate(data)
    except ValueError, e:
      logging.warn(e)
      return error_response(400, 'Could not parse JSON')
    except ValidationError, e:
      logging.warn(e)
      return error_response(400, e.error)

    if not assignment_template.user_can_update(auth_user):
      return error_response(
          403, 'Assignment Template cannot be modified by the user')

    try:
      convert_assignment_data_to_db_format(data)
      assignment_template.update(data)
      assignment_template.save()
      update_json = {'updated': assignment_template.updated_timestamp()}
      return encode_json(update_json)
    except Exception, e:
      logging.error(e)
      return error_response(500)


class AssignmentsHandler(OpenMindsAPIHandler):
  '''
  Handler for retrieving basic information about assignments and creating
  new assignment.
  '''

  @add_cors_headers
  @public_api_auth
  def GET(self, auth_user=None, auth_app_id=None):
    '''
    Returns a JSON array of basic information about assignment.
    '''
    params = web.input(
        student_user_id=None, class_id=None, availability=None, num=50)
    depth = parse_int_param(util.get_header('X-OpenMinds-Depth'), 0)
    try:
      num = parse_int_param(params.num, 50)
    except Exception, e:
      logging.error(e)
      return error_response(400, 'Could not parse num parameter.')

    try:
      # If student_user_id is present, we're asking for all assignments assigned
      # to user X. Access is limited by auth_users rights to see student X's
      # info.
      #
      # If student_user_id is not present but class_id is present, we're asking
      # for all assignments given to that class.
      # Access is limited by auth_users rights to see class X info.
      #
      # If both student_user_id and class_id are missing, we assume auth_user is
      # a teacher and we look for all assignments created by that teacher.
      assignment_spec = {
        'deleted': False,
      }
      if params.student_user_id is not None:
        try:
          # Note we don't actually use the converted id, we can search with
          # just the plain string.  But it's a nice sanity check.
          student_user_id = ObjectId(params.student_user_id)
        except Exception, e:
          logging.warn(e)
          return error_response(400, 'student_user_id is not a valid id')

        if not can_see_student_data(auth_user, student_user_id):
          return error_response(401)

        # Find all classes he belongs to.
        classes_spec = {'students': params.student_user_id}
        classes_list = Class.collection.find(classes_spec)

        # Now find all assignments for these classes.
        class_ids = []
        for class_doc in classes_list:
          class_ids.append(str(class_doc._id))
        assignment_spec['classId'] = {'$in': class_ids}
      elif params.class_id is not None:
        try:
          class_id = ObjectId(params.class_id)
        except Exception, e:
          logging.warn(e)
          return error_response(400, 'class_id is not a valid id')

        if not can_see_class_data(auth_user, class_id):
          return error_response(401)
        assignment_spec['classId'] = params.class_id
      else:
        assignment_spec['creator'] = auth_user._id

      if params.availability is not None:
        assignment_spec['availability'] = parse_int_param(
            params.availability, Assignment.AVAILABILITY_OPEN)

      assignments = Assignment.collection.find(assignment_spec).limit(num)
      formatted_assignments = [assignment.formatted_dict(depth=depth)
                             for assignment in assignments]
      return encode_json(formatted_assignments)
    except Exception, e:
      logging.error(e)
      return error_response(500)

  @add_cors_headers
  @public_api_auth
  def POST(self, auth_user=None, auth_app_id=None):
    '''
    Creates a new Assignment and returns a JSON object containing the
    id for the new Assignment.

    You could pass up a fully specified assignment, but as a convenience we also
    allow you to pass up an assignment template id, which will fill in
    all the data for you.
    '''
    params = web.input(data=None)
    depth = parse_int_param(util.get_header('X-OpenMinds-Depth'), 0)

    try:
      if params.data:
        data = decode_json(params.data)
      else:
        data = decode_json(web.ctx.data)
    except ValueError, e:
      logging.warn(e)
      return error_response(400, 'Could not parse JSON')

    if 'assignmentTemplateId' in data:
      try:
        assignment_template = get_generic_document(
            data['assignmentTemplateId'], AssignmentTemplate)
        del data['assignmentTemplateId']
      except HTTPError, e:
        return e.error_response()
      formatted_data = assignment_template.formatted_dict(depth=0)
      if 'units' in formatted_data:
        data['units'] = formatted_data['units']
      if 'name' in formatted_data:
        data['name'] = formatted_data['name']

    try:
      Assignment.validate(data)
    except ValidationError, e:
      logging.warn(e)
      return error_response(400, e.error)

    try:
      convert_assignment_data_to_db_format(data)
      assignment = Assignment(data)
      assignment.set_creator(auth_user)
      assignment.save()
      response = assignment.formatted_dict(depth=depth)
      return encode_json(response)
    except Exception, e:
      logging.error(e)
      logging.error(500, 'Server Error')


class AssignmentHandler(OpenMindsAPIHandler):
  """
  Handler for getting and updating Assignments
  """

  @add_cors_headers
  @public_api_auth
  def GET(self, assignment_id, auth_user=None, auth_app_id=None):
    '''
    Return a JSON object containing information about the
    specific Assignment.
    '''
    try:
      assignment = get_generic_document(assignment_id, Assignment)
    except HTTPError, e:
      return e.error_response()

    depth = parse_int_param(util.get_header('X-OpenMinds-Depth'), 0)
    formatted_dict = assignment.formatted_dict(depth=depth)
    return encode_json(formatted_dict)
      
  @add_cors_headers
  @public_api_auth
  def PUT(self, assignment_id, auth_user=None, auth_app_id=None):
    '''
    Update existing Assignment.
    '''
    try:
      assignment = get_generic_document(assignment_id, Assignment)
    except HTTPError, e:
      return e.error_response()

    params = web.input(data=None)
    try:
      if params.data:
        data = decode_json(params.data)
      else:
        data = decode_json(web.ctx.data)
      Assignment.validate(data)
    except ValueError, e:
      logging.warn(e)
      return error_response(400, 'Could not parse JSON')
    except ValidationError, e:
      logging.warn(e)
      return error_response(400, e.error)

    if not assignment.user_can_update(auth_user):
      return error_response(403, 'Assignment cannot be modified by the user')

    try:
      convert_assignment_data_to_db_format(data)
      assignment.update(data)
      assignment.save()
      update_json = {'updated': assignment.updated_timestamp()}
      return encode_json(update_json)
    except Exception, e:
      logging.error(e)
      return error_response(500)


def convert_assignment_data_to_db_format(data):
  '''
  Convert the API format for assignment and assignment templates to the data
  format stored in the database.
  '''
  for unit in data.get('units', []):
    if 'lists' in unit:
      lists = unit['lists']
      del unit['lists']
      unit['listIds'] = map(lambda l: l['id'], lists)

  if 'class' in data:
    class_id = data['class']['id']
    del data['class']
    data['classId'] = class_id


class ListsHandler(OpenMindsAPIHandler):
  '''
  Handler for retrieving basic information about lists and creating
  new lists.
  '''

  @add_cors_headers
  @public_api_auth
  def GET(self, auth_user=None, auth_app_id=None):
    '''
    Returns a JSON array of basic information about lists created
    by the authenticated user.
    '''
    params = web.input(
        search=None, num=50, grade=None, standard=None, section=None)

    try:
      item_lists = get_lists(auth_user, params)
      formatted_lists = [item_list.formatted_dict() for item_list in item_lists]
      return encode_json(formatted_lists)
    except Exception, e:
      logging.error(e)
      return error_response(500)

  @add_cors_headers
  @public_api_auth
  def POST(self, auth_user=None, auth_app_id=None):
    '''
    Create a new list and returns a JSON object containing the new
    list information.
    '''
    params = web.input(data=None)
    try:
      if params.data:
        data = decode_json(params.data)
      else:
        data = decode_json(web.ctx.data)
      List.validate(data)
    except ValueError, e:
      logging.warn(e)
      return error_response(400, 'Could not parse JSON')
    except ValidationError, e:
      logging.warn(e)
      return error_response(400, e.error)

    try:
      item_list = List(data)
      item_list.set_creator(auth_user)
      item_list.save()
      formatted_dict = item_list.formatted_dict(extended=True)
      formatted_dict['editable'] = item_list.user_can_update(auth_user)
      return encode_json(formatted_dict)
    except Exception, e:
      logging.error(e)
      return error_response(500)


class ListHandler(OpenMindsAPIHandler):
  '''
  Handler for retrieving extended information about a specific list,
  or updating/deleting a list's information.
  '''

  @add_cors_headers
  @public_api_auth
  def GET(self, list_id, auth_user=None, auth_app_id=None):
    '''
    Return a JSON object containing extended information about the
    specific list.
    '''
    try:
      item_list = get_generic_document(list_id, List)
    except HTTPError, e:
      return e.error_response()

    params = web.input(sort=None)
    try:
      formatted_dict = item_list.formatted_dict(extended=True)
      if params.sort == 'adaptive' and 'items' in formatted_dict:
        formatted_dict['items'] = \
          adaptive_sort_item_list(formatted_dict['items'], auth_user)
      formatted_dict['editable'] = item_list.user_can_update(auth_user)
      return encode_json(formatted_dict)
    except Exception, e:
      logging.error(e)
      return error_response(500, 'Server Error')

  @add_cors_headers
  @public_api_auth
  def PUT(self, list_id, auth_user=None, auth_app_id=None):
    '''
    Update the given list, and returns a JSON object containing the
    new timestamp.
    '''
    item_list = get_generic_document(list_id, List)

    try:
      data = decode_json(web.ctx.data)
      List.validate(data)
    except ValueError, e:
      logging.warn(e)
      return error_response(400, 'Could not parse JSON')
    except ValidationError, e:
      logging.warn(e)
      return error_response(400, e.error)

    if not item_list.user_can_update(auth_user):
      message = 'List cannot be modified by the user'
      logging.warn(message)
      return error_response(403, message)

    try:
      item_list.update(data)
      item_list.save()
      update_json = {'updated': item_list.updated_timestamp()}
      return encode_json(update_json)
    except Exception, e:
      logging.error(e)
      return error_response(500)

  @add_cors_headers
  @public_api_auth
  def POST(self, list_id, auth_user=None, auth_app_id=None):
    '''
    Create a new item and add it to the list.
    '''
    try:
      item_list = get_generic_document(list_id, List)
    except HTTPError, e:
      return e.error_response()

    if not item_list.user_can_update(auth_user):
      message = 'List cannot be modified by the user'
      logging.warn(message)
      return error_response(403, message)

    # Validate data for new item.
    params = web.input(data=None)
    try:
      if params.data:
        item_data = decode_json(params.data)
      else:
        item_data = decode_json(web.ctx.data)
      Item.validate(item_data)
    except ValueError, e:
      logging.warn(e)
      return error_response(400, 'Could not parse JSON')
    except ValidationError, e:
      logging.warn(e)
      return error_response(400, e.error)

    try:
      item = Item(item_data)
      item.set_creator(auth_user)
      item.save()
      item_added = item_list.add_item(item)
      if item_added:
        item_list.save()
        formatted_dict = item.formatted_dict()
        formatted_dict['editable'] = item.user_can_update(auth_user)
        return encode_json(formatted_dict)
      else:
        return error_response(
            500,
            'List cannot contain more than %d items.' % List.max_list_size)
    except Exception, e:
      logging.error(e)
      return error_response(500)

  @add_cors_headers
  @public_api_auth
  def DELETE(self, list_id, auth_user=None, auth_app_id=None):
    '''
    Delete the given list, and returns a JSON object containing a
    success notification.
    '''
    try:
      item_list = get_generic_document(list_id, List)
    except HTTPError, e:
      return e.error_response()

    if not item_list.user_can_update(auth_user):
      message = 'List cannot be modified by the user'
      logging.warn(message)
      return error_response(403, message)

    try:
      item_list.delete()
      item_list.save()
      update_json = {'success': True}
      return encode_json(update_json)
    except Exception, e:
      logging.error(e)
      return error_response(500)


class ItemHandler(OpenMindsAPIHandler):
  @add_cors_headers
  @public_api_auth
  def GET(self, list_id, item_id, auth_user=None, auth_app_id=None):
    '''
    Return details for the given item.
    '''
    try:
      # Verify that item list exists for the given list id.
      item_list = get_generic_document(list_id, List)
      item = get_generic_document(item_id, Item)
    except HTTPError, e:
      return e.error_response()

    formatted_dict = item.formatted_dict()
    formatted_dict['editable'] = item.user_can_update(auth_user)
    return encode_json(formatted_dict)

  @add_cors_headers
  @public_api_auth
  def PUT(self, list_id, item_id, auth_user=None, auth_app_id=None):
    '''
    Update the given item.
    '''
    try:
      # Verify that item list exists for the given list id.
      item_list = get_generic_document(list_id, List)
      item = get_generic_document(item_id, Item)
    except HTTPError, e:
      return e.error_response()

    if not item.user_can_update(auth_user):
      message = 'Item cannot be modified by the user'
      logging.warn(message)
      return error_response(403, message)

    if not item_list.item_is_in_list(item):
      message = 'Item is not in list'
      logging.warn(message)
      return error_response(404, message)

    try:
      item.update(data)
      item.save()
      return encode_json(item.formatted_dict())
    except Exception, e:
      logging.error(e)
      return error_response(500)

  @add_cors_headers
  @public_api_auth
  def DELETE(self, list_id, item_id, auth_user=None, auth_app_id=None):
    '''
    Delete the given item from the list.
    '''
    try:
      item_list = get_generic_document(list_id, List)
      item = get_generic_document(item_id, Item)
    except HTTPError, e:
      return e.error_response()

    if not item_list.user_can_update(auth_user):
      message = 'List cannot be modified by the user'
      logging.warn(message)
      return error_response(403, message)

    if not item.user_can_update(auth_user):
      message = 'Item cannot be modified by the user'
      logging.warn(message)
      return error_response(403, message)

    if not item_list.item_is_in_list(item):
      message = 'Item is not in list'
      logging.warn(message)
      return error_response(404, message)

    try:
      success = item_list.remove_item(item)
      if success:
        item_list.save()
        item.delete()
        item.save()
        update_json = {'success': True}
        return encode_json(update_json)
      else:
        update_json = {'success': False}
        return encode_json(update_json)
    except Exception, e:
      logging.error(e)
      return error_response(500)


class LeaderboardHandler(OpenMindsAPIHandler):
  @add_cors_headers
  @public_api_auth
  def GET(self, auth_user=None, auth_app_id=None):
    params = web.input(num=20, class_only=0)
    num_entries = parse_int_param(params.num, 20)
    #class_only = parse_int_param_as_bool(params.class_only)
    class_only = auth_user.get('littlelives_teacher', False)

    spec = {
      'points': {'$exists': True},
      '$or': [{'flagged': {'$exists': False}},{'flagged': False}],
    }

    if class_only:
      key = 'acl.%s' % str(auth_user._id)
      spec[key] = {'$exists': True}

    users_data = User.collection.find(
        spec,
        {'username': 1, 'name': 1, 'points': 1},
        sort=[('points', pymongo.DESCENDING)],
        limit=num_entries)
    users = [User(data) for data in users_data]
    users = [user.formatted_dict() for user in users]
    return encode_json(users)


class EventsHandler(OpenMindsAPIHandler):
  @add_cors_headers
  @public_api_auth
  def POST(self, auth_user=None, auth_app_id=None):
    '''Record the given events.'''
    list_id = None
    params = web.input(data=None)
    try:
      if params.data:
        data = decode_json(params.data)
      else:
        data = decode_json(web.ctx.data)
    except ValueError, e:
      logging.warn(e)
      return error_response(400, 'Could not parse JSON')

    # make sure event list is properly formatted
    try:
      Event.validate_list(data)
      events_datetime = datetime.fromtimestamp(data['timestamp'])
      if 'listId' in data:
        list_id = ObjectId(data['listId'])
    except Exception, e:
      logging.warn(e)
      return error_response(400)

    log_user = None
    if not ('userId' in data):
      # User id was not specified, log events for the auth user.
      log_user = auth_user
    else:
      try:
        log_user_id = ObjectId(data['userId'])
      except Exception, e:
        logging.warn(e)
        return error_response(400, 'Not a valid user id')

      if log_user_id == auth_user._id:
        # Specified user is auth user.
        log_user = auth_user
      else:
        # Specified user is not auth user. Make sure specified
        # user exists, and auth user has logging permissions.
        log_user = User.collection.find_one(
            {'_id': log_user_id, 'deleted': False})
        if not log_user:
          message = 'User does not exist'
          logging.warn(message)
          return error_response(404, message)
        if not log_user.user_can_update(auth_user):
          message = 'Forbidden'
          logging.warn(message)
          return error_response(403, message)

    events_json = data['events']

    new_points = 0
    events = []
    for event_json in events_json:
      try:
        Event.validate(event_json)
        # make sure item id is valid bson object id.
        event_json['itemId'] = ObjectId(event_json['itemId'])
        # make sure timestamp is valid time
        event_json['timestamp'] = datetime.fromtimestamp(event_json['timestamp'])
        event = Event(event_json)
        event.set_user(log_user)
        event.save()
        events.append(event)
      except ValidationError, e:
        logging.warn(e)
        return error_response(400, e.error)

    for event in events:
      if event.outcome is True:
        new_points = new_points + 10

      try:
        item_info = adaptive_model.update_user_item_info(log_user, event)
        item_info.save()

        if list_id is not None:
          list_info = adaptive_model.update_user_list_info(
              log_user, list_id, event)
          list_info.save()

      except Exception, e:
        logging.error(e)
        return error_response(500, 'Could not log events')

    log_user.points = log_user.get('points', 0) + new_points

    try:
      self.add_sampling_records(log_user._id, list_id, auth_app_id, data['timestamp'],
                                events)
    except Exception, e:
      logging.error(e)
      return error_response(500, 'Could not log sampling record.')

    try:
      log_user.save()
    except Exception, e:
      logging.error(e)
      return error_response(500, 'Could not save user')

    return encode_json({'success': True})

  def add_sampling_records(self, user_id, list_id, app_id, timestamp, events):
    """
    These events represent a 'sampling' of activities on the given list
    across one or more apps.
    We want to record a summary of this sampling: at this time user
    was tested on this list and got this percent right.
    """
    outcomes = []
    for event in events:
      # We are not going to be searching over these itemIds in the
      # database, feels a bit saner to store them as strings.
      outcome = {
        'itemId': str(event.itemId),
        'outcome': adaptive_model.event_outcome_is_positive(event),
      }
      outcomes.append(outcome)
    sampling_record = adaptive_model.create_sampling_record(user_id, list_id,
                                                            app_id, timestamp,
                                                            outcomes)
    sampling_record.save()


class CommonCoreHandler(object):
  def GET(self, grade):
    grade = parse_int_param(grade, 5)
    common_core = CommonCore()
    data = common_core.get_grade(grade)
    if not data:
      logging.warn('Cannot find data for grade %d' % grade)
      return error_response(404)

    try:
      grade_json = encode_json(data)
      return grade_json
    except Exception, e:
      logging.error(e)
      return error_response(500)
    return grade


class LittleLivesAuthenticateHandler(object):
  @private_api_auth
  def GET(self, auth_user=None, auth_app_id=None):
    params = web.input(username=None, password=None)
    if params.username == None or params.password == None:
      logging.warn('Missing username or password.')
      return error_response(400, 'Could not authenticate')

    client = littlelives_info.get_client();
    auth_info = client.authenticate(params.username, params.password)
    if 'success' in auth_info or 'sucess' in auth_info:
      # temp workaround for typo in littlelives response
      success = auth_info.get('success', auth_info.get('sucess'))
      if success and 'id' in auth_info:
        # Associate the littlelives id with the user.
        littlelives_id = auth_info['id']
        auth_user.littlelives_id = littlelives_id

        status = {'success': True, 'id': littlelives_id}

        # Check if the user is a teacher on littlelives.
        user_info = client.get_user(littlelives_id)
        if user_info:
          role = user_info.get('role', None)
          if role == 'TCHR':
            auth_user.littlelives_teacher = True
            status['teacher'] = True

        try:
          auth_user.save()
          return encode_json(status)
        except Exception, e:
          logging.error(e)
          return error_response(500, 'Server Error')
      else:
        message = 'Could not authenticate'
        logging.warn(message)
        return error_response(400, message)
    else:
      message = 'LittleLives Server Error'
      logging.error(message)
      return error_response(500, message)


class LittleLivesUsersHandler(object):
  @private_api_auth
  def GET(self, auth_user=None, auth_app_id=None):
    client = littlelives_info.get_client();

    littlelives_id = auth_user.get('littlelives_id', None)
    if not littlelives_id:
      message = 'Could not authenticate'
      logging.warn(message)
      return error_response(400, message)

    user_info = client.get_user(littlelives_id)
    if not user_info:
      message = 'User not found'
      logging.warn(message)
      return error_response(404, message)
    else:
      return encode_json(user_info)
