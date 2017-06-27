# -*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function
import os
import unittest
import json
from marbles.ie.ccg import Category, parse_ccg_derivation2 as parse_ccg_derivation, sentence_from_pt
from marbles.ie.ccg_derivation import process_ccg_pt, Ccg2Drs
from marbles.ie.compose import CO_VERIFY_SIGNATURES, CO_ADD_STATE_PREDICATES, CO_NO_VERBNET, CO_FAST_RENAME
from marbles.ie.compose import DrsProduction, PropProduction, FunctorProduction, ProductionList
from marbles.ie.drt.drs import *
from marbles.ie.drt.utils import compare_lists_eq
from marbles.ie.parse import parse_drs  #, parse_ccg_derivation
from marbles.ie import grpc
from nltk.tokenize import sent_tokenize
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
