# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import unittest
from marbles.ie import grpc
from marbles.ie.ccg import parse_ccg_derivation2 as parse_ccg_derivation
from marbles.ie.drt.drs import Rel
from marbles.ie.semantics.ccg import process_ccg_pt, pt_to_ccg_derivation
from marbles.ie.core.constants import *
from marbles.ie.utils.text import preprocess_sentence
from marbles.test import dprint


class PossessiveTest(unittest.TestCase):
    def setUp(self):
        self.svc = grpc.CcgParserService('easysrl')
        self.stub = self.svc.open_client()

    def tearDown(self):
        self.svc.shutdown()

    def test1_Ccgbank_00_0036(self):
        text = "Average maturity of the funds' investments lengthened by a day to 41 days, the longest since early August, according to Donoghue's."
        etext = "Average maturity of the funds ' investments lengthened by a day to 41 days , the longest since early August , according to Donoghue 's ."
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
        #self.assertTrue('Average maturity' in nps)
        self.assertTrue('the funds' in nps)
        self.assertTrue('a day' in nps)
        self.assertTrue('41 days' in nps)
        self.assertTrue('the longest' in nps)
        self.assertTrue('early August' in nps)
        fvps = sentence.get_vp_nominals()
        vps = [sp.text for r, sp in fvps]
        self.assertTrue('lengthened' in vps)
        self.assertTrue('according' in vps)

    def test2_Ccgbank_00_0099(self):
        text = "Plans that give advertisers discounts for maintaining or increasing ad spending have become permanent fixtures at the news weeklies and underscore the fierce competition between Newsweek, Time Warner Inc.'s Time magazine, and Mortimer B. Zuckerman's U.S. News & World Report."
        mtext = preprocess_sentence(text)
        derivation = grpc.ccg_parse(self.stub, mtext, grpc.DEFAULT_SESSION)
        pt = parse_ccg_derivation(derivation)
        sentence = process_ccg_pt(pt, CO_NO_VERBNET|CO_NO_WIKI_SEARCH)
        d = sentence.get_drs()
        dprint(pt_to_ccg_derivation(pt))
        dprint(d)
        f = sentence.get_np_nominals()
        phrases = [sp.text for r, sp in f]
        self.assertTrue('Plans' in phrases)
        self.assertTrue('advertisers' in phrases)
        self.assertTrue('discounts' in phrases)
        self.assertTrue('ad spending' in phrases)
        self.assertTrue('permanent fixtures' in phrases)
        self.assertTrue('the news weeklies' in phrases)
        self.assertTrue('the fierce competition' in phrases)
        self.assertTrue("Newsweek" in phrases)
        self.assertTrue("Time-Warner-Inc." in phrases)
        self.assertTrue("Time-magazine" in phrases)
        self.assertTrue("Mortimer-B.-Zuckerman" in phrases)
        self.assertTrue("U.S.-News-&-World-Report" in phrases)
        vf = sentence.get_vp_nominals()
        vphrases = [sp.text for r, sp in vf]
        self.assertTrue('give' in vphrases)
        self.assertTrue('maintaining increasing' in vphrases)
        self.assertTrue('have become' in vphrases)
        self.assertTrue('underscore' in vphrases)
        give = filter(lambda x: 'give' == x[1].text, vf)[0][0]
        become = filter(lambda x: 'have become' == x[1].text, vf)[0][0]
        uscore = filter(lambda x: 'underscore' == x[1].text, vf)[0][0]
        minc = filter(lambda x: 'maintaining increasing' == x[1].text, vf)[0][0]
        plans = filter(lambda x: 'Plans' == x[1].text, f)[0][0]
        advertisers = filter(lambda x: 'advertisers' == x[1].text, f)[0][0]
        discounts = filter(lambda x: 'discounts' == x[1].text, f)[0][0]
        spending = filter(lambda x: 'ad spending' == x[1].text, f)[0][0]
        fixtures = filter(lambda x: 'permanent fixtures' == x[1].text, f)[0][0]
        weeklies = filter(lambda x: 'the news weeklies' == x[1].text, f)[0][0]
        timeinc = filter(lambda x: 'Time-Warner-Inc.' == x[1].text, f)[0][0]
        timemag = filter(lambda x: 'Time-magazine' == x[1].text, f)[0][0]
        mortimer = filter(lambda x: 'Mortimer-B.-Zuckerman' == x[1].text, f)[0][0]
        uswr = filter(lambda x: 'U.S.-News-&-World-Report' == x[1].text, f)[0][0]
        self.assertTrue(d.find_condition(Rel('_ARG0', [give, plans])) is not None)
        self.assertTrue(d.find_condition(Rel('_ARG1', [give, advertisers])) is not None)
        self.assertTrue(d.find_condition(Rel('_ARG2', [give, discounts])) is not None)
        self.assertTrue(d.find_condition(Rel('_ARG0', [minc, plans])) is not None)
        self.assertTrue(d.find_condition(Rel('_ARG1', [minc, spending])) is not None)
        self.assertTrue(d.find_condition(Rel('_ARG0', [become, plans])) is not None)
        self.assertTrue(d.find_condition(Rel('_ARG1', [become, fixtures])) is not None)
        self.assertTrue(d.find_condition(Rel('_POSS', [mortimer, uswr])) is not None)
        self.assertTrue(d.find_condition(Rel('_POSS', [timeinc, timemag])) is not None)


if __name__ == '__main__':
    unittest.main()
