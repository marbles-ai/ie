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
        self.svc = grpc.CcgParserService('neuralccg')
        self.stub = self.svc.open_client()

    def tearDown(self):
        self.svc.shutdown()

    def test1_Currency_00_0194(self):
        text = r"Without the Cray-3 research and development expenses, the company would have been able to report a profit of $19.3 million for the first half of 1989 rather than the $5.9 million it posted."
        etext = r"Without the Cray-3 research and development expenses , the company would have been able to report a profit of $ 19.3 million for the first half of 1989 rather than the $ 5.9 million it posted"
        mtext = preprocess_sentence(text)
        self.assertEqual(etext, mtext)
        derivation = grpc.ccg_parse(self.stub, mtext, grpc.DEFAULT_SESSION)
        pt = parse_ccg_derivation(derivation)
        sentence = process_ccg_pt(pt, CO_NO_VERBNET|CO_NO_WIKI_SEARCH)
        d = sentence.get_drs(nodups=True)
        dprint(pt_to_ccg_derivation(pt))
        dprint(d)
        fnps = sentence.get_np_nominals()
        nps = [sp.text for r, sp in fnps]
        self.assertTrue('the Cray-3 research and development expenses' in nps)
        self.assertTrue('the company' in nps)
        self.assertTrue('a profit' in nps)
        self.assertTrue('$ 19.3 million' in nps)
        self.assertTrue('the first half' in nps)
        self.assertTrue('the $ 5.9 million' in nps)
        self.assertTrue('1989' in nps)
        fvps = sentence.get_vp_nominals()
        vps = [sp.text for r, sp in fvps]
        self.assertTrue('would have been' in vps)
        self.assertTrue('report' in vps)
        self.assertTrue('posted' in vps)
        would_have_been = filter(lambda x: 'would have been' == x[1].text, fvps)[0][0]
        report = filter(lambda x: 'report' == x[1].text, fvps)[0][0]
        posted = filter(lambda x: 'posted' == x[1].text, fvps)[0][0]
        cray_rnd = filter(lambda x: 'the Cray-3 research and development expenses' == x[1].text, fnps)[0][0]
        company = filter(lambda x: 'the company' == x[1].text, fnps)[0][0]
        profit = filter(lambda x: 'a profit' == x[1].text, fnps)[0][0]
        first_half = filter(lambda x: 'the first half' == x[1].text, fnps)[0][0]
        n1989 = filter(lambda x: '1989' == x[1].text, fnps)[0][0]
        n19_3M = filter(lambda x: '$ 19.3 million' == x[1].text, fnps)[0][0]
        n5_9M = filter(lambda x: 'the $ 5.9 million' == x[1].text, fnps)[0][0]
        self.assertTrue(d.find_condition(Rel('without', [would_have_been, cray_rnd])) is not None)
        self.assertTrue(d.find_condition(Rel('_ARG0', [would_have_been, company])) is not None)
        self.assertTrue(d.find_condition(Rel('_ARG0', [report, company])) is not None)
        self.assertTrue(d.find_condition(Rel('_ARG1', [report, profit])) is not None)
        self.assertTrue(d.find_condition(Rel('of', [profit, n19_3M])) is not None)
        self.assertTrue(d.find_condition(Rel('for', [profit, first_half])) is not None)
        self.assertTrue(d.find_condition(Rel('of', [first_half, n1989])) is not None)
        self.assertTrue(d.find_condition(Rel('_ARG1', [posted, n5_9M])) is not None)

    def test1_Currency_00_0195(self):
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
        fnps = sentence.get_np_nominals()
        nps = [sp.text for r, sp in fnps]
        self.assertTrue('the other hand' in nps)
        self.assertTrue('Cray-Computer' in nps)
        self.assertTrue('$ 20.5 million' in nps)
        fvps = sentence.get_vp_nominals()
        vps = [sp.text for r, sp in fvps]
        self.assertTrue('had' in vps)
        self.assertTrue('existed' in vps)
        self.assertTrue('would have incurred' in vps)

    def test2_Date_00_1228(self):
        text = r"The reduced dividend is payable Jan. 2 to stock of record Dec. 15"
        etext = r"The reduced dividend is payable Jan. 2 to stock of record Dec. 15"
        mtext = preprocess_sentence(text)
        self.assertEqual(etext, mtext)
        derivation = grpc.ccg_parse(self.stub, mtext, grpc.DEFAULT_SESSION)
        pt = parse_ccg_derivation(derivation)
        sentence = process_ccg_pt(pt, CO_NO_VERBNET|CO_NO_WIKI_SEARCH)
        d = sentence.get_drs()
        dprint(pt_to_ccg_derivation(pt))
        dprint(d)
        fnps = sentence.get_np_nominals()
        nps = [sp.text for r, sp in fnps]
        self.assertTrue('The reduced dividend' in nps)
        self.assertTrue('payable' in nps)
        self.assertTrue('Jan. 2' in nps)
        self.assertTrue('Dec. 15' in nps)
        self.assertTrue('stock' in nps)
        self.assertTrue('record' in nps)

    # Same as wsj_2147.1
    def test2_Date_21_0985(self):
        text = r"Annualized interest rates on certain investments as reported by the Federal Reserve Board on a weekly-average basis: 1989 and Wednesday October 4, 1989."
        etext = r"Annualized interest rates on certain investments as reported by the Federal Reserve Board on a weekly-average basis : 1989 and Wednesday October 4 , 1989"
        mtext = preprocess_sentence(text)
        self.assertEqual(etext, mtext)
        derivation = grpc.ccg_parse(self.stub, mtext, grpc.DEFAULT_SESSION)
        pt = parse_ccg_derivation(derivation)
        sentence = process_ccg_pt(pt, CO_NO_VERBNET|CO_NO_WIKI_SEARCH)
        d = sentence.get_drs()
        dprint(pt_to_ccg_derivation(pt))
        dprint(d)
        fnps = sentence.get_np_nominals()
        nps = [sp.text for r, sp in fnps]
        self.assertTrue('Annualized interest rates' in nps)
        self.assertTrue('certain investments' in nps)
        self.assertTrue('the Federal-Reserve-Board' in nps)
        self.assertTrue('a weekly-average basis' in nps)
        self.assertTrue('Wednesday October 4' in nps)




if __name__ == '__main__':
    unittest.main()
