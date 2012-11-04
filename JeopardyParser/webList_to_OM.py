import re
import sys
import requests
import string
from bs4 import BeautifulSoup
import gflags

from om_utils import *
import cfg

def escape_special_characters_in_string(ctxt):
    '''
    If a pattern string has special chars, those must be escaped
     before re.sub can work successfully
    '''
    ctxt = re.sub('\(','\\(',ctxt)
    ctxt = re.sub('\)','\\)',ctxt)
    ctxt = re.sub('\[','\\[',ctxt)
    ctxt = re.sub('\]','\\]',ctxt)
    ctxt = re.sub('\+','\\+',ctxt)
    # print repr(ctxt) , "--", repr(dtxt)
    return ctxt


WORD_TAG_NAME = "span"
WORD_CLASS_NAME="qWord lang-en"
DEFN_TAG_NAME = "span"
DEFN_CLASS_NAME="qDef lang-en"

def create_itemsDictList_from_singleURL_soup(soup):                

    idictList = []

    # First, read the header 5 items
    numW = -1
    word = []
    skipRows = []

    #print_all_useful_tags_in_soup(soup)
    #navigate_soup(soup) #prints only the USEFUL_TAGS
    #print soup

    for q in soup(class_=WORD_CLASS_NAME):
        numW+=1
        try:
            print numW, q.get_text()
            word.append(q.get_text())
        except:
            print "UNPRINTABLE WORD"
            word.append("UNPRINTABLE")
            skipRows.append(numW)

    defn = []
    numD = -1
    for d in soup(class_=DEFN_CLASS_NAME):
        cut = d.find("span","grey")
        numD+=1
        try:
            d1 = d.get_text()
            dtxt = d1[:d1.rfind('\n')]  # Slice only till the first line of string
            print "defn ", numD, dtxt, " enddefn."
            dtxt = d1.split('\n', 1)[0] # Slice only till the first line of string
            print dtxt

            if cut:
                ctxt = cut.get_text()
                ctxt = escape_special_characters_in_string(ctxt)
                dtxt = re.sub(ctxt,"",dtxt)
                # print numD, dtxt
            defn.append(dtxt)
        except:
            print "UNPRINTABLE DEFN"
            defn.append("UNPRINTABLE")
            skipRows.append(numD)

    print numW, numD
    if numW != numD:
        print "\n\n Unequal number of Words and Definitions. Aborting URL.\n\n"
        return [] #forget this list

    #print out list of all Rows to be skipped
    for r in skipRows:
        print "Skip:", r

    for index, w in enumerate(word):
        idict = {}
        if not index in skipRows:
            idict['word'] = w
            idict['defn']= defn[index]
            idictList.append(idict)

    return idictList



def navigate_soup(soup):
    for tag in soup.findAll(True):
        if tag.name in USEFUL_TAGS:
            if WORD_CLASS_NAME in str(tag):
                print "word :", tag.contents
            if DEFN_CLASS_NAME in str(tag):
                print "defn :", tag.contents
                print "--------"

            print tag.renderContents()




def prepare_List_of_URLs(BASE_URL, keyword,numPages=100):
    quizlet_search_url = BASE_URL+keyword
    urls=[]
    urls.append(quizlet_search_url+'/')
    
    for l in xrange(2, numPages+1):
        print "Search Page:", l
        urls.append(quizlet_search_url + '/page/'+ str(l) + '/')

    return urls


def create_megaDictList_from_URLS(urls):

    megaDictList = [] #List of dicts from all the URLS
    urlItemsDictList = [] #List of dicts from one single URL

    for u in urls:    
        print u, " ----------"
        print u
        print u, " ----------"
        try:
            r = requests.get(u)
        except:
            continue

        soup = BeautifulSoup(r.content,"html5lib")
        title = soup.title.string
        try:
            print title
        except:
            pass

        urlItemsDictList = create_itemsDictList_from_singleURL_soup(soup)
        for entry in urlItemsDictList:
            megaDictList.append(entry)

    #for index, entry in enumerate(megaDictList):
    #    print index, entry

    print "Big list of Items created"
    return megaDictList


def create_keyword_URLS(urls):

    kwURLs = []
    for u in urls:    
        print "Scan Search Result:", u, "\n"

        try:
            r = requests.get(u)
        except:
            print "Skipping one"
            continue
        soup = BeautifulSoup(r.content,"html5lib")
        title = soup.title.string
        print "Search Page Title", title
        qz_url = print_all_useful_tags_in_soup(soup)

        #put it all together
        for qu in qz_url:
            #print "indiv URL", qu
            kwURLs.append(qu)

    return kwURLs


USEFUL_TAGS = ['a', 'td']
#USEFUL_TAGS = ['numc', 'setresults', 'h1', 'strong']
BASE = 'http://quizlet.com'

def print_all_useful_tags_in_soup(soup):
    numU=0
    uList = []
    for tag in soup.findAll(True):
        if tag.name in USEFUL_TAGS:
            tc = str(tag.contents)
            if 'href' in tc:
                url = re.search('.*<a href="(.*)/"' , tc, re.IGNORECASE)
                try:
                    print url.group(1)
                    u = BASE + url.group(1)+'/'
                    # print u
                    uList.append(u)
                except:
                    pass
    print len(uList), " Useful lists"
    return uList


def  output_list_of_quizlet_kw_URLs(oFname, BASE_URL, keyword, numPages=100):
    search_pages = []
    search_pages = prepare_List_of_URLs(BASE_URL, keyword,numPages)
    # List of URLs to be searched
    print len(search_pages), "Page(s) to search for", keyword

    kwURLs = []
    kwURLs = create_keyword_URLS(search_pages)
    print len(kwURLs)

    for u in kwURLs:
        write_to_file(oFname,str(u)+'\n')
    print "Done Writing to", oFname


def read_urls(jsonfname):
    f = open(jsonfname,'r')
    urls = []
    for line in f.readlines():
        print line
        urls.append(line)
    return urls

    

if __name__ == '__main__':

    argv = cfg.FLAGS(sys.argv)
    print argv

    rt_param = ""
    if len(argv) > 1:
        print argv[1]
        rt_param = argv[1]

    print "Keyword :", cfg.FLAGS.quizlet_kw
    print "Pages to Search:", cfg.FLAGS.PagesToSearch    

    keyword = cfg.FLAGS.quizlet_kw
    jsonfname = "Quizlet_URL_" + keyword + ".html"
    outfname = "Quizlet_Items_" + keyword + ".txt"
    
    BASE_URL = 'http://quizlet.com/subject/'

    # Store the list of the QZL URLs that contain the items
    output_list_of_quizlet_kw_URLs(jsonfname, BASE_URL, keyword, cfg.FLAGS.PagesToSearch)

    if rt_param == "items":
        kwURLs = read_urls(jsonfname)
        itemDictsList = []
        itemDictsList = create_megaDictList_from_URLS(kwURLs)
        write_object_to_file(outfname, itemDictsList) #om_utils Store the JSON for creating other lists
        print "Done writing", outfname

