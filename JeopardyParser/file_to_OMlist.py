'''
A Python script to read Jeopardy J!Archive files
Parses the XML files using BeautifulSoup
Creates dictionaries
Then calls the OpenMinds API and creates Lists

Author: Ram Narasimhan
(Using OpenMinds API code authored by Adam Stepinski)
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
from bs4 import BeautifulSoup

from libraries.python.web_util import encode_json, decode_json

import cfg
from text_utils import *
from om_utils import *
from om_client import *

#Steps:
#1. Read 'word' and 'defn' from a list_file
#2. Form Dicts of Lists and Items
#3. Create OM Lists
#4. Record the creations in a separate file

logging.basicConfig(level=logging.DEBUG, filename='jt.log')
logging.basicConfig(level=logging.INFO, filename='jt.log')
logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)

def store_words_and_definitions(filecontents):
    word = []
    defn = []
    useful = 0
    idictsList = []

    iDict = {}
    for index, line in enumerate(filecontents):
        
        if line.strip(): #if line is not a blank
            useful = useful+1
            if useful % 2 == 1:
                addElementToDict("vocab", iDict, "word", line.strip())
            else:
                addElementToDict("vocab", iDict, "defn", line.strip())         
                idictsList.append(iDict)
                iDict =  {}

    return idictsList


if __name__ == '__main__':

  argv = cfg.FLAGS(sys.argv)
  print argv
  if cfg.FLAGS.om_access_token:
      client = OpenMindsThreeLeggedClient(cfg.FLAGS.om_access_token, cfg.FLAGS.om_host)
  else:
      client = OpenMindsTwoLeggedClient(cfg.FLAGS.om_key, cfg.FLAGS.om_secret, cfg.FLAGS.om_host)
  
  #logging.info("Me: %s" % client.get_user('me'))

  # Step 1 Read in the relevant file
  #read the input directory path
  rawDirPath = r'C:\Documents and Settings\u163202\Root-1\OM-API-Utilities\ListsToBeCreated'

  #dirList=os.listdir(rawDirPath) #list of filenames
  #  filename = os.path.join(rawDirPath,"game_id_3704")
  #  filename = os.path.join(rawDirPath,"game_id_3686")
  filename = os.path.join(rawDirPath,"chemistry")
  f = open(filename)

 
  # Step 2. Form Dicts of Items
  # Create a List of Dictionaries  
  itemDictsList = store_words_and_definitions(f)
  # for i in itemDictsList:
  #    print i["word"], i["defn"]

  # Step 3. Create a shell list with List Meta Information
  title = "Chemistry FlexBook List #8"
  tags = ["Chemistry", "flexbook"]
  ldict = createADictWithListMetadata(title, tags, lformat = "vocabulary", sharing = "public")

  # Step 5. Create OM List Shell (Meta)
  if (cfg.FLAGS.debug_lvl == False): #not debug means create OM Lists
      newList =  client.create_list(ldict) # the actual OM list shell creation
      if isResponseErrorFree(newList)!=1:
          logging.warning("new List creation had errors.")

      try:
          lid= newList["id"]
          print "Creating a new List with ID: ", lid
      except ValueError, e:
          logging.warning("new List ID is incorrect")

  # step 6: Add all the items to this new List    
  numI =0
  for iteminfo in itemDictsList:
      numI += 1
      if numI % 8 == 0: #split the list into 8 parts
          print iteminfo["word"].upper(), " : ", iteminfo["defn"]
          if (cfg.FLAGS.debug_lvl == False): #not debug means create OM Lists      
              it = client.create_item(lid, iteminfo)
              isResponseErrorFree(it) # will print out errors if any

  # Step 6. Record the creations in two separate files
  fname = "lists_created.txt"
  jsonfname = "chemistry.json"

  if (cfg.FLAGS.debug_lvl == False): 
      print lid, title
      string = lid + "| " + title + "\n"
      write_to_file(fname, string) #om_utils Store the ListIDs for later reference
      write_object_to_file(jsonfname, itemDictsList) #om_utils Store the JSON for creating other lists




#  sys.exit(0)
