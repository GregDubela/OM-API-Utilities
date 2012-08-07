'''
Utility functions and classes shared between the various API applications.

Author: Adam Stepinski
'''

from libraries.python.cors_util import CrossOriginRequestHandler

ALLOWED_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
ALLOWED_HEADERS = [
    'Origin', 'Content-Type', 'Accept',
    'X-OpenMinds-Access-Token',
    'X-Openminds-Depth',
]

class OpenMindsAPIHandler(CrossOriginRequestHandler):
  '''
  Sets the allowed methods and headers for Cross Origin API requests.
  '''
  def __init__(self):
    CrossOriginRequestHandler.__init__(self, ALLOWED_METHODS, ALLOWED_HEADERS)
        
