# -*- coding: utf-8 -*-

import os
import unittest

from marbles.ie.ccg.ccg2drs import process_ccg_pt, sentence_from_pt
from marbles.ie.ccg.ccgcat import Category
from marbles.ie.drt.compose import CO_VERIFY_SIGNATURES
from marbles.ie.drt.compose import DrsProduction, PropProduction, FunctorProduction, ProductionList
from marbles.ie.drt.drs import *
from marbles.ie.drt.utils import compare_lists_eq
from marbles.ie.parse import parse_drs, parse_ccg_derivation


# Like NLTK's dexpr()
def dexpr(s):
    return parse_drs(s, 'nltk')


class ComposeTest(unittest.TestCase):
    
    def test1_Compose(self):
        cl1 = ProductionList()
        # [|exist(x)];[x|school(x)],bus(x)]
        cl1.push_right(DrsProduction(drs=dexpr('([],[exists(x)])'), category=Category('NP')))
        cl1.push_right(DrsProduction(drs=dexpr('([],[school(x)])'), category=Category('NP')))
        cl1.push_right(DrsProduction(drs=dexpr('([x],[bus(x)])'), category=Category('NP')))
        self.assertEquals(0, len(cl1.freerefs))
        self.assertTrue(compare_lists_eq([DRSRef('x')], cl1.universe))
        cl1.set_category(Category('NP'))

        cl = ProductionList()
        fn = FunctorProduction(Category(r'S\NP'), DRSRef('x'), FunctorProduction(Category(r'(S\NP)/NP'), DRSRef('y'),
                                                                                 dexpr('([],[wheeze(x,y)])')))
        self.assertEquals('λQλPλxλy.(P(x);[| wheeze(x,y)];Q(y))', repr(fn))
        cl.push_right(fn)

        # λP.[x|me(x),own(x,y)];P(y)
        cl2 = ProductionList()
        fn = FunctorProduction(Category(r'NP/N'), DRSRef('y'), dexpr('([x],[me(x),own(x,y)])'))
        self.assertEquals('λPλy.([x| me(x),own(x,y)];P(y))', repr(fn))
        cl2.push_right(fn)
        cl2.push_right(DrsProduction(drs=dexpr('([x],[corner(x)])'), category=Category('N')))
        cl.push_right(cl2.apply_forward().unify())

        fn = PropProduction(Category(r'PP\NP'), DRSRef('p'))
        self.assertEquals('λPλp.([p| p: P(*)])', repr(fn))
        cl.push_right(fn)

        cl.apply_backward()
        cl.apply_forward()
        cl.push_left(cl1.unify())
        cl.apply_backward()

        d = cl.unify()
        d = d.drs.simplify_props()
        s = d.show(SHOW_SET)
        x = u'<{x2,y1},{exists(x2),school(x2),bus(x2),wheeze(x2,y1),y1: <{x1,y},{me(x1),own(x1,y),corner(y)}>}>'
        self.assertEquals(x, s)

    def test2_Wsj0002_1(self):
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
        txt = '''(<T S[dcl] 0 2> (<T S[dcl] 1 2> (<T NP 0 2> (<T NP 0 2> (<T NP 0 2> (<T NP 0 1> (<T N 1 2>
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
        d = process_ccg_pt(pt, CO_VERIFY_SIGNATURES)
        self.assertIsNotNone(d)
        print(d.drs.show(SHOW_LINEAR))

    def test2_Wsj0001_1(self):
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
        txt = '''(<T S[dcl] 0 2> (<T S[dcl] 1 2> (<T NP 0 2> (<T NP 0 2> (<T NP 0 2> (<T NP 0 1> (<T N 1 2>
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
        d = process_ccg_pt(pt, CO_VERIFY_SIGNATURES)
        self.assertIsNotNone(d)
        d = d.unify()
        self.assertIsNotNone(d)
        self.assertIsInstance(d, DrsProduction)
        print(d.drs.show(SHOW_LINEAR))

    def test2_Wsj0001_2(self):
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
        txt = '''
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
        self.assertIsNotNone(pt)
        d = process_ccg_pt(pt, CO_VERIFY_SIGNATURES)
        self.assertIsNotNone(d)
        d = d.unify()
        self.assertIsNotNone(d)
        self.assertIsInstance(d, DrsProduction)
        print(d.drs.show(SHOW_LINEAR))

    def test2_Wsj0003_1(self):
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
        txt = '''(<T S[dcl] 0 2> (<T S[dcl] 1 2> (<T S[dcl] 1 2> (<T NP 0 2> (<T NP 0 2> (<T NP 1 2>
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
        self.assertIsNotNone(pt)
        #d = process_ccg_pt(pt, CO_PRINT_DERIVATION|CO_VERIFY_SIGNATURES)
        d = process_ccg_pt(pt, CO_VERIFY_SIGNATURES)
        self.assertIsNotNone(d)
        d = d.unify()
        self.assertIsNotNone(d)
        self.assertIsInstance(d, DrsProduction)
        print('\n')
        print(d.drs.show(SHOW_LINEAR))
        pass

    def test2_Wsj0004_1(self):
        # Yields on money-market mutual funds continued to slide, amid signs that portfolio managers expect further
        # declines in interest rates.
        '''
        [x,e,y| x: [x3,y3| yields(x3),on(x3,y3),money-market(y3),mutual(y3),funds(y3)],event.attribute.continued(e,x),
        event.attribute.to(e,x),event(e),event.verb.slide(e),event.agent(e,x),amid(y),event.related(e,y),signs(y),
        event.related(y), y: [x2,e1,y2| portfolio(x2),managers(x2),event(e1),event.verb.expect(e1),event.agent(e1,x2),
        event.theme(e1,y2),y2: [x1,y1| further(x1),declines(x1),in(x1,y1),interest(y1),rates(y1)]]]        '''
        txt='''(<T S[dcl] 0 2> (<T S[dcl] 1 2> (<T NP 0 2> (<T NP 0 1> (<L N NNS NNS Yields N>) ) (<T NP\NP 0 2>
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
        #d = process_ccg_pt(pt, CO_PRINT_DERIVATION|CO_VERIFY_SIGNATURES)
        d = process_ccg_pt(pt, CO_VERIFY_SIGNATURES)
        self.assertIsNotNone(d)
        d = d.unify()
        self.assertIsNotNone(d)
        self.assertIsInstance(d, DrsProduction)
        print('\n')
        print(d.drs.show(SHOW_LINEAR))

    def test2_Wsj0004_1_EasySRL(self):
        # Same sentence as test12_Wsj0004_1() but parse tree generated by EasySRL rather than LDC.
        txt= '''(<T S[dcl] 1 2> (<T NP 0 1> (<T N 0 2> (<L N/PP NNS NNS Yields N/PP>) (<T PP 0 2>
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
        #d = process_ccg_pt(pt, CO_PRINT_DERIVATION|CO_VERIFY_SIGNATURES)
        d = process_ccg_pt(pt, CO_VERIFY_SIGNATURES)
        self.assertIsNotNone(d)
        d = d.unify()
        self.assertIsNotNone(d)
        self.assertIsInstance(d, DrsProduction)
        print('\n')
        print(d.drs.show(SHOW_LINEAR))

    def test2_Wsj0012_1(self):
        txt = '''
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
        #d = process_ccg_pt(pt, CO_PRINT_DERIVATION|CO_VERIFY_SIGNATURES)
        d = process_ccg_pt(pt, CO_VERIFY_SIGNATURES)
        self.assertIsNotNone(d)
        d = d.unify()
        self.assertIsNotNone(d)
        self.assertIsInstance(d, DrsProduction)
        print('\n')
        print(d.drs.show(SHOW_LINEAR))

    def test3_ParseEasySrl(self):
        # Welcome to MerryWeather High
        txt = '''(<T S[b]\NP 0 2> (<L (S[b]\NP)/PP VB VB Welcome (S[b]\NP)/PP>) (<T PP 0 2> (<L PP/NP TO TO to PP/NP>)
            (<T NP 0 1> (<T N 1 2> (<L N/N NNP NNP Merryweather N/N>) (<L N NNP NNP High. N>) ) ) ) )'''
        pt = parse_ccg_derivation(txt)
        self.assertIsNotNone(pt)
        d = process_ccg_pt(pt)
        self.assertIsNotNone(d)
        s = d.drs.show(SHOW_LINEAR)
        x = u'[x2,e1,Merryweather-High| .EVENT(e1),welcome(e1),.AGENT(e1,x2),.THEME(e1,Merryweather-High),to(Merryweather-High)]'
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
        txt = '''(<T S[dcl] 1 2> (<T S[dcl] 1 2> (<T NP 0 2> (<L NP/N DT DT The NP/N>) (<L N NN NN door N>) )
            (<L S[dcl]\NP VBZ VBZ opens S[dcl]\NP>) ) (<T S[dcl]\S[dcl] 1 2> (<L conj CC CC and conj>) (<T S[dcl] 1 2>
            (<L NP PRP PRP I NP>) (<T S[dcl]\NP 0 2> (<L S[dcl]\NP VBP VBP step S[dcl]\NP>)
            (<L (S\NP)\(S\NP) RB RB up. (S\NP)\(S\NP)>) ) ) ) )'''
        pt = parse_ccg_derivation(txt)
        self.assertIsNotNone(pt)
        d = process_ccg_pt(pt, CO_VERIFY_SIGNATURES)
        self.assertIsNotNone(d)
        d = d.drs.simplify_props()
        s = d.show(SHOW_LINEAR)
        x = u'[x1,e2,e3,x4| .EXISTS(x1),door(x1),.EVENT(e2),opens(e2),.AGENT(e2,x1),[| i(x4)] \u21D2 [| me(x4)],.EVENT(e3),step(e3),.AGENT(e3,x4),up(e3),direction(e3)]'
        self.assertEquals(x, s)

        # The school bus wheezes to my corner.
        txt = '''(<T S[dcl] 1 2> (<T NP 0 2> (<L NP/N DT DT The NP/N>) (<T N 1 2> (<L N/N NN NN school N/N>)
            (<L N NN NN bus N>) ) ) (<T S[dcl]\NP 0 2> (<L (S[dcl]\NP)/PP VBZ VBZ wheezes (S[dcl]\NP)/PP>)
            (<T PP 0 2> (<L PP/NP TO TO to PP/NP>) (<T NP 0 2> (<L NP/N PRP$ PRP$ my NP/N>)
            (<L N NN NN corner. N>) ) ) ) )'''
        pt = parse_ccg_derivation(txt)
        self.assertIsNotNone(pt)
        d = process_ccg_pt(pt)
        self.assertIsNotNone(d)
        s = d.drs.show(SHOW_LINEAR)
        x = u'[x3,e1,x2| .EXISTS(x3),school(x3),bus(x3),.EVENT(e1),wheezes(e1),.AGENT(e1,x3),.THEME(e1,x2),to(x2),my(x2),corner(x2)]'
        self.assertEquals(x, s)


    def test4_Asbestos(self):
        txt='''(<T S[dcl] 1 2> (<T S[dcl] 1 2> (<T NP 0 2> (<L NP/N DT DT A NP/N>) (<T N 0 2> (<L N/PP NN NN form N/PP>)
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
        d = process_ccg_pt(pt, CO_VERIFY_SIGNATURES)
        self.assertIsNotNone(d)

    def test5_PrepositionOf(self):
        #txt = '''(<T NP 0 2> (<T NP 0 1> (<T N 1 2> (<L N/N NNP NNP J.P. N/N>) (<L N NNP NNP Bolduc N>) ) ) (<T NP\NP 1 2> (<L , , , , ,>) (<T NP 0 1> (<T N 1 2> (<L N/N NN NN vice N/N>) (<T N 0 2> (<L N/PP NN NN chairman N/PP>) (<T PP 0 2> (<T PP 0 2> (<L PP/NP IN IN of PP/NP>) (<T NP 0 2> (<T NP 0 1> (<T N 1 2> (<T N/N 1 2> (<L (N/N)/(N/N) NNP NNP W.R. (N/N)/(N/N)>) (<L N/N NNP NNP Grace N/N>) ) (<T N 1 2> (<L N/N CC CC & N/N>) (<T N 0 2> (<L N NNP NNP Co. N>) (<L , , , , ,>) ) ) ) ) (<T NP\NP 0 2> (<L (NP\NP)/(S[dcl]\NP) WDT WDT which (NP\NP)/(S[dcl]\NP)>) (<T S[dcl]\NP 0 2> (<T S[dcl]\NP 0 2> (<L (S[dcl]\NP)/NP VBZ VBZ holds (S[dcl]\NP)/NP>) (<T NP 0 2> (<L NP/N DT DT a NP/N>) (<T N 1 2> (<T N/N 1 2> (<L (N/N)/(N/N) CD CD 83.4 (N/N)/(N/N)>) (<L N/N NN NN % N/N>) ) (<T N 0 2> (<L N/PP NN NN interest N/PP>) (<T PP 0 2> (<L PP/NP IN IN in PP/NP>) (<T NP 0 2> (<L NP/N DT DT this NP/N>) (<T N 1 2> (<L N/N JJ JJ energy-services N/N>) (<L N NN NN company N>) ) ) ) ) ) ) ) (<T (S[dcl]\NP)\(S[dcl]\NP) 1 2> (<L , , , , ,>) (<T S[dcl]\NP 0 2> (<L (S[dcl]\NP)/(S[pss]\NP) VBD VBD was (S[dcl]\NP)/(S[pss]\NP)>) (<T S[pss]\NP 0 2> (<L (S[pss]\NP)/NP VBN VBN elected (S[pss]\NP)/NP>) (<T NP 0 2> (<L NP/N DT DT a NP/N>) (<L N NN NN director N>) ) ) ) ) ) ) ) ) (<L . . . . .>) ) ) ) ) ) ) '''
        txt = '''
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
        d = process_ccg_pt(pt, CO_VERIFY_SIGNATURES)
        self.assertIsNotNone(d)

    def test6_ParseEasySRL2005T13(self):
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
        projdir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))))
        ldcpath = os.path.join(projdir, 'data', 'ldc', 'easysrl', 'ccgbank')
        dirlist1 = os.listdir(ldcpath)
        for fname in dirlist1:
            if 'ccg_derivation' not in fname:
                continue
            ldcpath1 = os.path.join(ldcpath, fname)
            if os.path.isfile(ldcpath1):
                allfiles.append(ldcpath1)

        failed_parse = 0
        failed_ccg2drs = []
        start = 50
        for fn in allfiles[0:]:
            with open(fn, 'r') as fd:
                lines = fd.readlines()

            name, _ = os.path.splitext(os.path.basename(fn))
            for i in range(start, len(lines), 100):
                start = 50
                ccgbank = lines[i]
                print('%s-%04d' % (name, i))
                try:
                    pt = parse_ccg_derivation(ccgbank)
                except Exception:
                    failed_parse += 1
                    continue
                self.assertIsNotNone(pt)
                print(sentence_from_pt(pt))
                #d = process_ccg_pt(pt, CO_PRINT_DERIVATION|CO_VERIFY_SIGNATURES)
                try:
                    d = process_ccg_pt(pt, CO_VERIFY_SIGNATURES)
                    assert d is not None
                    d = d.unify()
                    assert d is not None
                    assert isinstance(d, DrsProduction)
                    s = d.drs.show(SHOW_LINEAR).encode('utf-8')
                    print(s)
                except Exception as e:
                    print(e)
                    failed_ccg2drs.append((name, i, ccgbank))
                    continue

        if failed_parse != 0:
            print('%d derivations failed to parse' % failed_parse)
        if len(failed_ccg2drs) != 0:
            print('%d derivations failed to convert to DRS' % len(failed_ccg2drs))
            for x in failed_ccg2drs:
                print('%s-%04d failed: {%s}' % x)

        self.assertEqual(len(failed_ccg2drs), 0)
        self.assertEqual(failed_parse, 0)

    def test6_ParseLdc2005T13(self):
        # Mar-2017 PWG
        #
        # LDC2005T13 is a conversion of the Penn Treebank into CCG derivations.
        # This was done with a algorithm that required support for special CCG
        # type changing rules. It is my understanding that these rules are never
        # required in derivations from a CCG parser, so while I implemented
        # some, I did not implement them all, hence some tests are expected to fail.
        allfiles = []
        projdir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))))
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

        failed_parse = 0
        failed_ccg2drs = 0
        for fn in allfiles[0::100]:
            with open(fn, 'r') as fd:
                lines = fd.readlines()
            for hdr,ccgbank in zip(lines[0::10], lines[1::10]):
                print(hdr.strip())
                try:
                    pt = parse_ccg_derivation(ccgbank)
                except Exception:
                    failed_parse += 1
                    continue
                self.assertIsNotNone(pt)
                print(sentence_from_pt(pt))
                #d = process_ccg_pt(pt, CO_PRINT_DERIVATION|CO_VERIFY_SIGNATURES)
                try:
                    d = process_ccg_pt(pt, CO_VERIFY_SIGNATURES)
                    assert d is not None
                    d = d.unify()
                    assert d is not None
                    assert isinstance(d, DrsProduction)
                    s = d.drs.show(SHOW_LINEAR).encode('utf-8')
                    print(s)
                except Exception as e:
                    raise
                    print(e)
                    failed_ccg2drs += 1
                    continue

        print('%d derivations failed to parse' % failed_parse)
        print('%d derivations failed to convert to DRS' % failed_ccg2drs)

        self.assertEqual(failed_parse, 0)
        self.assertEqual(failed_ccg2drs, 0)


