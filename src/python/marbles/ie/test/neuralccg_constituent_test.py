# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import logging
import os
import re
import unittest

from marbles.ie.ccg import Category, parse_ccg_derivation2 as parse_ccg_derivation
from marbles.ie.ccg.utils import sentence_from_pt
from marbles.ie.drt.drs import *
from marbles.ie.drt.utils import compare_lists_eq
from marbles.ie.parse import parse_drs  #, parse_ccg_derivation
from marbles.ie.semantics.ccg import process_ccg_pt, Ccg2Drs
from marbles.ie.semantics.compose import CO_VERIFY_SIGNATURES, CO_NO_VERBNET, \
    CO_FAST_RENAME, CO_NO_WIKI_SEARCH
from marbles.ie.semantics.compose import DrsProduction, PropProduction, FunctorProduction, ProductionList
from marbles.test import dprint, DPRINT_ON
from marbles.ie import grpc


# Like NLTK's dexpr()
def dexpr(s):
    return parse_drs(s, 'nltk')


def dprint(*args, **kwargs):
    if DPRINT_ON:
        print(*args, **kwargs)


def dprint_constituent_tree(ccg, ctree):
    if DPRINT_ON:
        ccg.print_constituent_tree(ctree)


def dprint_dependency_tree(ccg, dtree):
    if DPRINT_ON:
        ccg.print_dependency_tree(dtree)


_NDS= re.compile(r'(\(<[TL]|\s\))')
def dprint_ccgbank(ccgbank):
    global _NDS
    if DPRINT_ON:
        nds = filter(lambda s: len(s) != 0, [x.strip() for x in _NDS.sub(r'\n\1', ccgbank).split('\n')])
        level = 0
        for nd in nds:
            if nd[0] == '(' and nd[2] == 'T':
                print('  '* level + nd)
                level += 1
            elif nd[0] == ')':
                level -= 1
                print('  '* level + nd)
            else:
                print('  '* level + nd)


def get_constituents_string_list(sent):
    s = []
    for i in range(len(sent.constituents)):
        c = sent.constituents[i]
        headword = c.get_head().idx
        txt = [lex.word if headword != lex.idx else '#'+lex.word for lex in c.span]
        s.append('%s(%s)' % (c.vntype.signature, ' '.join(txt)))
    return s


def get_constituent_string(sent, ch=' '):
    s = get_constituents_string_list(sent)
    return ch.join(s)


class NccgSRLConstituentTest(unittest.TestCase):
    def setUp(self):
        # Print log messages to console
        self.logger = logging.getLogger('marbles')
        self.logger.setLevel(logging.DEBUG)
        if DPRINT_ON:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)
            self.logger.addHandler(console_handler)
        # Load gRPC service
        self.svc = grpc.CcgParserService('neuralccg')
        self.stub = self.svc.open_client()

    def tearDown(self):
        logging.shutdown()
        self.svc.shutdown()

    def test1_PP_Attachment(self):
        # NCCG get the PP attachment wrong
        txt = "Eat spaghetti with meatballs"
        derivation = grpc.ccg_parse(self.stub, txt, grpc.DEFAULT_SESSION)
        pt = parse_ccg_derivation(derivation)
        self.assertIsNotNone(pt)
        s = sentence_from_pt(pt)
        dprint(s)
        sent = process_ccg_pt(pt, CO_NO_VERBNET|CO_NO_WIKI_SEARCH)
        d = sent.get_drs()
        s = d.show(SHOW_LINEAR)
        dprint(s)
        a = get_constituents_string_list(sent)
        dprint('\n'.join(a))
        x = [
            'S_INF(#Eat spaghetti with meatballs)', # 0
                'NP(#spaghetti)',                   # 1
                'NP(#meatballs)',                   # 2
        ]
        self.assertListEqual(x, a)
        x = (0, [(1, []), (2, [])])
        a = sent.get_constituent_tree()
        dprint_constituent_tree(sent, a)
        self.assertEqual(repr(x), repr(a))
        vsent = get_constituent_string(sent.get_verbnet_sentence())
        self.assertEqual('S_INF(#Eat with) NP(#spaghetti) NP(#meatballs)', vsent)

    def test2_Wsj_0056_1(self):
        # RAW 1043
        txt = '''@'''
        derivation = grpc.ccg_parse(self.stub, txt, grpc.DEFAULT_SESSION)
        pt = parse_ccg_derivation(derivation)
        self.assertIsNotNone(pt)
        s = sentence_from_pt(pt)
        dprint(s)
        sent = process_ccg_pt(pt, CO_NO_VERBNET|CO_NO_WIKI_SEARCH)
        d = sent.get_drs()
        s = d.show(SHOW_LINEAR)
        dprint(s)
        a = get_constituents_string_list(sent)
        dprint('\n'.join(a))
        x = [
            'S(#@)'
        ]
        self.assertListEqual(x, a)


if __name__ == '__main__':
    unittest.main()
