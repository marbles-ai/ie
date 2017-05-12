# -*- coding: utf-8 -*-

import os
import unittest

from marbles.ie.ccg.ccgcat import Category, get_rule, CAT_EMPTY, RL_TCL_UNARY, RL_TCR_UNARY, RL_LPASS, RL_RPASS, \
    RL_TC_ATOM, RL_TC_CONJ, RL_TYPE_RAISE, CAT_Sem
from marbles.ie.ccg.ccg2drs import Ccg2Drs, PushOp, ExecOp, pt_to_utf8
from marbles.ie.ccg.ccg2drs import parse_ccg_derivation2 as parse_ccg_derivation
from marbles.ie.parse import parse_ccg_derivation as parse_ccg_derivation_old


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
        ccg = Ccg2Drs()
        ccg.build_execution_sequence(pt)
        # Check execution queue
        actual = [repr(x) for x in ccg.exeque]
        expected = [
            '<PushOp>:(Mr, N/N, NNP)',
            '<PushOp>:(Vinken, N, NNP)',
            '<ExecOp>:(2, FA N)',
            '<ExecOp>:(1, LP NP)',
            '<PushOp>:(be, (S[dcl]\NP)/NP, VBZ)',
            '<PushOp>:(chairman, N, NN)',
            '<ExecOp>:(1, LP NP)',
            '<PushOp>:(of, (NP\NP)/NP, IN)',
            '<PushOp>:(Elsevier, N/N, NNP)',
            '<PushOp>:(N.V, N, NNP)',
            '<ExecOp>:(2, FA N)',
            '<ExecOp>:(1, LP NP)',
            '<PushOp>:(,, ,, ,)',
            '<PushOp>:(the, NP[nb]/N, DT)',
            '<PushOp>:(Dutch, N/N, NNP)',
            '<PushOp>:(publish, N/N, VBG)',
            '<PushOp>:(group, N, NN)',
            '<ExecOp>:(2, FA N)',
            '<ExecOp>:(2, FA N)',
            '<ExecOp>:(2, FA NP)',
            '<ExecOp>:(2, RP NP[conj])',
            '<ExecOp>:(2, RCONJ NP)',
            '<ExecOp>:(2, FA NP\NP)',
            '<ExecOp>:(2, BA NP)',
            '<ExecOp>:(2, FA S[dcl]\NP)',
            '<ExecOp>:(2, BA S[dcl])',
            '<PushOp>:(., ., .)',
            '<ExecOp>:(2, LP S[dcl])',
        ]
        self.assertListEqual(expected, actual)
        # Check ccgbank generation
        txt2 = '\n' + ccg.get_predarg_ccgbank(pretty=True)
        self.assertEquals(txt, txt2)
        # Check lexicon
        expected = [
            'Mr.',      'Vinken',       'is',
            'chairman', 'of',           'Elsevier',
            'N.V.',     ',',            'the',
            'Dutch',    'publishing',   'group',        '.'
        ]
        actual = [x.word for x in ccg.lexque]
        self.assertListEqual(expected, actual)
        # Check dependencies
        self.assertEquals(ccg.lexque[0].head, 1)    # Mr. -> Vinken
        self.assertEquals(ccg.lexque[1].head, 2)    # Vinken -> is
        self.assertEquals(ccg.lexque[2].head, 2)    # root
        self.assertEquals(ccg.lexque[3].head, 2)    # chairman -> is
        self.assertEquals(ccg.lexque[4].head, 3)    # of -> chairman
        self.assertEquals(ccg.lexque[5].head, 6)    # Elsevier -> N.V.
        self.assertEquals(ccg.lexque[6].head, 4)    # N.V. -> of
        self.assertEquals(ccg.lexque[8].head, 11)   # the -> group
        self.assertEquals(ccg.lexque[9].head, 11)   # Dutch -> group
        self.assertEquals(ccg.lexque[10].head, 11)  # publishing -> group
        self.assertEquals(ccg.lexque[11].head, 6)   # group -> N.V

    def test6_Wsj0037_37(self):
        txt = '''
(<T S[dcl] 0 2>
  (<T S[dcl] 1 2>
    (<T NP 0 2>
      (<T NP 0 1>
        (<T N 1 2>
          (<T N/N 0 2>
            (<L N/N JJR JJR More N_134/N_134>)
            (<T N/N[conj] 1 2>
              (<L conj CC CC and conj>)
              (<L N/N JJR JJR more N_141/N_141>)
            )
          )
          (<L N NNS NNS corners N>)
        )
      )
      (<T NP\NP 0 2>
        (<L (NP\NP)/NP IN IN of (NP_152\NP_152)/NP_153>)
        (<T NP 1 2>
          (<L NP[nb]/N DT DT the NP[nb]_160/N_160>)
          (<L N NN NN globe N>)
        )
      )
    )
    (<T S[dcl]\NP 0 2>
      (<L (S[dcl]\NP)/(S[ng]\NP) VBP VBP are (S[dcl]\NP_91)/(S[ng]_92\NP_91:B)_92>)
      (<T S[ng]\NP 0 2>
        (<L (S[ng]\NP)/(S[adj]\NP) VBG VBG becoming (S[ng]\NP_101)/(S[adj]_102\NP_101:B)_102>)
        (<T S[adj]\NP 0 2>
          (<L (S[adj]\NP)/PP JJ JJ free (S[adj]\NP_109)/PP_110>)
          (<T PP 0 2>
            (<L PP/NP IN IN of PP/NP_115>)
            (<T NP 0 1>
              (<T N 1 2>
                (<L N/N NN NN tobacco N_124/N_124>)
                (<L N NN NN smoke N>)
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
        ccg = Ccg2Drs()
        ccg.build_execution_sequence(pt)
        # Check execution queue
        actual = [repr(x) for x in ccg.exeque]
        expected = [
            '<PushOp>:(more, N/N, JJR)',
            '<PushOp>:(and, conj, CC)',
            '<PushOp>:(more, N/N, JJR)',
            '<ExecOp>:(2, RP N/N[conj])',
            '<ExecOp>:(2, RCONJ N/N)',
            '<PushOp>:(corners, N, NNS)',
            '<ExecOp>:(2, FA N)',
            '<ExecOp>:(1, LP NP)',
            '<PushOp>:(of, (NP\\NP)/NP, IN)',
            '<PushOp>:(the, NP[nb]/N, DT)',
            '<PushOp>:(globe, N, NN)',
            '<ExecOp>:(2, FA NP)',
            '<ExecOp>:(2, FA NP\\NP)',
            '<ExecOp>:(2, BA NP)',
            '<PushOp>:(be, (S[dcl]\\NP)/(S[ng]\\NP), VBP)',
            '<PushOp>:(become, (S[ng]\\NP)/(S[adj]\\NP), VBG)',
            '<PushOp>:(free, (S[adj]\\NP)/PP, JJ)',
            '<PushOp>:(of, PP/NP, IN)',
            '<PushOp>:(tobacco, N/N, NN)',
            '<PushOp>:(smoke, N, NN)',
            '<ExecOp>:(2, FA N)',
            '<ExecOp>:(1, LP NP)',
            '<ExecOp>:(2, FA PP)',
            '<ExecOp>:(2, FA S[adj]\\NP)',
            '<ExecOp>:(2, FA S[ng]\\NP)',
            '<ExecOp>:(2, FA S[dcl]\\NP)',
            '<ExecOp>:(2, BA S[dcl])',
            '<PushOp>:(., ., .)',
            '<ExecOp>:(2, LP S[dcl])',
        ]
        self.assertListEqual(expected, actual)
        # Check lexicon
        expected = [
            'More',     'and',      'more',     'corners',      'of',
            'the',      'globe',    'are',      'becoming',     'free',
            'of',       'tobacco',  'smoke',    '.'
        ]
        actual = [x.word for x in ccg.lexque]
        self.assertListEqual(expected, actual)
        # Check dependencies
        self.assertEquals(ccg.lexque[0].head, 3)    # More -> corners
        self.assertEquals(ccg.lexque[2].head, 0)    # more -> More
        self.assertEquals(ccg.lexque[3].head, 7)    # corners -> are
        self.assertEquals(ccg.lexque[4].head, 3)    # of -> corners
        self.assertEquals(ccg.lexque[5].head, 6)    # the -> globe
        self.assertEquals(ccg.lexque[6].head, 4)    # globe -> of
        self.assertEquals(ccg.lexque[7].head, 7)    # root
        self.assertEquals(ccg.lexque[8].head, 7)    # becoming -> are
        self.assertEquals(ccg.lexque[9].head, 8)    # free -> becoming
        self.assertEquals(ccg.lexque[10].head, 9)   # of -> free
        self.assertEquals(ccg.lexque[11].head, 12)  # tobacco -> smoke
        self.assertEquals(ccg.lexque[12].head, 10)  # smoke -> of

    def test6_Wsj0002_1(self):
        # Rudolph Agnew, 55 years old and former chairman of Consolidated Gold Fields PLC, was named a nonexecutive
        # director of this British industrial conglomerate.
        txt = '''
(<T S[dcl] 0 2>
  (<T S[dcl] 1 2>
    (<T NP 0 2>
      (<T NP 0 2>
        (<T NP 0 2>
          (<T NP 0 1>
            (<T N 1 2>
              (<L N/N NNP NNP Rudolph N_72/N_72>)
              (<L N NNP NNP Agnew N>)
            )
          )
          (<L , , , , ,>)
        )
        (<T NP\NP 0 1>
          (<T S[adj]\NP 0 2>
            (<T S[adj]\NP 1 2>
              (<T NP 0 1>
                (<T N 1 2>
                  (<L N/N CD CD 55 N_92/N_92>)
                  (<L N NNS NNS years N>)
                )
              )
              (<L (S[adj]\NP)\NP JJ JJ old (S[adj]\NP_82)\NP_83>)
            )
            (<T S[adj]\NP[conj] 1 2>
              (<L conj CC CC and conj>)
              (<T NP 0 2>
                (<T NP 0 1>
                  (<T N 1 2>
                    (<L N/N JJ JJ former N_102/N_102>)
                    (<L N NN NN chairman N>)
                  )
                )
                (<T NP\NP 0 2>
                  (<L (NP\NP)/NP IN IN of (NP_111\NP_111)/NP_112>)
                  (<T NP 0 1>
                    (<T N 1 2>
                      (<L N/N NNP NNP Consolidated N_135/N_135>)
                      (<T N 1 2>
                        (<L N/N NNP NNP Gold N_128/N_128>)
                        (<T N 1 2>
                          (<L N/N NNP NNP Fields N_121/N_121>)
                          (<L N NNP NNP PLC N>)
                        )
                      )
                    )
                  )
                )
              )
            )
          )
        )
      )
      (<L , , , , ,>)
    )
    (<T S[dcl]\NP 0 2>
      (<L (S[dcl]\NP)/(S[pss]\NP) VBD VBD was (S[dcl]\NP_10)/(S[pss]_11\NP_10:B)_11>)
      (<T S[pss]\NP 0 2>
        (<L (S[pss]\NP)/NP VBN VBN named (S[pss]\NP_18)/NP_19>)
          (<T NP 0 2> (<T NP 1 2>
            (<L NP[nb]/N DT DT a NP[nb]_33/N_33>)
            (<T N 1 2>
              (<L N/N JJ JJ nonexecutive N_28/N_28>)
              (<L N NN NN director N>)
            )
          )
          (<T NP\NP 0 2>
            (<L (NP\NP)/NP IN IN of (NP_41\NP_41)/NP_42>)
            (<T NP 1 2>
              (<L NP[nb]/N DT DT this NP[nb]_63/N_63>)
              (<T N 1 2>
                (<L N/N JJ JJ British N_58/N_58>)
                (<T N 1 2>
                  (<L N/N JJ JJ industrial N_51/N_51>)
                  (<L N NN NN conglomerate N>)
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
        pt_old = pt_to_utf8(parse_ccg_derivation_old(txt), True)
        actual = repr(pt)
        expected = repr(pt_old)
        self.assertEquals(expected, actual)
        ccg = Ccg2Drs()
        ccg.build_execution_sequence(pt)
        # Check execution queue
        actual = [repr(x) for x in ccg.exeque]
        expected = [
            '<PushOp>:(Rudolph, N/N, NNP)',
            '<PushOp>:(Agnew, N, NNP)',
            '<ExecOp>:(2, FA N)',
            '<ExecOp>:(1, LP NP)',
            '<PushOp>:(,, ,, ,)',
            '<ExecOp>:(2, LP NP)',
            '<PushOp>:(55, N/N, CD)',
            '<PushOp>:(years, N, NNS)',
            '<ExecOp>:(2, FA N)',
            '<ExecOp>:(1, LP NP)',
            '<PushOp>:(old, (S[adj]\NP)\NP, JJ)',
            '<ExecOp>:(2, BA S[adj]\NP)',
            '<PushOp>:(and, conj, CC)',
            '<PushOp>:(former, N/N, JJ)',
            '<PushOp>:(chairman, N, NN)',
            '<ExecOp>:(2, FA N)',
            '<ExecOp>:(1, LP NP)',
            '<PushOp>:(of, (NP\NP)/NP, IN)',
            '<PushOp>:(Consolidated, N/N, NNP)',
            '<PushOp>:(Gold, N/N, NNP)',
            '<PushOp>:(Fields, N/N, NNP)',
            '<PushOp>:(PLC, N, NNP)',
            '<ExecOp>:(2, FA N)',
            '<ExecOp>:(2, FA N)',
            '<ExecOp>:(2, FA N)',
            '<ExecOp>:(1, LP NP)',
            '<ExecOp>:(2, FA NP\NP)',
            '<ExecOp>:(2, BA NP)',
            '<ExecOp>:(2, CONJ_TC S[adj]\NP[conj])',
            '<ExecOp>:(2, RCONJ S[adj]\NP)',
            '<ExecOp>:(1, L_UNARY_TC NP\NP)',
            '<ExecOp>:(2, BA NP)',
            '<PushOp>:(,, ,, ,)',
            '<ExecOp>:(2, LP NP)',
            '<PushOp>:(be, (S[dcl]\NP)/(S[pss]\NP), VBD)',
            '<PushOp>:(name, (S[pss]\NP)/NP, VBN)',
            '<PushOp>:(a, NP[nb]/N, DT)',
            '<PushOp>:(nonexecutive, N/N, JJ)',
            '<PushOp>:(director, N, NN)',
            '<ExecOp>:(2, FA N)',
            '<ExecOp>:(2, FA NP)',
            '<PushOp>:(of, (NP\NP)/NP, IN)',
            '<PushOp>:(this, NP[nb]/N, DT)',
            '<PushOp>:(british, N/N, JJ)',
            '<PushOp>:(industrial, N/N, JJ)',
            '<PushOp>:(conglomerate, N, NN)',
            '<ExecOp>:(2, FA N)',
            '<ExecOp>:(2, FA N)',
            '<ExecOp>:(2, FA NP)',
            '<ExecOp>:(2, FA NP\NP)',
            '<ExecOp>:(2, BA NP)',
            '<ExecOp>:(2, FA S[pss]\NP)',
            '<ExecOp>:(2, FA S[dcl]\NP)',
            '<ExecOp>:(2, BA S[dcl])',
            '<PushOp>:(., ., .)',
            '<ExecOp>:(2, LP S[dcl])',
        ]
        self.assertListEqual(expected, actual)

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

