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


class ComposeTest(unittest.TestCase):

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

    def test1_Plural(self):
        txt = r'''(<T S[dcl] 1 2> (<T NP 0 2> (<L NP/N DT DT A NP/N>) (<L N NN NN farmer N>) ) (<T S[dcl]\NP 0 2>
        (<L (S[dcl]\NP)/PP VBN VBN protested (S[dcl]\NP)/PP>) (<T PP 0 2> (<L PP/NP IN IN against PP/NP>)
        (<T NP 0 2> (<L NP/N DT DT the NP/N>) (<T N 1 2> (<L N/N JJ JJ new N/N>) (<L N NN NN tax N>) ) ) ) ) )'''
        pt = parse_ccg_derivation(txt)
        self.assertIsNotNone(pt)
        d = process_ccg_pt(pt, CO_VERIFY_SIGNATURES | CO_NO_VERBNET | CO_NO_WIKI_SEARCH).get_drs()
        s = d.show(SHOW_LINEAR)
        dprint(s)

    def test1_BoyGirl1(self):
        txt = r'''(<T S[dcl] 1 2> (<T NP 0 2> (<L NP/N DT DT The NP/N>) (<L N NN NN boy N>) ) (<T S[dcl]\NP 0 2>
        (<L (S[dcl]\NP)/(S[to]\NP) VBZ VBZ wants (S[dcl]\NP)/(S[to]\NP)>) (<T S[to]\NP 0 2>
        (<L (S[to]\NP)/(S[b]\NP) TO TO to (S[to]\NP)/(S[b]\NP)>) (<T S[b]\NP 0 2>
        (<L (S[b]\NP)/NP VB VB believe (S[b]\NP)/NP>) (<T NP 0 2> (<L NP/N DT DT the NP/N>)
        (<L N NN NN girl N>) ) ) ) ) )'''
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
        x = '[X1,E2,E3,X4| boy(X1),want(E2),_EVENT(E2),_AGENT(E2,X1),_THEME(E2,E3),believe(E3),_EVENT(E3),_AGENT(E3,X1),_THEME(E3,X4),girl(X4)]'
        self.assertEqual(x, s)
        s = get_constituent_string(ccg)
        dprint(s)
        self.assertEqual('S_DCL(The boy #wants to believe the girl) NP(#The boy) S_INF(#to believe the girl) S_INF(#believe the girl) NP(#the girl)', s)
        s = get_constituent_string(ccg.get_verbnet_sentence())
        self.assertEqual('NP(#The boy) VP(#wants) S_INF(#to believe) NP(#the girl)', s)

    def test1_EasySrl(self):
        # Welcome to MerryWeather High
        txt = r'''(<T S[b]\NP 0 2> (<L (S[b]\NP)/PP VB VB Welcome (S[b]\NP)/PP>) (<T PP 0 2> (<L PP/NP TO TO to PP/NP>)
            (<T NP 0 1> (<T N 1 2> (<L N/N NNP NNP Merryweather N/N>) (<L N NNP NNP High. N>) ) ) ) )'''
        pt = parse_ccg_derivation(txt)
        self.assertIsNotNone(pt)
        ccg = Ccg2Drs(CO_FAST_RENAME | CO_VERIFY_SIGNATURES | CO_NO_VERBNET | CO_NO_WIKI_SEARCH)
        ccg.build_execution_sequence(pt)
        ccg.create_drs()
        ccg.final_rename()
        s = ccg.get_drs().show(SHOW_LINEAR)
        x = u'[E1,X2| welcome(E1),_EVENT(E1),_AGENT(E1,X3),_THEME(E1,X2),to(X2),Merryweather(X2),High(X2)]'
        self.assertEquals(x, s)
        ccg.resolve_proper_names()
        x = u'[E1,X2| welcome(E1),_EVENT(E1),_AGENT(E1,X3),_THEME(E1,X2),to(X2),Merryweather-High(X2)]'
        s = ccg.get_drs().show(SHOW_LINEAR)
        self.assertEquals(x, s)

        # The door opens and I step up.
        # (<T S[dcl] 1 2>
        #   (<T S[dcl] 1 2>
        #       (<T NP 0 2>
        #           (<L NP/N DT DT The NP/N>)
        #           (<L N NN NN door N>)
        #       )
        #       (<L S[dcl]\NP VBZ VBZ opens S[dcl]\NP>)
        #   )
        #   (<T S[dcl]\S[dcl] 1 2>
        #       (<L conj CC CC and conj>)
        #       (<T S[dcl] 1 2>
        #           (<L NP PRP PRP I NP>)
        #           (<T S[dcl]\NP 0 2>
        #               (<L S[dcl]\NP VBP VBP step S[dcl]\NP>)
        #               (<L (S\NP)\(S\NP) RB RB up. (S\NP)\(S\NP)>)
        #           )
        #       )
        #   )
        # )
        txt = r'''(<T S[dcl] 1 2> (<T S[dcl] 1 2> (<T NP 0 2> (<L NP/N DT DT The NP/N>) (<L N NN NN door N>) )
            (<L S[dcl]\NP VBZ VBZ opens S[dcl]\NP>) ) (<T S[dcl]\S[dcl] 1 2> (<L conj CC CC and conj>) (<T S[dcl] 1 2>
            (<L NP PRP PRP I NP>) (<T S[dcl]\NP 0 2> (<L S[dcl]\NP VBP VBP step S[dcl]\NP>)
            (<L (S\NP)\(S\NP) RB RB up. (S\NP)\(S\NP)>) ) ) ) )'''
        pt = parse_ccg_derivation(txt)
        self.assertIsNotNone(pt)
        ccg = Ccg2Drs(CO_VERIFY_SIGNATURES | CO_NO_VERBNET | CO_NO_WIKI_SEARCH)
        ccg.build_execution_sequence(pt)
        ccg.create_drs()
        ccg.final_rename()
        s = ccg.get_drs().show(SHOW_LINEAR)
        x = u'[X1,E2,E3| door(X1),open(E2),_EVENT(E2),_AGENT(E2,X1),i(X4),step(E3),_EVENT(E3),_AGENT(E3,X4),up(E3),direction(E3)]'
        self.assertEquals(x, s)

        # The school bus wheezes to my corner.
        txt = r'''(<T S[dcl] 1 2> (<T NP 0 2> (<L NP/N DT DT The NP/N>) (<T N 1 2> (<L N/N NN NN school N/N>)
            (<L N NN NN bus N>) ) ) (<T S[dcl]\NP 0 2> (<L (S[dcl]\NP)/PP VBZ VBZ wheezes (S[dcl]\NP)/PP>)
            (<T PP 0 2> (<L PP/NP TO TO to PP/NP>) (<T NP 0 2> (<L NP/N PRP$ PRP$ my NP/N>)
            (<L N NN NN corner. N>) ) ) ) )'''
        pt = parse_ccg_derivation(txt)
        self.assertIsNotNone(pt)
        ccg = Ccg2Drs(CO_VERIFY_SIGNATURES | CO_NO_VERBNET | CO_NO_WIKI_SEARCH)
        ccg.build_execution_sequence(pt)
        ccg.create_drs()
        ccg.final_rename()
        s = ccg.get_drs().show(SHOW_LINEAR)
        x = u'[X1,E2,X3| school(X1),bus(X1),wheeze(E2),_EVENT(E2),_AGENT(E2,X1),_THEME(E2,X3),to(X3),i(X4),_POSS(X4,X3),corner(X3)]'
        self.assertEquals(x, s)

    def test2_Wsj0004_1(self):
        # Yields on money-market mutual funds continued to slide, amid signs that portfolio managers expect further
        # declines in interest rates.
        txt=r'''(<T S[dcl] 0 2> (<T S[dcl] 1 2> (<T NP 0 2> (<T NP 0 1> (<L N NNS NNS Yields N>) ) (<T NP\NP 0 2>
        (<L (NP\NP)/NP IN IN on (NP_111\NP_111)/NP_112>) (<T NP 0 1> (<T N 1 2> (<L N/N JJ JJ money-market N_128/N_128>)
        (<T N 1 2> (<L N/N JJ JJ mutual N_121/N_121>) (<L N NNS NNS funds N>) ) ) ) ) ) (<T S[dcl]\NP 0 2>
        (<T S[dcl]\NP 0 2> (<T S[dcl]\NP 0 2> (<L (S[dcl]\NP)/(S[to]\NP) VBD VBD continued
        (S[dcl]\NP_10)/(S[to]_11\NP_10:B)_11>) (<T S[to]\NP 0 2>
        (<L (S[to]\NP)/(S[b]\NP) TO TO to (S[to]\NP_20)/(S[b]_21\NP_20:B)_21>)
        (<L S[b]\NP VB VB slide S[b]\NP_26>) ) ) (<L , , , , ,>) ) (<T (S\NP)\(S\NP) 0 2>
        (<L ((S\NP)\(S\NP))/NP IN IN amid ((S_41\NP_36)_41\(S_41\NP_36)_41)/NP_42>) (<T NP 0 1> (<T N 0 2>
        (<L N/S[em] NNS NNS signs N/S[em]_47>) (<T S[em] 0 2> (<L S[em]/S[dcl] IN IN that S[em]/S[dcl]_52>)
        (<T S[dcl] 1 2> (<T NP 0 1> (<T N 1 2> (<L N/N NN NN portfolio N_98/N_98>) (<L N NNS NNS managers N>) ) )
        (<T S[dcl]\NP 0 2> (<L (S[dcl]\NP)/NP VBP VBP expect (S[dcl]\NP_59)/NP_60>) (<T NP 0 2> (<T NP 0 1> (<T N 1 2>
        (<L N/N JJ JJ further N_69/N_69>) (<L N NNS NNS declines N>) ) ) (<T NP\NP 0 2>
        (<L (NP\NP)/NP IN IN in (NP_78\NP_78)/NP_79>) (<T NP 0 1> (<T N 1 2> (<L N/N NN NN interest N_88/N_88>)
        (<L N NNS NNS rates N>) ) ) ) ) ) ) ) ) ) ) ) ) (<L . . . . .>) )'''
        pt = parse_ccg_derivation(txt)
        self.assertIsNotNone(pt)
        ccg = Ccg2Drs(CO_VERIFY_SIGNATURES | CO_NO_VERBNET | CO_NO_WIKI_SEARCH)
        ccg.build_execution_sequence(pt)
        ccg.create_drs()
        ccg.final_rename()
        d = ccg.get_drs()
        s = d.show(SHOW_LINEAR)
        dprint(s)

    def test2_Wsj0004_1_EasySRL(self):
        # Same sentence as test12_Wsj0004_1() but parse tree generated by EasySRL rather than LDC.
        txt= r'''(<T S[dcl] 1 2> (<T NP 0 1> (<T N 0 2> (<L N/PP NNS NNS Yields N/PP>) (<T PP 0 2>
        (<L PP/NP IN IN on PP/NP>) (<T NP 0 1> (<T N 1 2> (<L N/N JJ JJ money-market N/N>) (<T N 1 2>
        (<L N/N JJ JJ mutual N/N>) (<L N NNS NNS funds N>) ) ) ) ) ) ) (<T S[dcl]\NP 0 2> (<T S[dcl]\NP 0 2>
        (<L (S[dcl]\NP)/PP VBD VBD continued (S[dcl]\NP)/PP>) (<T PP 0 2> (<L PP/NP TO TO to PP/NP>) (<T NP 0 1>
        (<L N VB VB slide, N>) ) ) ) (<T (S\NP)\(S\NP) 0 2> (<L ((S\NP)\(S\NP))/NP IN IN amid ((S\NP)\(S\NP))/NP>)
        (<T NP 0 1> (<T N 0 2> (<L N/S[em] NNS NNS signs N/S[em]>) (<T S[em] 0 2>
        (<L S[em]/S[dcl] IN IN that S[em]/S[dcl]>) (<T S[dcl] 1 2> (<T NP 0 1> (<T N 1 2> (<L N/N NN NN portfolio N/N>)
        (<L N NNS NNS managers N>) ) ) (<T S[dcl]\NP 0 2> (<L (S[dcl]\NP)/NP VBP VBP expect (S[dcl]\NP)/NP>)
        (<T NP 0 1> (<T N 1 2> (<L N/N JJ JJ further N/N>) (<T N 0 2> (<L N/PP NNS NNS declines N/PP>) (<T PP 0 2>
        (<L PP/NP IN IN in PP/NP>) (<T NP 0 1> (<T N 1 2> (<L N/N NN NN interest N/N>) (<L N NN NN rates. N>) ) ) ) )
        ) ) ) ) ) ) ) ) ) )'''
        pt = parse_ccg_derivation(txt)
        self.assertIsNotNone(pt)
        ccg = Ccg2Drs(CO_VERIFY_SIGNATURES | CO_NO_VERBNET | CO_NO_WIKI_SEARCH)
        ccg.build_execution_sequence(pt)
        ccg.create_drs()
        ccg.final_rename()
        d = ccg.get_drs()
        s = d.show(SHOW_LINEAR)
        dprint(s)
        s = ''
        for c in ccg.constituents:
            s += c.vntype.signature + '(' + c.span.text + ') '
        dprint(s.strip())

    def test2_Wsj0012_1(self):
        txt = r'''
(<T S[dcl] 0 2>
    (<T S[dcl] 1 2>
        (<T NP 0 1>
            (<L N NNP NNP Newsweek N>)
        )
        (<T S[dcl]\NP 1 2>
            (<L , , , , ,>)
            (<T S[dcl]\NP 1 2>
                (<T (S\NP)/(S\NP) 0 1>
                    (<T S[ng]\NP 0 2>
                        (<L (S[ng]\NP)/(S[to]\NP) VBG VBG trying (S[ng]\NP_112)/(S[to]_113\NP_112:B)_113>)
                        (<T S[to]\NP 0 2>
                            (<L (S[to]\NP)/(S[b]\NP) TO TO to (S[to]\NP_122)/(S[b]_123\NP_122:B)_123>)
                            (<T S[b]\NP 0 2>
                                (<T (S[b]\NP)/PP 0 2>
                                    (<L ((S[b]\NP)/PP)/NP VB VB keep ((S[b]\NP_132)/PP_133)/NP_134>)
                                    (<T NP 0 1>
                                        (<L N NN NN pace N>)
                                    )
                                )
                                (<T PP 0 2>
                                    (<L PP/NP IN IN with PP/NP_142>)
                                    (<T NP 0 2>
                                        (<T NP 0 1>
                                            (<L N NN JJ rival N>)
                                        )
                                        (<T NP\NP 1 2>
                                            (<L (NP\NP)/(NP\NP) NNP NNP Time (NP_166\NP_160)_166/(NP_166\NP_160)_166>)
                                            (<L NP\NP NN NN magazine NP_152\NP_152>)
                                        )
                                    )
                                )
                            )
                        )
                    )
                )
                (<T S[dcl]\NP 1 2>
                    (<L , , , , ,>)
                    (<T S[dcl]\NP 0 2>
                        (<T S[dcl]\NP 0 2>
                            (<L (S[dcl]\NP)/NP VBD VBD announced (S[dcl]\NP_8)/NP_9>)
                            (<T NP 0 2>
                                (<T NP 0 1>
                                    (<T N 1 2>
                                        (<L N/N JJ JJ new N_25/N_25>)
                                        (<T N 1 2>
                                            (<L N/N NN NN advertising N_18/N_18>)
                                            (<L N NNS NNS rates N>)
                                        )
                                    )
                                )
                                (<T NP\NP 0 2>
                                    (<L (NP\NP)/NP IN IN for (NP_34\NP_34)/NP_35>)
                                    (<T NP 0 1>
                                        (<L N CD CD 1990 N>)
                                    )
                                )
                            )
                        )
                        (<T S[dcl]\NP[conj] 1 2>
                            (<L conj CC CC and conj>)
                            (<T S[dcl]\NP 0 2>
                                (<L (S[dcl]\NP)/S[dcl] VBD VBD said (S[dcl]\NP_45)/S[dcl]_46>)
                                (<T S[dcl] 1 2>
                                    (<L NP PRP PRP it NP>)
                                    (<T S[dcl]\NP 0 2>
                                        (<L (S[dcl]\NP)/(S[b]\NP) MD MD will (S[dcl]\NP_55)/(S[b]_56\NP_55:B)_56>)
                                        (<T S[b]\NP 0 2>
                                            (<L (S[b]\NP)/NP VB VB introduce (S[b]\NP_63)/NP_64>)
                                            (<T NP 0 2>
                                                (<T NP 1 2>
                                                    (<L NP[nb]/N DT DT a NP[nb]_85/N_85>)
                                                    (<T N 1 2>
                                                        (<L N/N JJ JJ new N_80/N_80>)
                                                        (<T N 1 2>
                                                            (<L N/N NN NN incentive N_73/N_73>)
                                                            (<L N NN NN plan N>)
                                                        )
                                                    )
                                                )
                                                (<T NP\NP 0 2>
                                                    (<L (NP\NP)/NP IN IN for (NP_93\NP_93)/NP_94>)
                                                    (<T NP 0 1>
                                                        (<L N NNS NNS advertisers N>)
                                                    )
                                                )
                                            )
                                        )
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
)
'''
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
        dtree = ccg.get_dependency_tree()
        dprint_dependency_tree(ccg, dtree)
        s = []
        for c in ccg.constituents:
            s.append(c.vntype.signature + '(' + c.span.text + ')')
        dprint(' '.join(s))
        ctree = ccg.get_constituent_tree()
        dprint_constituent_tree(ccg, ctree)

    def test2_Wsj0999_31(self):
        txt = r'''
(<T S[dcl] 0 2>
    (<T S[dcl] 1 2>
        (<T NP 0 2>
            (<T NP 1 2>
                (<L NP[nb]/N DT DT AN NP[nb]_137/N_137>)
                (<T N 1 2>
                    (<L N/N NNP NNP AIDS N_132/N_132>)
                    (<L N NN NN DIRECTORY N>)
                )
            )
            (<T NP\NP 0 2>
                (<L (NP\NP)/NP IN IN from (NP_145\NP_145)/NP_146>)
                (<T NP 0 2>
                    (<T NP 1 2>
                        (<L NP[nb]/N DT DT the NP[nb]_160/N_160>)
                        (<T N 1 2>
                            (<L N/N NNP NNP American N_155/N_155>)
                            (<L N NNP NNP Foundation N>)
                        )
                    )
                    (<T NP\NP 0 2>
                        (<L (NP\NP)/NP IN IN for (NP_168\NP_168)/NP_169>)
                        (<T NP 0 1>
                            (<T N 1 2>
                                (<L N/N NNP NNP AIDS N_178/N_178>)
                                (<L N NNP NNP Research N>)
                            )
                        )
                    )
                )
            )
        )
        (<T S[dcl]\NP 0 2>
            (<T (S[dcl]\NP)/NP 0 2>
                (<L (S[dcl]\NP)/NP VBZ VBZ rates (S[dcl]\NP_102)/NP_103>)
                (<T (S[dcl]\NP)/NP[conj] 1 2>
                    (<L conj CC CC and conj>)
                    (<L (S[dcl]\NP)/NP VBZ VBZ reviews (S[dcl]\NP_110)/NP_111>)
                )
            )
            (<T NP 0 1>
                (<T N 1 2>
                    (<L N/N JJ JJ educational N_122/N_122>)
                    (<L N NNS NNS materials N>)
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
        ccg = Ccg2Drs(CO_VERIFY_SIGNATURES | CO_NO_VERBNET | CO_NO_WIKI_SEARCH)
        ccg.build_execution_sequence(pt)
        ccg.create_drs()
        ccg.resolve_proper_names()
        ccg.final_rename()
        d = ccg.get_drs()
        s = d.show(SHOW_LINEAR)
        dprint(s)
        x = u'[X1,X2,X3,E4,E5,X6| AIDS-DIRECTORY(X1),from(X1,X2),American-Foundation(X2),for(X2,X3),AIDS-Research(X3),rat(E4),_EVENT(E4),_AGENT(E4,X1),_THEME(E4,X6),review(E5),_EVENT(E5),_AGENT(E5,X7),_THEME(E5,X8),educational(X6),materials(X6)]'
        self.assertEqual(x, s)
        dtree = ccg.get_dependency_tree()
        dprint_dependency_tree(ccg, dtree)
        s = []
        for c in ccg.constituents:
            s.append(c.vntype.signature + '(' + c.span.text + ')')
        dprint('\n'.join(s))
        ctree = ccg.get_constituent_tree()
        dprint_constituent_tree(ccg, ctree)

    def test2_Wsj0620_01(self):
        txt = r'''
(<T S[dcl] 0 2>
    (<T S[dcl] 1 2>
        (<T NP 0 1>
            (<T N 1 2>
                (<L N/N NNP NNP Exxon N_208/N_208>)
                (<L N NNP NNP Corp. N>)
            )
        )
        (<T S[dcl]\NP 0 2>
            (<L (S[dcl]\NP)/(S[ng]\NP) VBZ VBZ is (S[dcl]\NP_10)/(S[ng]_11\NP_10:B)_11>)
            (<T S[ng]\NP 0 2>
                (<T S[ng]\NP 0 2>
                    (<T S[ng]\NP 0 2>
                        (<L (S[ng]\NP)/PP VBG VBG resigning (S[ng]\NP_18)/PP_19>)
                        (<T PP 0 2>
                            (<L PP/NP IN IN from PP/NP_24>)
                            (<T NP 1 2>
                                (<T NP[nb]/N 1 2>
                                    (<T NP 1 2>
                                        (<L NP[nb]/N DT DT the NP[nb]_69/N_69>)
                                        (<T N 1 2>
                                            (<L N/N NNP NNP National N_64/N_64>)
                                            (<T N 1 2>
                                                (<L N/N NNP NNP Wildlife N_57/N_57>)
                                                (<L N NNP NNP Federation N>)
                                            )
                                        )
                                    )
                                    (<L (NP[nb]/N)\NP POS POS 's (NP[nb]_47/N_47)\NP_48>)
                                )
                                (<T N 1 2>
                                (<L N/N JJ JJ corporate N_40/N_40>)
                                    (<T N 1 2>
                                        (<L N/N JJ JJ advisory N_33/N_33>)
                                        (<L N NN NN panel N>)
                                    )
                                )
                            )
                        )
                    )
                    (<L , , , , ,>)
                )
                (<T (S\NP)\(S\NP) 0 1>
                    (<T S[ng]\NP 0 2>
                        (<L (S[ng]\NP)/S[dcl] VBG VBG saying (S[ng]\NP_78)/S[dcl]_79>)
                        (<T S[dcl] 1 2>
                            (<T NP 1 2>
                                (<L NP[nb]/N DT DT the NP[nb]_189/N_189>)
                                (<T N 1 2>
                                    (<L N/N NN NN conservation N_184/N_184>)
                                    (<L N NN NN group N>)
                                )
                            )
                            (<T S[dcl]\NP 0 2>
                                (<L (S[dcl]\NP)/(S[pt]\NP) VBZ VBZ has (S[dcl]\NP_88)/(S[pt]_89\NP_88:B)_89>)
                                (<T S[pt]\NP 0 2>
                                    (<L (S[pt]\NP)/(S[adj]\NP) VBN VBN been (S[pt]\NP_98)/(S[adj]_99\NP_98:B)_99>)
                                    (<T S[adj]\NP 1 2>
                                        (<L (S[adj]\NP)/(S[adj]\NP) RB RB unfairly (S[adj]_175\NP_170)_175/(S[adj]_175\NP_170)_175>)
                                        (<T S[adj]\NP 0 2>
                                            (<L (S[adj]\NP)/PP JJ JJ critical (S[adj]\NP_106)/PP_107>)
                                            (<T PP 0 2>
                                                (<L PP/NP IN IN of PP/NP_112>)
                                                (<T NP 0 2>
                                                    (<T NP 1 2>
                                                        (<L NP[nb]/N DT DT the NP[nb]_140/N_140>)
                                                        (<T N 1 2>
                                                            (<L N/N NNP NNP Exxon N_135/N_135>)
                                                            (<T N 1 2>
                                                                (<L N/N NNP NNP Valdez N_128/N_128>)
                                                                (<T N 1 2>
                                                                    (<L N/N NN NN oil N_121/N_121>)
                                                                    (<L N NN NN spill N>)
                                                                )
                                                            )
                                                        )
                                                    )
                                                    (<T NP\NP 0 2>
                                                        (<L (NP\NP)/NP IN IN along (NP_148\NP_148)/NP_149>)
                                                        (<T NP 1 2>
                                                            (<L NP[nb]/N DT DT the NP[nb]_163/N_163>)
                                                            (<T N 1 2>
                                                                (<L N/N JJ JJ Alaskan N_158/N_158>)
                                                                (<L N NN NN coast N>)
                                                            )
                                                        )
                                                    )
                                                )
                                            )
                                        )
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
)
'''
        pt = parse_ccg_derivation(txt)
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
        dtree = ccg.get_dependency_tree()
        dprint_dependency_tree(ccg, dtree)
        s = []
        for c in ccg.constituents:
            s.append(c.vntype.signature + '(' + c.span.text + ')')
        dprint('\n'.join(s))
        ctree = ccg.get_constituent_tree()
        dprint_constituent_tree(ccg, ctree)

    def test3_EasySrl_00_1200(self):
        # The department 's roof-crush proposal would apply to vehicles weighing 10,000 pounds or less.
        txt = r'''
(<T S[dcl] 1 2>
    (<T NP 0 2>
        (<T NP/(N/PP) 1 2>
            (<T NP 0 2>
                (<L NP/N DT DT The NP/N>)
                (<L N NN NN department N>)
            )
            (<L (NP/(N/PP))\NP POS POS 's (NP/(N/PP))\NP>)
        )
        (<T N/PP 1 2>
            (<L N/N JJ JJ roof-crush N/N>)
            (<L N/PP NN NN proposal N/PP>)
        )
    )
    (<T S[dcl]\NP 0 2>
        (<T S[dcl]\NP 0 2>
            (<L (S[dcl]\NP)/(S[b]\NP) MD MD would (S[dcl]\NP)/(S[b]\NP)>)
            (<T S[b]\NP 0 2>
                (<L (S[b]\NP)/PP VB VB apply (S[b]\NP)/PP>)
                (<T PP 0 2>
                    (<L PP/NP TO TO to PP/NP>)
                    (<T NP 0 1>
                        (<T N 0 2>
                            (<L N NNS NNS vehicles N>)
                            (<T N\N 0 2>
                                (<T N\N 0 1>
                                    (<T S[ng]\NP 0 2>
                                        (<L (S[ng]\NP)/NP VBG VBG weighing (S[ng]\NP)/NP>)
                                        (<T NP 0 1>
                                            (<T N 1 2>
                                                (<L N/N CD CD 10,000 N/N>)
                                                (<L N NNS NNS pounds N>)
                                            )
                                        )
                                    )
                                )
                                (<T (N\N)\(N\N) 1 2>
                                    (<L conj CC CC or conj>)
                                    (<L N\N JJR JJR less N\N>)
                                )
                            )
                        )
                    )
                )
            )
        )
        (<L . . . . .>)
    )
) '''
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
        dtree = ccg.get_dependency_tree()
        dprint_dependency_tree(ccg, dtree)
        s = []
        for c in ccg.constituents:
            s.append(c.vntype.signature + '(' + c.span.text + ')')
        dprint(' '.join(s))
        ctree = ccg.get_constituent_tree()
        dprint_constituent_tree(ccg, ctree)

    def test3_EasySrl_00_1096(self):
        txt = r'''(<T S[dcl] 1 2> (<L NP PRP PRP We NP>) (<T S[dcl]\NP 0 2> (<T S[dcl]\NP 0 2>
        (<L (S[dcl]\NP)/(S[b]\NP) MD MD would (S[dcl]\NP)/(S[b]\NP)>) (<T S[b]\NP 0 2>
        (<L (S[b]\NP)/(S[to]\NP) VB VB like (S[b]\NP)/(S[to]\NP)>) (<T S[to]\NP 0 2>
        (<L (S[to]\NP)/(S[b]\NP) TO TO to (S[to]\NP)/(S[b]\NP)>) (<T S[b]\NP 0 2>
        (<L (S[b]\NP)/PP VB VB apologize (S[b]\NP)/PP>) (<T PP 0 2> (<L PP/(S[ng]\NP) IN IN for PP/(S[ng]\NP)>)
        (<T S[ng]\NP 0 2> (<L (S[ng]\NP)/(S[pt]\NP) VBG VBG having (S[ng]\NP)/(S[pt]\NP)>) (<T S[pt]\NP 0 2>
        (<L (S[pt]\NP)/NP VBN VBN caused (S[pt]\NP)/NP>) (<T NP 0 2> (<T NP 0 1> (<T N 1 2> (<L N/N JJ JJ huge N/N>)
        (<L N NN NN trouble N>) ) ) (<T NP\NP 1 2> (<L , , , , ,>) (<T NP 0 1> (<T N 1 2> (<T N/N 1 2>
        (<L (N/N)/(N/N) NNP NNP Fujitsu (N/N)/(N/N)>) (<L N/N NNP NNP President N/N>) ) (<T N 1 2>
        (<L N/N NNP NNP Takuma N/N>) (<L N NNP NNP Yamamoto N>) ) ) ) ) ) ) ) ) ) ) ) ) (<T (S[dcl]\NP)\(S[dcl]\NP) 1 2>
        (<L , , , , ,>) (<T S[dcl]\NP 0 2> (<T S[dcl]\NP 0 2> (<L (S[dcl]\NP)/PP VBD VBD read (S[dcl]\NP)/PP>)
        (<T PP 0 2> (<L PP/NP IN IN from PP/NP>) (<T NP 0 2> (<L NP/N DT DT a NP/N>) (<T N 1 2>
        (<L N/N JJ JJ prepared N/N>) (<L N NN NN statement N>) ) ) ) ) (<T (S\NP)\(S\NP) 0 2>
        (<L ((S\NP)\(S\NP))/S[dcl] IN IN as ((S\NP)\(S\NP))/S[dcl]>) (<T S[dcl] 1 2> (<L NP PRP PRP he NP>)
        (<T S[dcl]\NP 0 2> (<T S[dcl]\NP 0 2> (<L S[dcl]\NP VBD VBD stood S[dcl]\NP>) (<T (S\NP)\(S\NP) 0 2>
        (<L ((S\NP)\(S\NP))/NP IN IN before ((S\NP)\(S\NP))/NP>) (<T NP 0 2> (<L NP/N DT DT a NP/N>) (<T N 1 2>
        (<L N/N JJ JJ packed N/N>) (<T N 1 2> (<L N/N NN NN news N/N>) (<L N NN NN conference N>) ) ) ) ) )
        (<T (S\NP)\(S\NP) 0 2> (<L ((S\NP)\(S\NP))/NP IN IN at ((S\NP)\(S\NP))/NP>) (<T NP 0 2> (<T NP/(N/PP) 1 2>
        (<T NP 0 2> (<L NP/N PRP$ PRP$ his NP/N>) (<L N NN NN company N>) )
        (<L (NP/(N/PP))\NP POS POS 's (NP/(N/PP))\NP>) ) (<T N/PP 1 2> (<L N/N NN NN downtown N/N>)
        (<L N/PP NN NN headquarters N/PP>) ) ) ) ) ) ) ) ) ) )'''
        pt = parse_ccg_derivation(txt)
        self.assertIsNotNone(pt)
        ccg = Ccg2Drs(CO_VERIFY_SIGNATURES | CO_NO_VERBNET | CO_NO_WIKI_SEARCH)
        ccg.build_execution_sequence(pt)
        ccg.create_drs()
        ccg.final_rename()
        d = ccg.get_drs()
        s = d.show(SHOW_LINEAR)
        dprint(s)

    def test4_Asbestos(self):
        txt=r'''(<T S[dcl] 1 2> (<T S[dcl] 1 2> (<T NP 0 2> (<L NP/N DT DT A NP/N>) (<T N 0 2> (<L N/PP NN NN form N/PP>)
        (<T PP 0 2> (<L PP/NP IN IN of PP/NP>) (<T NP 0 1> (<T N 0 2> (<L N NN NN asbestos N>) (<T N\N 0 1>
        (<T S[pss]\NP 1 2> (<L (S\NP)/(S\NP) RB RB once (S\NP)/(S\NP)>) (<T S[pss]\NP 0 2>
        (<L (S[pss]\NP)/(S[to]\NP) VBN VBN used (S[pss]\NP)/(S[to]\NP)>) (<T S[to]\NP 0 2>
        (<L (S[to]\NP)/(S[b]\NP) TO TO to (S[to]\NP)/(S[b]\NP)>) (<T S[b]\NP 0 2>
        (<L (S[b]\NP)/NP VB VB make (S[b]\NP)/NP>) (<T NP 0 1> (<T N 1 2> (<L N/N NNP NNP Kent N/N>) (<T N 1 2>
        (<L N/N NN NN cigarette N/N>) (<L N NNS NNS filters N>) ) ) ) ) ) ) ) ) ) ) ) ) ) (<T S[dcl]\NP 0 2>
        (<L (S[dcl]\NP)/(S[pt]\NP) VBZ VBZ has (S[dcl]\NP)/(S[pt]\NP)>) (<T S[pt]\NP 0 2>
        (<L (S[pt]\NP)/NP VBN VBN caused (S[pt]\NP)/NP>) (<T NP 0 2> (<L NP/N DT DT a NP/N>) (<T N 1 2>
        (<L N/N JJ JJ high N/N>) (<T N 0 2> (<T N 0 2> (<T N 0 2> (<L N/PP NN NN percentage N/PP>) (<T PP 0 2>
        (<L PP/NP IN IN of PP/NP>) (<T NP 0 1> (<T N 1 2> (<L N/N NN NN cancer N/N>) (<L N NNS NNS deaths N>) ) ) ) )
        (<T N\N 0 2> (<L (N\N)/NP IN IN among (N\N)/NP>) (<T NP 0 2> (<L NP/N DT DT a NP/N>) (<T N 0 2>
        (<L N/PP NN NN group N/PP>) (<T PP 0 2> (<L PP/NP IN IN of PP/NP>) (<T NP 0 1> (<T N 0 2>
        (<L N NNS NNS workers N>) (<T N\N 0 1> (<T S[pss]\NP 0 2> (<T S[pss]\NP 0 2>
        (<L (S[pss]\NP)/PP VBN VBN exposed (S[pss]\NP)/PP>) (<T PP 0 2> (<L PP/NP TO TO to PP/NP>)
        (<L NP PRP PRP it NP>) ) ) (<T (S\NP)\(S\NP) 1 2> (<T NP 0 1> (<T N 1 2> (<T N/N 1 2> (<T (N/N)/(N/N) 1 2>
        (<L S[adj]\NP JJR JJR more S[adj]\NP>) (<L ((N/N)/(N/N))\(S[adj]\NP) IN IN than ((N/N)/(N/N))\(S[adj]\NP)>) )
        (<L N/N CD CD 30 N/N>) ) (<L N NNS NNS years N>) ) ) (<L ((S\NP)\(S\NP))\NP RB RB ago ((S\NP)\(S\NP))\NP>) ) )
        ) ) ) ) ) ) ) ) (<L , , , , ,>) ) ) ) ) ) ) (<T S[dcl]\S[dcl] 0 2> (<T S[dcl]\S[dcl] 1 2> (<T NP 0 1>
        (<L N NNS NNS researchers N>) ) (<L (S[dcl]\S[dcl])\NP VBD VBD reported (S[dcl]\S[dcl])\NP>) )
        (<L . . . . .>) ) )'''
        pt = parse_ccg_derivation(txt)
        self.assertIsNotNone(pt)
        ccg = Ccg2Drs(CO_VERIFY_SIGNATURES | CO_NO_VERBNET | CO_NO_WIKI_SEARCH)
        ccg.build_execution_sequence(pt)
        ccg.create_drs()
        s = ccg.get_drs().show(SHOW_LINEAR)
        dprint(s)
        s = ''
        for c in ccg.constituents:
            s += c.vntype.signature + '(' + c.span.text + ') '
        dprint(s.strip())

    def test5_ProperNouns1(self):
        #txt = '''(<T NP 0 2> (<T NP 0 1> (<T N 1 2> (<L N/N NNP NNP J.P. N/N>) (<L N NNP NNP Bolduc N>) ) ) (<T NP\NP 1 2> (<L , , , , ,>) (<T NP 0 1> (<T N 1 2> (<L N/N NN NN vice N/N>) (<T N 0 2> (<L N/PP NN NN chairman N/PP>) (<T PP 0 2> (<T PP 0 2> (<L PP/NP IN IN of PP/NP>) (<T NP 0 2> (<T NP 0 1> (<T N 1 2> (<T N/N 1 2> (<L (N/N)/(N/N) NNP NNP W.R. (N/N)/(N/N)>) (<L N/N NNP NNP Grace N/N>) ) (<T N 1 2> (<L N/N CC CC & N/N>) (<T N 0 2> (<L N NNP NNP Co. N>) (<L , , , , ,>) ) ) ) ) (<T NP\NP 0 2> (<L (NP\NP)/(S[dcl]\NP) WDT WDT which (NP\NP)/(S[dcl]\NP)>) (<T S[dcl]\NP 0 2> (<T S[dcl]\NP 0 2> (<L (S[dcl]\NP)/NP VBZ VBZ holds (S[dcl]\NP)/NP>) (<T NP 0 2> (<L NP/N DT DT a NP/N>) (<T N 1 2> (<T N/N 1 2> (<L (N/N)/(N/N) CD CD 83.4 (N/N)/(N/N)>) (<L N/N NN NN % N/N>) ) (<T N 0 2> (<L N/PP NN NN interest N/PP>) (<T PP 0 2> (<L PP/NP IN IN in PP/NP>) (<T NP 0 2> (<L NP/N DT DT this NP/N>) (<T N 1 2> (<L N/N JJ JJ energy-services N/N>) (<L N NN NN company N>) ) ) ) ) ) ) ) (<T (S[dcl]\NP)\(S[dcl]\NP) 1 2> (<L , , , , ,>) (<T S[dcl]\NP 0 2> (<L (S[dcl]\NP)/(S[pss]\NP) VBD VBD was (S[dcl]\NP)/(S[pss]\NP)>) (<T S[pss]\NP 0 2> (<L (S[pss]\NP)/NP VBN VBN elected (S[pss]\NP)/NP>) (<T NP 0 2> (<L NP/N DT DT a NP/N>) (<L N NN NN director N>) ) ) ) ) ) ) ) ) (<L . . . . .>) ) ) ) ) ) ) '''
        txt = r'''
(<T NP 0 2>
    (<T NP 0 1>
        (<T N 1 2>
            (<L N/N NNP NNP J.P. N/N>)
            (<L N NNP NNP Bolduc N>)
        )
    )
    (<T NP\NP 1 2>
        (<L , , , , ,>)
        (<T NP 0 1>
            (<T N 1 2>
                (<L N/N NN NN vice N/N>)
                (<T N 0 2>
                    (<L N/PP NN NN chairman N/PP>)
                    (<T PP 0 2>
                        (<T PP 0 2>
                            (<L PP/NP IN IN of PP/NP>)
                            (<T NP 0 2>
                                (<T NP 0 1>
                                    (<T N 1 2>
                                        (<T N/N 1 2>
                                            (<L (N/N)/(N/N) NNP NNP W.R. (N/N)/(N/N)>)
                                            (<L N/N NNP NNP Grace N/N>)
                                        )
                                        (<T N 1 2>
                                            (<L N/N CC CC & N/N>)
                                            (<T N 0 2>
                                                (<L N NNP NNP Co. N>)
                                                (<L , , , , ,>)
                                            )
                                        )
                                    )
                                )
                                (<T NP\NP 0 2>
                                    (<L (NP\NP)/(S[dcl]\NP) WDT WDT which (NP\NP)/(S[dcl]\NP)>)
                                    (<T S[dcl]\NP 0 2>
                                        (<T S[dcl]\NP 0 2>
                                            (<L (S[dcl]\NP)/NP VBZ VBZ holds (S[dcl]\NP)/NP>)
                                            (<T NP 0 2>
                                                (<L NP/N DT DT a NP/N>)
                                                (<T N 1 2>
                                                    (<T N/N 1 2>
                                                        (<L (N/N)/(N/N) CD CD 83.4 (N/N)/(N/N)>)
                                                        (<L N/N NN NN % N/N>)
                                                    )
                                                    (<T N 0 2>
                                                        (<L N/PP NN NN interest N/PP>)
                                                        (<T PP 0 2>
                                                            (<L PP/NP IN IN in PP/NP>)
                                                            (<T NP 0 2>
                                                                (<L NP/N DT DT this NP/N>)
                                                                (<T N 1 2>
                                                                    (<L N/N JJ JJ energy-services N/N>)
                                                                    (<L N NN NN company N>)
                                                                )
                                                            )
                                                        )
                                                    )
                                                )
                                            )
                                        )
                                        (<T (S[dcl]\NP)\(S[dcl]\NP) 1 2>
                                            (<L , , , , ,>)
                                            (<T S[dcl]\NP 0 2>
                                                (<L (S[dcl]\NP)/(S[pss]\NP) VBD VBD was (S[dcl]\NP)/(S[pss]\NP)>)
                                                (<T S[pss]\NP 0 2>
                                                    (<L (S[pss]\NP)/NP VBN VBN elected (S[pss]\NP)/NP>)
                                                    (<T NP 0 2>
                                                        (<L NP/N DT DT a NP/N>)
                                                        (<L N NN NN director N>)
                                                    )
                                                )
                                            )
                                        )
                                    )
                                )
                            )
                        )
                        (<L . . . . .>)
                    )
                )
            )
        )
    )
) '''
        pt = parse_ccg_derivation(txt)
        self.assertIsNotNone(pt)
        d = process_ccg_pt(pt, CO_VERIFY_SIGNATURES | CO_NO_VERBNET | CO_NO_WIKI_SEARCH).get_drs()
        s = d.show(SHOW_LINEAR)
        dprint(s)

    def test5_ProperNouns2(self):
        txt=r'''
(<T S[dcl] 1 2>
    (<T S[dcl] 0 2>
        (<T S[dcl] 1 2>
            (<T S/S 0 2>
                (<L S/S RB RB Rather S/S>)
                (<L , , , , ,>)
            )
            (<T S[dcl] 1 2>
                (<T NP 0 1>
                    (<T N 1 2>
                        (<L N/N JJ JJ Japanese N/N>)
                        (<L N NN NN investment N>)
                    )
                )
                (<T S[dcl]\NP 0 2>
                    (<L (S[dcl]\NP)/(S[b]\NP) MD MD will (S[dcl]\NP)/(S[b]\NP)>)
                    (<T S[b]\NP 0 2>
                        (<L (S[b]\NP)/NP VB VB spur (S[b]\NP)/NP>)
                        (<T NP 0 1>
                            (<T N 0 2>
                                (<L N/PP NN NN integration N/PP>)
                                (<T PP 0 2>
                                    (<L PP/NP IN IN of PP/NP>)
                                    (<T NP 0 1>
                                        (<T N 1 2>
                                            (<L N/N JJ JJ certain N/N>)
                                            (<L N NNS NNS sectors N>)
                                        )
                                    )
                                )
                            )
                        )
                    )
                )
            )
        )
        (<L , , , , ,>)
    )
    (<T S[dcl]\S[dcl] 0 2>
        (<L (S[dcl]\S[dcl])/NP VBZ VBZ says (S[dcl]\S[dcl])/NP>)
        (<T NP 0 2>
            (<T NP 0 1>
                (<T N 1 2>
                    (<L N/N NNP NNP Kent N/N>)
                    (<L N NNP NNP Calder N>)
                )
            )
            (<T NP\NP 1 2>
                (<L , , , , ,>)
                (<T NP 0 2>
                    (<L NP/N DT DT a NP/N>)
                    (<T N 0 2>
                        (<T N 0 2>
                            (<L N/PP NN NN specialist N/PP>)
                            (<T PP 0 2>
                                (<L PP/NP IN IN in PP/NP>)
                                (<T NP 0 1>
                                    (<T N 0 2>
                                        (<T N 0 2>
                                            (<T N 1 2>
                                                (<T N/N 1 2>
                                                    (<L (N/N)/(N/N) JJ JJ East (N/N)/(N/N)>)
                                                    (<L N/N JJ JJ Asian N/N>)
                                                )
                                                (<L N NNS NNS economies N>)
                                            )
                                            (<T N\N 0 2>
                                                (<L (N\N)/NP IN IN at (N\N)/NP>)
                                                (<T NP 0 2>
                                                    (<L NP/N DT DT the NP/N>)
                                                    (<T N 1 2>
                                                        (<L N/N NNP NNP Woodrow N/N>)
                                                        (<T N 1 2>
                                                            (<L N/N NNP NNP Wilson N/N>)
                                                            (<L N NNP NNP School N>)
                                                        )
                                                    )
                                                )
                                            )
                                        )
                                        (<T N\N 0 2>
                                            (<L (N\N)/NP IN IN for (N\N)/NP>)
                                            (<T NP 0 1>
                                                (<T N 1 2>
                                                    (<T N/N 0 2>
                                                        (<L N/N NNP NNP Public N/N>)
                                                        (<T (N/N)\(N/N) 1 2>
                                                            (<L conj CC CC and conj>)
                                                            (<L N/N NNP NNP International N/N>)
                                                        )
                                                    )
                                                    (<L N NNP NNP Affairs N>)
                                                )
                                            )
                                        )
                                    )
                                )
                            )
                        )
                        (<T N\N 0 2>
                            (<T N\N 0 2>
                                (<L (N\N)/NP IN IN at (N\N)/NP>)
                                (<T NP 0 1>
                                    (<T N 1 2>
                                        (<L N/N NNP NNP Princeton N/N>)
                                        (<L N NNP NNP University N>)
                                    )
                                )
                            )
                            (<L . . . . .>)
                        )
                    )
                )
            )
        )
    )
)'''
        pt = parse_ccg_derivation(txt)
        self.assertIsNotNone(pt)
        ccg = process_ccg_pt(pt, CO_VERIFY_SIGNATURES | CO_NO_VERBNET | CO_NO_WIKI_SEARCH)
        d = ccg.get_drs()
        s = d.show(SHOW_LINEAR)
        dprint(s)
        s = []
        for c in ccg.constituents:
            s.append(c.vntype.signature + '(' + c.span.text + ')')
        dprint(' '.join(s))
        a = ccg.get_constituent_tree()
        dprint_constituent_tree(ccg, a)
        #ccg.add_wikipedia_links(browser=)
        dprint(ccg.get_drs().show(SHOW_LINEAR))

    def test6_Pronouns(self):
        txt = r'''(<T S[dcl] 1 2> (<L NP PRP PRP I NP>) (<T S[dcl]\NP 0 2> (<T (S[dcl]\NP)/PP 0 2> (<L ((S[dcl]\NP)/PP)/NP VBD VBD leased ((S[dcl]\NP)/PP)/NP>) (<T NP 0 2> (<L NP/N DT DT the NP/N>) (<L N NN NN car N>) ) ) (<T PP 0 2> (<L PP/NP TO TO to PP/NP>) (<T NP 0 2> (<L NP/(N/PP) PRP$ PRP$ my NP/(N/PP)>) (<T N/PP 0 2> (<L N/PP NN NN friend N/PP>) (<T (N/PP)\(N/PP) 0 2> (<L ((N/PP)\(N/PP))/NP IN IN for ((N/PP)\(N/PP))/NP>) (<T NP 0 1> (<T N 0 2> (<L N CD CD $5 N>) (<T N\N 0 2> (<L (N\N)/N DT DT a (N\N)/N>) (<L N NN NN month. N>) ) ) ) ) ) ) ) ) )'''
        pt = parse_ccg_derivation(txt)
        self.assertIsNotNone(pt)
        d = process_ccg_pt(pt, CO_VERIFY_SIGNATURES).get_drs()
        self.assertIsNotNone(d)

    def test7_Brexit(self):
        # 0: The managing director of the International Monetary Fund has said she wants Britain to stay in the EU,
        # warning that a looming Brexit referendum posed a risk to the UK economy
        txt = []
        txt.append(r'''(<T S[dcl] 1 2> (<T NP 0 2> (<L NP/N DT DT The NP/N>) (<T N 1 2> (<L N/N NN NN managing N/N>)
        (<T N 0 2> (<L N/PP NN NN director N/PP>) (<T PP 0 2> (<L PP/NP IN IN of PP/NP>) (<T NP 0 2>
        (<L NP/N DT DT the NP/N>) (<T N 1 2> (<L N/N NNP NNP International N/N>) (<T N 1 2>
        (<L N/N NNP NNP Monetary N/N>) (<L N NNP NNP Fund N>) ) ) ) ) ) ) ) (<T S[dcl]\NP 0 2>
        (<L (S[dcl]\NP)/(S[pt]\NP) VBZ VBZ has (S[dcl]\NP)/(S[pt]\NP)>) (<T S[pt]\NP 0 2>
        (<L (S[pt]\NP)/S[dcl] VBN VBN said (S[pt]\NP)/S[dcl]>) (<T S[dcl] 1 2> (<L NP PRP PRP she NP>)
        (<T S[dcl]\NP 0 2> (<T (S[dcl]\NP)/(S[to]\NP) 0 2> (<L ((S[dcl]\NP)/(S[to]\NP))/NP VBZ VBZ wants
        ((S[dcl]\NP)/(S[to]\NP))/NP>) (<T NP 0 1> (<L N NNP NNP Britain N>) ) ) (<T S[to]\NP 0 2>
        (<L (S[to]\NP)/(S[b]\NP) TO TO to (S[to]\NP)/(S[b]\NP)>) (<T S[b]\NP 0 2>
        (<L (S[b]\NP)/PP VB VB stay (S[b]\NP)/PP>) (<T PP 0 2> (<L PP/NP IN IN in PP/NP>) (<T NP 0 2>
        (<L NP/N DT DT the NP/N>) (<T N 0 2> (<L N NN NN EU, N>) (<T N\N 0 1> (<T S[ng]\NP 0 2>
        (<L (S[ng]\NP)/S[em] NN NN warning (S[ng]\NP)/S[em]>) (<T S[em] 0 2> (<L S[em]/S[dcl] IN IN that S[em]/S[dcl]>)
        (<T S[dcl] 1 2> (<T NP 0 2> (<L NP/N DT DT a NP/N>) (<T N 1 2> (<L N/N VBG VBG looming N/N>) (<T N 1 2>
        (<L N/N NN NN Brexit N/N>) (<L N NN NN referendum N>) ) ) ) (<T S[dcl]\NP 0 2> (<T (S[dcl]\NP)/PP 0 2>
        (<L ((S[dcl]\NP)/PP)/NP VBD VBD posed ((S[dcl]\NP)/PP)/NP>) (<T NP 0 2> (<L NP/N DT DT a NP/N>)
        (<L N NN NN risk N>) ) ) (<T PP 0 2> (<L PP/NP TO TO to PP/NP>) (<T NP 0 2> (<L NP/N DT DT the NP/N>)
        (<T N 1 2> (<L N/N NNP NNP UK N/N>) (<L N NN NN economy N>) ) ) ) ) ) ) ) ) ) ) ) ) ) ) ) ) ) )''')
        # 1: In an upbeat assessment, Christine Lagarde said the UK was enjoying strong growth, record employment and had
        # largely recovered from the global financial crisis
        txt.append(r'''(<T S[dcl] 1 2> (<T S/S 0 2> (<L (S/S)/NP IN IN In (S/S)/NP>) (<T NP 0 2> (<L NP/N DT DT an NP/N>)
        (<T N 1 2> (<L N/N JJ JJ upbeat N/N>) (<L N NN NN assessment, N>) ) ) ) (<T S[dcl] 1 2> (<T NP 0 1>
        (<T N 1 2> (<L N/N NNP NNP Christine N/N>) (<L N NNP NNP Lagarde N>) ) ) (<T S[dcl]\NP 0 2>
        (<L (S[dcl]\NP)/S[dcl] VBD VBD said (S[dcl]\NP)/S[dcl]>) (<T S[dcl] 1 2> (<T NP 0 2> (<L NP/N DT DT the NP/N>)
        (<L N NNP NNP UK N>) ) (<T S[dcl]\NP 0 2> (<T S[dcl]\NP 0 2>
        (<L (S[dcl]\NP)/(S[ng]\NP) VBD VBD was (S[dcl]\NP)/(S[ng]\NP)>) (<T S[ng]\NP 0 2>
        (<L (S[ng]\NP)/NP VBG VBG enjoying (S[ng]\NP)/NP>) (<T NP 0 1> (<T N 1 2> (<L N/N JJ JJ strong N/N>)
        (<T N 1 2> (<L N/N NN NN growth, N/N>) (<T N 1 2> (<L N/N NN NN record N/N>) (<L N NN NN employment N>) ) ) )
        ) ) ) (<T (S[dcl]\NP)\(S[dcl]\NP) 1 2> (<L conj CC CC and conj>) (<T S[dcl]\NP 0 2>
        (<T (S[dcl]\NP)/(S[pt]\NP) 0 2> (<L (S[dcl]\NP)/(S[pt]\NP) VBD VBD had (S[dcl]\NP)/(S[pt]\NP)>)
        (<L (S\NP)\(S\NP) RB RB largely (S\NP)\(S\NP)>) ) (<T S[pt]\NP 0 2>
        (<L (S[pt]\NP)/PP VBN VBN recovered (S[pt]\NP)/PP>) (<T PP 0 2> (<L PP/NP IN IN from PP/NP>)
        (<T NP 0 2> (<L NP/N DT DT the NP/N>) (<T N 1 2> (<L N/N JJ JJ global N/N>) (<T N 1 2>
        (<L N/N JJ JJ financial N/N>) (<L N NN NN crisis N>) ) ) ) ) ) ) ) ) ) ) ) )''')
        # 2: Presenting the IMF’s annual healthcheck of the economy alongside George Osborne, Lagarde said there were
        # risks to the outlook, including from the housing market, but she was generally positive
        txt.append(r'''(<T S[dcl] 1 2> (<T S/S 0 1> (<T S[ng]\NP 0 2> (<T S[ng]\NP 0 2> (<T (S[ng]\NP)/PP 0 2>
        (<T (S[ng]\NP)/PP 0 2> (<L ((S[ng]\NP)/PP)/NP VBG VBG Presenting ((S[ng]\NP)/PP)/NP>) (<T NP 0 2>
        (<L NP/N DT DT the NP/N>) (<T N 1 2> (<L N/N NNS NNS IMF’s N/N>) (<T N 1 2> (<L N/N JJ JJ annual N/N>)
        (<T N 0 2> (<L N/PP NN NN healthcheck N/PP>) (<T PP 0 2> (<L PP/NP IN IN of PP/NP>) (<T NP 0 2>
        (<L NP/N DT DT the NP/N>) (<L N NN NN economy N>) ) ) ) ) ) ) ) (<T (S\NP)\(S\NP) 0 2>
        (<L ((S\NP)\(S\NP))/S[dcl] IN IN alongside ((S\NP)\(S\NP))/S[dcl]>) (<T S[dcl] 1 2> (<T NP 0 1> (<T N 1 2>
        (<L N/N NNP NNP George N/N>) (<T N 1 2> (<L N/N NNP NNP Osborne, N/N>) (<L N NNP NNP Lagarde N>) ) ) )
        (<T S[dcl]\NP 0 2> (<L (S[dcl]\NP)/S[dcl] VBD VBD said (S[dcl]\NP)/S[dcl]>) (<T S[dcl] 1 2>
        (<L NP[thr] EX EX there NP[thr]>) (<T S[dcl]\NP[thr] 0 2>
        (<L (S[dcl]\NP[thr])/NP VBD VBD were (S[dcl]\NP[thr])/NP>) (<T NP 0 1> (<L N NNS NNS risks N>) ) ) ) ) ) ) )
        (<T PP 0 2> (<L PP/NP TO TO to PP/NP>) (<T NP 0 2> (<L NP/N DT DT the NP/N>) (<L N NN NN outlook, N>) ) ) )
        (<T (S\NP)\(S\NP) 0 2> (<L ((S\NP)\(S\NP))/PP VBG VBG including ((S\NP)\(S\NP))/PP>) (<T PP 0 2>
        (<L PP/NP IN IN from PP/NP>) (<T NP 0 2> (<L NP/N DT DT the NP/N>) (<L N NN NN housing N>) ) ) ) ) )
        (<T S[dcl] 1 2> (<T NP 0 2> (<T NP 0 1> (<L N NN NN market, N>) ) (<T NP\NP 1 2> (<L conj CC CC but conj>)
        (<L NP PRP PRP she NP>) ) ) (<T S[dcl]\NP 0 2> (<L (S[dcl]\NP)/(S[adj]\NP) VBD VBD was (S[dcl]\NP)/(S[adj]\NP)>)
        (<T S[adj]\NP 1 2> (<L (S[adj]\NP)/(S[adj]\NP) RB RB generally (S[adj]\NP)/(S[adj]\NP)>)
        (<L S[adj]\NP JJ JJ positive S[adj]\NP>) ) ) ) )''')
        # 3: “The UK authorities have managed to repair the damage of the crisis in a way few other countries have been
        # able to do,” she said
        txt.append(r'''(<T S[dcl] 1 2> (<T NP 0 1> (<T N 1 2> (<L N/N NNP NNP “The N/N>) (<T N 1 2> (<L N/N NNP NNP UK N/N>)
        (<L N NNS NNS authorities N>) ) ) ) (<T S[dcl]\NP 0 2>
        (<L (S[dcl]\NP)/(S[pt]\NP) VBP VBP have (S[dcl]\NP)/(S[pt]\NP)>) (<T S[pt]\NP 0 2>
        (<L (S[pt]\NP)/(S[to]\NP) VBN VBN managed (S[pt]\NP)/(S[to]\NP)>) (<T S[to]\NP 0 2> (<T S[to]\NP 0 2>
        (<L (S[to]\NP)/(S[b]\NP) TO TO to (S[to]\NP)/(S[b]\NP)>) (<T S[b]\NP 0 2>
        (<L (S[b]\NP)/NP VB VB repair (S[b]\NP)/NP>) (<T NP 0 2> (<L NP/N DT DT the NP/N>) (<T N 0 2>
        (<L N/PP NN NN damage N/PP>) (<T PP 0 2> (<L PP/NP IN IN of PP/NP>) (<T NP 0 2> (<L NP/N DT DT the NP/N>)
        (<L N NN NN crisis N>) ) ) ) ) ) ) (<T (S\NP)\(S\NP) 0 2> (<L ((S\NP)\(S\NP))/NP IN IN in ((S\NP)\(S\NP))/NP>)
        (<T NP 0 2> (<L NP/N DT DT a NP/N>) (<T N 0 2> (<L N/S[dcl] NN NN way N/S[dcl]>) (<T S[dcl] 1 2>
        (<T S[dcl] 1 2> (<T NP 0 1> (<T N 1 2> (<L N/N JJ JJ few N/N>) (<T N 1 2> (<L N/N JJ JJ other N/N>)
        (<L N NNS NNS countries N>) ) ) ) (<T S[dcl]\NP 0 2>
        (<L (S[dcl]\NP)/(S[pt]\NP) VBP VBP have (S[dcl]\NP)/(S[pt]\NP)>) (<T S[pt]\NP 0 2>
        (<L (S[pt]\NP)/(S[adj]\NP) VBN VBN been (S[pt]\NP)/(S[adj]\NP)>) (<T S[adj]\NP 0 2>
        (<L (S[adj]\NP)/(S[to]\NP) JJ JJ able (S[adj]\NP)/(S[to]\NP)>) (<T S[to]\NP 0 2>
        (<L S[to]\NP TO TO to S[to]\NP>) (<L RQU VB VB do,” RQU>) ) ) ) ) ) (<T S[dcl]\S[dcl] 1 2>
        (<L NP PRP PRP she NP>) (<L (S[dcl]\S[dcl])\NP VBD VBD said (S[dcl]\S[dcl])\NP>) ) ) ) ) ) ) ) ) )''')
        # 4: Lagarde said the IMF would work through various scenarios for the EU referendum outcome in its next assessment
        # of the UK in May 2016
        txt.append(r'''(<T S[dcl] 1 2> (<T NP 0 1> (<L N NNP NNP Lagarde N>) ) (<T S[dcl]\NP 0 2>
        (<L (S[dcl]\NP)/S[dcl] VBD VBD said (S[dcl]\NP)/S[dcl]>) (<T S[dcl] 1 2> (<T NP 0 2> (<L NP/N DT DT the NP/N>)
        (<L N NNP NNP IMF N>) ) (<T S[dcl]\NP 0 2> (<T S[dcl]\NP 0 2>
        (<L (S[dcl]\NP)/(S[b]\NP) MD MD would (S[dcl]\NP)/(S[b]\NP)>) (<T S[b]\NP 0 2>
        (<L (S[b]\NP)/PP VB VB work (S[b]\NP)/PP>) (<T PP 0 2> (<L PP/NP IN IN through PP/NP>) (<T NP 0 1>
        (<T N 1 2> (<L N/N JJ JJ various N/N>) (<T N 0 2> (<L N/PP NNS NNS scenarios N/PP>) (<T PP 0 2>
        (<L PP/NP IN IN for PP/NP>) (<T NP 0 2> (<L NP/N DT DT the NP/N>) (<T N 1 2> (<L N/N NNP NNP EU N/N>)
        (<T N 1 2> (<L N/N NN NN referendum N/N>) (<T N 0 2> (<L N/PP NN NN outcome N/PP>) (<T PP 0 2>
        (<L PP/NP IN IN in PP/NP>) (<T NP 0 2> (<L NP/(N/PP) PRP$ PRP$ its NP/(N/PP)>) (<T N/PP 1 2>
        (<L N/N JJ JJ next N/N>) (<T N/PP 0 2> (<L (N/PP)/PP NN NN assessment (N/PP)/PP>) (<T PP 0 2>
        (<L PP/NP IN IN of PP/NP>) (<T NP 0 2> (<L NP/N DT DT the NP/N>) (<L N NNP NNP UK N>) ) ) ) ) ) ) ) ) ) ) ) ) )
        ) ) ) ) (<T (S\NP)\(S\NP) 0 2> (<L ((S\NP)\(S\NP))/NP IN IN in ((S\NP)\(S\NP))/NP>) (<T NP 0 1> (<T N 0 2>
        (<L N NNP NNP May N>) (<L N\N CD CD 2016 N\N>) ) ) ) ) ) ) )''')
        # 5: “On a personal basis … I am very, very much hopeful that the UK stays within the EU,” she added
        txt.append(r'''
(<T NP 1 2>
    (<L NP/NP NN NN “On NP/NP>)
    (<T NP 0 2>
        (<L NP/N DT DT a NP/N>)
        (<T N 0 2>
            (<T N 0 2>
                (<T N 1 2>
                    (<L N/N JJ JJ personal N/N>)
                    (<T N 0 2>
                        (<L N NN NN basis N>)
                        (<L RQU NN NN … RQU>)
                    )
                )
                (<T N\N 0 1>
                    (<T S[dcl]/NP 1 2>
                        (<T S[X]/(S[X]\NP) 0 1>
                            (<L NP PRP PRP I NP>)
                        )
                        (<L (S[dcl]\NP)/NP VBP VBP am (S[dcl]\NP)/NP>)
                    )
                )
            )
            (<T N\N 0 1>
                (<T S[adj]\NP 0 2>
                    (<T (S[adj]\NP)/S[em] 0 2>
                        (<L ((S[adj]\NP)/S[em])/(S[adj]\NP) RB RB very, ((S[adj]\NP)/S[em])/(S[adj]\NP)>)
                        (<T S[adj]\NP 1 2>
                            (<L (S[adj]\NP)/(S[adj]\NP) RB RB very (S[adj]\NP)/(S[adj]\NP)>)
                            (<T S[adj]\NP 1 2>
                                (<L (S[adj]\NP)/(S[adj]\NP) JJ JJ much (S[adj]\NP)/(S[adj]\NP)>)
                                (<L S[adj]\NP NN NN hopeful S[adj]\NP>)
                            )
                        )
                    )
                    (<T S[em] 0 2>
                        (<L S[em]/S[dcl] IN IN that S[em]/S[dcl]>)
                        (<T S[dcl] 1 2>
                            (<T S[dcl] 1 2>
                                (<T NP 0 2>
                                    (<L NP/N DT DT the NP/N>)
                                    (<L N NNP NNP UK N>)
                                )
                                (<T S[dcl]\NP 0 2>
                                    (<L (S[dcl]\NP)/PP VBZ VBZ stays (S[dcl]\NP)/PP>)
                                    (<T PP 0 2>
                                        (<L PP/NP IN IN within PP/NP>)
                                        (<T NP 0 2>
                                            (<L NP/N DT DT the NP/N>)
                                            (<L N NNP NNP EU,” N>)
                                        )
                                    )
                                )
                            )
                            (<T S[dcl]\S[dcl] 1 2>
                                (<L NP PRP PRP she NP>)
                                (<L (S[dcl]\S[dcl])\NP VBD VBD added (S[dcl]\S[dcl])\NP>)
                            )
                        )
                    )
                )
            )
        )
    )
)''')
        # 6: Separately, ratings agency Standard & Poor’s reiterated a warning on Friday that leaving the EU could cost
        # the UK its top credit score
        txt.append(r'''(<T S[dcl] 1 2> (<T NP 0 1> (<T N 1 2> (<T N/N 1 2> (<L (N/N)/(N/N) NN NN Separately, (N/N)/(N/N)>)
        (<T N/N 1 2> (<L (N/N)/(N/N) NNS NNS ratings (N/N)/(N/N)>) (<L N/N NN NN agency N/N>) ) ) (<T N 1 2>
        (<L N/N NNP NNP Standard N/N>) (<T N 1 2> (<L N/N CC CC & N/N>) (<L N NNP NNP Poor’s N>) ) ) ) )
        (<T S[dcl]\NP 0 2> (<T S[dcl]\NP 0 2> (<L (S[dcl]\NP)/NP VBD VBD reiterated (S[dcl]\NP)/NP>) (<T NP 0 2>
        (<L NP/N DT DT a NP/N>) (<L N NN NN warning N>) ) ) (<T (S\NP)\(S\NP) 0 2>
        (<L ((S\NP)\(S\NP))/NP IN IN on ((S\NP)\(S\NP))/NP>) (<T NP 0 1> (<T N 0 2> (<L N NNP NNP Friday N>)
        (<T N\N 0 2> (<L (N\N)/S[dcl] WDT WDT that (N\N)/S[dcl]>) (<T S[dcl] 1 2> (<T NP 0 1> (<T S[ng]\NP 0 2>
        (<L (S[ng]\NP)/NP VBG VBG leaving (S[ng]\NP)/NP>) (<T NP 0 2> (<L NP/N DT DT the NP/N>) (<L N NNP NNP EU N>) ) )
         ) (<T S[dcl]\NP 0 2> (<L (S[dcl]\NP)/(S[b]\NP) MD MD could (S[dcl]\NP)/(S[b]\NP)>) (<T S[b]\NP 0 2>
         (<T (S[b]\NP)/NP 0 2> (<L ((S[b]\NP)/NP)/NP VB VB cost ((S[b]\NP)/NP)/NP>) (<T NP 0 2>
         (<L NP/N DT DT the NP/N>) (<L N NNP NNP UK N>) ) ) (<T NP 0 2> (<L NP/(N/PP) PRP$ PRP$ its NP/(N/PP)>)
         (<T N/PP 1 2> (<L N/N JJ JJ top N/N>) (<T N/PP 1 2> (<L N/N NN NN credit N/N>) (<L N/PP NN NN score N/PP>) ) )
        ) ) ) ) ) ) ) ) ) )''')
        # 7: The IMF, which is based in Washington, also used its assessment to recommend that interest rates remain at
        # their record low of 0
        txt.append(r'''(<T S[dcl] 1 2> (<T NP 0 2> (<L NP/N DT DT The NP/N>) (<T N 0 2> (<L N NN NN IMF, N>) (<T N\N 0 2>
        (<L (N\N)/(S[dcl]\NP) WDT WDT which (N\N)/(S[dcl]\NP)>) (<T S[dcl]\NP 0 2>
        (<L (S[dcl]\NP)/(S[pss]\NP) VBZ VBZ is (S[dcl]\NP)/(S[pss]\NP)>) (<T S[pss]\NP 0 2>
        (<L (S[pss]\NP)/PP VBN VBN based (S[pss]\NP)/PP>) (<T PP 0 2> (<L PP/NP IN IN in PP/NP>) (<T NP 0 1>
        (<L N NNP NNP Washington, N>) ) ) ) ) ) ) ) (<T S[dcl]\NP 1 2> (<L (S\NP)/(S\NP) RB RB also (S\NP)/(S\NP)>)
        (<T S[dcl]\NP 0 2> (<T (S[dcl]\NP)/(S[to]\NP) 0 2>
        (<L ((S[dcl]\NP)/(S[to]\NP))/NP VBD VBD used ((S[dcl]\NP)/(S[to]\NP))/NP>) (<T NP 0 2>
        (<L NP/(N/PP) PRP$ PRP$ its NP/(N/PP)>) (<L N/PP NN NN assessment N/PP>) ) ) (<T S[to]\NP 0 2>
        (<L (S[to]\NP)/(S[b]\NP) TO TO to (S[to]\NP)/(S[b]\NP)>) (<T S[b]\NP 0 2>
        (<L (S[b]\NP)/S[em] VB VB recommend (S[b]\NP)/S[em]>) (<T S[em] 0 2> (<L S[em]/S[dcl] IN IN that S[em]/S[dcl]>)
        (<T S[dcl] 1 2> (<T NP 0 1> (<T N 1 2> (<L N/N NN NN interest N/N>) (<L N NNS NNS rates N>) ) )
        (<T S[dcl]\NP 0 2> (<L (S[dcl]\NP)/PP VBP VBP remain (S[dcl]\NP)/PP>) (<T PP 0 2> (<L PP/NP IN IN at PP/NP>)
        (<T NP 0 2> (<L NP/(N/PP) PRP$ PRP$ their NP/(N/PP)>) (<T N/PP 1 2> (<L N/N NN NN record N/N>) (<T N/PP 0 2>
        (<L (N/PP)/PP NN NN low (N/PP)/PP>) (<T PP 0 2> (<L PP/NP IN IN of PP/NP>) (<T NP 0 1> (<L N CD CD 0 N>) ) ) )
        ) ) ) ) ) ) ) ) ) ) )''')
        # 8: 0.5% until there were clearer signs of inflationary pressures
        txt.append(r'''(<T NP 0 1> (<T N 0 2> (<L N NN NN 5% N>) (<T N\N 0 2> (<L (N\N)/S[dcl] IN IN until (N\N)/S[dcl]>)
        (<T S[dcl] 1 2> (<L NP[thr] EX EX there NP[thr]>) (<T S[dcl]\NP[thr] 0 2>
        (<L (S[dcl]\NP[thr])/NP VBD VBD were (S[dcl]\NP[thr])/NP>) (<T NP 0 1> (<T N 1 2>
        (<L N/N JJR JJR clearer N/N>) (<T N 0 2> (<L N/PP NNS NNS signs N/PP>) (<T PP 0 2> (<L PP/NP IN IN of PP/NP>)
        (<T NP 0 1> (<T N 1 2> (<L N/N JJ JJ inflationary N/N>) (<L N NNS NNS pressures N>) ) ) ) ) ) ) ) ) ) ) )''')
        # 9: Its report on the UK was delayed for six months due to the general election
        txt.append(r'''(<T S[dcl] 1 2> (<T NP 0 2> (<L NP/(N/PP) PRP$ PRP$ Its NP/(N/PP)>) (<T N/PP 0 2>
        (<L (N/PP)/PP NN NN report (N/PP)/PP>) (<T PP 0 2> (<L PP/NP IN IN on PP/NP>) (<T NP 0 2>
        (<L NP/N DT DT the NP/N>) (<L N NNP NNP UK N>) ) ) ) ) (<T S[dcl]\NP 0 2> (<T S[dcl]\NP 0 2> (<T S[dcl]\NP 0 2>
        (<L (S[dcl]\NP)/(S[pss]\NP) VBD VBD was (S[dcl]\NP)/(S[pss]\NP)>) (<L S[pss]\NP VBN VBN delayed S[pss]\NP>) )
        (<T (S\NP)\(S\NP) 0 2> (<L ((S\NP)\(S\NP))/NP IN IN for ((S\NP)\(S\NP))/NP>) (<T NP 0 1> (<T N 1 2>
        (<L N/N CD CD six N/N>) (<L N NNS NNS months N>) ) ) ) ) (<T (S\NP)\(S\NP) 0 2>
        (<L ((S\NP)\(S\NP))/PP JJ JJ due ((S\NP)\(S\NP))/PP>) (<T PP 0 2> (<L PP/NP TO TO to PP/NP>) (<T NP 0 2>
        (<L NP/N DT DT the NP/N>) (<T N 1 2> (<L N/N JJ JJ general N/N>) (<L N NN NN election N>) ) ) ) ) ) )''')
        for t in txt[5:6]:
            pt = parse_ccg_derivation(t)
            self.assertIsNotNone(pt)
            s = sentence_from_pt(pt)
            dprint(s)
            d = process_ccg_pt(pt, CO_VERIFY_SIGNATURES | CO_NO_VERBNET | CO_NO_WIKI_SEARCH).get_drs()
            self.assertIsNotNone(d)
            dprint(d)

    def test5_AT1(self):
        txt = r'''(<T S[dcl] 1 2> (<T S/S 0 2> (<L (S/S)/NP IN IN At (S/S)/NP>) (<T NP 0 2> (<L NP/N DT DT a NP/N>) (<L N NN NN minimum, N>) ) ) (<T S[dcl] 1 2> (<L NP PRP PRP we NP>) (<T S[dcl]\NP 0 2> (<L (S[dcl]\NP)/(S[to]\NP) VBP VBP need (S[dcl]\NP)/(S[to]\NP)>) (<T S[to]\NP 0 2> (<L (S[to]\NP)/(S[b]\NP) TO TO to (S[to]\NP)/(S[b]\NP)>) (<T S[b]\NP 0 2> (<L (S[b]\NP)/NP VB VB get (S[b]\NP)/NP>) (<T NP 0 2> (<L NP/N DT DT this NP/N>) (<L N NN NN right. N>) ) ) ) ) ) )'''
        pt = parse_ccg_derivation(txt)
        self.assertIsNotNone(pt)
        s = sentence_from_pt(pt)
        dprint(s)
        d = process_ccg_pt(pt, CO_VERIFY_SIGNATURES | CO_NO_VERBNET | CO_NO_WIKI_SEARCH).get_drs()
        self.assertIsNotNone(d)
        dprint(d)

    def test5_AT2(self):
        txt = r'''(<T NP 0 2> (<L NP/N DT DT The NP/N>) (<T N 0 2> (<L N NN NN world N>) (<T N\N 0 2> (<L (N\N)/NP IN IN at (N\N)/NP>) (<T NP 0 1> (<L N NN NN large. N>) ) ) ) )'''
        pt = parse_ccg_derivation(txt)
        self.assertIsNotNone(pt)
        s = sentence_from_pt(pt)
        dprint(s)
        d = process_ccg_pt(pt, CO_VERIFY_SIGNATURES | CO_NO_VERBNET | CO_NO_WIKI_SEARCH).get_drs()
        self.assertIsNotNone(d)
        dprint(d)

    def test6_Gerund1(self):
        txt = r'''(<T S[dcl] 1 2> (<T S[dcl] 1 2> (<T S/S 0 1> (<T S[ng]\NP 0 2> (<T (S[ng]\NP)/PP 0 2> (<L ((S[ng]\NP)/PP)/NP VBG VBG Presenting ((S[ng]\NP)/PP)/NP>) (<T NP 0 2> (<L NP/N DT DT the NP/N>) (<T N 1 2> (<L N/N NNS NNS IMF’s N/N>) (<T N 1 2> (<L N/N JJ JJ annual N/N>) (<T N 0 2> (<L N/PP NN NN healthcheck N/PP>) (<T PP 0 2> (<L PP/NP IN IN of PP/NP>) (<T NP 0 2> (<L NP/N DT DT the NP/N>) (<L N NN NN economy N>) ) ) ) ) ) ) ) (<T PP 0 2> (<T PP 0 2> (<L PP/NP IN IN alongside PP/NP>) (<T NP 0 1> (<T N 1 2> (<L N/N NNP NNP George N/N>) (<L N NNP NNP Osborne N>) ) ) ) (<L , , , , ,>) ) ) ) (<T S[dcl] 0 2> (<T S[dcl] 0 2> (<T S[dcl] 0 2> (<T S[dcl] 1 2> (<T NP 0 1> (<L N NNP NNP Lagarde N>) ) (<T S[dcl]\NP 0 2> (<L (S[dcl]\NP)/S[dcl] VBD VBD said (S[dcl]\NP)/S[dcl]>) (<T S[dcl] 1 2> (<L NP[thr] EX EX there NP[thr]>) (<T S[dcl]\NP[thr] 0 2> (<L (S[dcl]\NP[thr])/NP VBD VBD were (S[dcl]\NP[thr])/NP>) (<T NP 0 1> (<T N 0 2> (<L N/PP NNS NNS risks N/PP>) (<T PP 0 2> (<L PP/NP TO TO to PP/NP>) (<T NP 0 2> (<L NP/N DT DT the NP/N>) (<L N NN NN outlook N>) ) ) ) ) ) ) ) ) (<L , , , , ,>) ) (<T S\S 0 2> (<L (S\S)/PP VBG VBG including (S\S)/PP>) (<T PP 0 2> (<L PP/NP IN IN from PP/NP>) (<T NP 0 2> (<L NP/N DT DT the NP/N>) (<T N 1 2> (<L N/N NN NN housing N/N>) (<L N NN NN market N>) ) ) ) ) ) (<L , , , , ,>) ) ) (<T S[dcl]\S[dcl] 1 2> (<L conj CC CC but conj>) (<T S[dcl] 1 2> (<L NP PRP PRP she NP>) (<T S[dcl]\NP 0 2> (<L (S[dcl]\NP)/(S[adj]\NP) VBD VBD was (S[dcl]\NP)/(S[adj]\NP)>) (<T S[adj]\NP 1 2> (<L (S[adj]\NP)/(S[adj]\NP) RB RB generally (S[adj]\NP)/(S[adj]\NP)>) (<L S[adj]\NP JJ JJ positive. S[adj]\NP>) ) ) ) ) )'''
        pt = parse_ccg_derivation(txt)
        self.assertIsNotNone(pt)
        s = sentence_from_pt(pt)
        dprint(s)
        d = process_ccg_pt(pt, CO_VERIFY_SIGNATURES | CO_NO_VERBNET | CO_NO_WIKI_SEARCH).get_drs()
        self.assertIsNotNone(d)
        dprint(d)

    def test7_AdjPhrasE1(self):
        txt = r'''(<T S[dcl] 1 2> (<T NP 0 2> (<L NP/N PRP$ PRP$ Your NP/N>) (<T N 1 2> (<L N/N NN NN apple N/N>) (<L N NN NN pie N>) ) ) (<T S[dcl]\NP 0 2> (<L S[dcl]\NP VBZ VBZ smells S[dcl]\NP>) (<T (S\NP)\(S\NP) 1 2> (<L ((S\NP)\(S\NP))/((S\NP)\(S\NP)) RB RB very ((S\NP)\(S\NP))/((S\NP)\(S\NP))>) (<L (S\NP)\(S\NP) JJ JJ tempting. (S\NP)\(S\NP)>) ) ) )'''
        # (<T S[dcl] 1 2>
        #   (<T NP 0 2>
        #     (<L NP/N PRP$ PRP$ Your NP_636/N_636>)
        #     (<T N 1 2>
        #       (<L N/N NN NN apple N_107/N_107>)
        #       (<L N NN NN pie N>)
        #     )
        #   )
        #   (<T S[dcl]\NP 0 2>
        #     (<L S[dcl]\NP VBZ VBZ smells S[dcl]\NP_125>)
        #     (<T (S\NP)\(S\NP) 1 2>
        #       (<L ((S\NP)\(S\NP))/((S\NP)\(S\NP)) RB RB very ((S_133\NP_134)\(S_133\NP_134))/((S_133\NP_134)\(S_133\NP_134))>)
        #       (<L (S\NP)\(S\NP) JJ JJ tempting. (S_113\NP_114)\(S_113\NP_114)>)
        #     )
        #   )
        # )
        # [X1,E2,X3| _ENTITY(X1),_ENTITY(X1),[| your(X3)] ⇒ [| you(X1),owns(X1,X3)],apple(X1),pie(X1),_EVENT(E2),smells(E2),_AGENT(E2,X3),very(E2),tempting(E2)]
        pt = parse_ccg_derivation(txt)
        self.assertIsNotNone(pt)
        s = sentence_from_pt(pt)
        dprint(s)
        d = process_ccg_pt(pt, CO_VERIFY_SIGNATURES | CO_NO_VERBNET | CO_NO_WIKI_SEARCH).get_drs()
        self.assertIsNotNone(d)
        dprint(d)

    def test8_CopularToBE1(self):
        # I am sorry
        txt=r'''(<T S[dcl] 1 2> (<L NP PRP PRP I NP>) (<T S[dcl]\NP 0 2>
        (<L (S[dcl]\NP)/(S[adj]\NP) VBP VBP am (S[dcl]\NP)/(S[adj]\NP)>) (<L S[adj]\NP IN IN sorry. S[adj]\NP>) ) )'''
        pt = parse_ccg_derivation(txt)
        self.assertIsNotNone(pt)
        s = sentence_from_pt(pt)
        dprint(s)
        d = process_ccg_pt(pt, CO_VERIFY_SIGNATURES | CO_NO_VERBNET).get_drs()
        self.assertIsNotNone(d)
        dprint(d)

    def test8_NonCopularToBE1(self):
        txt = r'''(<T S[dcl] 1 2> (<L NP PRP PRP I NP>) (<T S[dcl]\NP 0 2>
        (<L (S[dcl]\NP)/(S[adj]\NP) VBP VBP am (S[dcl]\NP)/(S[adj]\NP)>) (<T S[adj]\NP 1 2>
        (<L (S[adj]\NP)/(S[adj]\NP) RB RB really (S[adj]\NP)/(S[adj]\NP)>) (<T S[adj]\NP 0 2>
        (<L (S[adj]\NP)/PP VBN VBN disappointed (S[adj]\NP)/PP>) (<T PP 0 2> (<L PP/NP IN IN with PP/NP>) (<T NP 0 2>
        (<L NP/N DT DT the NP/N>) (<L N NN NN review. N>) ) ) ) ) ) )'''
        pt = parse_ccg_derivation(txt)
        self.assertIsNotNone(pt)
        s = sentence_from_pt(pt)
        dprint(s)
        d = process_ccg_pt(pt, CO_VERIFY_SIGNATURES | CO_NO_VERBNET | CO_NO_WIKI_SEARCH).get_drs()
        self.assertIsNotNone(d)
        dprint(d)

    def test8_NonCopularToBE2(self):
        # I am really sorry
        txt = r'''(<T S[dcl] 1 2> (<L NP PRP PRP I NP>) (<T S[dcl]\NP 0 2> (<T (S[dcl]\NP)/(S[adj]\NP) 0 2>
        (<L (S[dcl]\NP)/(S[adj]\NP) VBP VBP am (S[dcl]\NP)/(S[adj]\NP)>) (<L (S\NP)\(S\NP) RB RB really (S\NP)\(S\NP)>)
        ) (<L S[adj]\NP JJ JJ sorry. S[adj]\NP>) ) )'''
        pt = parse_ccg_derivation(txt)
        self.assertIsNotNone(pt)
        s = sentence_from_pt(pt)
        dprint(s)
        d = process_ccg_pt(pt, CO_VERIFY_SIGNATURES | CO_NO_VERBNET).get_drs()
        self.assertIsNotNone(d)
        dprint(d)

    def test9_Verbnet1(self):
        txt = r'''(<T S[dcl] 1 2> (<T NP 0 1> (<L N NNP NNP Jim N>) ) (<T S[dcl]\NP 0 2> (<L (S[dcl]\NP)/(S[to]\NP) VBZ VBZ likes (S[dcl]\NP)/(S[to]\NP)>) (<T S[to]\NP 0 2> (<L (S[to]\NP)/(S[b]\NP) TO TO to (S[to]\NP)/(S[b]\NP)>) (<T S[b]\NP 0 2> (<L (S[b]\NP)/PP VB VB jump (S[b]\NP)/PP>) (<T PP 0 2> (<L PP/NP IN IN over PP/NP>) (<T NP 0 2> (<L NP/N DT DT the NP/N>) (<L N NN NN dog. N>) ) ) ) ) ) )'''
        pt = parse_ccg_derivation(txt)
        self.assertIsNotNone(pt)
        s = sentence_from_pt(pt)
        dprint(s)
        d = process_ccg_pt(pt, CO_VERIFY_SIGNATURES | CO_NO_WIKI_SEARCH).get_drs()
        self.assertIsNotNone(d)
        dprint(d)

    def test9_VPcordination(self):
        # I was early yesterday and late today
        txt = r'''(<T S[dcl] 1 2> (<L NP PRP PRP I NP>) (<T S[dcl]\NP 0 2> (<L S[dcl]\NP VBD VBD was S[dcl]\NP>)
        (<T (S\NP)\(S\NP) 0 2> (<T (S\NP)\(S\NP) 1 2>
        (<L ((S\NP)\(S\NP))/((S\NP)\(S\NP)) JJ JJ early ((S\NP)\(S\NP))/((S\NP)\(S\NP))>)
        (<L (S\NP)\(S\NP) NN NN yesterday (S\NP)\(S\NP)>) ) (<T ((S\NP)\(S\NP))\((S\NP)\(S\NP)) 1 2>
        (<L conj CC CC and conj>) (<T (S\NP)\(S\NP) 1 2>
        (<L ((S\NP)\(S\NP))/((S\NP)\(S\NP)) JJ JJ late ((S\NP)\(S\NP))/((S\NP)\(S\NP))>)
        (<L (S\NP)\(S\NP) NN NN today (S\NP)\(S\NP)>) ) ) ) ) )'''
        # 00 <PushOp>:(i, NP, PRP)
        # 01 <PushOp>:(be, S[dcl]\NP, VBD)
        # 02 <PushOp>:(early, ((S\NP)\(S\NP))/((S\NP)\(S\NP)), JJ)
        # 03 <PushOp>:(yesterday, (S\NP)\(S\NP), NN)
        # 04 <ExecOp>:(2, FA (S\NP)\(S\NP))
        # 05 <PushOp>:(and, conj, CC)
        # 06 <PushOp>:(late, ((S\NP)\(S\NP))/((S\NP)\(S\NP)), JJ)
        # 07 <PushOp>:(today, (S\NP)\(S\NP), NN)
        # 08 <ExecOp>:(2, FA (S\NP)\(S\NP))
        # 09 <ExecOp>:(2, R_UNARY_TC ((S\NP)\(S\NP))\((S\NP)\(S\NP)))
        # 10 <ExecOp>:(2, BA (S\NP)\(S\NP))
        # 11 <ExecOp>:(2, BA S[dcl]\NP)
        # 12 <ExecOp>:(2, BA S[dcl])
        pt = parse_ccg_derivation(txt)
        self.assertIsNotNone(pt)
        s = sentence_from_pt(pt)
        dprint(s)
        builder = process_ccg_pt(pt, CO_VERIFY_SIGNATURES | CO_NO_VERBNET | CO_NO_WIKI_SEARCH)
        d = builder.get_drs()
        self.assertIsNotNone(d)
        dprint(d)

    def test9_ApposExtraposition(self):
        # Factory inventories fell 0.1% in September , the first decline since February 1987.
        #
        # [X1,E2,X3,X4,X5| factory(X1),inventories(X1),fell(E2),_EVENT(E2),_AGENT(E2,X1),_THEME(E2,X6),0.1%(X6),
        # in(E2,X4),September(X3),first(X4),decline(X4),since(X4,X5),February(X5),1987(X5),_NUM(X5)]
        #
        # should be in(E2, X3)
        txt = r'''(<T S[dcl] 1 2> (<T NP 0 1> (<T N 1 2> (<L N/N NN NN Factory N/N>) (<L N NNS NNS inventories N>) ) )
        (<T S[dcl]\NP 0 2> (<T S[dcl]\NP 0 2> (<L (S[dcl]\NP)/PP VBD VBD fell (S[dcl]\NP)/PP>) (<L PP CD CD 0.1% PP>) )
        (<T (S\NP)\(S\NP) 0 2> (<L ((S\NP)\(S\NP))/NP IN IN in ((S\NP)\(S\NP))/NP>) (<T NP 0 2> (<T NP 0 1>
        (<L N NNP NNP September N>) ) (<T NP\NP 1 2> (<L , , , , ,>) (<T NP 0 2> (<L NP/N DT DT the NP/N>) (<T N 0 2>
        (<T N 1 2> (<L N/N JJ JJ first N/N>) (<L N NN NN decline N>) ) (<T N\N 0 2> (<L (N\N)/NP IN IN since (N\N)/NP>)
        (<T NP 0 1> (<T N 0 2> (<L N NNP NNP February N>) (<L N\N CD CD 1987. N\N>) ) ) ) ) ) ) ) ) ) )'''
        pt = parse_ccg_derivation(txt)
        self.assertIsNotNone(pt)
        s = sentence_from_pt(pt)
        dprint(s)
        builder = process_ccg_pt(pt, CO_VERIFY_SIGNATURES | CO_NO_VERBNET | CO_NO_WIKI_SEARCH)
        d = builder.get_drs()
        self.assertIsNotNone(d)
        dprint(d)

    def testA0_NYIMES(self):
        txt = r'''
(<T S[dcl] 1 2>
    (<T S[dcl] 1 2>
        (<T NP 0 2>
            (<L NP/N DT DT The NP/N>)
            (<T N 1 2>
                (<L N/N JJ JJ long N/N>)
                (<T N 1 2>
                    (<L N/N NN NN smelting N/N>)
                    (<L N NNS NNS sheds N>)
                )
            )
        )
        (<T S[dcl]\NP 0 2>
            (<T S[dcl]\NP 0 2>
                (<L (S[dcl]\NP)/(S[pss]\NP) VBP VBP are (S[dcl]\NP)/(S[pss]\NP)>)
                (<T S[pss]\NP 0 2>
                    (<T (S[pss]\NP)/PP 0 2>
                        (<L (S[pss]\NP)/PP VBN VBN bound (S[pss]\NP)/PP>)
                        (<L (S\NP)\(S\NP) RB RB together (S\NP)\(S\NP)>)
                    )
                    (<T PP 0 2>
                        (<L PP/NP IN IN by PP/NP>)
                        (<T NP 0 1>
                            (<T N 1 2>
                                (<T N/N 0 2>
                                    (<L N/N JJ JJ large N/N>)
                                    (<L , , , , ,>)
                                )
                                (<T N 1 2>
                                    (<L N/N JJ JJ colorful N/N>)
                                    (<L N NNS NNS pipes N>)
                                )
                            )
                        )
                    )
                )
            )
            (<L , , , , ,>)
        )
    )
    (<T S[dcl]\S[dcl] 1 2>
        (<T conj 0 2>
            (<L conj CC CC and conj>)
            (<L , , , , ,>)
        )
        (<T S[dcl] 1 2>
            (<T S/S 0 2>
                (<L (S/S)/S[dcl] IN IN because (S/S)/S[dcl]>)
                (<T S[dcl] 1 2>
                    (<L NP DT DT this NP>)
                    (<T S[dcl]\NP 0 2>
                        (<T S[dcl]\NP 0 2>
                            (<L (S[dcl]\NP)/NP VBZ VBZ is (S[dcl]\NP)/NP>)
                            (<T NP 0 1>
                                (<L N NNP NNP Scandinavia N>)
                            )
                        )
                        (<L , , , , ,>)
                    )
                )
            )
            (<T S[dcl] 1 2>
                (<T NP 0 2>
                    (<L NP/N DT DT the NP/N>)
                    (<L N NN NN company N>)
                )
                (<T S[dcl]\NP 0 2>
                    (<L (S[dcl]\NP)/NP VBD VBD held (S[dcl]\NP)/NP>)
                    (<T NP 0 2>
                        (<L NP/N DT DT an NP/N>)
                        (<T N 1 2>
                            (<L N/N JJ JJ architectural N/N>)
                            (<T N 0 2>
                                (<L N/PP NN NN competition N/PP>)
                                (<T PP 0 2>
                                    (<L PP/NP IN IN for PP/NP>)
                                    (<T NP 0 2>
                                        (<L NP/N DT DT the NP/N>)
                                        (<T N 0 2>
                                            (<L N/PP NN NN design N/PP>)
                                            (<T PP 0 2>
                                                (<L PP/NP IN IN of PP/NP>)
                                                (<T NP 0 2>
                                                    (<L NP/N DT DT the NP/N>)
                                                    (<T N 1 2>
                                                        (<L N/N JJ JJ administrative N/N>)
                                                        (<L N NN NN wing. N>)
                                                    )
                                                )
                                            )
                                        )
                                    )
                                )
                            )
                        )
                    )
                )
            )
        )
    )
)'''
        pt = parse_ccg_derivation(txt)
        self.assertIsNotNone(pt)
        s = sentence_from_pt(pt)
        dprint(s)
        builder = process_ccg_pt(pt, CO_VERIFY_SIGNATURES | CO_NO_VERBNET | CO_NO_WIKI_SEARCH)
        d = builder.get_drs()
        self.assertIsNotNone(d)
        dprint(d)

    def testA1_ParseEasySRL2005T13(self):
        # This test requires you run the following scripts:
        # - ./scripts/extract_lfs.sh
        #   Extracts LDC2005T13 dataset
        # - ./scripts/start_server.sh easysrl
        #   Starts the easysrl server. You can also run in a shell if you wish by
        #   opening a new shell and running ./daemons/easysrl
        # - ./scripts/make_easysrl_ldc_derivations.py
        #
        # Once that is done you can stop the server with:
        #    ./scripts/stop_server.sh easysrl
        #    or Ctrl-C if you ran the daemon in a shell.
        #
        # This only needs to be done once to build the EasySRL CCG derivations for
        # the LDC2005T13 dataset.
        allfiles = []
        projdir = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))))))
        ldcpath = os.path.join(projdir, 'data', 'ldc', 'easysrl', 'ccgbank')
        dirlist1 = os.listdir(ldcpath)
        for fname in dirlist1:
            if 'ccg_derivation' not in fname:
                continue
            ldcpath1 = os.path.join(ldcpath, fname)
            if os.path.isfile(ldcpath1):
                allfiles.append(ldcpath1)

        failed_parse = []
        failed_ccg2drs = []
        start = 0
        for fn in allfiles:
            with open(fn, 'r') as fd:
                lines = fd.readlines()

            name, _ = os.path.splitext(os.path.basename(fn))
            for i in range(start, len(lines), 200):
                start = 50
                ccgbank = lines[i]
                hdr = '%s-%04d' % (name, i)
                dprint(hdr)
                try:
                    pt = parse_ccg_derivation(ccgbank)
                    dprint(sentence_from_pt(pt))
                    dprint_ccgbank(ccgbank)
                except Exception:
                    failed_parse.append(hdr)
                    continue
                #d = process_ccg_pt(pt, CO_PRINT_DERIVATION|CO_VERIFY_SIGNATURES)
                try:
                    ccg = process_ccg_pt(pt, CO_VERIFY_SIGNATURES | CO_NO_VERBNET | CO_NO_WIKI_SEARCH)
                    dprint_constituent_tree(ccg, ccg.get_constituent_tree())
                    dprint_dependency_tree(ccg, ccg.get_dependency_tree())
                    d = ccg.get_drs()
                    assert d is not None
                    s = d.show(SHOW_LINEAR)
                    dprint(s)
                except Exception as e:
                    raise
                    dprint(e)
                    failed_ccg2drs.append(hdr)
                    continue

        if failed_parse != 0:
            dprint('%d derivations failed to parse' % len(failed_parse))
            for x in failed_parse:
                dprint('  ' + x)
        if len(failed_ccg2drs) != 0:
            dprint('%d derivations failed to convert to DRS' % len(failed_ccg2drs))
            for x in failed_ccg2drs:
                dprint('  ' + x)

        self.assertEqual(len(failed_ccg2drs), 0)
        self.assertEqual(len(failed_parse), 0)

    def testA2_ParseLdc2005T13(self):
        # LDC2005T13 is a conversion of the Penn Treebank into CCG derivations.
        allfiles = []
        projdir = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))))))
        ldcpath = os.path.join(projdir, 'data', 'ldc', 'ccgbank_1_1', 'data', 'AUTO')
        dirlist1 = os.listdir(ldcpath)
        for dir1 in dirlist1:
            ldcpath1 = os.path.join(ldcpath, dir1)
            if os.path.isdir(ldcpath1):
                dirlist2 = os.listdir(ldcpath1)
                for fname in dirlist2:
                    if '.auto' not in fname:
                        continue
                    ldcpath2 = os.path.join(ldcpath1, fname)
                    if os.path.isfile(ldcpath2):
                        allfiles.append(ldcpath2)

        failed_parse = []
        failed_ccg2drs = []
        for fn in allfiles[0::100]:
            with open(fn, 'r') as fd:
                lines = fd.readlines()
            for hdr,ccgbank in zip(lines[0::20], lines[1::20]):
                if hdr.split(' ')[0] in ['ID=wsj_1099.21']:
                    # These rules have an error in the ccgbank
                    continue
                hdr = hdr.strip()
                dprint(hdr)
                try:
                    pt = parse_ccg_derivation(ccgbank)
                except Exception:
                    failed_parse.append(hdr)
                    continue
                self.assertIsNotNone(pt)
                dprint(sentence_from_pt(pt))
                #d = process_ccg_pt(pt, CO_PRINT_DERIVATION|CO_VERIFY_SIGNATURES)
                try:
                    d = process_ccg_pt(pt, CO_VERIFY_SIGNATURES | CO_NO_VERBNET | CO_NO_WIKI_SEARCH).get_drs()
                    assert d is not None
                    s = d.show(SHOW_LINEAR)
                    dprint(s)
                except Exception as e:
                    raise
                    dprint(e)
                    failed_ccg2drs.append(hdr)
                    continue

        if len(failed_parse) != 0:
            dprint('%d derivations failed to parse' % len(failed_parse))
            for e in failed_parse:
                dprint('  ' + e)

        if len(failed_ccg2drs) != 0:
            dprint('%d derivations failed to convert to DRS' % len(failed_ccg2drs))
            for e in failed_parse:
                dprint('  ' + e)

        self.assertEqual(len(failed_ccg2drs), 0)
        self.assertEqual(len(failed_parse), 0)


