# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import unittest

from marbles.ie import grpc
from marbles.ie.ccg import parse_ccg_derivation2 as parse_ccg_derivation, POS
from marbles.ie.drt.drs import Rel
from marbles.ie.semantics.ccg import process_ccg_pt, pt_to_ccg_derivation
from marbles.ie.core.constants import *
from marbles.ie.utils.text import preprocess_sentence
from marbles.test import dprint, DPRINT_ON


class ConjTest(unittest.TestCase):
    def setUp(self):
        self.svc = grpc.CcgParserService('easysrl')
        self.stub = self.svc.open_client()

    def tearDown(self):
        self.svc.shutdown()

    def test01_AndOfSubj(self):
        text = "John and Paul went to the movies"
        mtext = preprocess_sentence(text)
        derivation = grpc.ccg_parse(self.stub, mtext, grpc.DEFAULT_SESSION)
        pt = parse_ccg_derivation(derivation)
        sentence = process_ccg_pt(pt, CO_NO_VERBNET|CO_NO_WIKI_SEARCH)
        f = sentence.get_functor_phrases(RT_PROPERNAME|RT_EVENT)
        phrases = [sp.text for r, sp in f.iteritems()]
        self.assertTrue('John' in phrases)
        self.assertTrue('Paul' in phrases)
        self.assertTrue('went' in phrases)
        john = filter(lambda x: 'John' == x[1].text, f.iteritems())[0]
        paul = filter(lambda x: 'Paul' == x[1].text, f.iteritems())[0]
        went = filter(lambda x: 'went' == x[1].text, f.iteritems())[0]
        J = john[0]
        P = paul[0]
        E = went[0]
        d = sentence.get_drs()
        dprint(d)
        self.assertTrue(d.find_condition(Rel('_EVENT', [E])) is not None)
        self.assertTrue(d.find_condition(Rel('go', [E])) is not None)
        self.assertTrue(d.find_condition(Rel('John', [J])) is not None)
        self.assertTrue(d.find_condition(Rel('Paul', [P])) is not None)
        self.assertTrue(d.find_condition(Rel('_AGENT', [E, P])) is not None)
        self.assertTrue(d.find_condition(Rel('_AGENT', [E, J])) is not None)

    def test02_AndOfObj(self):
        text = "He saw John and Paul"
        mtext = preprocess_sentence(text)
        derivation = grpc.ccg_parse(self.stub, mtext, grpc.DEFAULT_SESSION)
        pt = parse_ccg_derivation(derivation)
        sentence = process_ccg_pt(pt, CO_NO_VERBNET|CO_NO_WIKI_SEARCH)
        f = sentence.get_functor_phrases(RT_PROPERNAME|RT_EVENT)
        phrases = [sp.text for r, sp in f.iteritems()]
        self.assertTrue('John' in phrases)
        self.assertTrue('Paul' in phrases)
        self.assertTrue('saw' in phrases)
        john = filter(lambda x: 'John' == x[1].text, f.iteritems())[0]
        paul = filter(lambda x: 'Paul' == x[1].text, f.iteritems())[0]
        saw = filter(lambda x: 'saw' == x[1].text, f.iteritems())[0]
        J = john[0]
        P = paul[0]
        E = saw[0]
        d = sentence.get_drs()
        dprint(d)
        # FIXME: wn lemmatizer does not convert saw to see - I guess to to ambiguity
        self.assertTrue(d.find_condition(Rel('_EVENT', [E])) is not None)
        self.assertTrue(d.find_condition(Rel('saw', [E])) is not None)
        self.assertTrue(d.find_condition(Rel('John', [J])) is not None)
        self.assertTrue(d.find_condition(Rel('Paul', [P])) is not None)
        self.assertTrue(d.find_condition(Rel('_THEME', [E, P])) is not None)
        self.assertTrue(d.find_condition(Rel('_THEME', [E, J])) is not None)

    def test03_OrOfObj(self):
        text = "To participate in games or sport"
        mtext = preprocess_sentence(text)
        derivation = grpc.ccg_parse(self.stub, mtext, grpc.DEFAULT_SESSION)
        pt = parse_ccg_derivation(derivation)
        sentence = process_ccg_pt(pt, CO_NO_VERBNET|CO_NO_WIKI_SEARCH)
        f = sentence.get_functor_phrases(RT_ENTITY|RT_EVENT)
        phrases = [sp.text for r, sp in f.iteritems()]
        self.assertTrue('participate' in phrases)
        self.assertTrue('games' in phrases)
        self.assertTrue('sport' in phrases)
        noun1 = filter(lambda x: 'games' == x[1].text, f.iteritems())[0]
        noun2 = filter(lambda x: 'sport' == x[1].text, f.iteritems())[0]
        verb = filter(lambda x: 'participate' == x[1].text, f.iteritems())[0]
        X1 = noun1[0]
        X2 = noun2[0]
        E = verb[0]
        d = sentence.get_drs()
        dprint(d)
        self.assertTrue(d.find_condition(Rel('_EVENT', [E])) is not None)
        self.assertTrue(d.find_condition(Rel('participate', [E])) is not None)
        self.assertTrue(d.find_condition(Rel('games', [X1])) is not None)
        self.assertTrue(d.find_condition(Rel('sport', [X2])) is not None)
        self.assertTrue(d.find_condition(Rel('_THEME', [E, X1])) is not None)
        self.assertTrue(d.find_condition(Rel('_THEME', [E, X2])) is not None)

    def test04_AndOfVerb(self):
        text = "Bell makes and distributes computers"
        mtext = preprocess_sentence(text)
        derivation = grpc.ccg_parse(self.stub, mtext, grpc.DEFAULT_SESSION)
        pt = parse_ccg_derivation(derivation)
        sentence = process_ccg_pt(pt, CO_NO_VERBNET|CO_NO_WIKI_SEARCH)
        f = sentence.get_functor_phrases(RT_PROPERNAME|RT_ENTITY|RT_EVENT)
        phrases = [sp.text for r, sp in f.iteritems()]
        self.assertTrue('Bell' in phrases)
        self.assertTrue('makes' in phrases)
        self.assertTrue('distributes' in phrases)
        self.assertTrue('computers' in phrases)
        verb1 = filter(lambda x: 'makes' == x[1].text, f.iteritems())[0]
        verb2 = filter(lambda x: 'distributes' == x[1].text, f.iteritems())[0]
        agent = filter(lambda x: 'Bell' == x[1].text, f.iteritems())[0]
        theme = filter(lambda x: 'computers' == x[1].text, f.iteritems())[0]
        X1 = agent[0]
        X2 = theme[0]
        E1 = verb1[0]
        E2 = verb2[0]
        d = sentence.get_drs()
        dprint(d)
        self.assertTrue(d.find_condition(Rel('_EVENT', [E1])) is not None)
        self.assertTrue(d.find_condition(Rel('_EVENT', [E2])) is not None)
        self.assertTrue(d.find_condition(Rel('_AGENT', [E1, X1])) is not None)
        self.assertTrue(d.find_condition(Rel('_AGENT', [E2, X1])) is not None)
        self.assertTrue(d.find_condition(Rel('_THEME', [E1, X2])) is not None)
        self.assertTrue(d.find_condition(Rel('_THEME', [E2, X2])) is not None)

    def test05_AndOfVerb_AndOfObj(self):
        text = "Bell makes and distributes computers, electronics, and building products"
        mtext = preprocess_sentence(text)
        derivation = grpc.ccg_parse(self.stub, mtext, grpc.DEFAULT_SESSION)
        pt = parse_ccg_derivation(derivation)
        sentence = process_ccg_pt(pt, CO_NO_VERBNET|CO_NO_WIKI_SEARCH)
        f = sentence.get_functor_phrases(RT_PROPERNAME|RT_ENTITY|RT_EVENT|RT_ATTRIBUTE)
        phrases = [sp.text for r, sp in f.iteritems()]
        self.assertTrue('Bell' in phrases)
        self.assertTrue('makes' in phrases)
        self.assertTrue('distributes' in phrases)
        self.assertTrue('computers' in phrases)
        self.assertTrue('electronics' in phrases)
        # Note if we add RT_EMPTY_DRS to the selection criteria then this phrase becomes 'and building products'
        self.assertTrue('building products' in phrases)
        self.assertEqual(6, len(phrases))
        verb1 = filter(lambda x: 'makes' == x[1].text, f.iteritems())[0]
        verb2 = filter(lambda x: 'distributes' == x[1].text, f.iteritems())[0]
        agent = filter(lambda x: 'Bell' == x[1].text, f.iteritems())[0]
        theme1 = filter(lambda x: 'computers' == x[1].text, f.iteritems())[0]
        theme2 = filter(lambda x: 'electronics' == x[1].text, f.iteritems())[0]
        theme3 = filter(lambda x: 'building products' == x[1].text, f.iteritems())[0]
        X1 = agent[0]
        Y1 = theme1[0]
        Y2 = theme2[0]
        Y3 = theme3[0]
        E1 = verb1[0]
        E2 = verb2[0]
        d = sentence.get_drs()
        dprint(d)
        self.assertTrue(d.find_condition(Rel('_EVENT', [E1])) is not None)
        self.assertTrue(d.find_condition(Rel('_EVENT', [E2])) is not None)
        self.assertTrue(d.find_condition(Rel('_AGENT', [E1, X1])) is not None)
        self.assertTrue(d.find_condition(Rel('_AGENT', [E2, X1])) is not None)
        self.assertTrue(d.find_condition(Rel('_THEME', [E1, Y1])) is not None)
        self.assertTrue(d.find_condition(Rel('_THEME', [E1, Y2])) is not None)
        self.assertTrue(d.find_condition(Rel('_THEME', [E1, Y3])) is not None)
        self.assertTrue(d.find_condition(Rel('_THEME', [E2, Y1])) is not None)
        self.assertTrue(d.find_condition(Rel('_THEME', [E2, Y2])) is not None)
        self.assertTrue(d.find_condition(Rel('_THEME', [E2, Y3])) is not None)

    def test10_OrOfVerb_OrInBrackets(self):
        text = "That which is perceived or known or inferred to have its own distinct existence (living or nonliving)"
        mtext = preprocess_sentence(text)
        derivation = grpc.ccg_parse(self.stub, mtext, grpc.DEFAULT_SESSION)
        pt = parse_ccg_derivation(derivation)
        sentence = process_ccg_pt(pt, CO_NO_VERBNET|CO_NO_WIKI_SEARCH)
        d = sentence.get_drs()
        dprint(pt_to_ccg_derivation(pt))
        dprint(d)
        # RT_EMPTY_DRS adds 'or' to phrases
        f = sentence.get_functor_phrases(lambda x: x.pos is POS.from_cache('WDT') or \
                                                   0 == (x.mask & RT_EMPTY_DRS),
                                         contiguous=False)
        phrases = [sp.text for r, sp in f.iteritems()]
        self.assertTrue('That which living nonliving' in phrases)
        self.assertTrue('perceived' in phrases)
        self.assertTrue('known' in phrases)
        self.assertTrue('inferred' in phrases)
        self.assertTrue('have' in phrases)
        self.assertTrue('is' in phrases)
        verb1 = filter(lambda x: 'perceived' == x[1].text, f.iteritems())[0]
        verb2 = filter(lambda x: 'known' == x[1].text, f.iteritems())[0]
        verb3 = filter(lambda x: 'inferred' == x[1].text, f.iteritems())[0]
        agent = filter(lambda x: 'That which living nonliving' == x[1].text, f.iteritems())[0]
        X1 = agent[0]
        E1 = verb1[0]
        E2 = verb2[0]
        E3 = verb3[0]
        self.assertTrue(d.find_condition(Rel('_EVENT', [E1])) is not None)
        self.assertTrue(d.find_condition(Rel('_EVENT', [E2])) is not None)
        self.assertTrue(d.find_condition(Rel('_EVENT', [E3])) is not None)
        self.assertTrue(d.find_condition(Rel('_AGENT', [E1, X1])) is not None)
        self.assertTrue(d.find_condition(Rel('_AGENT', [E2, X1])) is not None)
        self.assertTrue(d.find_condition(Rel('_AGENT', [E3, X1])) is not None)
