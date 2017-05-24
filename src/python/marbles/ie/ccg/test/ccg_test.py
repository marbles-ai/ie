# -*- coding: utf-8 -*-

import os
import unittest

from marbles.ie.ccg import Category, get_rule, CAT_EMPTY, RL_TCL_UNARY, RL_TCR_UNARY, RL_LPASS, RL_RPASS, \
    RL_TC_ATOM, RL_TC_CONJ, RL_TYPE_RAISE, CAT_Sem
from marbles.ie.ccg2drs import Ccg2Drs, PushOp, ExecOp
from marbles.ie.ccg import parse_ccg_derivation2 as parse_ccg_derivation
from marbles.ie.ccg.datapath import DATAPATH


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

        va = Category('(S/A)/(S/A)').extract_unify_atoms(True)
        vx = [[Category('A'), Category('S')], [Category('A')], [Category('S')]]
        self.assertListEqual(va, vx)

    def test4_Cache(self):
        if Category._use_cache:
            for k, v in Category._cache:
                # Use repr() because it includes conj
                self.assertEquals(k, repr(v))
                self.assertEquals(Category._cache[k], v)

    def test5_Cache(self):
        if Category._use_cache:
            cats = [v for k, v in Category.copy_cache()]
            Category.clear_cache()
            Category.initialize_cache(cats)
            for k, v in Category.copy_cache():
                self.assertEquals(k, v.signature)
                self.assertEquals(Category._cache[k], v)
        self.assertTrue(CAT_Sem == Category.from_cache('S[em]'))

    def test6_Wsj0001_2(self):
        txt = '''
(<T S[dcl] 0 2>
  (<T S[dcl] 1 2>
    (<T NP 0 1>
      (<T N 1 2>
        (<L N/N NNP NNP Mr. N_107/N_107>)
        (<L N NNP NNP Vinken N>)
      )
    )
    (<T S[dcl]\NP 0 2>
      (<L (S[dcl]\NP)/NP VBZ VBZ is (S[dcl]\NP_112)/NP_113>)
      (<T NP 0 2>
        (<T NP 0 1>
          (<L N NN NN chairman N>)
        )
        (<T NP\NP 0 2>
          (<L (NP\NP)/NP IN IN of (NP_109\NP_109)/NP_110>)
          (<T NP 0 2>
            (<T NP 0 1>
              (<T N 1 2>
                (<L N/N NNP NNP Elsevier N_107/N_107>)
                (<L N NNP NNP N.V. N>)
              )
            )
            (<T NP[conj] 1 2>
              (<L , , , , ,>)
              (<T NP 1 2>
                (<L NP[nb]/N DT DT the NP[nb]_48/N_48>)
                (<T N 1 2>
                  (<L N/N NNP NNP Dutch N_107/N_107>)
                  (<T N 1 2>
                    (<L N/N VBG VBG publishing N_107/N_107>)
                    (<L N NN NN group N>)
                  )
                )
              )
            )
          )
        )
      )
    )
  )
  (<L . . . . .>)
)'''
        pt = parse_ccg_derivation(txt)
        expected_pt = [
            ['S[dcl]', 0, 2],
            [
                ['S[dcl]', 1, 2],
                [
                    ['NP', 0, 1],
                    [
                        ['N', 1, 2],
                        ['N/N', 'Mr.', 'NNP', 'NNP', 'N_107/N_107', 'L'],
                        ['N', 'Vinken', 'NNP', 'NNP', 'N', 'L'],
                        'T'
                    ],
                    'T'
                ],
                [
                    ['S[dcl]\\NP', 0, 2],
                    ['(S[dcl]\\NP)/NP', 'is', 'VBZ', 'VBZ', '(S[dcl]\\NP_112)/NP_113', 'L'],
                    [
                        ['NP', 0, 2],
                        [
                            ['NP', 0, 1],
                            ['N', 'chairman', 'NN', 'NN', 'N', 'L'],
                            'T'
                        ],
                        [
                            ['NP\\NP', 0, 2],
                            ['(NP\\NP)/NP', 'of', 'IN', 'IN', '(NP_109\\NP_109)/NP_110', 'L'],
                            [
                                ['NP', 0, 2],
                                [
                                    ['NP', 0, 1],
                                    [
                                        ['N', 1, 2],
                                        ['N/N', 'Elsevier', 'NNP', 'NNP', 'N_107/N_107', 'L'],
                                        ['N', 'N.V.', 'NNP', 'NNP', 'N', 'L'],
                                        'T'
                                    ],
                                    'T'
                                ],
                                [
                                    ['NP[conj]', 1, 2],
                                    [',', ',', ',', ',', ',', 'L'],
                                    [
                                        ['NP', 1, 2],
                                        ['NP[nb]/N', 'the', 'DT', 'DT', 'NP[nb]_48/N_48', 'L'],
                                        [
                                            ['N', 1, 2],
                                            ['N/N', 'Dutch', 'NNP', 'NNP', 'N_107/N_107', 'L'],
                                            [
                                                ['N', 1, 2],
                                                ['N/N', 'publishing', 'VBG', 'VBG', 'N_107/N_107', 'L'],
                                                ['N', 'group', 'NN', 'NN', 'N', 'L'],
                                                'T'
                                            ],
                                            'T'
                                        ],
                                        'T'
                                    ],
                                    'T'
                                ],
                                'T'
                            ],
                            'T'
                        ],
                        'T'
                    ],
                    'T'
                ],
                'T'
            ],
            ['.', '.', '.', '.', '.', 'L'],
            'T'
        ]
        # Use strings since it returns a diff on failure
        #self.assertListEqual(expected_pt, pt)
        x = repr(expected_pt)
        a = repr(pt)
        self.assertEquals(x, a)

    def test7_RuleUniquenessLDC(self):
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
            for hdr, ccgbank in zip(lines[0::10], lines[1::10]):
                print(hdr.strip())
                ccg = Ccg2Drs()
                try:
                    pt = parse_ccg_derivation(ccgbank)
                    ccg.build_execution_sequence(pt)
                except Exception:
                    failed_parse += 1
                    continue
                self.assertIsNotNone(pt)

                for op in ccg.exeque:
                    if isinstance(op, PushOp):
                        continue
                    self.assertIsInstance(op, ExecOp)
                    left = op.sub_ops[0].category
                    result = op.category
                    if len(op.sub_ops) == 2:
                        right = op.sub_ops[1].category
                    else:
                        right = CAT_EMPTY

                    exclude = []
                    # Should not have ambiguity
                    rule = get_rule(left, right, result, exclude)
                    limit = 5
                    rstr = ''
                    while rule is not None:
                        rstr += repr(rule)+'|'
                        rule = get_rule(left, right, result, exclude)
                        limit -= 1
                        if limit == 0:
                            rule = get_rule(left, right, result, exclude)
                            break
                    if len(exclude) > 1:
                        ambiguous.append(('%s <- %s <{%s}> %s' % (result, left, rstr, right), exclude))
                    self.assertGreater(limit, 0)

        for x in ambiguous:
            print('ambiguous rule: %s {%s}' % x)
        self.assertTrue(len(ambiguous) == 0)

    def test8_RuleUniquenessEasySRL(self):
        allfiles = []
        projdir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))))
        ldcpath = os.path.join(projdir, 'data', 'ldc', 'easysrl', 'ccgbank')
        dirlist1 = os.listdir(ldcpath)
        for fname in dirlist1:
            if 'ccg_derivation' not in fname:
                continue
            ldcpath1 = os.path.join(ldcpath, fname)
            if os.path.isfile(ldcpath1):
                allfiles.append(ldcpath1)

        failed_parse = 0
        ambiguous = []
        start = 0
        for fn in allfiles:
            with open(fn, 'r') as fd:
                lines = fd.readlines()

            name, _ = os.path.splitext(os.path.basename(fn))
            for i in range(start, len(lines), 50):
                start = 0
                ccgbank = lines[i]
                print('%s-%04d' % (name, i))
                ccg = Ccg2Drs()
                try:
                    pt = parse_ccg_derivation(ccgbank)
                    ccg.build_execution_sequence(pt)
                except Exception:
                    failed_parse += 1
                    continue

                self.assertIsNotNone(pt)
                for op in ccg.exeque:
                    if isinstance(op, PushOp):
                        continue
                    self.assertIsInstance(op, ExecOp)
                    left = op.sub_ops[0].category
                    result = op.category
                    if len(op.sub_ops) == 2:
                        right = op.sub_ops[1].category
                    else:
                        right = CAT_EMPTY
                    exclude = []
                    # Should not have ambiguity
                    rule = get_rule(left, right, result, exclude)
                    if rule is None and right != CAT_EMPTY:
                        rule = get_rule(left.remove_features(), right.remove_features(), result.remove_features(), exclude)
                    self.assertIsNotNone(rule)
                    rstr = ''
                    while rule is not None:
                        rstr += repr(rule)+'|'
                        rule = get_rule(left, right, result, exclude)
                    if len(exclude) > 1:
                        ambiguous.append(('%s <- %s <{%s}> %s' % (result, left, rstr, right), exclude))
        for x in ambiguous:
            print('ambiguous rule in %s-%04d: %s {%s}' % x)
        self.assertTrue(len(ambiguous) == 0)

    def test9_RuleExecutionEasySRL(self):
        allfiles = []
        projdir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))))
        ldcpath = os.path.join(projdir, 'data', 'ldc', 'easysrl', 'ccgbank')
        dirlist1 = os.listdir(ldcpath)
        for fname in dirlist1:
            if 'ccg_derivation' not in fname:
                continue
            ldcpath1 = os.path.join(ldcpath, fname)
            if os.path.isfile(ldcpath1):
                allfiles.append(ldcpath1)

        failed_parse = 0
        failed_exec = []
        start = 0
        for fn in allfiles[0:]:
            with open(fn, 'r') as fd:
                lines = fd.readlines()

            name, _ = os.path.splitext(os.path.basename(fn))
            for i in range(start, len(lines), 50):
                start = 0
                ccgbank = lines[i]
                print('%s-%04d' % (name, i))
                ccg = Ccg2Drs()
                try:
                    pt = parse_ccg_derivation(ccgbank)
                    ccg.build_execution_sequence(pt)
                except Exception:
                    failed_parse += 1
                    continue

                for op in ccg.exeque:
                    if isinstance(op, PushOp):
                        continue
                    self.assertIsInstance(op, ExecOp)
                    left = op.sub_ops[0].category.remove_wildcards()
                    result = op.category.remove_wildcards()
                    if len(op.sub_ops) == 2:
                        right = op.sub_ops[1].category.remove_wildcards()
                    else:
                        right = CAT_EMPTY

                    if op.rule is not None and op.rule not in [RL_TCL_UNARY, RL_TCR_UNARY, RL_TC_ATOM, RL_TC_CONJ, \
                                                               RL_LPASS, RL_RPASS, RL_TYPE_RAISE]:
                        actual = op.rule.apply_rule_to_category(left, right)
                        if not actual.can_unify(result):
                            print('%s <!> %s' % (actual, result))
                            print('%s <- %s %s %s', actual, left, op.rule, right)
                            print(ccgbank)
                        self.assertTrue(actual.can_unify(result))

        if len(failed_exec) != 0:
            print('%d rules failed exec' % len(failed_exec))
            for x in failed_exec:
                print('%s-%04d: failed exec - {%s}' % x)

        self.assertTrue(len(failed_exec) == 0)

    # Test disabled for the moment
    def __test9A_Parser(self):
        filename = os.path.join(DATAPATH, 'parse_ccg_derivation_failed.dat')
        if os.path.exists(filename):
            success = 0
            with open(filename, 'r') as fd:
                failed = fd.readlines()
            for ln, msg in zip(failed[0::2], failed[1::2]):
                ln = ln.replace('CCGBANK:', '').strip()
                try:
                    pt = parse_ccg_derivation(ln)
                    if pt is not None:
                        success += 1
                except Exception:
                    pass
            self.assertEqual(len(failed), success)



