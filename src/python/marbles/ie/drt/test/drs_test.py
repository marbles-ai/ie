# -*- coding: utf-8 -*-

import unittest
import os
from ..drs import *
from ..common import *
from ..parse import parse_drs, parse_ccg_derivation
from ..utils import compare_lists_eq
from ..ccg2drs import DrsComposition, ArgLeft, ArgRight, PropComposition, FunctionComposition, CompositionList
from ..ccg2drs import process_ccg_pt, CcgTypeMapper, CO_REMOVE_UNARY_PROPS, CO_PRINT_DERIVATION
#from pysmt.shortcuts import Solver


# Like NLTK's dexpr()
def dexpr(s):
    return parse_drs(s, 'nltk')


class DrsTest(unittest.TestCase):

    def test0_Empty(self):
        d = DRS([],[])
        s = d.show(SHOW_SET)
        x = u'<{},{}>'
        self.assertEquals(x,s)
        s = d.show(SHOW_BOX)
        x = u'\u250C---\u2510\n|   |\n\u251C---\u2524\n|   |\n|   |\n\u2514---\u2518\n'
        self.assertEquals(x,s)
        s = d.show(SHOW_LINEAR)
        x = u'[| ]'
        self.assertEquals(x,s)
        f, _ = d.to_fol()
        s = f.show(SHOW_SET)
        x = u'\u22A4'
        self.assertEquals(x, s)

    def test1_HappyMan(self):
        # "A man is happy."
        d = DRS([DRSRef('x')],
                    [Rel(DRSRelation('man'),[DRSRef('x')])
                    ,Rel(DRSRelation('happy'),[DRSRef('x')])])
        s = d.show(SHOW_SET)
        x = u'<{x},{man(x),happy(x)}>'
        self.assertEquals(x,s)
        self.assertEquals(parse_drs(x), d)
        s = d.show(SHOW_LINEAR)
        x = u'[x| man(x),happy(x)]'
        self.assertEquals(x,s)
        self.assertFalse(d.islambda)
        self.assertTrue(d.isresolved)
        self.assertFalse(d.ismerge)
        self.assertTrue(d.isproper)
        self.assertTrue(d.ispure)
        self.assertTrue(d.isfol)
        f, _ = d.to_fol()
        s = f.show(SHOW_SET)
        x = u'\u2203x(man(w,x) \u2227 happy(w,x))'
        self.assertEquals(x, s)

    def test2_NotHappyMan(self):
        # "A man is not happy."
        d = DRS([DRSRef('x')],
                    [Rel(DRSRelation('man'),[DRSRef('x')])
                    ,Neg(DRS([],[Rel(DRSRelation('happy'),[DRSRef('x')])]))])
        self.assertEquals(d.conditions[1].drs, d.find_subdrs(DRS([],[Rel(DRSRelation('happy'),[DRSRef('x')])])))
        self.assertEquals(d, d.find_subdrs(DRS([],[Rel(DRSRelation('happy'),[DRSRef('x')])])).global_drs)
        self.assertTrue(compare_lists_eq(d.conditions[1].drs.accessible_universe, [DRSRef('x')]))
        self.assertTrue(compare_lists_eq(d.accessible_universe, [DRSRef('x')]))
        s = d.show(SHOW_SET)
        x = u'<{x},{man(x),\u00AC<{},{happy(x)}>}>'
        self.assertEquals(x,s)
        self.assertEquals(parse_drs('<{x},{man(x),not<{},{happy(x)}>}>'), d)
        s = d.show(SHOW_BOX)
        x = u'''\u250C----------------\u2510
| x              |
\u251C----------------\u2524
| man(x)         |
|   \u250C----------\u2510 |
|   |          | |
| \u00AC \u251C----------\u2524 |
|   | happy(x) | |
|   |          | |
|   |          | |
|   \u2514----------\u2518 |
|                |
|                |
\u2514----------------\u2518
'''
        self.assertEquals(x,s)
        s = d.show(SHOW_LINEAR)
        x = u'[x| man(x),\u00AC[| happy(x)]]'
        self.assertEquals(x,s)
        self.assertFalse(d.islambda)
        self.assertTrue(d.isresolved)
        self.assertFalse(d.ismerge)
        self.assertTrue(d.isproper)
        self.assertTrue(d.ispure)
        self.assertTrue(d.isfol)
        f, _ = d.to_fol()
        s = f.show(SHOW_SET)
        x = u'\u2203x(man(w,x) \u2227 \u00AChappy(w,x))'
        self.assertEquals(x, s)

    def test3_FarmerDonkey(self):
        # "If a farmer owns a donkey, he feeds it."
        d = DRS([],
                [Imp(
                    DRS([DRSRef('x'), DRSRef('y')],
                        [Rel(DRSRelation('farmer'),[DRSRef('x')])
                        ,Rel(DRSRelation('donkey'),[DRSRef('y')])
                        ,Rel(DRSRelation('owns'),[DRSRef('x'), DRSRef('y')])]),
                    DRS([], [Rel(DRSRelation('feeds'), [DRSRef('x'), DRSRef('y')])]))])
        s = d.show(SHOW_SET)
        x = u'<{},{<{x,y},{farmer(x),donkey(y),owns(x,y)}> \u21D2 <{},{feeds(x,y)}>}>'
        self.assertEquals(x,s)
        self.assertEquals(parse_drs('<{},{<{x,y},{farmer(x),donkey(y),owns(x,y)}> -> <{},{feeds(x,y)}>}>'), d)
        s = d.show(SHOW_LINEAR)
        x = u'[| [x,y| farmer(x),donkey(y),owns(x,y)] \u21D2 [| feeds(x,y)]]'
        self.assertEquals(x,s)
        self.assertFalse(d.islambda)
        self.assertTrue(d.isresolved)
        self.assertFalse(d.ismerge)
        self.assertTrue(d.isproper)
        self.assertTrue(d.ispure)
        self.assertTrue(d.isfol)
        f, _ = d.to_fol()
        s = f.show(SHOW_SET)
        x = u'\u2200x\u2200y((farmer(w,x) \u2227 (donkey(w,y) \u2227 owns(w,x,y)))) \u2192 (feeds(w,x,y))'
        self.assertEquals(x, s)

    def test4_ManLoveWoman(self):
        # "A man believes he loves a woman."
        d = DRS([DRSRef('x'), DRSRef('y'), DRSRef('p')],
                [Rel(DRSRelation('man'), [DRSRef('x')])
                ,Rel(DRSRelation('woman'), [DRSRef('y')])
                ,Rel(DRSRelation('believes'), [DRSRef('x'), DRSRef('p')])
                ,Prop(DRSRef('p'),DRS([], [Rel(DRSRelation('loves'),[DRSRef('x'), DRSRef('y')])]))])
        s = d.show(SHOW_SET)
        x = u'<{x,y,p},{man(x),woman(y),believes(x,p),p: <{},{loves(x,y)}>}>'
        self.assertEquals(x,s)
        self.assertEquals(parse_drs('<{x,y,p},{man(x),woman(y),believes(x,p),p: <{},{loves(x,y)}>}>'), d)
        s = d.show(SHOW_LINEAR)
        x = u'[x,y,p| man(x),woman(y),believes(x,p),p: [| loves(x,y)]]'
        self.assertEquals(x,s)
        self.assertFalse(d.islambda)
        self.assertTrue(d.isresolved)
        self.assertFalse(d.ismerge)
        self.assertTrue(d.isproper)
        self.assertTrue(d.ispure)
        self.assertTrue(d.isfol)
        f, _ = d.to_fol()
        s = f.show(SHOW_SET)
        x = u'\u2203x\u2203y\u2203p(man(w,x) \u2227 (woman(w,y) \u2227 (believes(w,x,p) \u2227 (Acc(w,p) \u2227 loves(w,x,y)))))'
        self.assertEquals(x, s)

    def test5_ManHappyNotSad(self):
        # "A man is happy and not sad."
        d = DRS([DRSRef('x')],
                [Rel(DRSRelation('man'),[DRSRef('x')])
                ,Rel(DRSRelation('happy'),[DRSRef('x')])
                ,Neg(DRS([],[Rel(DRSRelation('sad'),[DRSRef('x')])]))])
        s = d.show(SHOW_SET)
        x = u'<{x},{man(x),happy(x),\u00AC<{},{sad(x)}>}>'
        self.assertEquals(x,s)
        self.assertEquals(parse_drs('<{x},{man(x),happy(x),not<{},{sad(x)}>}>'), d)
        s = d.show(SHOW_LINEAR)
        x = u'[x| man(x),happy(x),\u00AC[| sad(x)]]'
        self.assertEquals(x,s)
        self.assertFalse(d.islambda)
        self.assertTrue(d.isresolved)
        self.assertFalse(d.ismerge)
        self.assertTrue(d.isproper)
        self.assertTrue(d.ispure)
        self.assertTrue(d.isfol)

    def test6_MergeHappyNotHappyMan(self):
        # "A man is happy and a man is not happy."
        h = DRS([DRSRef('x')],
                    [Rel(DRSRelation('man'),[DRSRef('x')])
                    ,Rel(DRSRelation('happy'),[DRSRef('x')])])
        nh = DRS([DRSRef('x')],
                    [Rel(DRSRelation('man'),[DRSRef('x')])
                    ,Neg(DRS([],[Rel(DRSRelation('happy'),[DRSRef('x')])]))])
        m = Merge(h, nh)
        s = m.show(SHOW_SET)
        x = u'<{x,x1},{man(x),happy(x),man(x1),\u00AC<{},{happy(x1)}>}>'
        self.assertEquals(x, s)
        p = parse_drs('<{x,x1},{man(x),happy(x),man(x1), !<{},{happy(x1)}>}>')
        s = p.show(SHOW_SET)
        self.assertEquals(x, s)
        s = m.show(SHOW_LINEAR)
        x = u'[x,x1| man(x),happy(x),man(x1),\u00AC[| happy(x1)]]'
        self.assertEquals(x,s)
        d = m.resolve_merges()
        s = d.show(SHOW_LINEAR)
        self.assertEquals(x,s)

    def test7_MergeHappySadMan(self):
        # "A man is not happy."
        d1 = DRS([DRSRef('x')],
                    [Rel(DRSRelation('man'),[DRSRef('x')])
                    ,Neg(DRS([],[Rel(DRSRelation('happy'),[DRSRef('x')])]))])
        d2 = DRS([], [Rel(DRSRelation('sad'), [DRSRef('x')])])
        d = merge(d1, d2)
        s = d.show(SHOW_SET)
        x = u'<{x},{man(x),\u00AC<{},{happy(x)}>,sad(x)}>'
        self.assertEquals(x, s)

    def test8_MergeRecordDate(self):
        # "A record date."
        a = DRS([DRSRef('x')],[])
        record = DRS([DRSRef('y')],[Rel(DRSRelation('record'),[DRSRef('y')]), Rel(DRSRelation('nn'),[DRSRef('y'),DRSRef('x')])])
        date = DRS([],[Rel(DRSRelation('date'), [DRSRef('x')])])
        d1 = merge(record, date)
        d2 = merge(a,d1)
        s = d2.show(SHOW_SET)
        x = u'<{x,y},{record(y),nn(y,x),date(x)}>'
        self.assertEquals(x, s)

    def test9_NLTK0(self):
        # Parse in NLTK format
        n1 = parse_drs('([x], [man(x), walk(x)])', 'nltk')
        n2 = parse_drs('([y], [woman(y), stop(y)])', 'nltk')
        x = parse_drs('([x, y], [man(x), walk(x), woman(y), stop(y)])', 'nltk')
        m = merge(n1, n2)
        self.assertTrue(x == m)

    def test10_NLTKRegressions(self):
        d1 = parse_drs('<{x}, {A(c), <{y},{B(x,y,z,a)}> -> <{z},{C(x,y,z,a)}>}>')
        d = dexpr('([x],[A(c), ([y], [B(x,y,z,a)])->([z],[C(x,y,z,a)])])')
        self.assertEquals(2, len(d.conditions))
        self.assertEquals(d, d1)
        self.assertTrue(d.has_subdrs(d.conditions[1].antecedent))
        self.assertTrue(d.has_subdrs(d.conditions[1].consequent))
        self.assertFalse(d.conditions[1].antecedent.has_subdrs(d.conditions[1].consequent))

        # Unbound referents
        self.assertFalse(DRSRef('a').has_bound(d, d))
        self.assertFalse(DRSRef('a').has_bound(d.conditions[1].antecedent, d))
        self.assertFalse(DRSRef('a').has_bound(d.conditions[1].consequent, d))
        self.assertFalse(DRSRef('y').has_bound(d, d))
        self.assertFalse(DRSRef('y').has_bound(d.conditions[1].consequent, d.conditions[1].consequent))
        self.assertFalse(DRSRef('z').has_bound(d, d))
        self.assertFalse(DRSRef('c').has_bound(d, d))
        self.assertFalse(DRSRef('z').has_bound(d.conditions[1].antecedent, d))

        # Bound referents
        self.assertTrue(DRSRef('x').has_bound(d, d))
        self.assertTrue(DRSRef('y').has_bound(d.conditions[1].antecedent, d))
        self.assertTrue(DRSRef('y').has_bound(d.conditions[1].consequent, d))
        self.assertTrue(DRSRef('y').has_bound(d.conditions[1].consequent, d.conditions[1].antecedent))
        self.assertTrue(DRSRef('z').has_bound(d.conditions[1].consequent, d))
        self.assertTrue(DRSRef('z').has_bound(d.conditions[1].consequent, d.conditions[1].antecedent))

        # Accessibility
        self.assertTrue(compare_lists_eq([DRSRef(x) for x in['x','y']], d.conditions[1].antecedent.accessible_universe))
        self.assertTrue(compare_lists_eq([DRSRef(x) for x in['x','y','z']], d.conditions[1].consequent.accessible_universe))
        self.assertEquals(d, d.conditions[1].antecedent.global_drs)
        self.assertEquals(d, d.conditions[1].consequent.global_drs)

        # Check free variables
        a = d.conditions[1].antecedent.get_freerefs(d.conditions[1].antecedent)
        self.assertTrue(compare_lists_eq(a, [DRSRef(x) for x in['x','z','a']]))
        a = d.conditions[1].antecedent.get_freerefs()
        self.assertTrue(compare_lists_eq(a, [DRSRef(x) for x in['z','a']]))
        a = d.conditions[1].consequent.get_freerefs(d.conditions[1].consequent)
        self.assertTrue(compare_lists_eq(a, [DRSRef(x) for x in['x','y','a']]))
        a = d.conditions[1].consequent.get_freerefs()
        self.assertTrue(compare_lists_eq(a, [DRSRef(x) for x in['a']]))
        a = d.get_freerefs()
        self.assertTrue(compare_lists_eq(a, [DRSRef(x) for x in['c','z','a']]))
        dp = d.purify()
        a = dp.get_freerefs()
        self.assertTrue(compare_lists_eq(a, [DRSRef(x) for x in['c','z','a']]))
        a = dp.get_universes()
        self.assertTrue(compare_lists_eq(a, [DRSRef(x) for x in['x','y','z1']]))

        # Check universe
        self.assertTrue(compare_lists_eq(d.universe, [DRSRef('x')]))
        self.assertTrue(compare_lists_eq(d.conditions[1].antecedent.universe, [DRSRef('y')]))
        self.assertTrue(compare_lists_eq(d.conditions[1].consequent.universe, [DRSRef('z')]))
        self.assertTrue(compare_lists_eq(d.get_universes(), [DRSRef('x'), DRSRef('y'), DRSRef('z')]))
        self.assertTrue(compare_lists_eq(d.get_variables(), [DRSRef('c'), DRSRef('a'), DRSRef('x'), DRSRef('y'), DRSRef('z')]))

        # Cannot convert free variables
        a = d.alpha_convert([(DRSRef('a'), DRSRef('r')), (DRSRef('c'), DRSRef('s')), (DRSRef('z'), DRSRef('t'))])
        self.assertEquals(a, parse_drs('<{x},{A(c),<{y},{B(x,y,z,a)}> -> <{t},{C(x,y,t,a)}>}>'))

        # Can substitute free variables
        a = d.substitute([(DRSRef('a'), DRSRef('r')), (DRSRef('c'), DRSRef('s')), (DRSRef('z'), DRSRef('t'))])
        self.assertEquals(a, parse_drs('<{x},{A(s),<{y},{B(x,y,t,r)}> -> <{z},{C(x,y,z,r)}>}>'))
        a = a.purify()
        self.assertEquals(a, parse_drs('<{x},{A(s),<{y},{B(x,y,t,r)}> -> <{z},{C(x,y,z,r)}>}>'))

        # Can convert bound variables
        a = d.alpha_convert([(DRSRef('x'), DRSRef('x1')), (DRSRef('y'), DRSRef('y1')), (DRSRef('c'), DRSRef('c1'))])
        x = dexpr('([x1],[A(c), (([y1],[B(x1,y1,z,a)]) -> ([z],[C(x1,y1,z,a)]))])')
        self.assertEquals(x, a)
        a = d.alpha_convert((DRSRef('x'), DRSRef('r')))
        x = dexpr('([r],[A(c), (([y],[B(r,y,z,a)]) -> ([z],[C(r,y,z,a)]))])')
        self.assertEquals(x, a)
        a = a.alpha_convert((DRSRef('y'), DRSRef('z1')))
        d = a.purify()
        x = dexpr('([r],[A(c), (([z1],[B(r,z1,z,a)]) -> ([z2],[C(r,z1,z2,a)]))])')
        self.assertEquals(x, d)

    def test11_Compose(self):
        cl = CompositionList()
        # [|exist(x)];[x|school(x)],bus(x)]
        cl.push_right(dexpr('([],[exists(x)])'))
        cl.push_right(dexpr('([],[school(x)])'))
        cl.push_right(dexpr('([x],[bus(x)])'))
        self.assertEquals(0, len(cl.freerefs))
        self.assertTrue(compare_lists_eq([DRSRef('x')], cl.universe))

        cl = CompositionList().push_right(cl)

        fn = FunctionComposition(ArgLeft, DRSRef('x'), FunctionComposition(ArgRight, DRSRef('y'), dexpr('([],[wheeze(x,y)])')))
        self.assertEquals(repr(fn), 'λQλPλxλy.P(x);[| wheeze(x,y)];Q(y)')
        cl.push_right(fn)

        fn = PropComposition(ArgRight, DRSRef('p'))
        self.assertEquals(repr(fn), 'λPλp.[p| p: P(*)]')
        cl.push_right(fn)

        # λP.[x|me(x),own(x,y)];P(y)
        fn = FunctionComposition(ArgRight, DRSRef('y'), dexpr('([x],[me(x),own(x,y)])'))
        self.assertEquals(repr(fn), 'λPλy.[x| me(x),own(x,y)];P(y)')
        cl.push_right(fn)
        cl.push_right(dexpr('([x],[corner(x)])'))

        d = cl.apply()
        d = d.drs.simplify_props()
        s = d.show(SHOW_SET)
        x = u'<{x,y},{exists(x),school(x),bus(x),wheeze(x,y),y: <{x1,y1},{me(x1),own(x1,y1),corner(y1)}>}>'
        self.assertEquals(x, s)

    def test12_Wsj0002_1(self):
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
        #d = process_ccg_pt(pt, CO_PRINT_DERIVATION)
        d = process_ccg_pt(pt)
        self.assertIsNotNone(d)

    def test12_Wsj0001_1(self):
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
        d = process_ccg_pt(pt, CO_PRINT_DERIVATION)
        #d = process_ccg_pt(pt)
        self.assertIsNotNone(d)

    def test13_ParseEasySrl(self):
        # Welcome to MerryWeather High
        txt = '''(<T S[b]\NP 0 2> (<L (S[b]\NP)/PP VB VB Welcome (S[b]\NP)/PP>) (<T PP 0 2> (<L PP/NP TO TO to PP/NP>)
            (<T NP 0 1> (<T N 1 2> (<L N/N NNP NNP Merryweather N/N>) (<L N NNP NNP High. N>) ) ) ) )'''
        pt = parse_ccg_derivation(txt)
        self.assertIsNotNone(pt)
        d = process_ccg_pt(pt)
        self.assertIsNotNone(d)
        s = d.drs.show(SHOW_LINEAR)
        x = u'[x,e,y| event(e),welcome(e),event.agent(e,x),event.theme(e,y),y: [x1| Merryweather-High(x1)]]'
        self.assertEquals(x, s)

        # The door opens and I step up.
        txt = '''(<T S[dcl] 1 2> (<T S[dcl] 1 2> (<T NP 0 2> (<L NP/N DT DT The NP/N>) (<L N NN NN door N>) )
            (<L S[dcl]\NP VBZ VBZ opens S[dcl]\NP>) ) (<T S[dcl]\S[dcl] 1 2> (<L conj CC CC and conj>) (<T S[dcl] 1 2>
            (<L NP PRP PRP I NP>) (<T S[dcl]\NP 0 2> (<L S[dcl]\NP VBP VBP step S[dcl]\NP>)
            (<L (S\NP)\(S\NP) RB RB up. (S\NP)\(S\NP)>) ) ) ) )'''
        pt = parse_ccg_derivation(txt)
        self.assertIsNotNone(pt)
        d = process_ccg_pt(pt)
        self.assertIsNotNone(d)
        d = d.drs.simplify_props()
        s = d.show(SHOW_LINEAR)
        x = u'[x1,e1,x,e| exists(x1),door(x1),event(e1),opens(e1),event.agent(e1,x1),[| i(x)] \u21D2 [| me(x)],event(e),step(e),event.agent(e,x),up(e),direction(e)]'
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
        x = u'[x,e,y| exists(x),school(x),bus(x),event(e),wheezes(e),event.agent(e,x),event.theme(e,y),y: [x1| my(x1),corner(x1)]]'
        self.assertEquals(x, s)

    def test14_ModelCategories(self):
        projdir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))))
        modelpath = os.path.join(projdir, 'ext', 'easysrl', 'model', 'text', 'categories')
        missing = CcgTypeMapper.add_model_categories(modelpath)
        self.assertIsNone(missing)

    def test100_ParseLdc2005T13(self):
        allfiles = []
        projdir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))))
        ldcpath = os.path.join(projdir, 'data', 'ldc', 'ccgbank_1_1', 'data', 'AUTO')
        dirlist1 = os.listdir(ldcpath)
        for dir1 in dirlist1:
            ldcpath1 = os.path.join(ldcpath, dir1)
            if os.path.isdir(ldcpath1):
                dirlist2 = os.listdir(ldcpath1)
                for dir2 in dirlist2:
                    ldcpath2 = os.path.join(ldcpath1, dir2)
                    if os.path.isfile(ldcpath2):
                        allfiles.append(ldcpath2)

        for fn in allfiles:
            with open(fn, 'r') as fd:
                lines = fd.readlines()
            for hdr,ccgbank in zip(lines[0:2:], lines[1:2:]):
                print(hdr.strip())
                pt = parse_ccg_derivation(ccgbank)
                self.assertIsNotNone(pt)
                d = process_ccg_pt(pt, CO_PRINT_DERIVATION)
                #d = process_ccg_pt(pt)
                self.assertIsNotNone(d)
                s = d.drs.show(SHOW_LINEAR)


