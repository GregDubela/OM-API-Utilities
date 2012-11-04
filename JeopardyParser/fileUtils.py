import gflags
import oauth2
import time
import httplib
import os
os.system("cls")    #Windows based systems us
import logging
import sys
import csv
from cfg import *
from web_util import encode_json, decode_json
from codecs import decode
from unidecode import unidecode
import re

def filenameendsin(fname,filext):
    m = re.search(r'csv$',fname)
    if m:
      return True
    return False


def  write_to_file(fname, string):

  fo = open(fname, "a+") #append
  fo.write(string)
  fo.close()


def  write_list_to_file(fname, lst):
  fo = open(fname, "a+") #append
  for w in lst:
    fo.write("%s\n" % w)
  fo.close()




def  write_object_to_file(fname, obj):

  fo = open(fname, "a+") #append
  fo.write("\n\n\n\n")
  for o in obj:
    #for k,v in o.items():

    try:
      fo.write(unidecode(o["word"]).upper() + " :: " + unidecode(o["defn"]) + "\n")
    except Exception, e:
      print "Unprintable char found:", e

  fo.close()

def  write_soup_to_file(fname, soup):

  fo = open(fname, "a+") #append
  fo.write("\n\n\n\n")
  for tag in soup:
    fo.write(tag)

  fo.close()


def create_list_of_files_for_this_run(rawDirPath,startfile=0, endfile=0):
    # read the input directory path
    fileList=os.listdir(rawDirPath) #list of filenames
    print len(fileList), "files in all."

    if endfile==0: #not specified, so run for all the files
        endfile = len(fileList)

    fList = fileList[startfile:endfile+1]
    return fList



