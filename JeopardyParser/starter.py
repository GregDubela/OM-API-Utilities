import logging
import oauth2
import os
os.system("cls")    #Windows based systems us
import time
import httplib
import urllib
import sys

import string
import math

import gflags
#NLTK related imports
import re
import enchant
from nltk.corpus import wordnet as wn
from bs4 import BeautifulSoup

from unidecode import unidecode
from web_util import encode_json, decode_json

import cfg
from text_utils import *
from om_utils import *
from om_client import *
from webList_to_OM import *

logging.basicConfig(level=logging.DEBUG, filename='jt.log')
logging.basicConfig(level=logging.INFO, filename='jt.log')
logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)

if __name__ == '__main__':

  argv = cfg.FLAGS(sys.argv)
  print argv
  if cfg.FLAGS.om_access_token:
      client = OpenMindsThreeLeggedClient(cfg.FLAGS.om_access_token, cfg.FLAGS.om_host)
  else:
      client = OpenMindsTwoLeggedClient(cfg.FLAGS.om_key, cfg.FLAGS.om_secret, cfg.FLAGS.om_host)
  
  # Step 1 Read in the relevant file
  #read the input directory path
  rawDirPath = r'C:\Users\Ram\Root-1\OM-API-Utilities\ListsToBeCreated'

  #dirList=os.listdir(rawDirPath) #list of filenames
###########################
  
