# -*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function

import json
import os
import unittest

from nltk.tokenize import sent_tokenize

from marbles.ie import grpc
from marbles.ie.ccg import parse_ccg_derivation2 as parse_ccg_derivation
from marbles.ie.semantics.ccg import process_ccg_pt

datapath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')


class MyTestCase(unittest.TestCase):

    def setUp(self):
        self.svc = grpc.CcgParserService('easysrl')
        self.stub = self.svc.open_client()

    def tearDown(self):
        self.svc.shutdown()

    def test1_LookAtMajorDrugPricing(self):
        with open(os.path.join(datapath, 'c0053ac368cf2e5c2599f035f2ee4eea.json'), 'r') as fd:
            body = json.load(fd, encoding='utf-8')

        ccgbank = grpc.ccg_parse(self.stub, body['title'], grpc.DEFAULT_SESSION)
        pt = parse_ccg_derivation(ccgbank)
        ccg = process_ccg_pt(pt)

        ccgbody = {}
        ccgbody['story'] = {
            'title': [x.get_json() for x in ccg.get_span()],
            'paragraphs': []
        }
        paragraphs = filter(lambda y: len(y) != 0, map(lambda x: x.strip(), body['content'].split('\n')))
        for p in paragraphs:
            sentences = filter(lambda x: len(x.strip()) != 0, sent_tokenize(p))
            sp = []
            for s in sentences:
                ccgbank = grpc.ccg_parse(self.stub, s, grpc.DEFAULT_SESSION)
                pt = parse_ccg_derivation(ccgbank)
                ccg = process_ccg_pt(pt)
                sp.append([x.get_json() for x in ccg.get_span()])
            ccgbody['story']['paragraphs'].append(sp)

        msgbody = json.dumps(ccgbody)

        pass




if __name__ == '__main__':
    unittest.main()
