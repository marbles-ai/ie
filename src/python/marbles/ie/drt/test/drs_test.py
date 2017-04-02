# -*- coding: utf-8 -*-

import unittest

from marbles.ie.drt.common import *
from marbles.ie.drt.drs import *
from marbles.ie.drt.utils import compare_lists_eq
from marbles.ie.parse import parse_drs


#from pysmt.shortcuts import Solver


# Like NLTK's dexpr()
def dexpr(s):
    return parse_drs(s, 'nltk')


class DrsTest(unittest.TestCase):

    def test00_Empty(self):
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

    def test01_HappyMan(self):
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

    def test02_NotHappyMan(self):
        # "A man is not happy."
        d = DRS([DRSRef('x')],
                    [Rel(DRSRelation('man'),[DRSRef('x')])
                    ,Neg(DRS([],[Rel(DRSRelation('happy'),[DRSRef('x')])]))])
        self.assertEquals(d.conditions[1].drs, d.find_subdrs(DRS([],[Rel(DRSRelation('happy'),[DRSRef('x')])])))
        self.assertEquals(d, d.find_subdrs(DRS([],[Rel(DRSRelation('happy'),[DRSRef('x')])])).global_drs)
        self.assertListEqual(d.conditions[1].drs.accessible_universe, [DRSRef('x')])
        self.assertListEqual(d.accessible_universe, [DRSRef('x')])
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

    def test03_FarmerDonkey(self):
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

    def test04_ManLoveWoman(self):
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

    def test05_ManHappyNotSad(self):
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

    def test06_MergeHappyNotHappyMan(self):
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

    def test07_MergeHappySadMan(self):
        # "A man is not happy."
        d1 = DRS([DRSRef('x')],
                    [Rel(DRSRelation('man'),[DRSRef('x')])
                    ,Neg(DRS([],[Rel(DRSRelation('happy'),[DRSRef('x')])]))])
        d2 = DRS([], [Rel(DRSRelation('sad'), [DRSRef('x')])])
        d = merge(d1, d2)
        s = d.show(SHOW_SET)
        x = u'<{x},{man(x),\u00AC<{},{happy(x)}>,sad(x)}>'
        self.assertEquals(x, s)

    def test08_MergeRecordDate(self):
        # "A record date."
        a = DRS([DRSRef('x')],[])
        record = DRS([DRSRef('y')],[Rel(DRSRelation('record'),[DRSRef('y')]), Rel(DRSRelation('nn'),[DRSRef('y'),DRSRef('x')])])
        date = DRS([],[Rel(DRSRelation('date'), [DRSRef('x')])])
        d1 = merge(record, date)
        d2 = merge(a,d1)
        s = d2.show(SHOW_SET)
        x = u'<{x,y},{record(y),nn(y,x),date(x)}>'
        self.assertEquals(x, s)

    def test09_NLTK0(self):
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
