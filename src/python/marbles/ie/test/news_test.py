# -*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function

import json
import os
import unittest

from nltk.tokenize import sent_tokenize

from marbles.ie import grpc
from marbles.ie.ccg import parse_ccg_derivation2 as parse_ccg_derivation
from marbles.ie.semantics.ccg import process_ccg_pt
from marbles.ie.core.constants import *
from marbles.ie.utils.text import preprocess_sentence

datapath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')


class MyTestCase(unittest.TestCase):

    def setUp(self):
        self.svc = grpc.CcgParserService('easysrl')
        self.stub = self.svc.open_client()

    def tearDown(self):
        self.svc.shutdown()

    # c0053ac368cf2e5c2599f035f2ee4eea.json
    # 9255a890ffe40c05876d8d402044ab11.json
    def test1_JsonFiles(self):
        filelist = os.listdir(datapath)
        allfiles =[]
        for fn in filelist:
            if not os.path.isfile(os.path.join(datapath, fn)):
                continue
            f, x = os.path.splitext(fn)
            if x == '.json' and f == '9255a890ffe40c05876d8d402044ab11':
                allfiles.append(os.path.join(datapath, fn))

        for fn in allfiles:
            with open(fn, 'r') as fd:
                body = json.load(fd, encoding='utf-8')

            smod = preprocess_sentence(body['title'])
            ccgbank = grpc.ccg_parse(self.stub, smod, grpc.DEFAULT_SESSION)
            pt = parse_ccg_derivation(ccgbank)
            ccg = process_ccg_pt(pt)

            ccgbody = {}
            ccgbody['story'] = {
                'title': [x.get_json() for x in ccg.get_span()],
                'paragraphs': []
            }
            paragraphs = filter(lambda y: len(y) != 0, map(lambda x: x.strip(), body['content'].split('\n')))
            i = 0
            for p in paragraphs[i:]:
                sentences = filter(lambda x: len(x.strip()) != 0, sent_tokenize(p))
                sp = []
                j = 0
                for s in sentences[j:]:
                    #print('p:s = %d:%d' % (i, j))
                    smod = preprocess_sentence(s)
                    ccgbank = grpc.ccg_parse(self.stub, smod, grpc.DEFAULT_SESSION)
                    pt = parse_ccg_derivation(ccgbank)
                    ccg = process_ccg_pt(pt, CO_NO_VERBNET | CO_NO_WIKI_SEARCH)
                    sp.append([x.get_json() for x in ccg.get_span()])
                    j += 1
                ccgbody['story']['paragraphs'].append(sp)
                i += 1

            msgbody = json.dumps(ccgbody)

        pass




if __name__ == '__main__':
    unittest.main()
