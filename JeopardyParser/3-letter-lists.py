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
from nltk.stem.lancaster import LancasterStemmer
from nltk.stem.porter import PorterStemmer

from unidecode import unidecode
from web_util import encode_json, decode_json

import cfg
from text_utils import *
from om_utils import *
from om_client import *
from fileUtils import *
from webList_to_OM import *

logging.basicConfig(level=logging.DEBUG, filename='jt.log')
logging.basicConfig(level=logging.INFO, filename='jt.log')
logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)

#LOGIC
#Word stemming
#* Make a list of all 3 letter Eng words
#* find all eng words that start with those 3 letters...
#* Calc their stems.
#  If new, add word to list, add stem to stem list.
#* repeat for all words in the list

def searchDictFor(dictionary,regpattern,minlength=1,maxlength=15,plurals=False):
    print "Searching Dictionary for",regpattern
    matchcount = 0
    matches = []
    reg = re.compile(regpattern, re.I)
    m = ""
    for word in dictionary:
        m = reg.match(word)
        if m:
            wlen = word.__len__()
            if wlen<=maxlength and wlen>=minlength:
                matchcount += 1            
                #print "For", regpattern, "Found",matchcount, word
                matches.append(word)

    return matches


def keepOnlyUniqueStemWords(matches):

  # initialize the stemmer object for (optional) stemming later
    porter= PorterStemmer()  
    lancaster=LancasterStemmer()

    unqiueStemMatches=[]
    stems=[]

    for w in matches:
        pstem = porter.stem(w)
        lstem = lancaster.stem(w)
        if pstem not in stems:
            stems.append(pstem)
            unqiueStemMatches.append(w)
            #print w, pstem, lstem
            

    return unqiueStemMatches



if __name__ == '__main__':

  argv = cfg.FLAGS(sys.argv)
  print argv
  if cfg.FLAGS.om_access_token:
      client = OpenMindsThreeLeggedClient(cfg.FLAGS.om_access_token, cfg.FLAGS.om_host)
  else:
      client = OpenMindsTwoLeggedClient(cfg.FLAGS.om_key, cfg.FLAGS.om_secret, cfg.FLAGS.om_host)
  
  # Step 1 Read in the relevant file

  #read the input directory path
  rawDirPath = r'C:\Users\Ram\Root-1\OM-API-Utilities\ListsToBeCreated\3L'
  #run this in chunks of files
  startfile = 0  #first file is 0
  endfile = 15

  #dirList=os.listdir(rawDirPath) #list of filenames
  # ##########################



  # dict to hold all words
  eng_d = load_dictionary(r'C:\Users\Ram\Root-1\OM-API-Utilities\CROSSWD.TXT')

  # norvig dictionary
  norvig_d = load_word_dictionary(r'C:\Users\Ram\Root-1\OM-API-Utilities\word.list.txt')


  #print type(d).__name__

  # print type(dList).__name__
  print len(eng_d)
  print len(norvig_d) #norvig dictionary





#old code
  for w in L3:
      # Step 2: find all eng words that start with those 3 letters...
      regpattern = w.strip()
      print "Trying", w
      matches = searchDictFor(norvig_d,regpattern,minlength=5,maxlength=15,plurals=False)
      uniqueStemMatches = []
      uniqueStemMatches = keepOnlyUniqueStemWords(matches)

      fname = rawDirPath +"\\"+ str(w.strip())+ ".txt"
      print fname

      #for u in uniqueStemMatches:
      #    print u
          
      try:
          write_list_to_file(fname, uniqueStemMatches )      
      except Exception, e:
          print e





#* Calc their stems.
#  If new, add word to list, add stem to stem list.
#* repeat for all words in the list




  
  regpattern = 'perm.*$' # should return 'abash' and 'abase'
  
  searchDictFor(d,regpattern,maxlength=6)
  
#print word_in_dict("found",d)


    #remove all things that are 1 or 2 characters long (punctuation)
  w= [x for x in w if len(x)>2]
    
    #get rid of all stop words
  w= [x for x in w if not x in stopwords]
    
    #stem each word
  w= [stemmer.stem(x,0,len(x)-1) for x in w]
    
