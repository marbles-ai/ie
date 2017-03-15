# -*- coding: utf-8 -*-

import unittest
from ..ccg2drs import CcgTypeMapper
from ..ccgcat import Category
from ..utils import compare_lists_eq


class CcgTest(unittest.TestCase):

    def test1_Category(self):
        cat = Category('(S/NP)/(S/NP)')
        self.assertTrue(cat.isfunctor)
        self.assertTrue(cat.ismodifier)
        self.assertFalse(cat.isatom)

        cat = Category('(S[b]/NP)/(S/NP)')
        self.assertTrue(cat.isfunctor)
        self.assertFalse(cat.ismodifier)
        self.assertFalse(cat.isatom)

        cat = Category()
        self.assertFalse(cat.isfunctor)
        self.assertFalse(cat.ismodifier)
        self.assertFalse(cat.isatom)

    def test2_Unify(self):
        self.assertTrue(Category('N').can_unify(Category('N')))
        self.assertTrue(Category('S').can_unify(Category('S')))
        self.assertTrue(Category('S[adj]').can_unify(Category('S')))
        self.assertTrue(Category('S').can_unify(Category('S[adj]')))
        self.assertTrue(Category('NP').can_unify(Category('N')))
        self.assertTrue(Category('N').can_unify(Category('NP')))
        self.assertFalse(Category('S[adj]').can_unify(Category('S[dcl]')))
        self.assertFalse(Category('S[adj]').can_unify(Category('S[em]')))
        self.assertFalse(Category('S[dcl]').can_unify(Category('S[adj]')))
        self.assertFalse(Category('S[em]').can_unify(Category('S[adj]')))

    def test3_CategoryToVars(self):
        va = Category('N/N').extract_atoms()
        vx = [Category('N')]
        self.assertListEqual(va, vx)

        va = Category(r'N\N').extract_atoms()
        vx = [Category('N')]
        self.assertListEqual(va, vx)

        va = Category('NP/NP').extract_atoms()
        vx = [Category('NP')]
        self.assertListEqual(va, vx)

        va = Category(r'NP\NP').extract_atoms()
        vx = [Category('NP')]
        self.assertListEqual(va, vx)

        va = Category(r'S\A').extract_atoms()
        vx = [Category('A'), Category('S')]
        self.assertListEqual(va, vx)

        va = Category(r'(S\A)/B').extract_atoms()
        vx = [Category('A'), Category('B'), Category('S')]
        self.assertListEqual(va, vx)

        va = Category(r'(A\A)\(B/B)').extract_atoms()
        vx = [Category('B'), Category('A')]
        self.assertListEqual(va, vx)

        va = Category(r'(A/A)\(B/B)').extract_atoms()
        vx = [Category('B'), Category('A')]
        self.assertListEqual(va, vx)

        va = Category('(S/A)/(S/A)').extract_atoms()
        vx = [Category('A'), Category('S')]
        self.assertListEqual(va, vx)



