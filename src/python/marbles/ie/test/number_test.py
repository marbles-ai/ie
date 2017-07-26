# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import json
import os
import unittest
from marbles.ie import grpc
from marbles.ie.ccg import parse_ccg_derivation2 as parse_ccg_derivation
from marbles.ie.drt.drs import Rel
from marbles.ie.semantics.ccg import process_ccg_pt, pt_to_ccg_derivation
from marbles.ie.core.constants import *
from marbles.ie.utils.text import preprocess_sentence
from marbles.test import dprint, DPRINT_ON


class PossessiveTest(unittest.TestCase):
    def setUp(self):
        self.svc = grpc.CcgParserService('easysrl')
        self.stub = self.svc.open_client()

    def tearDown(self):
        self.svc.shutdown()

    def test10_Ccgbank_00_0194(self):
        text = r"Without the Cray-3 research and development expenses, the company would have been able to report a profit of $19.3 million for the first half of 1989 rather than the $5.9 million it posted."
        etext = r"Without the Cray-3 research and development expenses , the company would have been able to report a profit of $ 19.3 million for the first half of 1989 rather than the $ 5.9 million it posted"
        mtext = preprocess_sentence(text)
        self.assertEqual(etext, mtext)
        derivation = grpc.ccg_parse(self.stub, mtext, grpc.DEFAULT_SESSION)
        pt = parse_ccg_derivation(derivation)
        sentence = process_ccg_pt(pt, CO_NO_VERBNET|CO_NO_WIKI_SEARCH)
        d = sentence.get_drs()
        dprint(pt_to_ccg_derivation(pt))
        dprint(d)
        fnps = sentence.get_np_functors()
        nps = [sp.text for r, sp in fnps]
        self.assertTrue('the Cray-3 research and development expenses' in nps)
        self.assertTrue('the company' in nps)
        self.assertTrue('a profit' in nps)
        self.assertTrue('19.3 million' in nps)
        self.assertTrue('the first half' in nps)
        self.assertTrue('5.9 million' in nps)
        fvps = sentence.get_vp_functors()
        vps = [sp.text for r, sp in fvps]
        self.assertTrue('' in vps)
        self.assertTrue('' in vps)
        self.assertTrue('' in vps)

    def test10_Ccgbank_00_0195(self):
        text = r"On the other hand, had it existed then, Cray Computer would have incurred a $20.5 million loss."
        etext = r"On the other hand , had it existed then , Cray Computer would have incurred a $ 20.5 million loss ."
        mtext = preprocess_sentence(text)
        self.assertEqual(etext, mtext)
        derivation = grpc.ccg_parse(self.stub, mtext, grpc.DEFAULT_SESSION)
        pt = parse_ccg_derivation(derivation)
        sentence = process_ccg_pt(pt, CO_NO_VERBNET|CO_NO_WIKI_SEARCH)
        d = sentence.get_drs()
        dprint(pt_to_ccg_derivation(pt))
        dprint(d)
        fnps = sentence.get_np_functors()
        nps = [sp.text for r, sp in fnps]
        self.assertTrue('the other hand' in nps)
        self.assertTrue('Cray-Computer' in nps)
        self.assertTrue('20.5 million' in nps)
        fvps = sentence.get_vp_functors()
        vps = [sp.text for r, sp in fvps]
        self.assertTrue('had' in vps)
        self.assertTrue('existed' in vps)
        self.assertTrue('would have incurred' in vps)



if __name__ == '__main__':
    unittest.main()
