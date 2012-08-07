# globals variables
import gflags

DEBUG = False

DEFAULT_HOST = 'openminds.io'

FLAGS = gflags.FLAGS

#All DEFINE macros take the same three arguments: the name of the flag, its default value, and a 'help' string that describes its use. The 'help' string is displayed when the user runs the application with the --help flag.

gflags.DEFINE_string('om_host', DEFAULT_HOST, 'OpenMinds Host')

gflags.DEFINE_string('om_key', '', 'OpenMinds API user key. Used by an individual to access the OpenMinds API.')
gflags.DEFINE_string('om_secret', '', 'OpenMinds API user secret. Used by an individual to access the OpenMinds API.')

gflags.DEFINE_string('om_access_token', '', 'OpenMindsAPI access token. Used by an app to access the OpenMinds API on behalf of a user. If this flag is defined, om_key and om_secret are ignored.')

gflags.DEFINE_bool('debug_lvl', True, 'Level of Debugging')


gflags.DEFINE_string('directory','','The name of the directory where the List CSV files are located')
gflags.DEFINE_string('file','','Name of the CSV file to read')
