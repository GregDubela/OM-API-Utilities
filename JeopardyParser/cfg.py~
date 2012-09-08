# globals variables
import gflags

DEBUG = False

DEFAULT_HOST = 'openminds.io'

FLAGS = gflags.FLAGS

#All DEFINE macros take the same three arguments: 
# the name of the flag, 
# its default value, 
# a 'help' string that describes its use. The 'help' string is displayed when the user runs the application with the --help flag.

gflags.DEFINE_string('om_host', DEFAULT_HOST, 'OpenMinds Host')

gflags.DEFINE_string('om_key', '', 'OpenMinds API user key. Used by an individual to access the OpenMinds API.')
gflags.DEFINE_string('om_secret', '', 'OpenMinds API user secret. Used by an individual to access the OpenMinds API.')

gflags.DEFINE_string('om_access_token', '', 'OpenMindsAPI access token. Used by an app to access the OpenMinds API on behalf of a user. If this flag is defined, om_key and om_secret are ignored.')

gflags.DEFINE_bool('debug_lvl', True, 'Level of Debugging')


gflags.DEFINE_string('directory','','The name of the directory where the List CSV files are located')
gflags.DEFINE_string('file','','Name of the CSV file to read')


gflags.DEFINE_bool('plurals', False, 'Should plurals be treated as separate words')

gflags.DEFINE_string('ends_with','ed','String fragment for word to end with')
gflags.DEFINE_string('starts_with','vib','String fragment for word to end with')

gflags.DEFINE_string('autoTitle','List Title','The Title string for this collection of words')

gflags.DEFINE_string('regex','.*','A Regex pattern to match set of words')

gflags.DEFINE_integer('maxLength', 14, "The maximum word length for this pattern")
gflags.DEFINE_integer('minLength', 3, "The minimum word length for this pattern")
