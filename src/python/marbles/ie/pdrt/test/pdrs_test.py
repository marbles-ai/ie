import unittest
from ..pdrs import *
from ..common import *
from ..drs import DRSRelation


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

    def test2_HappyMan(self):
        d = PDRS(1, [MAP(2, -1)], [PRef(2, PDRSRef('x'))],
                    [PCond(2, PRel(DRSRelation('man'),[PDRSRef('x')]))
                    ,PCond(1, PRel(DRSRelation('happy'),[PDRSRef('x')]))])


    def test2_ManSmiles(self):
        # "A man smiles."
        # "The man smiles"
        # "It is not the case that the man smiles."
        pass

    def test1_LanceArmstrong(self):
        # "It is not true that Lance Armstrong, a former cyclist, is a Tour-winner."
        pass


