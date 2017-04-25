'''
    The purpose of this script is to scrape verbnet information from the internet.
    It will compile a list of example sentences and their relevant verbnet classes

'''

# Utility imports
from lxml import html
import requests
import re

WORDREGEX = re.compile(r"[a-z]+(\.)?([a-z])?")
CLASSREGEX = re.compile(r"[a-zA-Z_]+\-([0-9]+\.)*[0-9]+")

def isword(string):

    return WORDREGEX.match(string)

def isclass(string):

    return CLASSREGEX.match(string)

if __name__ == '__main__':

    # List comprehension for the alphabet
    alphabet = [chr(x) for x in range(ord('A'), ord('Z') + 1)]

    verbs = {}
    classes = []
    # Iterate through each character of the alphabet and shove them into dict
    for letter in ['A']:

        # Make a list of all of our verbs for each starting letter

        # Grab the relevant page
        page = requests.get('http://verbs.colorado.edu/verb-index/index/' + letter + '.php')

        # Convert flat text into manageable tree
        tree = html.fromstring(page.content)

        body = tree[1]

        # This seems really hacky, but their HTML sucks
        candidates = body.xpath('//tr[@class="EntryColor1"]')
        candidates.extend(body.xpath('//tr[@class="EntryColor2"]'))

        # Let's try to cut through the mess
        for i in candidates:

            for j in i.xpath('//td'):

                stripped = ""

                for k in j.xpath('text()'):

                    stripped = k.strip()

                    if isword(stripped):
                        if stripped not in verbs:
                            verbs[stripped] = []
                            print stripped, ": "

        for l in j.xpath('//td/a/text()'):

            if isclass(l):

                if l not in classes:

                    classes.append(l)

    for _class in classes:

        print _class

        page = requests.get('http://verbs.colorado.edu/verb-index/vn/' + _class + '.php')

        tree = html.fromstring(page.content)

        body = tree[1]



        exit()


            # for verb in i.xpath('//td/text()'):

            #     stripped = verb.strip()

            #     if isclass(stripped):

            #         classes[letter].append(stripped)

            #     elif isword(stripped):

            #         verbs[letter].append(stripped)

    #for i, j in verbs.iteritems():
    #    print i, j