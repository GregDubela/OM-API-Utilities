from auth import public_api_auth
from bson.objectid import ObjectId
from apps import App
from libraries.python.web_util import encode_json, decode_json
from libraries.python.web_util import parse_int_param, parse_int_param_as_bool
from libraries.python.web_util import error_response
import json
import logging
import pymongo
import web

urls = (
  '/apps/?', 'AppsHandler',
  '/apps/([^/]+)/?', 'AppHandler',
)
app = web.application(urls, locals())


class AppsHandler(object):
  '''
  Handler for retrieving information about a developer's registered
  apps. Also allows for new apps to be registered.
  '''

  @public_api_auth
  def GET(self, auth_user=None, auth_app_id=None):
    '''
    Return JSON array of basic app info. Only returns apps
    created by the authenticated user.
    '''
    try:
      spec = {
        'deleted': False,
        'creator': auth_user._id
      }
      apps = App.collection.find(spec)
      formatted_apps = [app.formatted_dict() for app in apps]
      return encode_json(formatted_apps)
    except Exception, e:
      logging.error(e)
      return error_response(500)

  @public_api_auth
  def POST(self, auth_user=None, auth_app_id=None):
    '''
    Create a new app and return a JSON object containing the new
    app information.
    '''
    params = web.input(data=None)
    try:
      if params.data:
        data = decode_json(params.data)
      else:
        data = decode_json(web.ctx.data)
      App.validate(data)
    except Exception, e:
      logging.error(e)
      return error_response(400, 'Data did not pass validation')

    try:
      app = App(data)
      app.set_creator(auth_user)
      app.save()
      formatted_dict = app.formatted_dict()
      return encode_json(formatted_dict)
    except Exception, e:
      logging.error(e)
      return error_response(500)


class AppHandler(object):
  '''
  Handler for retrieving information about a specific app. Also
  allows app information to be updated, or for an app to be deleted. Only
  the creator can access and modify the app information.
  '''

  @public_api_auth
  def GET(self, app_id, auth_user=None, auth_app_id=None):
    '''
    Return a JSON object containing information about the specific app.
    '''
    try:
      app_id = ObjectId(app_id)
    except Exception, e:
      logging.error(e)
      return error_response(400, 'Not a valid app id')

    try:
      app = App.collection.find_one({'_id': app_id, 'deleted': False})
      if not app:
        message = 'App does not exist'
        logging.warn(message)
        return error_response(404, message)
      if not app.user_can_update(auth_user):
        message = 'App cannot be accessed by the user'
        logging.warn(message)
        return error_response(403, message)
      formatted_dict = app.formatted_dict()
      return encode_json(formatted_dict)
    except Exception, e:
      logging.error(e)
      return error_response(500, 'Server Error')

  @public_api_auth
  def PUT(self, app_id, auth_user=None, auth_app_id=None):
    '''
    Update the given app, and returns a JSON object containing the new
    timestamp.
    '''
    try:
      app_id = ObjectId(app_id)
    except Exception, e:
      logging.error(e)
      return error_response(400, 'Not a valid app id')

    try:
      data = decode_json(web.ctx.data)
      App.validate(data)
    except Exception, e:
      return error_response(400, 'Data did not pass validation')

    try:
      app = App.collection.find_one({'_id': app_id, 'deleted': False})
    except Exception, e:
      logging.error(e)
      return error_response(500, 'Server Error')

    if not app:
      message = 'App does not exist'
      logging.warn(message)
      return error_response(404, message)
    if not app.user_can_update(auth_user):
      message = 'App cannot be accessed by the user'
      logging.warn(message)
      return error_response(403, message)

    try:
      app.update(data)
      app.save()
      update_json = {'updated': app.updated_timestamp()}
      return encode_json(update_json)
    except Exception, e:
      logging.error(e)
      return error_response(500)

  @public_api_auth
  def DELETE(self, app_id, auth_user=None, auth_app_id=None):
    '''
    Delete the given app, and returns a JSON object containing a
    success notification.
    '''
    try:
      app_id = ObjectId(app_id)
    except Exception, e:
      return error_response(400, 'Not a valid app id')

    try:
      app = App.collection.find_one({'_id': app_id, 'deleted': False})
    except Exception, e:
      logging.error(e)
      return error_response(500, 'Server Error')
    if not app:
      message = 'App does not exist'
      logging.warn(message)
      return error_response(404, message)
    if not app.user_can_update(auth_user):
      message = 'App cannot be modified by the user'
      logging.warn(message)
      return error_response(403, message)

    try:
      app.delete()
      app.save()
      update_json = {'success': True}
      return encode_json(update_json)
    except Exception, e:
      logging.error(e)
      return error_response(500)

