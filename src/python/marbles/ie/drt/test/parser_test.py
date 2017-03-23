import unittest
import os
from ..parse import parse_pdrs, parse_drs, parse_ccgtype, parse_ccg_derivation
from ..pdrs import *
from ..drs import *
import pickle


def dirname(filepath, up):
    for u in range(up):
        filepath = os.path.dirname(filepath)
    return filepath


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

    def test2_CCGCategories(self):
        pt = parse_ccgtype('NP')
        self.assertIsNotNone(pt)
        pt = parse_ccgtype('PP')
        self.assertIsNotNone(pt)
        pt = parse_ccgtype('N')
        self.assertIsNotNone(pt)
        pt = parse_ccgtype('S')
        self.assertIsNotNone(pt)
        pt = parse_ccgtype('S[dcl]')
        self.assertIsNotNone(pt)
        pt = parse_ccgtype('N/N')
        self.assertIsNotNone(pt)
        pt = parse_ccgtype(r'(S/NP)\NP')
        self.assertIsNotNone(pt)
        self.assertEqual(3, len(pt))
        pt = parse_ccgtype('((N/(S\NP))\(N/(S\NP)))/NP')
        self.assertIsNotNone(pt)
        self.assertEqual(3, len(pt))

    def test3_CCGCategories(self):
        categories = os.path.join(dirname(__file__, 7), 'ext', 'easysrl', 'model', 'text', 'categories')
        with open(categories, 'r') as fd:
            lines = fd.readlines()
            for ln in lines:
                ln = ln.strip()
                if len(ln) == 0:
                    continue
                pt = parse_ccgtype(ln)
                self.assertIsNotNone(pt)
                self.assertLessEqual(len(pt), 3)

    def test4_Parser(self):
        filename = os.path.join(os.path.dirname(__file__), 'parse_ccg_derivation_failed.dat')
        if os.path.exists(filename):
            success = 0
            with open(filename, 'r') as fd:
                failed = pickle.load(fd)
            for ln, msg in failed:
                try:
                    pt = parse_ccg_derivation(ln)
                    if pt is not None:
                        success += 1
                except Exception:
                    pass
            self.assertEqual(len(failed), success)


