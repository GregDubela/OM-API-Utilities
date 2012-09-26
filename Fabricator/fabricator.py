'''
A utility to CREATE Automated OM Lists using the API
Reads a regex, looks up matching words in the Dictionary, gets their meanings and uploads to OpenMinds

Adapted from Adam's version by Ram Narasimhan
'''

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

from libraries.python.web_util import encode_json, decode_json

import cfg
from text_utils import *
from om_utils import *
from om_client import *

#Imports should be grouped in the following order:
#    standard library imports
#    related third party imports
#    local application/library specific imports


logging.basicConfig(level=logging.DEBUG, filename='omFab.log')
logging.basicConfig(level=logging.INFO, filename='omFab.log')
logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)
# http://antonym.org/2005/03/a-real-python-logging-example.html is very good

#It is important to use the right severity levels when you write you log calls. I tend to use INFO for generally useful stuff that I like to see traced while developing, but not at runtime, while I reserve DEBUG for the extra detailed information that is only useful when something is going wrong. The WARNING and lower I always have on at runtime, and in production are sent to an operator console.


def create_list_of_item_dicts(mWords):

    idictsList = []

    for w in mWords:
        iDict = {}
        addElementToDict("vocab", iDict, "word", w)
        addElementToDict("vocab", iDict, "defn", meaning(w)[0])        
        idictsList.append(iDict)

    return idictsList



if __name__ == '__main__':

  argv = cfg.FLAGS(sys.argv)
  print argv
  if cfg.FLAGS.om_access_token:
      client = OpenMindsThreeLeggedClient(cfg.FLAGS.om_access_token, cfg.FLAGS.om_host)
  else:
      client = OpenMindsTwoLeggedClient(cfg.FLAGS.om_key, cfg.FLAGS.om_secret, cfg.FLAGS.om_host)
  
  #logging.info("Me: %s" % client.get_user('me'))


  # dict to hold all words
  logging.info("Loading Small English Dictionary")
  eng_d = load_word_dictionary()
  #print type(d).__name__
  dList = eng_d.items()
  #print type(dList).__name__
  print len(dList), "English words loaded"


  # stitch the regEx pattern from all the input parameters in the flagfile
  regStart = cfg.FLAGS.starts_with
  regEnd = cfg.FLAGS.ends_with
  regpattern = regStart+regEnd
  reg = cfg.FLAGS.regex
  maxLength = cfg.FLAGS.maxLength
  minLength = cfg.FLAGS.minLength
  autoTitle = cfg.FLAGS.autoTitle

  matchedWords = searchDictFor(eng_d, reg, minLength, maxLength) #text_utils
  wList = create_list_of_words_with_meanings(matchedWords)
  numW = wList.__len__()
  print numW

  if numW <= 2:
      print "Too few words. Skipping OM list creation."
      print "Please Try another pattern."
      sys.exit(0)

  # create one dictionary for each item in matchedWords
  iDictsList = create_list_of_item_dicts(wList)

  ldict = createADictWithListMetadata(autoTitle, "vocabulary", "public") #om_utils

  if (cfg.FLAGS.debug_lvl == False): #not debug means create OM Lists
      newList =  client.create_list(ldict) # the actual OM list shell creation
      if isResponseErrorFree(newList)!=1:
          logging.warning("new List creation had errors.")

      try:
          lid= newList["id"]
          print "Creating a new List with ID: ", lid
      except ValueError, e:
          logging.warning("new List ID is incorrect")
  

  # Add items to the newly created List
  numI =0
  for iteminfo in iDictsList:
      numI += 1
      print iteminfo["word"].upper(), " : ", iteminfo["defn"]
      if (cfg.FLAGS.debug_lvl == False): #not debug means create OM Lists      
          it = client.create_item(lid,iteminfo)
          isResponseErrorFree(it) # will print out errors if any
    
  if newList:
      print
      print "A New Vocabulary List with", numI, "Words Created"
      print autoTitle
      print
  else:
      print
      print "Debug mode:", cfg.FLAGS.debug_lvl
      print "List was not created"
