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


class ApposTest(unittest.TestCase):
    def setUp(self):
        self.svc = grpc.CcgParserService('easysrl')
        self.stub = self.svc.open_client()

    def tearDown(self):
        self.svc.shutdown()

    def test1_ApposAtBegin(self):
        text = r"A hot-tempered tennis player, Robbie charged the umpire and tried to crack the poor man's skull with a racket."
        mtext = preprocess_sentence(text)
        derivation = grpc.ccg_parse(self.stub, mtext, grpc.DEFAULT_SESSION)
        pt = parse_ccg_derivation(derivation)
        sentence = process_ccg_pt(pt, CO_NO_VERBNET|CO_NO_WIKI_SEARCH)
        d = sentence.get_drs()
        dprint(pt_to_ccg_derivation(pt))
        dprint(d)
        f = sentence.get_np_functors()
        phrases = [sp.text for r, sp in f]
        self.assertTrue('Robbie' in phrases)
        self.assertTrue('A hot-tempered tennis player' in phrases)
        robbie = filter(lambda x: 'Robbie' == x[1].text, f)[0]
        temper = filter(lambda x: 'A hot-tempered tennis player' == x[1].text, f)[0]
        X = robbie[0]
        Y = temper[0]
        self.assertNotEqual(X, Y)
        self.assertTrue(d.find_condition(Rel('_AKA', [X, Y])) is not None)
        self.assertTrue(len(repr(d).split('_AKA')) == 2)

    def test2_ApposInterrupt(self):
        text = r"Reliable, Diane's eleven-year-old beagle, chews holes in the living room carpeting as if he were still a puppy."
        mtext = preprocess_sentence(text)
        derivation = grpc.ccg_parse(self.stub, mtext, grpc.DEFAULT_SESSION)
        pt = parse_ccg_derivation(derivation)
        sentence = process_ccg_pt(pt, CO_NO_VERBNET|CO_NO_WIKI_SEARCH)
        d = sentence.get_drs()
        dprint(pt_to_ccg_derivation(pt))
        dprint(d)
        f = sentence.get_np_functors()
        phrases = [sp.text for r, sp in f]
        self.assertTrue('Reliable' in phrases)
        self.assertTrue("eleven-year-old beagle" in phrases)
        self.assertTrue("Diane" in phrases)
        dog = filter(lambda x: 'Reliable' == x[1].text, f)[0]
        breed = filter(lambda x: "eleven-year-old beagle" == x[1].text, f)[0]
        X = dog[0]
        Y = breed[0]
        self.assertNotEqual(X, Y)
        self.assertTrue(d.find_condition(Rel('_AKA', [X, Y])) is not None)
        self.assertTrue(len(repr(d).split('_AKA')) == 2)

    def test3_ApposInterrupt(self):
        text = r"Robbie, a hot-tempered tennis player, charged the umpire and tried to crack the poor man's skull with a racket."
        mtext = preprocess_sentence(text)
        derivation = grpc.ccg_parse(self.stub, mtext, grpc.DEFAULT_SESSION)
        pt = parse_ccg_derivation(derivation)
        sentence = process_ccg_pt(pt, CO_NO_VERBNET|CO_NO_WIKI_SEARCH)
        d = sentence.get_drs()
        dprint(pt_to_ccg_derivation(pt))
        dprint(d)
        f = sentence.get_np_functors()
        phrases = [sp.text for r, sp in f]
        self.assertTrue('Robbie' in phrases)
        self.assertTrue('a hot-tempered tennis player' in phrases)
        robbie = filter(lambda x: 'Robbie' == x[1].text, f)[0]
        temper = filter(lambda x: 'a hot-tempered tennis player' == x[1].text, f)[0]
        X = robbie[0]
        Y = temper[0]
        self.assertNotEqual(X, Y)
        self.assertTrue(d.find_condition(Rel('_AKA', [X, Y])) is not None)
        self.assertTrue(len(repr(d).split('_AKA')) == 2)

    def test4_ApposInterrupt(self):
        text = r"Bell, a telecommunications company, which is located in Los Angeles, makes and distributes electronics, computers, and building products"
        mtext = preprocess_sentence(text)
        derivation = grpc.ccg_parse(self.stub, mtext, grpc.DEFAULT_SESSION)
        pt = parse_ccg_derivation(derivation)
        sentence = process_ccg_pt(pt, CO_NO_VERBNET|CO_NO_WIKI_SEARCH)
        d = sentence.get_drs()
        dprint(pt_to_ccg_derivation(pt))
        dprint(d)
        f = sentence.get_np_functors()
        phrases = [sp.text for r, sp in f]
        self.assertTrue('Bell' in phrases)
        self.assertTrue('a telecommunications company' in phrases)
        np1 = filter(lambda x: 'Bell' == x[1].text, f)[0]
        np2 = filter(lambda x: 'a telecommunications company' == x[1].text, f)[0]
        X = np1[0]
        Y = np2[0]
        self.assertNotEqual(X, Y)
        self.assertTrue(d.find_condition(Rel('_AKA', [X, Y])) is not None)
        self.assertTrue(len(repr(d).split('_AKA')) == 2)

    def test5_ApposAtEnd(self):
        # FIXME: this test fails. Need wordnet to disambiguate.
        text = r"Upset by the bad call, the crowd cheered Robbie, a hot-tempered tennis player who charged the umpire and tried to crack the poor man's skull with a racket."
        mtext = preprocess_sentence(text)
        derivation = grpc.ccg_parse(self.stub, mtext, grpc.DEFAULT_SESSION)
        pt = parse_ccg_derivation(derivation)
        sentence = process_ccg_pt(pt, CO_NO_VERBNET|CO_NO_WIKI_SEARCH)
        d = sentence.get_drs()
        dprint(pt_to_ccg_derivation(pt))
        dprint(d)
        f = sentence.get_np_functors()
        phrases = [sp.text for r, sp in f]
        self.assertTrue('Robbie' in phrases)
        self.assertTrue('a hot-tempered tennis player' in phrases)
        robbie = filter(lambda x: 'Robbie' == x[1].text, f)[0]
        temper = filter(lambda x: 'a hot-tempered tennis player' == x[1].text, f)[0]
        X = robbie[0]
        Y = temper[0]
        self.assertNotEqual(X, Y)
        self.assertTrue(d.find_condition(Rel('_AKA', [X, Y])) is not None)
        self.assertTrue(len(repr(d).split('_AKA')) == 2)



if __name__ == '__main__':
    unittest.main()
