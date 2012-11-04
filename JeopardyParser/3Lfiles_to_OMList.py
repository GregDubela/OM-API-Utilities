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

from unidecode import unidecode
from web_util import encode_json, decode_json

import cfg
from text_utils import *
from om_utils import *
from om_client import *
from fileUtils import *
from webList_to_OM import *

#Steps:
#1. Read 'word' and 'defn' from a list_file (or the web)
#2. Form Dicts of Lists and Items
#3. Create OM Lists
#4. Record the creations in a separate file

logging.basicConfig(level=logging.DEBUG, filename='jt.log')
logging.basicConfig(level=logging.INFO, filename='jt.log')
logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)


WORD = "word"
DEFN = "defn"

def store_words_and_definitions(filecontents,linesPerItem=2,splitString=":"):
    word = []
    defn = []
    useful = 0
    idictsList = []
    w_index = 0 #0 means word first. Usual. Rarely, word can be the last part
    d_index = 1
    # w_index = 1 #0 means word first. Usual. Rarely, word can be the last part
    # d_index = 0

    iDict = {}
    for index, line in enumerate(filecontents):        
        if line.strip(): #if line is not a blank
            useful = useful + 1
            if linesPerItem == 2: 
                if useful % 2 == 1:
                    addElementToDict("vocab", iDict, WORD, unidecode(line).strip())
                else:
                    addElementToDict("vocab", iDict, DEFN, unidecode(line).strip()) 
                    idictsList.append(iDict)
                    iDict =  {}
            if linesPerItem == 1: 
                l = unidecode(line).strip()
                itemList = l.split(splitString)
                if len(itemList) == 2:
                    addElementToDict("vocab", iDict, "word", itemList[w_index])
                    addElementToDict("vocab", iDict, "defn", itemList[d_index])
                    idictsList.append(iDict)
                    iDict =  {}

    return idictsList

def read_wordFile(filecontents, splitString=""):
  wList = []
  for index, line in enumerate(filecontents):  
      itemWord = line.strip()
      if splitString:
          l = line.strip()
          itemWord = l.split(splitString)[0]
          itemWord = unidecode(itemWord)
      wList.append(itemWord.strip())
  return(wList)


def attach_WordNet_meanings_and_convert_list_to_item_dicts(filecontents,splitString):

    idictsList = []
    wordsList = read_wordFile(filecontents, splitString)

#    for w in wordsList:
#        print w

    wList = subset_list_of_words_to_those_with_meaning(wordsList, wordlimit=True) #text_utils
    numW = wList.__len__()
    #print numW
    if numW <= 2:
        print "Too few words. Skipping OM list creation."
        print "Please Try another set of Words."
        return idictsList


    for w in wList:
        iDict = {}
        addElementToDict("vocab", iDict, "word", unidecode(w))
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
  
  #read the input directory path
  rawDirPath = r'C:\Users\Ram\Root-1\OM-API-Utilities\ListsToBeCreated\3L'
  #run this in chunks of files
  startfile = 101  #first file is 0
  endfile = 150


###########################
  
# RUNTIME PARAMETERS  
#  READ_DIRECTLY_FROM_WEB = True #if false read from local file
  READ_DIRECTLY_FROM_WEB = False #if false read from local file
#  DEFINITIONS_PROVIDED = True # flag to say if the file has definitions also
  DEFINITIONS_PROVIDED = False # flag to say if the file has definitions also
  delimiter = ':'  # what is the delimiter         
  linesPerItem = 1

  L3 = open("3LetterWords.txt","r").read().splitlines()
  # Step 1 Read in the relevant files
  fileList = create_list_of_files_for_this_run(rawDirPath,startfile,endfile)

  nChunks = 1
  subsectionStart = 1 #default value
  subsectionEnd = nChunks #default value
  #  subsectionStart = 151
#  subsectionEnd = nChunks

  title_base = "Learn Words starting with "
  tags = ["Vocabulary", "Starting with", "word lists"]
  desc = "The first 3 letters are given, can you find the word based on the definition provided?"
  jsonfname = "3L.json"
###########################

  # Step 2. Form Dicts of Items
  # Create a List of Dictionaries  
  if READ_DIRECTLY_FROM_WEB == False:

      for index, fl in enumerate(fileList):
          filename = os.path.join(rawDirPath,fl)
          # print "index:", startfile+index
          print "Now reading ", filename 
          # step 1 open the file
          words = open(filename,"r").read().splitlines()
          print len(words),"# of words"
          if len(words)<5:
              continue

          f = open(filename)
          if DEFINITIONS_PROVIDED:
              # use the following instead, when definitions are present
              itemDictsList = store_words_and_definitions(f, linesPerItem, splitString=delimiter)          
          else:
              # create one dictionary for each item in matchedWords
              itemDictsList = attach_WordNet_meanings_and_convert_list_to_item_dicts(f, splitString=delimiter)

          if len(itemDictsList)<5:
              print "-----------------------"
              continue

          title = title_base + fl.split(".")[0].upper()
          tags.append(fl.split(".")[0])
          # Title is now ready

      # Step 3. Create a shell list with List Meta Information
          ldict = createADictWithListMetadata(title, tags, desc, lformat = "vocabulary", sharing = "public") #omutils
          tags.pop()

      # ######## OPEN MINDS ###########
      # Step 4. Create OM List Shell (Meta)
          if (cfg.FLAGS.debug_lvl == False): #not debug means create OM Lists
              newList =  client.create_list(ldict) # the actual OM list shell creation
              if isResponseErrorFree(newList)!=1:
                  logging.warning("new List creation had errors.")

              try:
                  lid= newList["id"]
                  print "Creating a new List with ID: ", lid
              except ValueError, e:
                  logging.warning("new List ID is incorrect")

      # step 5: Add all the items to this new List    
          numI =0
          numItemsinList = 0

      #  nChunks defined above
      #  subsection defined above         # 0,1,2...nchunks-1
          for iteminfo in itemDictsList:
              numI += 1
              print unidecode(iteminfo["word"]).upper(), " : ", unidecode(iteminfo["defn"])
              if (cfg.FLAGS.debug_lvl == False): #not debug means create OM Lists      
                  try:
                      it = client.create_item(lid, iteminfo)
                      isResponseErrorFree(it) # will print out errors if any
                      numItemsinList += 1
                  except UnicodeDecodeError:
                      print("Bad character in item ", numI)

          print title
          print "-----------------------"

          # Step 6. Record the creations in two separate files
          fname = "lists_created.txt"
          if (cfg.FLAGS.debug_lvl == False): 
              print lid, title, numItemsinList
              string = lid + "| " + title + "| " + str(numItemsinList) + "\n"
              write_to_file(fname, string) #om_utils Store the ListIDs for later reference
              write_object_to_file(jsonfname, itemDictsList) #om_utils Store the JSON for creating other lists

