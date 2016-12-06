import unittest
from ..drs import *
from ..common import *


class DrsTest(unittest.TestCase):

    def test0_Empty(self):
        d = DRS([],[])
        s = d.show(SHOW_SET)
        x = u'<{},{}>'
        self.assertEquals(x,s)
        s = d.show(SHOW_BOX)
        x = u'\u250C---\u2510\n|   |\n\u251C---\u2524\n|   |\n|   |\n\u2514---\u2518\n'
        self.assertEquals(x,s)

    def test1_HappyMan(self):
        # "A man is happy."
        d = DRS([DRSRef('x')],
                    [Rel(DRSRelation('man'),[DRSRef('x')])
                    ,Rel(DRSRelation('happy'),[DRSRef('x')])])
        s = d.show(SHOW_SET)
        x = u'<{x},{man(x),happy(x)}>'
        self.assertEquals(x,s)
        self.assertFalse(d.islambda)
        self.assertTrue(d.isresolved)
        self.assertFalse(d.ismerge)
        self.assertTrue(d.isproper)
        self.assertTrue(d.ispure)
        self.assertTrue(d.isfol)

    def test2_NotHappyMan(self):
        # "A man is not happy."
        d = DRS([DRSRef('x')],
                    [Rel(DRSRelation('man'),[DRSRef('x')])
                    ,Neg(DRS([],[Rel(DRSRelation('happy'),[DRSRef('x')])]))])
        s = d.show(SHOW_SET)
        x = u'<{x},{man(x),\u00AC<{},{happy(x)}>}>'
        self.assertEquals(x,s)
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
        self.assertFalse(d.islambda)
        self.assertTrue(d.isresolved)
        self.assertFalse(d.ismerge)
        self.assertTrue(d.isproper)
        self.assertTrue(d.ispure)
        self.assertTrue(d.isfol)

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
        self.assertFalse(d.islambda)
        self.assertTrue(d.isresolved)
        self.assertFalse(d.ismerge)
        self.assertTrue(d.isproper)
        self.assertTrue(d.ispure)
        self.assertTrue(d.isfol)

    def test4_ManLoveWoman(self):
        # "A man believes he loves a woman."
        d = DRS([DRSRef('x'), DRSRef('y'), DRSRef('p')],
                [Rel(DRSRelation('man'), [DRSRef('x')])
                ,Rel(DRSRelation('woman'), [DRSRef('y')])
                ,Rel(DRSRelation('believes'), [DRSRef('x'), DRSRef('y')])
                ,Prop(DRSRef('p'),DRS([], [Rel(DRSRelation('loves'),[DRSRef('x'), DRSRef('y')])]))])
        s = d.show(SHOW_SET)
        x = u'<{x,y,p},{man(x),woman(y),believes(x,y),p: <{},{loves(x,y)}>}>'
        self.assertEquals(x,s)
        self.assertFalse(d.islambda)
        self.assertTrue(d.isresolved)
        self.assertFalse(d.ismerge)
        self.assertTrue(d.isproper)
        self.assertTrue(d.ispure)
        self.assertTrue(d.isfol)

    def test5_ManHappyNotSad(self):
        # "A man is happy and not sad."
        d = DRS([DRSRef('x')],
                [Rel(DRSRelation('man'),[DRSRef('x')])
                ,Rel(DRSRelation('happy'),[DRSRef('x')])
                ,Neg(DRS([],[Rel(DRSRelation('sad'),[DRSRef('x')])]))])
        s = d.show(SHOW_SET)
        x = u'<{x},{man(x),happy(x),\u00AC<{},{sad(x)}>}>'
        self.assertEquals(x,s)
        self.assertFalse(d.islambda)
        self.assertTrue(d.isresolved)
        self.assertFalse(d.ismerge)
        self.assertTrue(d.isproper)
        self.assertTrue(d.ispure)
        self.assertTrue(d.isfol)

    def test6_Merge1(self):
        # "A man is happy and a man is not happy."
        h = DRS([DRSRef('x')],
                    [Rel(DRSRelation('man'),[DRSRef('x')])
                    ,Rel(DRSRelation('happy'),[DRSRef('x')])])
        nh = DRS([DRSRef('x')],
                    [Rel(DRSRelation('man'),[DRSRef('x')])
                    ,Neg(DRS([],[Rel(DRSRelation('happy'),[DRSRef('x')])]))])
        d = Merge(h, nh).resolve_merges()
        s = d.show(SHOW_SET)
        x = u'<{x},{man(x),happy(x) \u00AC<{},{happy(x)}>}>'
        self.assertEquals(x,s)
