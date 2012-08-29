import math
import os #Imports your specific operating system (os)
os.system("cls")    #Windows based systems us
import enchant
import urllib
from nltk.corpus import wordnet as wn
import re
import sys
import string

from text_utils import *

# load dictionary (from enchant)

#Get all 6 letter words starting with Q

#d = enchant.Dict("en_US")

# Add GFlags
# Get meanings


def searchDictFor(dictionary,regpattern,minlength=1,maxlength=15,plurals=False):
    print "Searching for",regpattern
    matchcount = 0
    reg = re.compile(regpattern, re.I)
    m = ""
    for word in dictionary:
        m = reg.match(word)
        if m:
            wlen = word.__len__()
            if wlen<=maxlength and wlen>=minlength:

                # outfile.write(m.group()+' ')
                matchcount += 1            
                print "Found",matchcount, word, type(word).__name__
                
# return matchingWords


#dict to hold all words
d = load_word_dictionary()

print type(d).__name__

dList = d.items()
print type(dList).__name__
print len(dList)

regpattern = 'perm.*$' # should return 'abash' and 'abase'

searchDictFor(d,regpattern,maxlength=6)

#print word_in_dict("found",d)
