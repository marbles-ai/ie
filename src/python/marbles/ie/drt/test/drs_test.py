# -*- coding: utf-8 -*-

import unittest
import os
from ..drs import *
from ..common import *
from ..parse import parse_drs, parse_ccg_derivation
from ..utils import compare_lists_eq
from ..compose import DrsProduction, ArgRight, PropProduction, FunctorProduction, ProductionList
from ..compose import CO_REMOVE_UNARY_PROPS, CO_VERIFY_SIGNATURES, CO_PRINT_DERIVATION
from ..ccg2drs import process_ccg_pt, sentence_from_pt, CcgTypeMapper
from ..ccgcat import Category
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
        cl = ProductionList()
        # [|exist(x)];[x|school(x)],bus(x)]
        cl.push_right(dexpr('([],[exists(x)])'))
        cl.push_right(dexpr('([],[school(x)])'))
        cl.push_right(dexpr('([x],[bus(x)])'))
        self.assertEquals(0, len(cl.freerefs))
        self.assertTrue(compare_lists_eq([DRSRef('x')], cl.universe))

        cl = ProductionList().push_right(cl)

        fn = FunctorProduction(Category(r'S\NP'), DRSRef('x'), FunctorProduction(Category(r'(S\NP)/NP'), DRSRef('y'),
                                                                                      dexpr('([],[wheeze(x,y)])')))
        self.assertEquals(repr(fn), 'λQλPλxλy.P(x);[| wheeze(x,y)];Q(y)')
        cl.push_right(fn)

        fn = PropProduction(Category(r'NP/PP'), DRSRef('p'))
        self.assertEquals(repr(fn), 'λPλp.[p| p: P(*)]')
        cl.push_right(fn)

        # λP.[x|me(x),own(x,y)];P(y)
        cl2 = ProductionList()
        fn = FunctorProduction(Category(r'NP/N'), DRSRef('y'), dexpr('([x],[me(x),own(x,y)])'))
        self.assertEquals(repr(fn), 'λPλy.[x| me(x),own(x,y)];P(y)')
        cl2.push_right(fn)
        cl2.push_right(dexpr('([x],[corner(x)])'))
        cl.push_right(cl2.apply_forward().unify())

        d = cl.apply_reverse()
        d = d.unify()
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
        d = process_ccg_pt(pt, CO_VERIFY_SIGNATURES)
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
        d = process_ccg_pt(pt, CO_VERIFY_SIGNATURES)
        self.assertIsNotNone(d)
        d = d.unify()
        self.assertIsNotNone(d)
        self.assertIsInstance(d, DrsProduction)

    def test12_Wsj0003_1(self):
        # A form of asbestos once used to make Kent cigarette filters has caused a high percentage of cancer deaths among a group of workers exposed to it more than 30 years ago, researchers reported.
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
        # λx4λe1.P(x4);[| has(e1)];[e1| caused(e1), event.agent(x4), event.theme(p4)];[p4| p4:[p3,p2| p3:[x3,y1| a(x3), exists.maybe(x3), high(x3), percentage(x3), of(x3,y1) cancer(y1), deaths(y1)], among(p3,p2), p2:[p2: [x1,p| a(x1), exists.maybe(x1), group(x1), of(x1,p) p:[e,x,y,z| workers(x), event(e), event.agent(x), event.theme(z), to(z), z:[x2| it(x2)], more(e), than(e,y), 30(y), years(y), ago(e)]]]]
        #           (<T S[dcl]\NP 0 2>
        # λP'λxλe.[| has(e)];P'(x,e)
        #               (<L (S[dcl]\NP)/(S[pt]\NP) VBZ VBZ has (S[dcl]\NP_23)/(S[pt]_24\NP_23:B)_24>)
        # λPλx4λe1.P(x4);[e1| caused(e1), event.agent(x4), event.theme(p4)];[p4| p4:[p3,p2| p3:[x3,y1| a(x3), exists.maybe(x3), high(x3), percentage(x3), of(x3,y1) cancer(y1), deaths(y1)], among(p3,p2), p2:[p2: [x1,p| a(x1), exists.maybe(x1), group(x1), of(x1,p) p:[e,x,y,z| workers(x), event(e), event.agent(x), event.theme(z), to(z), z:[x2| it(x2)], more(e), than(e,y), 30(y), years(y), ago(e)]]]]
        #               (<T S[pt]\NP 0 2>
        # λQλPλxλyλe.P(x);[e| caused(e), event.agent(x), event.theme(y)];Q(y)
        #                   (<L (S[pt]\NP)/NP VBN VBN caused (S[pt]\NP_31)/NP_32>)
        # [p3| p3:[x3,y1| a(x3), exists.maybe(x3), high(x3), percentage(x3), of(x3,y1) cancer(y1), deaths(y1)]];[p2| among(p3,p2), p2:[p2: [x1,p| a(x1), exists.maybe(x1), group(x1), of(x1,p) p:[e,x,y,z| workers(x), event(e), event.agent(x), event.theme(z), to(z), z:[x2| it(x2)], more(e), than(e,y), 30(y), years(y), ago(e)]]]
        #                       (<T NP 0 2>
        # [x| a(x), exists.maybe(x), high(x), percentage(x)];[y| of(x,y) cancer(y), deaths(y)]
        #                           (<T NP 0 2>
        # λx.[| a(x), exists.maybe(x)];[| high(x)];[x| percentage(x)]
        #                               (<T NP 1 2>
        # λPλx.[| a(x), exists.maybe(x)];P(x)
        #                                   (<L NP[nb]/N DT DT a NP[nb]_46/N_46>)
        # [| high(x)];[x| percentage(x)]
        #                                   (<T N 1 2>
        # λPλx.[| high(x)];P(x)
        #                                       (<L N/N JJ JJ high N_41/N_41>)
        # [x| percentage(x)]
        #                                       (<L N NN NN percentage N>)
        #                                   )
        #                               )
        # λPλx.P(x);[| of(x,y)];[y| cancer(y), deaths(y)]
        #                               (<T NP\NP 0 2>
        # λQλPλxλy.P(x);[| of(x,y)];Q(y)
        #                                   (<L (NP\NP)/NP IN IN of (NP_54\NP_54)/NP_55>)
        # [x| cancer(x), deaths(x)]
        #                                   (<T NP 0 1>
        # [| cancer(x)];[x| deaths(x)]
        #                                       (<T N 1 2>
        # λPλx.[| cancer(x)];P(x)
        #                                           (<L N/N NN NN cancer N_64/N_64>)
        # [x| deaths]
        #                                           (<L N NNS NNS deaths N>)
        #                                       )
        #                                   )
        #                               )
        #                           )
        # λPλx.P(x);[| among(x,p2)];[p2| p2:[p2: [x1,p| a(x1), exists.maybe(x1), group(x1), of(x1,p) p:[e,x,y,z| workers(x), event(e), event.agent(x), event.theme(z), to(z), z:[x2| it(x2)], more(e), than(e,y), 30(y), years(y), ago(e)]]]
        #                           (<T NP\NP 0 2>
        # λQλPλxλy.P(x);[| among(x,y)];Q(y)
        #                               (<L (NP\NP)/NP IN IN among (NP_73\NP_73)/NP_74>)
        # [x1,p| a(x1), exists.maybe(x1), group(x1), of(x1,p) p:[e,x,y,z| workers(x), event(e), event.agent(x), event.theme(z), to(z), z:[x2| it(x2)], more(e), than(e,y), 30(y), years(y), ago(e)]]
        #                               (<T NP 0 2>
        # [x| a(x), exists.maybe(x)];[| group(x)]
        #                                   (<T NP 1 2>
        # λPλx.[| a(x), exists.maybe(x)];P(x)
        #                                       (<L NP[nb]/N DT DT a NP[nb]_81/N_81>)
        # [x| group(x)]
        #                                       (<L N NN NN group N>)
        #                                   )
        # λPλx1.P(x1);[| of(x1,p)];[p| p:[e,x,y,z| workers(x), event(e), event.agent(x), event.theme(z), to(z), z:[x2| it(x2)], more(e), than(e,y), 30(y), years(y), ago(e)]]
        #                                   (<T NP\NP 0 2>
        # λQλPλxλy.P(x);[| of(x,y)];Q(y)
        #                                       (<L (NP\NP)/NP IN IN of (NP_89\NP_89)/NP_90>)
        # [e,x,y,z| workers(x), event(e), event.agent(x), event.theme(z), to(z), z:[x2| it(x2)], more(e), than(e,y), 30(y), years(y), ago(e)]
        #                                       (<T NP 0 2>
        # [x| workers(x)];[e,y,z| event(e), event.agent(x), event.theme(z), to(z), z:[x2| it(x2)], more(e), than(e,y), 30(y), years(y), ago(e)]
        #                                           (<T NP 0 1>
        # [x| workers(x)]
        #                                               (<L N NNS NNS workers N>)
        #                                           )
        # λPλx.P(x);[e,y,z| event(e), event.agent(x), event.theme(z), to(z), z:[x2| it(x2)], more(e), than(e,y), 30(y), years(y), ago(e)]
        #                                           (<T NP\NP 0 1>
        # λP(λR)λxλe.P(x);R(e);[e| event(e), event.agent(x1), event.theme(z)];[z| to(z), z:[x2| it(x2)]];[y| more(e), than(e,y), 30(y), years(y), ago(e)]
        #                                               (<T S[pss]\NP 0 2>
        # λPλxλe.P(x);[e| event(e), event.agent(x), event.theme(y)];[y| to(y), y:[x| it(x)]]
        #                                                   (<T S[pss]\NP 0 2>
        # λQλPλxλyλe.P(x);[e| event(e), event.agent(x), event.theme(y)];Q(y)
        #                                                       (<L (S[pss]\NP)/PP VBN VBN exposed (S[pss]\NP_100)/PP_101>)
        # λp.[p| to(p), p:[x| it(x)]]
        #                                                       (<T PP 0 2>
        # λPλp.[p| to(p), p:P(*)]
        #                                                           (<L PP/NP TO TO to PP/NP_106>)
        # [x| it(x)]
        #                                                           (<L NP PRP PRP it NP>)
        #                                                       )
        #                                                   )
        # λP'λxλe.P'(x,e);[y| more(e), than(e,y), 30(y), years(y), ago(e)]
        #                                                   (<T (S\NP)\(S\NP) 1 2>
        # λP'λxλe.P'(x,e);(λRλe.R(e);[| more(e)];[y| than(e,y), 30(y), years(y)];[| ago(e)])
        #                                                       (<T NP 0 1>
        # λx.(λRλx.R(x);[| more(x)]);[| than(x,y)];[| 30(y), isnumber(y)];[y| years(y)])
        #                                                           (<T N 1 2>
        # λPλyλx.(λRλx.R(x);[| more(x)];[| than(x,y)];[| 30(y), isnumber(y)]);P(y)
        #                                                               (<T N/N 1 2>
        # λP'λyλx.(λRλx.R(x);[| more(x)]);[| than(x,y)]);P'(y)
        #                                                                   (<T (N/N)/(N/N) 1 2>
        # λRλx.R(x);[| more(x)]
        #                                                                       (<L S[adj]\NP RBR RBR more S[adj]\NP_153>)
        # λQ'λP'λxλy.Q'(x);[| than(x,y)];P'(y)
        #                                                                       (<L ((N/N)/(N/N))\(S[adj]\NP) IN IN than ((N_147/N_139)_147/(N_147/N_139)_147)\(S[adj]_148\NP_142)_148>)
        #                                                                   )
        # λPλx.[| 30(x), isnumber(x)];P(x)
        #                                                                   (<L N/N CD CD 30 N_131/N_131>)
        #                                                               )
        # [x| years(x)]
        #                                                               (<L N NNS NNS years N>)
        #                                                           )
        #                                                       )
        # λQλP'λxλe.P'(x,e);Q(e);[| ago(e)]
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
        # λQ'λPλxλe.Q'(e);P(x)
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

    def test12_Wsj0004_1(self):
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

    def test12_Wsj0004_1_EasySRL(self):
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
        d = process_ccg_pt(pt, CO_PRINT_DERIVATION|CO_VERIFY_SIGNATURES)
        #d = process_ccg_pt(pt, CO_VERIFY_SIGNATURES)
        self.assertIsNotNone(d)
        d = d.unify()
        self.assertIsNotNone(d)
        self.assertIsInstance(d, DrsProduction)
        print('\n')
        print(d.drs.show(SHOW_LINEAR))

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

    def __test14_ModelCategories(self):
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
                #d = process_ccg_pt(pt, CO_PRINT_DERIVATION|CO_VERIFY_SIGNATURES)
                print(sentence_from_pt(pt))
                d = process_ccg_pt(pt)
                self.assertIsNotNone(d)
                d = d.unify()
                self.assertIsNotNone(d)
                self.assertIsInstance(d, DrsProduction)
                s = d.drs.show(SHOW_LINEAR)
                print(s)


