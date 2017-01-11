import unittest
from ..pdrs import *
from ..parse import parse_pdrs, parse_drs
from ..drs import DRSRelation
from ..pdrs import *
from ..drs import *


class ParserTest(unittest.TestCase):

    def test0_PDRSHaskellFormat(self):
        s = u"<1,{},{ (1,not <5,{(2,x)},{(2,man(x)),(5,happy(x))}, {(5,2)}>) }, {}>"
        p = parse_pdrs(s)
        self.assertIsNotNone(p)
        x = PDRS(1, [], [],
                    [PCond(1, PNeg(PDRS(5, [MAP(5, 2)], [PRef(2, PDRSRef('x'))],
                        [PCond(2, PRel(DRSRelation('man'),[PDRSRef('x')]))
                        ,PCond(5, PRel(DRSRelation('happy'),[PDRSRef('x')]))])))])
        self.assertEquals(x, p)

    def test1_DRSHaskellFormat(self):
        s = u"<{x},{man(x), not <{},{happy(x)}>}>"
        p = parse_drs(s)
        self.assertIsNotNone(p)
        x = DRS([DRSRef('x')],
                [Rel(DRSRelation('man'),[DRSRef('x')]),
                 Neg(DRS([],[Rel(DRSRelation('happy'),[DRSRef('x')])]))])
        self.assertEquals(x, p)

