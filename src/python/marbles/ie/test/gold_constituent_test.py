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


def get_constituents_string_list(sent, noleaves=True):
    s = []
    for c in sent.iterconstituents(dfs=False):
        # ignore leaves - these come last
        if c.isleaf and noleaves:
            break
        s.append('%s(%s)' % (c.ndtype.signature, c.marked_text(minimal=False)))
    return s


def get_constituent_string(sent, ch=' '):
    s = get_constituents_string_list(sent)
    return ch.join(s)


class GoldConstituentTest(unittest.TestCase):
    def setUp(self):
        # Print log messages to console
        self.logger = logging.getLogger('marbles')
        self.logger.setLevel(logging.DEBUG)
        if DPRINT_ON:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)
            self.logger.addHandler(console_handler)

    def tearDown(self):
        logging.shutdown()

    def test1_EasySRL_BoyGirl2(self):
        txt = r'''(<T S[dcl] 1 2> (<T NP 0 2> (<L NP/N DT DT The NP/N>) (<L N NN NN boy N>) ) (<T S[dcl]\NP 0 2>
        (<L (S[dcl]\NP)/(S[b]\NP) MD MD will (S[dcl]\NP)/(S[b]\NP)>) (<T S[b]\NP 0 2>
        (<L (S[b]\NP)/(S[to]\NP) VB VB want (S[b]\NP)/(S[to]\NP)>) (<T S[to]\NP 0 2>
        (<L (S[to]\NP)/(S[b]\NP) TO TO to (S[to]\NP)/(S[b]\NP)>) (<T S[b]\NP 0 2>
        (<L (S[b]\NP)/NP VB VB believe (S[b]\NP)/NP>) (<T NP 0 2> (<L NP/N DT DT the NP/N>)
        (<L N NN NN girl N>) ) ) ) ) ) )'''
        pt = parse_ccg_derivation(txt)
        self.assertIsNotNone(pt)
        s = sentence_from_pt(pt)
        dprint(s)
        ccg = Ccg2Drs(CO_VERIFY_SIGNATURES | CO_NO_VERBNET | CO_NO_WIKI_SEARCH)
        ccg.build_execution_sequence(pt)
        ccg.create_drs()
        ccg.resolve_proper_names()
        ccg.final_rename()
        d = ccg.get_drs()
        s = d.show(SHOW_LINEAR)
        dprint(s)
        x = '[X1,E2,E3,X4| boy(X1),will(E2),_MODAL(E2),want(E2),_EVENT(E2),_ARG0(E2,X1),_ARG1(E2,E3),believe(E3),_EVENT(E3),_ARG0(E3,X1),_ARG1(E3,X4),girl(X4)]'
        self.assertEqual(x, s)
        sent = ccg.sorted_sentence()
        a = get_constituents_string_list(sent, noleaves=False)
        dprint('\n'.join(a))
        x = [
            'S_DCL(The boy #will want to believe the girl)',
            'NP(#The boy)',
            'VP(#will want to believe the girl)',
            'S_INF(#want to believe the girl)',
            'S_INF(#to believe the girl)',
            'S_INF(#believe the girl)',
            'NP(#the girl)',
            'NOUN(#girl)',
            'DET(#the)',
            'VERB(#believe)',
            'TO(#to)',
            'VERB(#want)',
            'VERB(#will)',
            'NOUN(#boy)',
            'DET(#The)',
        ]
        self.assertListEqual(x, a)

    def test2_GOLD_Wsj0002_1(self):
        # ID=wsj_0002.1 PARSER=GOLD NUMPARSE=1
        # Rudolph Agnew, 55 years old and former chairman of Consolidated Gold Fields PLC, was named a nonexecutive
        # director of this British industrial conglomerate.
        # (<T S[dcl] 0 2>
        #   (<T S[dcl] 1 2>
        #       (<T NP 0 2>
        #           (<T NP 0 2>
        #               (<T NP 0 2>
        #                   (<T NP 0 1>
        #                       (<T N 1 2>
        #                           (<L N/N NNP NNP Rudolph N_72/N_72>)
        #                           (<L N NNP NNP Agnew N>)
        #                       )
        #                   )
        #                   (<L , , , , ,>)
        #               )
        #               (<T NP\NP 0 1>
        #                   (<T S[adj]\NP 0 2>
        #                       (<T S[adj]\NP 1 2>
        #                           (<T NP 0 1>
        #                               (<T N 1 2>
        #                                   (<L N/N CD CD 55 N_92/N_92>)
        #                                   (<L N NNS NNS years N>)
        #                               )
        #                           )
        #                           (<L (S[adj]\NP)\NP JJ JJ old (S[adj]\NP_82)\NP_83>)
        #                       )
        #                       (<T S[adj]\NP[conj] 1 2>
        #                           (<L conj CC CC and conj>)
        #                           (<T NP 0 2>
        #                               (<T NP 0 1>
        #                                   (<T N 1 2>
        #                                       (<L N/N JJ JJ former N_102/N_102>)
        #                                       (<L N NN NN chairman N>)
        #                                   )
        #                               )
        #                               (<T NP\NP 0 2>
        #                                   (<L (NP\NP)/NP IN IN of (NP_111\NP_111)/NP_112>)
        #                                   (<T NP 0 1>
        #                                       (<T N 1 2>
        #                                           (<L N/N NNP NNP Consolidated N_135/N_135>)
        #                                           (<T N 1 2>
        #                                               (<L N/N NNP NNP Gold N_128/N_128>)
        #                                               (<T N 1 2>
        #                                                   (<L N/N NNP NNP Fields N_121/N_121>)
        #                                                   (<L N NNP NNP PLC N>)
        #                                               )
        #                                           )
        #                                       )
        #                                   )
        #                               )
        #                           )
        #                       )
        #                   )
        #               )
        #           )
        #           (<L , , , , ,>)
        #       )
        #       (<T S[dcl]\NP 0 2>
        #           (<L (S[dcl]\NP)/(S[pss]\NP) VBD VBD was (S[dcl]\NP_10)/(S[pss]_11\NP_10:B)_11>)
        #           (<T S[pss]\NP 0 2>
        #               (<L (S[pss]\NP)/NP VBN VBN named (S[pss]\NP_18)/NP_19>)
        #                   (<T NP 0 2> (<T NP 1 2>
        #                       (<L NP[nb]/N DT DT a NP[nb]_33/N_33>)
        #                       (<T N 1 2>
        #                           (<L N/N JJ JJ nonexecutive N_28/N_28>)
        #                           (<L N NN NN director N>)
        #                       )
        #                   )
        #                   (<T NP\NP 0 2>
        #                       (<L (NP\NP)/NP IN IN of (NP_41\NP_41)/NP_42>)
        #                       (<T NP 1 2>
        #                           (<L NP[nb]/N DT DT this NP[nb]_63/N_63>)
        #                           (<T N 1 2>
        #                               (<L N/N JJ JJ British N_58/N_58>)
        #                               (<T N 1 2>
        #                                   (<L N/N JJ JJ industrial N_51/N_51>)
        #                                   (<L N NN NN conglomerate N>)
        #                               )
        #                           )
        #                       )
        #                   )
        #               )
        #           )
        #       )
        #   )
        #   (<L . . . . .>)
        # )
        txt = r'''(<T S[dcl] 0 2> (<T S[dcl] 1 2> (<T NP 0 2> (<T NP 0 2> (<T NP 0 2> (<T NP 0 1> (<T N 1 2>
            (<L N/N NNP NNP Rudolph N_72/N_72>) (<L N NNP NNP Agnew N>) ) ) (<L , , , , ,>) ) (<T NP\NP 0 1>
            (<T S[adj]\NP 0 2> (<T S[adj]\NP 1 2> (<T NP 0 1> (<T N 1 2> (<L N/N CD CD 55 N_92/N_92>)
            (<L N NNS NNS years N>) ) ) (<L (S[adj]\NP)\NP JJ JJ old (S[adj]\NP_82)\NP_83>) ) (<T S[adj]\NP[conj] 1 2>
            (<L conj CC CC and conj>) (<T NP 0 2> (<T NP 0 1> (<T N 1 2> (<L N/N JJ JJ former N_102/N_102>)
            (<L N NN NN chairman N>) ) ) (<T NP\NP 0 2> (<L (NP\NP)/NP IN IN of (NP_111\NP_111)/NP_112>) (<T NP 0 1>
            (<T N 1 2> (<L N/N NNP NNP Consolidated N_135/N_135>) (<T N 1 2> (<L N/N NNP NNP Gold N_128/N_128>)
            (<T N 1 2> (<L N/N NNP NNP Fields N_121/N_121>) (<L N NNP NNP PLC N>) ) ) ) ) ) ) ) ) ) ) (<L , , , , ,>) )
            (<T S[dcl]\NP 0 2> (<L (S[dcl]\NP)/(S[pss]\NP) VBD VBD was (S[dcl]\NP_10)/(S[pss]_11\NP_10:B)_11>)
            (<T S[pss]\NP 0 2> (<L (S[pss]\NP)/NP VBN VBN named (S[pss]\NP_18)/NP_19>) (<T NP 0 2> (<T NP 1 2>
            (<L NP[nb]/N DT DT a NP[nb]_33/N_33>) (<T N 1 2> (<L N/N JJ JJ nonexecutive N_28/N_28>)
            (<L N NN NN director N>) ) ) (<T NP\NP 0 2> (<L (NP\NP)/NP IN IN of (NP_41\NP_41)/NP_42>) (<T NP 1 2>
            (<L NP[nb]/N DT DT this NP[nb]_63/N_63>) (<T N 1 2> (<L N/N JJ JJ British N_58/N_58>) (<T N 1 2>
            (<L N/N JJ JJ industrial N_51/N_51>) (<L N NN NN conglomerate N>) ) ) ) ) ) ) ) ) (<L . . . . .>) )'''
        pt = parse_ccg_derivation(txt)
        self.assertIsNotNone(pt)
        s = sentence_from_pt(pt)
        dprint(s)
        ccg = Ccg2Drs(CO_VERIFY_SIGNATURES | CO_NO_VERBNET | CO_NO_WIKI_SEARCH)
        ccg.build_execution_sequence(pt)
        ccg.create_drs()
        ccg.resolve_proper_names()
        ccg.final_rename()
        d = ccg.get_drs()
        s = d.show(SHOW_LINEAR)
        dprint(s)
        sent = ccg.sorted_sentence()
        # Leaves are excluded from this list
        a = get_constituents_string_list(sent)
        dprint('\n'.join(a))
        # Hash indicates head word in constituent
        x = [
            'S_DCL(Rudolph-Agnew , 55 years old and former chairman of Consolidated-Gold-Fields-PLC , #was named a nonexecutive director of this British industrial conglomerate .)',
            'S_DCL(Rudolph-Agnew , 55 years old and former chairman of Consolidated-Gold-Fields-PLC , #was named a nonexecutive director of this British industrial conglomerate)',
            'NP(#Rudolph-Agnew , 55 years old and former chairman of Consolidated-Gold-Fields-PLC)',
            'ADJP(55 years #old and former chairman of Consolidated-Gold-Fields-PLC)',
            'ADJP(55 years #old)',
            'NP(55 #years)',
            'NP(former #chairman of Consolidated-Gold-Fields-PLC)',
            'NP(former #chairman)',
            'PP(#of Consolidated-Gold-Fields-PLC)',
            'VP(#was named a nonexecutive director of this British industrial conglomerate)',
            'VP(#named a nonexecutive director of this British industrial conglomerate)',
            'NP(a nonexecutive #director of this British industrial conglomerate)',
            'NP(a nonexecutive #director)',
            'NP(nonexecutive #director)',
            'PP(#of this British industrial conglomerate)',
            'NP(this British industrial #conglomerate)',
            'NP(British industrial #conglomerate)',
            'NP(industrial #conglomerate)',
        ]
        self.assertListEqual(x, a)
        sp = sent.find_span('old and former chairman')
        self.assertIsNotNone(sp)
        c = sent.find_constituent(sp)
        self.assertIsNotNone(c)
        self.assertEqual(c.span.text, '55 years old and former chairman of Consolidated-Gold-Fields-PLC')

    def test2_GOLD_Wsj0001_1(self):
        # ID=wsj_0001.1 PARSER=GOLD NUMPARSE=1
        # Pierre Vinken, 61 years old, will join the board as a nonexecutive director Nov 29.
        # (<T S[dcl] 0 2>
        #   (<T S[dcl] 1 2>
        #       (<T NP 0 2>
        #           (<T NP 0 2>
        #               (<T NP 0 2>
        #                   (<T NP 0 1>
        #                       (<T N 1 2>
        #                           (<L N/N NNP NNP Pierre N_73/N_73>)
        #                           (<L N NNP NNP Vinken N>)
        #                       )
        #                   )
        #                   (<L , , , , ,>)
        #               )
        #               (<T NP\NP 0 1>
        #                   (<T S[adj]\NP 1 2>
        #                       (<T NP 0 1>
        #                           (<T N 1 2>
        #                               (<L N/N CD CD 61 N_93/N_93>)
        #                               (<L N NNS NNS years N>)
        #                           )
        #                       )
        #                       (<L (S[adj]\NP)\NP JJ JJ old (S[adj]\NP_83)\NP_84>)
        #                   )
        #               )
        #           )
        #           (<L , , , , ,>)
        #       )
        #       (<T S[dcl]\NP 0 2>
        #           (<L (S[dcl]\NP)/(S[b]\NP) MD MD will (S[dcl]\NP_10)/(S[b]_11\NP_10:B)_11>)
        #           (<T S[b]\NP 0 2>
        #               (<T S[b]\NP 0 2>
        #                   (<T (S[b]\NP)/PP 0 2>
        #                       (<L ((S[b]\NP)/PP)/NP VB VB join ((S[b]\NP_20)/PP_21)/NP_22>)
        #                       (<T NP 1 2>
        #                           (<L NP[nb]/N DT DT the NP[nb]_29/N_29>)
        #                           (<L N NN NN board N>)
        #                       )
        #                   )
        #                   (<T PP 0 2>
        #                       (<L PP/NP IN IN as PP/NP_34>)
        #                       (<T NP 1 2>
        #                           (<L NP[nb]/N DT DT a NP[nb]_48/N_48>)
        #                           (<T N 1 2>
        #                               (<L N/N JJ JJ nonexecutive N_43/N_43>)
        #                               (<L N NN NN director N>)
        #                           )
        #                       )
        #                   )
        #               )
        #               (<T (S\NP)\(S\NP) 0 2>
        #                   (<L ((S\NP)\(S\NP))/N[num] NNP NNP Nov. ((S_61\NP_56)_61\(S_61\NP_56)_61)/N[num]_62>)
        #                   (<L N[num] CD CD 29 N[num]>)
        #               )
        #           )
        #       )
        #   )
        #   (<L . . . . .>)
        # )
        txt = r'''(<T S[dcl] 0 2> (<T S[dcl] 1 2> (<T NP 0 2> (<T NP 0 2> (<T NP 0 2> (<T NP 0 1> (<T N 1 2>
            (<L N/N NNP NNP Pierre N_73/N_73>) (<L N NNP NNP Vinken N>) ) ) (<L , , , , ,>) ) (<T NP\NP 0 1>
            (<T S[adj]\NP 1 2> (<T NP 0 1> (<T N 1 2> (<L N/N CD CD 61 N_93/N_93>) (<L N NNS NNS years N>) ) )
            (<L (S[adj]\NP)\NP JJ JJ old (S[adj]\NP_83)\NP_84>) ) ) ) (<L , , , , ,>) ) (<T S[dcl]\NP 0 2>
            (<L (S[dcl]\NP)/(S[b]\NP) MD MD will (S[dcl]\NP_10)/(S[b]_11\NP_10:B)_11>) (<T S[b]\NP 0 2>
            (<T S[b]\NP 0 2> (<T (S[b]\NP)/PP 0 2> (<L ((S[b]\NP)/PP)/NP VB VB join ((S[b]\NP_20)/PP_21)/NP_22>)
            (<T NP 1 2> (<L NP[nb]/N DT DT the NP[nb]_29/N_29>) (<L N NN NN board N>) ) ) (<T PP 0 2>
            (<L PP/NP IN IN as PP/NP_34>) (<T NP 1 2> (<L NP[nb]/N DT DT a NP[nb]_48/N_48>) (<T N 1 2>
            (<L N/N JJ JJ nonexecutive N_43/N_43>) (<L N NN NN director N>) ) ) ) ) (<T (S\NP)\(S\NP) 0 2>
            (<L ((S\NP)\(S\NP))/N[num] NNP NNP Nov. ((S_61\NP_56)_61\(S_61\NP_56)_61)/N[num]_62>)
            (<L N[num] CD CD 29 N[num]>) ) ) ) ) (<L . . . . .>) )'''
        pt = parse_ccg_derivation(txt)
        self.assertIsNotNone(pt)
        s = sentence_from_pt(pt)
        dprint(s)
        ccg = Ccg2Drs(CO_VERIFY_SIGNATURES | CO_NO_VERBNET | CO_NO_WIKI_SEARCH)
        ccg.build_execution_sequence(pt)
        ccg.create_drs()
        ccg.resolve_proper_names()
        ccg.final_rename()
        d = ccg.get_drs()
        s = d.show(SHOW_LINEAR)
        dprint(s)
        sent = ccg.sorted_sentence()
        a = get_constituents_string_list(sent)
        # FIXME: VP(will #join) should be S_INF(will #join).
        # Issues occurs because I convert modal-verb combinator categories to modifiers. Must be fixed on functor
        # creation - Lexeme.get_production()
        # will: (S[dcl]\NP)/(S[b]/NP) -> (S\NP)/(S/NP)
        x = [
            'S_DCL(Pierre-Vinken , 61 years old , #will join the board as a nonexecutive director Nov. 29 .)',
            'S_DCL(Pierre-Vinken , 61 years old , #will join the board as a nonexecutive director Nov. 29)',
            'NP(#Pierre-Vinken , 61 years old)',
            'ADJP(61 years #old)',
            'NP(61 #years)',
            'VP(#will join the board as a nonexecutive director Nov. 29)',
            'S_INF(#join the board as a nonexecutive director Nov. 29)',
            'S_INF(#join the board as a nonexecutive director)',
            'VP(#join the board)',
            'NP(the #board)',
            'PP(#as a nonexecutive director)',
            'NP(a nonexecutive #director)',
            'NP(nonexecutive #director)',
            'ADJP(#Nov. 29)',
        ]
        dprint('\n'.join(a))
        self.assertListEqual(x, a)
        sp = sent.find_span('board as a')
        self.assertIsNotNone(sp)
        c = sent.find_constituent(sp)
        self.assertIsNotNone(c)
        self.assertEqual(c.span.text, 'join the board as a nonexecutive director')

    def test2_GOLD_Wsj0001_2(self):
        # Mr. Vinken is chairman of Elsevier N.V. , the Dutch publishing group .
        #
        # PARG
        # 1      0      N/N             1      Vinken Mr.
        # 1      2      (S[dcl]\NP)/NP  1      Vinken is
        # 3      2      (S[dcl]\NP)/NP  2      chairman is
        # 3      4      (NP\NP)/NP      1      chairman of
        # 6      4      (NP\NP)/NP      2      N.V. of
        # 6      5      N/N             1      N.V. Elsevier
        # 11     4      (NP\NP)/NP      2      group of
        # 11     8      NP[nb]/N        1      group the
        # 11     9      N/N             1      group Dutch
        # 11     10     N/N             1      group publishing
        txt = r'''
(<T S[dcl] 0 2>
    (<T S[dcl] 1 2>
        (<T NP 0 1>
            (<T N 1 2>
                (<L N/N NNP NNP Mr. N_142/N_142>)
                (<L N NNP NNP Vinken N>)
            )
        )
        (<T S[dcl]\NP 0 2>
            (<L (S[dcl]\NP)/NP VBZ VBZ is (S[dcl]\NP_87)/NP_88>)
            (<T NP 0 2>
                (<T NP 0 1>
                    (<L N NN NN chairman N>)
                )
                (<T NP\NP 0 2>
                    (<L (NP\NP)/NP IN IN of (NP_99\NP_99)/NP_100>)
                    (<T NP 0 2>
                        (<T NP 0 1>
                            (<T N 1 2>
                                (<L N/N NNP NNP Elsevier N_109/N_109>)
                                (<L N NNP NNP N.V. N>)
                            )
                        )
                        (<T NP[conj] 1 2>
                            (<L , , , , ,>)
                            (<T NP 1 2>
                                (<L NP[nb]/N DT DT the NP[nb]_131/N_131>)
                                (<T N 1 2>
                                    (<L N/N NNP NNP Dutch N_126/N_126>)
                                    (<T N 1 2>
                                        (<L N/N VBG VBG publishing N_119/N_119>)
                                        (<L N NN NN group N>)
                                    )
                                )
                            )
                        )
                    )
                )
            )
        )
    )
    (<L . . . . .>)
)'''
        pt = parse_ccg_derivation(txt)
        s = sentence_from_pt(pt)
        dprint(s)
        self.assertIsNotNone(pt)
        ccg = Ccg2Drs(CO_VERIFY_SIGNATURES | CO_NO_VERBNET | CO_NO_WIKI_SEARCH)
        ccg.build_execution_sequence(pt)
        ccg.create_drs()
        ccg.resolve_proper_names()
        ccg.final_rename()
        d = ccg.get_drs()
        s = d.show(SHOW_LINEAR)
        dprint(s)
        sent = ccg.sorted_sentence()
        a = get_constituents_string_list(sent)
        x = [
            'S_DCL(Mr.-Vinken #is chairman of Elsevier-N.V. , the Dutch publishing group .)',
            'S_DCL(Mr.-Vinken #is chairman of Elsevier-N.V. , the Dutch publishing group)',
            'VP(#is chairman of Elsevier-N.V. , the Dutch publishing group)',
            'NP(#chairman of Elsevier-N.V. , the Dutch publishing group)',
            'PP(#of Elsevier-N.V. , the Dutch publishing group)',
            'NP(#Elsevier-N.V. , the Dutch publishing group)',
            'NP(the Dutch publishing #group)',
            'NP(Dutch publishing #group)',
            'NP(publishing #group)',
        ]
        dprint('\n'.join(a))
        self.assertListEqual(x, a)

    def test2_GOLD_Wsj0003_1(self):
        # A form of asbestos once used to make Kent cigarette filters has caused a high percentage of cancer deaths
        # among a group of workers exposed to it more than 30 years ago, researchers reported.
        # ID=wsj_0003.1 PARSER=GOLD NUMPARSE=1
        # (<T S[dcl] 0 2>
        #   (<T S[dcl] 1 2>
        #       (<T S[dcl] 1 2>
        #           (<T NP 0 2>
        #               (<T NP 0 2>
        #                   (<T NP 1 2>
        #                       (<L NP[nb]/N DT DT A NP[nb]_166/N_166>)
        #                       (<L N NN NN form N>)
        #                   )
        #                   (<T NP\NP 0 2>
        #                       (<L (NP\NP)/NP IN IN of (NP_174\NP_174)/NP_175>)
        #                       (<T NP 0 1>
        #                           (<L N NN NN asbestos N>)
        #                       )
        #                   )
        #               )
        #               (<T NP\NP 0 1>
        #                   (<T S[pss]\NP 1 2>
        #                       (<L (S\NP)/(S\NP) RB RB once (S_235\NP_230)_235/(S_235\NP_230)_235>)
        #                       (<T S[pss]\NP 0 2>
        #                           (<L (S[pss]\NP)/(S[to]\NP) VBN VBN used (S[pss]\NP_187)/(S[to]_188\NP_187:B)_188>)
        #                           (<T S[to]\NP 0 2>
        #                               (<L (S[to]\NP)/(S[b]\NP) TO TO to (S[to]\NP_197)/(S[b]_198\NP_197:B)_198>)
        #                               (<T S[b]\NP 0 2>
        #                                   (<L (S[b]\NP)/NP VB VB make (S[b]\NP_205)/NP_206>)
        #                                   (<T NP 0 1>
        #                                       (<T N 1 2>
        #                                           (<L N/N NNP NNP Kent N_222/N_222>)
        #                                           (<T N 1 2>
        #                                               (<L N/N NN NN cigarette N_215/N_215>)
        #                                               (<L N NNS NNS filters N>)
        #                                           )
        #                                       )
        #                                   )
        #                               )
        #                           )
        #                       )
        #                   )
        #               )
        #           )
        #           (<T S[dcl]\NP 0 2>
        #               (<L (S[dcl]\NP)/(S[pt]\NP) VBZ VBZ has (S[dcl]\NP_23)/(S[pt]_24\NP_23:B)_24>)
        #               (<T S[pt]\NP 0 2>
        #                   (<L (S[pt]\NP)/NP VBN VBN caused (S[pt]\NP_31)/NP_32>)
        #                       (<T NP 0 2>
        #                           (<T NP 0 2>
        #                               (<T NP 1 2>
        #                                   (<L NP[nb]/N DT DT a NP[nb]_46/N_46>)
        #                                   (<T N 1 2>
        #                                       (<L N/N JJ JJ high N_41/N_41>)
        #                                       (<L N NN NN percentage N>)
        #                                   )
        #                               )
        #                               (<T NP\NP 0 2>
        #                                   (<L (NP\NP)/NP IN IN of (NP_54\NP_54)/NP_55>)
        #                                   (<T NP 0 1>
        #                                       (<T N 1 2>
        #                                           (<L N/N NN NN cancer N_64/N_64>)
        #                                           (<L N NNS NNS deaths N>)
        #                                       )
        #                                   )
        #                               )
        #                           )
        #                           (<T NP\NP 0 2>
        #                               (<L (NP\NP)/NP IN IN among (NP_73\NP_73)/NP_74>)
        #                               (<T NP 0 2>
        #                                   (<T NP 1 2>
        #                                       (<L NP[nb]/N DT DT a NP[nb]_81/N_81>)
        #                                       (<L N NN NN group N>)
        #                                   )
        #                                   (<T NP\NP 0 2>
        #                                       (<L (NP\NP)/NP IN IN of (NP_89\NP_89)/NP_90>)
        #                                       (<T NP 0 2>
        #                                           (<T NP 0 1>
        #                                               (<L N NNS NNS workers N>)
        #                                           )
        #                                           (<T NP\NP 0 1>
        #                                               (<T S[pss]\NP 0 2>
        #                                                   (<T S[pss]\NP 0 2>
        #                                                       (<L (S[pss]\NP)/PP VBN VBN exposed (S[pss]\NP_100)/PP_101>)
        #                                                       (<T PP 0 2>
        #                                                           (<L PP/NP TO TO to PP/NP_106>)
        #                                                           (<L NP PRP PRP it NP>)
        #                                                       )
        #                                                   )
        #                                                   (<T (S\NP)\(S\NP) 1 2>
        #                                                       (<T NP 0 1>
        #                                                           (<T N 1 2>
        #                                                               (<T N/N 1 2>
        #                                                                   (<T (N/N)/(N/N) 1 2>
        #                                                                       (<L S[adj]\NP RBR RBR more S[adj]\NP_153>)
        #                                                                       (<L ((N/N)/(N/N))\(S[adj]\NP) IN IN than ((N_147/N_139)_147/(N_147/N_139)_147)\(S[adj]_148\NP_142)_148>)
        #                                                                   )
        #                                                                   (<L N/N CD CD 30 N_131/N_131>)
        #                                                               )
        #                                                               (<L N NNS NNS years N>)
        #                                                           )
        #                                                       )
        #                                                       (<L ((S\NP)\(S\NP))\NP IN IN ago ((S_121\NP_116)_121\(S_121\NP_116)_121)\NP_122>)
        #                                                   )
        #                                               )
        #                                           )
        #                                       )
        #                                   )
        #                               )
        #                           )
        #                       )
        #                   )
        #               )
        #           )
        #           (<T S[dcl]\S[dcl] 1 2>
        #               (<L , , , , ,>)
        #               (<T S[dcl]\S[dcl] 1 2>
        #                   (<T NP 0 1>
        #                       (<L N NNS NNS researchers N>)
        #                   )
        #                   (<L (S[dcl]\S[dcl])\NP VBD VBD reported (S[dcl]\S[dcl]_8)\NP_9>)
        #               )
        #           )
        #       )
        #       (<L . . . . .>)
        #   )
        txt = r'''(<T S[dcl] 0 2> (<T S[dcl] 1 2> (<T S[dcl] 1 2> (<T NP 0 2> (<T NP 0 2> (<T NP 1 2>
        (<L NP[nb]/N DT DT A NP[nb]_166/N_166>) (<L N NN NN form N>) ) (<T NP\NP 0 2>
        (<L (NP\NP)/NP IN IN of (NP_174\NP_174)/NP_175>) (<T NP 0 1> (<L N NN NN asbestos N>) ) ) ) (<T NP\NP 0 1>
        (<T S[pss]\NP 1 2> (<L (S\NP)/(S\NP) RB RB once (S_235\NP_230)_235/(S_235\NP_230)_235>) (<T S[pss]\NP 0 2>
        (<L (S[pss]\NP)/(S[to]\NP) VBN VBN used (S[pss]\NP_187)/(S[to]_188\NP_187:B)_188>) (<T S[to]\NP 0 2>
        (<L (S[to]\NP)/(S[b]\NP) TO TO to (S[to]\NP_197)/(S[b]_198\NP_197:B)_198>) (<T S[b]\NP 0 2>
        (<L (S[b]\NP)/NP VB VB make (S[b]\NP_205)/NP_206>) (<T NP 0 1> (<T N 1 2> (<L N/N NNP NNP Kent N_222/N_222>)
        (<T N 1 2> (<L N/N NN NN cigarette N_215/N_215>) (<L N NNS NNS filters N>) ) ) ) ) ) ) ) ) ) (<T S[dcl]\NP 0 2>
        (<L (S[dcl]\NP)/(S[pt]\NP) VBZ VBZ has (S[dcl]\NP_23)/(S[pt]_24\NP_23:B)_24>) (<T S[pt]\NP 0 2>
        (<L (S[pt]\NP)/NP VBN VBN caused (S[pt]\NP_31)/NP_32>) (<T NP 0 2> (<T NP 0 2> (<T NP 1 2>
        (<L NP[nb]/N DT DT a NP[nb]_46/N_46>) (<T N 1 2> (<L N/N JJ JJ high N_41/N_41>) (<L N NN NN percentage N>) ) )
        (<T NP\NP 0 2> (<L (NP\NP)/NP IN IN of (NP_54\NP_54)/NP_55>) (<T NP 0 1> (<T N 1 2>
        (<L N/N NN NN cancer N_64/N_64>) (<L N NNS NNS deaths N>) ) ) ) ) (<T NP\NP 0 2>
        (<L (NP\NP)/NP IN IN among (NP_73\NP_73)/NP_74>) (<T NP 0 2> (<T NP 1 2> (<L NP[nb]/N DT DT a NP[nb]_81/N_81>)
        (<L N NN NN group N>) ) (<T NP\NP 0 2> (<L (NP\NP)/NP IN IN of (NP_89\NP_89)/NP_90>) (<T NP 0 2> (<T NP 0 1>
        (<L N NNS NNS workers N>) ) (<T NP\NP 0 1> (<T S[pss]\NP 0 2> (<T S[pss]\NP 0 2>
        (<L (S[pss]\NP)/PP VBN VBN exposed (S[pss]\NP_100)/PP_101>) (<T PP 0 2> (<L PP/NP TO TO to PP/NP_106>)
        (<L NP PRP PRP it NP>) ) ) (<T (S\NP)\(S\NP) 1 2> (<T NP 0 1> (<T N 1 2> (<T N/N 1 2> (<T (N/N)/(N/N) 1 2>
        (<L S[adj]\NP RBR RBR more S[adj]\NP_153>)
        (<L ((N/N)/(N/N))\(S[adj]\NP) IN IN than ((N_147/N_139)_147/(N_147/N_139)_147)\(S[adj]_148\NP_142)_148>) )
        (<L N/N CD CD 30 N_131/N_131>) ) (<L N NNS NNS years N>) ) )
        (<L ((S\NP)\(S\NP))\NP IN IN ago ((S_121\NP_116)_121\(S_121\NP_116)_121)\NP_122>) ) ) ) ) ) ) ) ) ) ) )
        (<T S[dcl]\S[dcl] 1 2> (<L , , , , ,>) (<T S[dcl]\S[dcl] 1 2> (<T NP 0 1> (<L N NNS NNS researchers N>) )
        (<L (S[dcl]\S[dcl])\NP VBD VBD reported (S[dcl]\S[dcl]_8)\NP_9>) ) ) ) (<L . . . . .>) )'''
        pt = parse_ccg_derivation(txt)
        s = sentence_from_pt(pt)
        dprint(s)
        self.assertIsNotNone(pt)
        ccg = Ccg2Drs(CO_VERIFY_SIGNATURES | CO_NO_VERBNET | CO_NO_WIKI_SEARCH)
        ccg.build_execution_sequence(pt)
        ccg.create_drs()
        ccg.final_rename()
        d = ccg.get_drs()
        s = d.show(SHOW_LINEAR)
        dprint(s)
        sent = ccg.sorted_sentence()
        a = get_constituents_string_list(sent)
        x = [
            'S_DCL(A form of asbestos once used to make Kent cigarette filters has caused a high percentage of cancer deaths among a group of workers exposed to it more than 30 years ago , researchers #reported .)',
            'S_DCL(A form of asbestos once used to make Kent cigarette filters has caused a high percentage of cancer deaths among a group of workers exposed to it more than 30 years ago , researchers #reported)',
            'S_DCL(A form of asbestos once used to make Kent cigarette filters #has caused a high percentage of cancer deaths among a group of workers exposed to it more than 30 years ago)',
            'NP(A #form of asbestos once used to make Kent cigarette filters)',
            'NP(A #form of asbestos)',
            'NP(A #form)',
            'PP(#of asbestos)',
            'VP(once #used to make Kent cigarette filters)',
            'VP(#used to make Kent cigarette filters)',
            'S_INF(#to make Kent cigarette filters)',
            'S_INF(#make Kent cigarette filters)',
            'NP(Kent cigarette #filters)',
            'NP(cigarette #filters)',
            'VP(#has caused a high percentage of cancer deaths among a group of workers exposed to it more than 30 years ago)',
            'VP(#caused a high percentage of cancer deaths among a group of workers exposed to it more than 30 years ago)',
            'NP(a high #percentage of cancer deaths among a group of workers exposed to it more than 30 years ago)',
            'NP(a high #percentage of cancer deaths)',
            'NP(a high #percentage)',
            'NP(high #percentage)',
            'PP(#of cancer deaths)',
            'NP(cancer #deaths)',
            'PP(#among a group of workers exposed to it more than 30 years ago)',
            'NP(a #group of workers exposed to it more than 30 years ago)',
            'NP(a #group)',
            'PP(#of workers exposed to it more than 30 years ago)',
            'NP(#workers exposed to it more than 30 years ago)',
            'VP(#exposed to it more than 30 years ago)',
            'VP(#exposed to it)',
            'PP(#to it)',
            'ADJP(more than 30 years #ago)',
            'NP(more than 30 #years)',
            'NP(more than #30)',
            'NP(more #than)',
            'VP(researchers #reported)',
        ]
        dprint('\n'.join(a))
        self.assertListEqual(x, a)

    def test2_GOLD_Wsj0051_13(self):
        txt = r'''
(<T S[dcl] 0 2> 
  (<T S[dcl] 1 2> 
    (<T NP 1 2> 
      (<L NP[nb]/N DT DT The NP[nb]_273/N_273>) 
      (<L N NNS NNS bids N>) 
    ) 
    (<T S[dcl]\NP 1 2> 
      (<T (S\NP)/(S\NP) 1 2> 
        (<L , , , , ,>) 
        (<T (S\NP)/(S\NP) 0 2> 
          (<T S[dcl]/S[dcl] 1 2> 
            (<T S/(S\NP) 0 1> 
              (<L NP PRP PRP he NP>) 
            ) 
            (<L (S[dcl]\NP)/S[dcl] VBD VBD added (S[dcl]\NP_242)/S[dcl]_243>) 
          ) 
          (<L , , , , ,>) 
        ) 
      ) 
      (<T S[dcl]\NP 0 2> 
        (<L (S[dcl]\NP)/(S[adj]\NP) VBD VBD were (S[dcl]\NP_211)/(S[adj]_212\NP_211:B)_212>) 
        (<T S[adj]\NP 0 2> 
          (<L (S[adj]\NP)/PP JJ JJ contrary (S[adj]\NP_219)/PP_220>) 
          (<T PP 0 2> 
            (<L PP/NP TO TO to PP/NP_225>) 
            (<T NP 0 1> 
              (<T N 1 2> 
                (<L N/N JJ JJ common N_234/N_234>) 
                (<L N NN NN sense N>) 
              ) 
            ) 
          ) 
        ) 
      ) 
    ) 
  ) 
  (<L . . . . .>) 
) 
'''
        pt = parse_ccg_derivation(txt)
        s = sentence_from_pt(pt)
        dprint(s)
        self.assertIsNotNone(pt)
        ccg = Ccg2Drs(CO_VERIFY_SIGNATURES | CO_NO_VERBNET | CO_NO_WIKI_SEARCH)
        ccg.build_execution_sequence(pt)
        ccg.create_drs()
        ccg.final_rename()
        d = ccg.get_drs()
        s = d.show(SHOW_LINEAR)
        dprint(s)
        sent = ccg.sorted_sentence()
        a = get_constituents_string_list(sent)
        x = [
            'S_DCL(The bids , he added , #were contrary to common sense .)',
            'S_DCL(The bids , he added , #were contrary to common sense)',
            'NP(The #bids)',
            'VP(he added , #were contrary to common sense)',
            'VP(he #added)',
            'VP(#were contrary to common sense)',
            'ADJP(#contrary to common sense)',
            'PP(#to common sense)',
            'NP(common #sense)',
        ]
        dprint('\n'.join(a))
        self.assertListEqual(x, a)

    def test2_GOLD_Wsj_0056_1(self):
        # RAW 1043
        txt = '''(<L PP IN IN @ PP>)'''


if __name__ == '__main__':
    unittest.main()
