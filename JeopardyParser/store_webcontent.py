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



    # First, read the header 5 items
    word = []
    defn = []

    defn_flag=0
    word_flag=0
    for tag in soup.findAll(True):
        if tag.name in USEFUL_TAGS:
            wordcloud = tag.find("a")
            if wordcloud:
                wordcloud = re.sub(r'\n',"",str(wordcloud)) #remove linebreaks
                wordcloud = re.sub(r'\s+'," ",str(wordcloud)) #remove extra spaces
                wordt = re.search('<a name=".*>(.*)</a>', str(wordcloud), re.IGNORECASE)
                if wordt: 
                    try:
                        print("word", wordt.group(1))
                        word_flag = 1                
                    except:
                        print "UNPRINTABLE WORD"
                        
            #print tag.renderContents()
            d1 = re.sub(r'\n',"",str(tag)) #remove linebreaks
            d1 = re.sub(r'\s+'," ", d1) #remove extra spaces
            defr = d1.split('</a></b>', 1)
            try: 
                d2 = defr[1]
                # print "full", d2
                d2 = re.sub(r'</?u>',"",d2)
                d2 = re.sub(r'</a>',"",d2)
                d2 = re.sub(r'</?span>',"",d2)
                d2 = re.sub(r'<a href=".*?_blank">',"",d2) #the ? after the * makes it a non-greedy match. Matches as little as possible
                d3 = re.sub(r'\s+'," ", d2) #remove extra spaces
                #print "Defn: ", d3
                defn_flag = 1
            except:
                print "UNPRINTABLE DEFN"

            if word_flag and defn_flag:
                defn.append(d3)
                word.append(wordt.group(1))
                defn_flag=0
                word_flag=0


    print "Items", len(defn), len(word)

    idictList = []
    for index, w in enumerate(word):
        idict = {}
        idict['word'] = w
        idict['defn']= defn[index]
        idictList.append(idict)

    return idictList


USEFUL_TAGS = ['span']
def navigate_soup(soup):
    for tag in soup.findAll(True):
        if tag.name in USEFUL_TAGS:
            wordcloud = tag.find("a")
            if wordcloud:
                wordcloud = re.sub(r'\n',"",str(wordcloud)) #remove linebreaks
                wordcloud = re.sub(r'\s+'," ",str(wordcloud)) #remove extra spaces
                word = re.search('<a name=".*>(.*)</a>', str(wordcloud), re.IGNORECASE)
                if word: 
                    print("word", word.group(1))

            #print tag.renderContents()
            d1 = re.sub(r'\n',"",str(tag)) #remove linebreaks
            d1 = re.sub(r'\s+'," ", d1) #remove extra spaces
            defn = d1.split('</a></b>', 1)
            try: 
                d2 = defn[1]
                # print "full", d2
                d2 = re.sub(r'</?u>',"",d2)
                d2 = re.sub(r'</a>',"",d2)
                d2 = re.sub(r'</?span>',"",d2)
                d2 = re.sub(r'<a href=".*?_blank">',"",d2) #the ? after the * makes it a non-greedy match. Matches as little as possible
                d2 = re.sub(r'\s+'," ", d2) #remove extra spaces
                print d2
            except:
                print "no defn"






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


def write_content_of_URLS(urls):

    megaDictList = [] #List of dicts from all the URLS
    urlItemsDictList = [] #List of dicts from one single URL

    for u in urls:    
        print " ----------"
        print u
        print " ----------"
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

#        f = open("geog1.htm", "w")
#        f.write(str(soup))
# navigate_soup(soup)

        urlItemsDictList = create_itemsDictList_from_singleURL_soup(soup)






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


BASE_URL = "http://www.tuition.com.hk/geography/"

def prepare_List_of_URLs():
    urls=[]
    # for l in string.lowercase[:26]:
    for l in string.lowercase[:26]:
        # print BASE_URL + l + '.html'
        urls.append(BASE_URL + l + '.htm')

    return urls



if __name__ == '__main__':

    argv = cfg.FLAGS(sys.argv)
    print argv

    urls = [] 
    urls = prepare_List_of_URLs()

    #write_content_of_URLS(urls)

    outfname = "hkgeog.json"

    itemDictsList = []
    itemDictsList = create_megaDictList_from_URLS(urls)
    write_object_to_file(outfname, itemDictsList) #om_utils Store the JSON for creating other lists
    print "Done writing", outfname
