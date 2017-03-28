# -*- coding: utf-8 -*-

import os
import unittest

from marbles.ie.ccg.ccgcat import Category, get_rule
from marbles.ie.drt.parse import parse_ccg_derivation


def rule_unique_helper(pt, lst):
    if pt[-1] == 'T':
        result = Category(pt[0][0])
        cats = [result]
        for nd in pt[1:-1]:
            c = rule_unique_helper(nd, lst)
            cats.append(c)
        lst.append(cats)
        return result
    else:
        # Leaf nodes contains six fields:
        # <L CCGcat mod_POS-tag orig_POS-tag word PredArgCat>
        return Category(pt[0])


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
        va = Category('S/NP').extract_unify_atoms()
        vx = [[Category('NP')], [Category('S')]]
        self.assertListEqual(va, vx)

        va = Category(r'S\NP').extract_unify_atoms()
        vx = [[Category('NP')], [Category('S')]]
        self.assertListEqual(va, vx)

        va = Category(r'(S\A)/B').extract_unify_atoms()
        vx = [[Category('B')], [Category('A')], [Category('S')]]
        self.assertListEqual(va, vx)

        va = Category(r'(A\B)\(C/D)').extract_unify_atoms()
        vx = [[Category('D'), Category('C')], [Category('B')], [Category('A')]]
        self.assertListEqual(va, vx)

        va = Category(r'(A/B)\(C/D)').extract_unify_atoms()
        vx = [[Category('D'), Category('C')], [Category('B')], [Category('A')]]
        self.assertListEqual(va, vx)

        va = Category('(S/A)/(S/A)').extract_unify_atoms()
        vx = [[Category('A'), Category('S')], [Category('A')], [Category('S')]]
        self.assertListEqual(va, vx)

        va = Category(r'S\NP').extract_unify_atoms(False)
        vx = [Category('NP'), Category('S')]
        self.assertListEqual(va, vx)

        va = Category(r'(S\A)/B').extract_unify_atoms(False)
        vx = [Category('B'), Category('A'), Category('S')]
        self.assertListEqual(va, vx)

        va = Category(r'(A\B)\(C/D)').extract_unify_atoms(False)
        vx = [Category('D'), Category('C'), Category('B'), Category('A')]
        self.assertListEqual(va, vx)

        va = Category(r'(A/B)\(C/D)').extract_unify_atoms(False)
        vx = [Category('D'), Category('C'), Category('B'), Category('A')]
        self.assertListEqual(va, vx)

        va = Category('(S/A)/(S/A)').extract_unify_atoms()
        vx = [Category('A'), Category('S'), Category('A'), Category('S')]
        self.assertListEqual(va, vx)

    def test4_RuleUniqueness(self):
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

        failed_parse = 0
        ambiguous = []
        for fn in allfiles:
            with open(fn, 'r') as fd:
                lines = fd.readlines()
            for hdr, ccgbank in zip(lines[0:2:], lines[1:2:]):
                print(hdr.strip())
                try:
                    pt = parse_ccg_derivation(ccgbank)
                except Exception:
                    failed_parse += 1
                    continue
                self.assertIsNotNone(pt)

                nodes = []
                rule_unique_helper(pt, nodes)
                for cats in nodes:
                    if len(cats) != 3:
                        continue
                    result = cats[0]
                    left = cats[1]
                    right = cats[2]
                    exclude = []
                    # Should not have ambiguity
                    rule = get_rule(left, right, result, exclude)
                    while rule is not None:
                        rule = get_rule(left, right, result, exclude)
                    if len(exclude) > 1:
                        ambiguous.append((cats, exclude))
        for x in ambiguous:
            print('ambiguous rule: %s {%s}' % x)
        self.assertTrue(len(ambiguous) == 0)



