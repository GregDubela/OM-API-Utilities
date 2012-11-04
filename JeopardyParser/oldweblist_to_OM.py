import re
import sys
import requests
import string
from bs4 import BeautifulSoup


URL = 'http://www.phschool.com/science/biology_place/glossary/a.html'


USEFUL_TAGS = ['div','span']


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


def create_url_itemsDictList(soup):                
    # Two useful classes - header5 and maintext2
    # we need to extract these, skipping problematic entries
    idictList = []

    # First, read the header 5 items
    numW = -1
    word = []
    skipRows = []

    for q in soup(class_="header5"):
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
    for d in soup(class_="maintext2"):
        cut = d.find("span","grey")
        numD+=1
        try:
            print numD, d.get_text()
            dtxt = d.get_text()
            dtxt = re.sub('\n\t\t\t',"",dtxt)
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

    for r in skipRows:
        print "Skip:", r

    for index, w in enumerate(word):
        idict = {}
        if not index in skipRows:
            idict['word'] = w
            idict['defn']= defn[index]
            idictList.append(idict)


    return idictList


def prepare_List_of_URLs():

    BASE_URL = 'http://www.phschool.com/science/biology_place/glossary/'

    urls=[]
    urls.append('http://www.phschool.com/science/biology_place/glossary/jk.html')
    urls.append('http://www.phschool.com/science/biology_place/glossary/qr.html')
    urls.append('http://www.phschool.com/science/biology_place/glossary/wxyz.html')
    for l in string.lowercase[:26]:
        # print BASE_URL + l + '.html'
        urls.append(BASE_URL + l + '.html')

    return urls


if __name__ == '__main__':

    # URLS are now ready

    urls=[]
    urls = prepare_List_of_URLs()

    megaDictList = [] 
    urlItemsDictList = []
    for u in urls:    
        r = requests.get(u)
        soup = BeautifulSoup(r.content,"html5lib")
        title = soup.title.string
        print title
        urlItemsDictList = create_url_itemsDictList(soup)
        for entry in urlItemsDictList:
            megaDictList.append(entry)

    for index, entry in enumerate(megaDictList):
        print index, entry

##########
    sys.exit()
##########

            


    sys.exit()




 #   for bit in soup.find_all("div","maintext2"):        
 #       cut = bit.find("span","grey")
 #       print "------------"
 #       print bit
 #       print cut
 
 #       print bit.get_text()












 #   for string in soup.strings:
 #       try:
#            #print(repr(string))
#            print(string)
#        except:
#            pass
#    


#  for a in soup("onmouseover"):
#      print a.get_text()

#  print  soup.find_all(text=re.compile("response"))


#    for tag in soup.findAll(True):
#        if tag.name in USEFUL_TAGS:
#            print tag.name, ":", tag.contents
#            print tag.renderContents()
#            defn = tag.find("div","maintext2") 
#            if defn:
#                print "defn: ", defn 
#            print "--------"
