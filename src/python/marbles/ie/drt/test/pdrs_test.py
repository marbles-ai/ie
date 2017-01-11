import unittest
from ..pdrs import *
from ..common import *
from ..drs import DRSRelation
from ..parse import parse_pdrs


class PDrsTest(unittest.TestCase):

    def test0_Empty(self):
        d = PDRS(1, [], [], [])
        s = d.show(SHOW_SET)
        x = u'<1,{},{},{}>'
        self.assertEquals(x, s)
        s = d.show(SHOW_BOX)
        x = u'\u250C--1--\u2510\n|     |\n\u251C-----\u2524\n|     |\n|     |\n\u251C-----\u2524\n|     |\n|     |\n\u2514-----\u2518\n'
        self.assertEquals(x, s)
        s = d.show(SHOW_LINEAR)
        x = u'1:[||]'
        self.assertEquals(x, s)
        f = d.to_fol()
        s = f.show(SHOW_SET)
        x = u'\u22A4'
        self.assertEquals(x, s)

    def test1_HappyMan(self):
        # "A man is happy."
        d = PDRS(1, [], [PRef(1, PDRSRef('x'))],
                    [PCond(1, PRel(DRSRelation('man'),[PDRSRef('x')]))
                    ,PCond(1, PRel(DRSRelation('happy'),[PDRSRef('x')]))])
        s = d.show(SHOW_SET)
        x = u'<1,{x},{(1,man(x)),(1,happy(x))},{}>'
        self.assertEquals(x,s)
        s = d.show(SHOW_LINEAR)
        x = u'1:[x|(1,man(x)),(1,happy(x))|]'
        self.assertEquals(x,s)
        self.assertFalse(d.islambda)
        self.assertTrue(d.isresolved)
        self.assertFalse(d.ismerge)
        self.assertTrue(d.isproper)
        self.assertTrue(d.ispure)
        self.assertTrue(d.isfol)
        f = d.to_fol()
        s = f.show(SHOW_SET)
        x = u'\u2203x(happy(w,x) \u2227 man(w,x))'
        self.assertEquals(x, s)

    def test2_NLTKRegressions(self):
        d = parse_pdrs('<1,{(1,x)},{(1,A(c)),(2,<2,{(2,y)},{(2,B(x,y,z,a))},{}> -> <3,{(3,z)},{(3,C(x,yd,z,a))},{}>)},{}>')
        self.assertEquals(2, len(d.conditions))
        self.assertTrue(d.has_subdrs(d.conditions[1].cond.antecedent))
        self.assertTrue(d.has_subdrs(d.conditions[1].cond.consequent))
        self.assertFalse(d.conditions[1].cond.antecedent.has_subdrs(d.conditions[1].cond.consequent))

        # Unbound referents
        self.assertFalse(PRef(1,PDRSRef('a')).has_bound(d, d))
        self.assertFalse(PRef(1,PDRSRef('a')).has_bound(d.conditions[1].cond.antecedent, d))
        self.assertFalse(PRef(1,PDRSRef('a')).has_bound(d.conditions[1].cond.consequent, d))
        self.assertFalse(PRef(1,PDRSRef('y')).has_bound(d, d))
        self.assertFalse(PRef(1,PDRSRef('y')).has_bound(d.conditions[1].cond.consequent, d.conditions[1].cond.consequent))
        self.assertFalse(PRef(1,PDRSRef('z')).has_bound(d, d))
        self.assertFalse(PRef(1,PDRSRef('c')).has_bound(d, d))
        self.assertFalse(PRef(1,PDRSRef('z')).has_bound(d.conditions[1].cond.antecedent, d))

        # Bound referents
        self.assertTrue(PRef(1,PDRSRef('x')).has_bound(d, d))
        self.assertTrue(PRef(1,PDRSRef('y')).has_bound(d.conditions[1].cond.antecedent, d))
        self.assertTrue(PRef(1,PDRSRef('y')).has_bound(d.conditions[1].cond.consequent, d))
        self.assertTrue(PRef(1,PDRSRef('y')).has_bound(d.conditions[1].cond.consequent, d.conditions[1].cond.antecedent))
        self.assertTrue(PRef(1,PDRSRef('z')).has_bound(d.conditions[1].cond.consequent, d))
        self.assertTrue(PRef(1,PDRSRef('z')).has_bound(d.conditions[1].cond.consequent, d.conditions[1].cond.antecedent))

        # Accessibility
        self.assertTrue(compare_lists_eq([PDRSRef(x) for x in['x','y']], d.conditions[1].cond.antecedent.accessible_universe))
        self.assertTrue(compare_lists_eq([PDRSRef(x) for x in['x','y','z']], d.conditions[1].cond.consequent.accessible_universe))
        self.assertEquals(d, d.conditions[1].cond.antecedent.global_drs)
        self.assertEquals(d, d.conditions[1].cond.consequent.global_drs)

        # Check free variables
        a = d.conditions[1].cond.antecedent.get_freerefs(d.conditions[1].cond.antecedent)
        self.assertTrue(compare_lists_eq(a, [PDRSRef(x) for x in['x','z','a']]))
        a = d.conditions[1].cond.antecedent.get_freerefs()
        self.assertTrue(compare_lists_eq(a, [PDRSRef(x) for x in['z','a']]))
        a = d.conditions[1].cond.consequent.get_freerefs(d.conditions[1].cond.consequent)
        self.assertTrue(compare_lists_eq(a, [PDRSRef(x) for x in['x','y','a']]))
        a = d.conditions[1].cond.consequent.get_freerefs()
        self.assertTrue(compare_lists_eq(a, [PDRSRef(x) for x in['a']]))
        a = d.get_freerefs()
        self.assertTrue(compare_lists_eq(a, [PDRSRef(x) for x in['c','z','a']]))
        dp = d.purify()
        a = dp.get_freerefs()
        self.assertTrue(compare_lists_eq(a, [PDRSRef(x) for x in['c','z','a']]))
        a = dp.get_universes()
        self.assertTrue(compare_lists_eq(a, [PDRSRef(x) for x in['x','y','z1']]))

        # Check universe
        self.assertTrue(compare_lists_eq(d.universe, [PDRSRef('x')]))
        self.assertTrue(compare_lists_eq(d.conditions[1].cond.antecedent.universe, [PDRSRef('y')]))
        self.assertTrue(compare_lists_eq(d.conditions[1].cond.consequent.universe, [PDRSRef('z')]))
        self.assertTrue(compare_lists_eq(d.get_universes(), [PDRSRef('x'), PDRSRef('y'), PDRSRef('z')]))
        self.assertTrue(compare_lists_eq(d.get_variables(), [PDRSRef('c'), PDRSRef('a'), PDRSRef('x'), PDRSRef('y'), PDRSRef('z')]))

        # Cannot convert free variables
        a = d.alpha_convert([(PDRSRef('a'), PDRSRef('r')), (PDRSRef('c'), PDRSRef('s')), (PDRSRef('z'), PDRSRef('t'))])
        self.assertEquals(a, parse_pdrs('<1,{},{(1,x)},{(1,A(c)),(1,<1,{},{(1,y)},{(1,B(x,y,z,a))}> -> <1,{},{(1,t)},{(1,C(x,y,t,a))}>)}>'))

        '''
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
        '''


    def test2_HappyMan(self):
        d = PDRS(1, [MAP(2, -1)], [PRef(2, PDRSRef('x'))],
                    [PCond(2, PRel(DRSRelation('man'),[PDRSRef('x')]))
                    ,PCond(1, PRel(DRSRelation('happy'),[PDRSRef('x')]))])

    def test3_MergeHappyMan(self):
        man = PDRS(1, [],
                   [PRef(1, PDRSRef('x'))],
                   [PCond(1, PRel(DRSRelation('man'),[PDRSRef('x')]))])
        happy = PDRS(1,[],[],
                     [PCond(1, PRel(DRSRelation('happy'), [PDRSRef('x')]))])
        # "A man is happy"
        d = amerge(man, happy)
        x = PDRS(1, [], [PRef(1, PDRSRef('x'))],
                    [PCond(1, PRel(DRSRelation('man'),[PDRSRef('x')]))
                    ,PCond(1, PRel(DRSRelation('happy'),[PDRSRef('x')]))])
        ds = d.show(SHOW_SET)
        xs = x.show(SHOW_SET)
        self.assertEqual(x ,d)
        # "The man is happy"
        d = pmerge(man, happy)
        x = PDRS(1, [(1,2)], [PRef(2, PDRSRef('x'))],
                    [PCond(2, PRel(DRSRelation('man'),[PDRSRef('x')]))
                    ,PCond(1, PRel(DRSRelation('happy'),[PDRSRef('x')]))])
        ds = d.show(SHOW_SET)
        xs = x.show(SHOW_SET)


    def test2_ManSmiles(self):
        # "A man smiles."
        # "The man smiles"
        # "It is not the case that the man smiles."
        pass

    def test1_LanceArmstrong(self):
        # "It is not true that Lance Armstrong, a former cyclist, is a Tour-winner."
        pass


