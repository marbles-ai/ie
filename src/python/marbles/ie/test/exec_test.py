# -*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function

import unittest

from marbles import future_string
from marbles.ie.ccg import parse_ccg_derivation2 as parse_ccg_derivation
from marbles.ie.ccg import get_rule, Category, RL_RPASS, RL_TC_ATOM
from marbles.ie.ccg.utils import pt_to_utf8
from marbles.ie.parse import parse_ccg_derivation as parse_ccg_derivation_old
from marbles.ie.semantics.ccg import Ccg2Drs
from marbles.test import dprint, DPRINT_ON


class ExecTest(unittest.TestCase):

    def test1_Wsj0001_2(self):
        txt = r'''
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
        ccg = Ccg2Drs()
        ccg.build_execution_sequence(pt)
        # Check execution queue
        actual = [repr(x) for x in ccg.exeque]
        expected = [
            '<PushOp>:(Mr, N/N, NNP)',
            '<PushOp>:(Vinken, N, NNP)',
            '<ExecOp>:(2, FA N)',
            '<ExecOp>:(1, LP NP)',
            '<PushOp>:(be, (S[dcl]\\NP)/NP, VBZ)',
            '<PushOp>:(chairman, N, NN)',
            '<ExecOp>:(1, LP NP)',
            '<PushOp>:(of, (NP\\NP)/NP, IN)',
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
            '<ExecOp>:(2, FA NP\\NP)',
            '<ExecOp>:(2, BA NP)',
            '<ExecOp>:(2, FA S[dcl]\\NP)',
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

    def test2_Wsj0037_37(self):
        txt = r'''
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

    def test3_Wsj0002_1(self):
        # Rudolph Agnew, 55 years old and former chairman of Consolidated Gold Fields PLC, was named a nonexecutive
        # director of this British industrial conglomerate.
        txt = r'''
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
        if future_string == unicode:
            pt_old = parse_ccg_derivation_old(txt)
        else:
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
            '<PushOp>:(old, (S[adj]\\NP)\\NP, JJ)',
            '<ExecOp>:(2, BA S[adj]\\NP)',
            '<PushOp>:(and, conj, CC)',
            '<PushOp>:(former, N/N, JJ)',
            '<PushOp>:(chairman, N, NN)',
            '<ExecOp>:(2, FA N)',
            '<ExecOp>:(1, LP NP)',
            '<PushOp>:(of, (NP\\NP)/NP, IN)',
            '<PushOp>:(Consolidated, N/N, NNP)',
            '<PushOp>:(Gold, N/N, NNP)',
            '<PushOp>:(Fields, N/N, NNP)',
            '<PushOp>:(PLC, N, NNP)',
            '<ExecOp>:(2, FA N)',
            '<ExecOp>:(2, FA N)',
            '<ExecOp>:(2, FA N)',
            '<ExecOp>:(1, LP NP)',
            '<ExecOp>:(2, FA NP\\NP)',
            '<ExecOp>:(2, BA NP)',
            '<ExecOp>:(2, CONJ_TC S[adj]\\NP[conj])',
            '<ExecOp>:(2, RCONJ S[adj]\\NP)',
            '<ExecOp>:(1, L_UNARY_TC NP\\NP)',
            '<ExecOp>:(2, BA NP)',
            '<PushOp>:(,, ,, ,)',
            '<ExecOp>:(2, LP NP)',
            '<PushOp>:(be, (S[dcl]\\NP)/(S[pss]\\NP), VBD)',
            '<PushOp>:(name, (S[pss]\\NP)/NP, VBN)',
            '<PushOp>:(a, NP[nb]/N, DT)',
            '<PushOp>:(nonexecutive, N/N, JJ)',
            '<PushOp>:(director, N, NN)',
            '<ExecOp>:(2, FA N)',
            '<ExecOp>:(2, FA NP)',
            '<PushOp>:(of, (NP\\NP)/NP, IN)',
            '<PushOp>:(this, NP[nb]/N, DT)',
            '<PushOp>:(british, N/N, JJ)',
            '<PushOp>:(industrial, N/N, JJ)',
            '<PushOp>:(conglomerate, N, NN)',
            '<ExecOp>:(2, FA N)',
            '<ExecOp>:(2, FA N)',
            '<ExecOp>:(2, FA NP)',
            '<ExecOp>:(2, FA NP\\NP)',
            '<ExecOp>:(2, BA NP)',
            '<ExecOp>:(2, FA S[pss]\\NP)',
            '<ExecOp>:(2, FA S[dcl]\\NP)',
            '<ExecOp>:(2, BA S[dcl])',
            '<PushOp>:(., ., .)',
            '<ExecOp>:(2, LP S[dcl])',
        ]
        self.assertListEqual(expected, actual)

    def test4_Wsj0999_11(self):
        txt = r'''
(<T S[dcl] 0 2>
  (<T S[dcl] 0 2>
    (<T S[dcl] 1 2>
      (<T NP 0 2>
        (<T NP 0 1>
          (<L N NNS NNS People N>)
        )
        (<T NP\NP 0 2>
          (<L (NP\NP)/NP IN IN on (NP_159\NP_159)/NP_160>)
          (<T NP 0 1>
            (<T N 1 2>
              (<L N/N VBN VBN fixed N_169/N_169>)
              (<L N NNS NNS incomes N>)
            )
          )
        )
      )
      (<T S[dcl]\NP 0 2>
        (<L (S[dcl]\NP)/NP VBP VBP get (S[dcl]\NP_128)/NP_129>)
        (<T NP 0 2>
          (<T NP 1 2>
            (<L NP[nb]/N DT DT a NP[nb]_136/N_136>)
            (<L N NN NN break N>)
          )
          (<T NP\NP 0 2>
            (<L (NP\NP)/NP IN IN at (NP_144\NP_144)/NP_145>)
            (<T NP 0 1>
              (<L N NNP NNP Espre N>)
            )
          )
        )
      )
    )
    (<T S[dcl][conj] 1 2>
      (<L ; ; : ; ;>)
      (<T S[dcl] 1 2>
        (<T NP 0 1>
          (<T N 1 2>
            (<L N/N IN IN over N_248/N_248>)
            (<L N CD CD 55 N>)
          )
        )
        (<T S[dcl]\NP 0 2>
          (<L (S[dcl]\NP)/NP VBZ NNS wins (S[dcl]\NP_177)/NP_178>)
          (<T NP 0 2>
            (<T NP 1 2>
              (<L NP[nb]/N DT DT a NP[nb]_206/N_206>)
              (<T N 1 2>
                (<T N/N 1 2>
                  (<L (N/N)/(N/N) CD CD 45 (N_201/N_195)_201/(N_201/N_195)_201>)
                  (<L N/N NN NN % N_187/N_187>)
                )
                (<L N NN NN discount N>)
              )
            )
            (<T NP\NP 0 2>
              (<L (NP\NP)/NP IN IN at (NP_214\NP_214)/NP_215>)
              (<T NP 0 1>
                (<T N 1 2>
                  (<L N/N NNP NNP Anaheim N_238/N_238>)
                  (<T N 1 2>
                    (<L N/N NNP NNP Imperial N_231/N_231>)
                    (<T N 1 2>
                      (<L N/N NNP NNP Health N_224/N_224>)
                      (<L N NNP NNP Spa N>)
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
  (<L . . . . .>)
)'''
        pt = parse_ccg_derivation(txt)
        ccg = Ccg2Drs()
        ccg.build_execution_sequence(pt)
        # Check execution queue
        actual = [repr(x) for x in ccg.exeque]
        expected = [
            '<PushOp>:(people, N, NNS)',
            '<ExecOp>:(1, LP NP)',
            '<PushOp>:(on, (NP\\NP)/NP, IN)',
            '<PushOp>:(fix, N/N, VBN)',
            '<PushOp>:(incomes, N, NNS)',
            '<ExecOp>:(2, FA N)',
            '<ExecOp>:(1, LP NP)',
            '<ExecOp>:(2, FA NP\\NP)',
            '<ExecOp>:(2, BA NP)',
            '<PushOp>:(get, (S[dcl]\\NP)/NP, VBP)',
            '<PushOp>:(a, NP[nb]/N, DT)',
            '<PushOp>:(break, N, NN)',
            '<ExecOp>:(2, FA NP)',
            '<PushOp>:(at, (NP\\NP)/NP, IN)',
            '<PushOp>:(Espre, N, NNP)',
            '<ExecOp>:(1, LP NP)',
            '<ExecOp>:(2, FA NP\\NP)',
            '<ExecOp>:(2, BA NP)',
            '<ExecOp>:(2, FA S[dcl]\\NP)',
            '<ExecOp>:(2, BA S[dcl])',
            '<PushOp>:(;, ;, ;)',
            '<PushOp>:(over, N/N, IN)',
            '<PushOp>:(55, N, CD)',
            '<ExecOp>:(2, FA N)',
            '<ExecOp>:(1, LP NP)',
            '<PushOp>:(win, (S[dcl]\\NP)/NP, VBZ)',
            '<PushOp>:(a, NP[nb]/N, DT)',
            '<PushOp>:(45, (N/N)/(N/N), CD)',
            '<PushOp>:(%, N/N, NN)',
            '<ExecOp>:(2, FA N/N)',
            '<PushOp>:(discount, N, NN)',
            '<ExecOp>:(2, FA N)',
            '<ExecOp>:(2, FA NP)',
            '<PushOp>:(at, (NP\\NP)/NP, IN)',
            '<PushOp>:(Anaheim, N/N, NNP)',
            '<PushOp>:(Imperial, N/N, NNP)',
            '<PushOp>:(Health, N/N, NNP)',
            '<PushOp>:(Spa, N, NNP)',
            '<ExecOp>:(2, FA N)',
            '<ExecOp>:(2, FA N)',
            '<ExecOp>:(2, FA N)',
            '<ExecOp>:(1, LP NP)',
            '<ExecOp>:(2, FA NP\\NP)',
            '<ExecOp>:(2, BA NP)',
            '<ExecOp>:(2, FA S[dcl]\\NP)',
            '<ExecOp>:(2, BA S[dcl])',
            '<ExecOp>:(2, RP S[dcl][conj])',
            '<ExecOp>:(2, RCONJ S[dcl])',
            '<PushOp>:(., ., .)',
            '<ExecOp>:(2, LP S[dcl])',
        ]
        self.assertListEqual(expected, actual)

    def test5_EasySRL_04_1850(self):
        txt = r'''
(<T S[dcl] 0 2>
  (<T S[dcl] 1 2>
    (<T NP 0 2>
      (<L NP/N DT DT The NP/N>)
      (<T N 1 2>
        (<L N/N NN NN investment N/N>)
        (<T N 0 2>
          (<L N NN NN community N>)
          (<L , , , , ,>)
        )
      )
    )
    (<T S[dcl]\NP 1 2>
      (<T (S\NP)/(S\NP) 0 2>
        (<L (S\NP)/(S\NP) RB RB however (S\NP)/(S\NP)>)
        (<T ((S\NP)/(S\NP))\((S\NP)/(S\NP)) 1 2>
          (<L , , , , ,>)
          (<L (S\NP)/(S\NP) RB RB strongly (S\NP)/(S\NP)>)
        )
      )
      (<T S[dcl]\NP 0 2>
        (<L (S[dcl]\NP)/S[em] VBZ VBZ believes (S[dcl]\NP)/S[em]>)
          (<T S[em] 0 2>
            (<L S[em]/S[dcl] IN IN that S[em]/S[dcl]>)
            (<T S[dcl] 1 2>
              (<T NP 0 2>
                 (<L NP/N DT DT the NP/N>)
                 (<L N NN NN strike N>)
              )
              (<T S[dcl]\NP 0 2>
                (<L (S[dcl]\NP)/(S[b]\NP) MD MD will (S[dcl]\NP)/(S[b]\NP)>)
                (<T S[b]\NP 0 2>
                  (<T S[b]\NP 0 2>
                    (<L (S[b]\NP)/(S[pss]\NP) VB VB be (S[b]\NP)/(S[pss]\NP)>)
                    (<L S[pss]\NP VBN VBN settled S[pss]\NP>)
                  )
                (<T (S\NP)\(S\NP) 0 2>
                  (<L ((S\NP)\(S\NP))/S[dcl] IN IN before ((S\NP)\(S\NP))/S[dcl]>)
                  (<T S[dcl] 1 2>
                    (<L NP[thr] EX EX there NP[thr]>)
                    (<T S[dcl]\NP[thr] 0 2>
                      (<L (S[dcl]\NP[thr])/NP VBZ VBZ is (S[dcl]\NP[thr])/NP>)
                      (<T NP 0 2>
                        (<T NP 0 2>
                          (<L NP/N DT DT any NP/N>)
                          (<T N 1 2>
                            (<L N/N JJ JJ lasting N/N>)
                            (<T N 0 2>
                              (<L N/PP NN NN effect N/PP>)
                              (<T PP 0 2>
                                (<L PP/NP IN IN on PP/NP>)
                                (<T NP 1 2>
                                  (<L NP/NP CC CC either NP/NP>)
                                  (<T NP 0 1>
                                    (<L N NNP NNP Boeing N>)
                                  )
                                )
                              )
                            )
                          )
                        )
                        (<T NP\NP 1 2>
                          (<L conj CC CC or conj>)
                          (<T NP 0 2>
                            (<L NP/(N/PP) PRP$ PRP$ its NP/(N/PP)>)
                            (<T N/PP 1 2>
                              (<L N/N NN NN work N/N>)
                              (<L N/PP NN NN force N/PP>)
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
            '<PushOp>:(the, NP/N, DT)',
            '<PushOp>:(investment, N/N, NN)',
            '<PushOp>:(community, N, NN)',
            '<PushOp>:(,, ,, ,)',
            '<ExecOp>:(2, LP N)',
            '<ExecOp>:(2, FA N)',
            '<ExecOp>:(2, FA NP)',
            '<PushOp>:(however, (S\\NP)/(S\\NP), RB)',
            '<PushOp>:(,, ,, ,)',
            '<PushOp>:(strongly, (S\\NP)/(S\\NP), RB)',
            '<ExecOp>:(2, R_UNARY_TC ((S\\NP)/(S\\NP))\((S\\NP)/(S\\NP)))',
            '<ExecOp>:(2, BA (S\\NP)/(S\\NP))',
            '<PushOp>:(believe, (S[dcl]\\NP)/S[em], VBZ)',
            '<PushOp>:(that, S[em]/S[dcl], IN)',
            '<PushOp>:(the, NP/N, DT)',
            '<PushOp>:(strike, N, NN)',
            '<ExecOp>:(2, FA NP)',
            '<PushOp>:(will, (S\\NP)/(S\\NP), MD)',
            '<PushOp>:(be, (S[b]\\NP)/(S[pss]\\NP), VB)',
            '<PushOp>:(settle, S[pss]\\NP, VBN)',
            '<ExecOp>:(2, FA S[b]\\NP)',
            '<PushOp>:(before, ((S\\NP)\(S\\NP))/S[dcl], IN)',
            '<PushOp>:(there, NP[thr], EX)',
            '<PushOp>:(be, (S[dcl]\\NP[thr])/NP, VBZ)',
            '<PushOp>:(any, NP/N, DT)',
            '<PushOp>:(lasting, N/N, JJ)',
            '<PushOp>:(effect, N/PP, NN)',
            '<PushOp>:(on, PP/NP, IN)',
            '<PushOp>:(either, NP/NP, CC)',
            '<PushOp>:(Boeing, N, NNP)',
            '<ExecOp>:(1, LP NP)',
            '<ExecOp>:(2, FA NP)',
            '<ExecOp>:(2, FA PP)',
            '<ExecOp>:(2, FA N)',
            '<ExecOp>:(2, FA N)',
            '<ExecOp>:(2, FA NP)',
            '<PushOp>:(or, conj, CC)',
            '<PushOp>:(its, NP/(N/PP), PRP$)',
            '<PushOp>:(work, N/N, NN)',
            '<PushOp>:(force, N/PP, NN)',
            '<ExecOp>:(2, FC N/PP)',
            '<ExecOp>:(2, FA NP)',
            '<ExecOp>:(2, R_UNARY_TC NP\\NP)',
            '<ExecOp>:(2, BA NP)',
            '<ExecOp>:(2, FA S[dcl]\\NP[thr])',
            '<ExecOp>:(2, BA S[dcl])',
            '<ExecOp>:(2, FA (S\\NP)\\(S\\NP))',
            '<ExecOp>:(2, BA S[b]\\NP)',
            '<ExecOp>:(2, FA S[dcl]\\NP)',
            '<ExecOp>:(2, BA S[dcl])',
            '<ExecOp>:(2, FA S[em])',
            '<ExecOp>:(2, FA S[dcl]\\NP)',
            '<ExecOp>:(2, FA S[dcl]\\NP)',
            '<ExecOp>:(2, BA S[dcl])',
            '<PushOp>:(., ., .)',
            '<ExecOp>:(2, LP S[dcl])',
        ]
        self.assertListEqual(expected, actual)

    def test6_Wsj0051_13(self):
        txt = r'''
(<T S[dcl] 0 2> 
  (<T S[dcl] 1 2> 
    (<T NP 1 2> 
      (<L NP[nb]/N DT DT The NP[nb]_273/N_273>) 
      (<L N NNS NNS bids N>) 
    ) 
    (<T S[dcl]\NP 1 2> 
      (<T (S\NP)/(S\NP) 1 2> 
        (<L , , , , ,>) 
        (<T (S\NP)/(S\NP) 0 2> 
          (<T S[dcl]/S[dcl] 1 2> 
            (<T S/(S\NP) 0 1> 
              (<L NP PRP PRP he NP>) 
            ) 
            (<L (S[dcl]\NP)/S[dcl] VBD VBD added (S[dcl]\NP_242)/S[dcl]_243>) 
          ) 
          (<L , , , , ,>) 
        ) 
      ) 
      (<T S[dcl]\NP 0 2> 
        (<L (S[dcl]\NP)/(S[adj]\NP) VBD VBD were (S[dcl]\NP_211)/(S[adj]_212\NP_211:B)_212>) 
        (<T S[adj]\NP 0 2> 
          (<L (S[adj]\NP)/PP JJ JJ contrary (S[adj]\NP_219)/PP_220>) 
          (<T PP 0 2> 
            (<L PP/NP TO TO to PP/NP_225>) 
            (<T NP 0 1> 
              (<T N 1 2> 
                (<L N/N JJ JJ common N_234/N_234>) 
                (<L N NN NN sense N>) 
              ) 
            ) 
          ) 
        ) 
      ) 
    ) 
  ) 
  (<L . . . . .>) 
) 
'''
        pt = parse_ccg_derivation(txt)
        ccg = Ccg2Drs()
        ccg.build_execution_sequence(pt)
        # Check execution queue
        actual = [repr(x) for x in ccg.exeque]
        expected = [
            '<PushOp>:(the, NP[nb]/N, DT)',
            '<PushOp>:(bids, N, NNS)',
            '<ExecOp>:(2, FA NP)',
            '<PushOp>:(,, ,, ,)',
            '<PushOp>:(he, NP, PRP)',
            '<ExecOp>:(1, TR S/(S\\NP))',
            '<PushOp>:(add, (S[dcl]\\NP)/S[dcl], VBD)',
            '<ExecOp>:(2, FC S[dcl]/S[dcl])',
            '<PushOp>:(,, ,, ,)',
            '<ExecOp>:(2, L_UNARY_TC (S\\NP)/(S\\NP))',
            '<ExecOp>:(2, RP (S\\NP)/(S\\NP))',
            '<PushOp>:(be, (S[dcl]\\NP)/(S[adj]\\NP), VBD)',
            '<PushOp>:(contrary, (S[adj]\\NP)/PP, JJ)',
            '<PushOp>:(to, PP/NP, TO)',
            '<PushOp>:(common, N/N, JJ)',
            '<PushOp>:(sense, N, NN)',
            '<ExecOp>:(2, FA N)',
            '<ExecOp>:(1, LP NP)',
            '<ExecOp>:(2, FA PP)',
            '<ExecOp>:(2, FA S[adj]\\NP)',
            '<ExecOp>:(2, FA S[dcl]\\NP)',
            '<ExecOp>:(2, FA S[dcl]\\NP)',
            '<ExecOp>:(2, BA S[dcl])',
            '<PushOp>:(., ., .)',
            '<ExecOp>:(2, LP S[dcl])',
        ]
        self.assertListEqual(expected, actual)

    def test7_Wsj0051_30(self):
        txt = r'''
(<T S[dcl] 0 2> 
  (<T S[dcl] 1 2> 
    (<T NP 0 1> 
      (<T N 1 2> 
        (<L N NNP NNP Fujitsu N>) 
        (<T N[conj] 1 2> 
          (<L conj CC CC and conj>) 
          (<L N NNP NNP NEC N>) 
        ) 
      ) 
    ) 
    (<T S[dcl]\NP 0 2> 
      (<L (S[dcl]\NP)/S[dcl] VBD VBD said (S[dcl]\NP_146)/S[dcl]_147>) 
      (<T S[dcl] 0 2> 
        (<T S[dcl] 1 2> 
          (<L NP PRP PRP they NP>) 
          (<T S[dcl]\NP 0 2> 
            (<T (S[dcl]\NP)/(S[ng]\NP) 0 2> 
              (<L (S[dcl]\NP)/(S[ng]\NP) VBD VBD were (S[dcl]\NP_156)/(S[ng]_157\NP_156:B)_157>) 
              (<L (S\NP)\(S\NP) RB RB still (S_169\NP_164)_169\(S_169\NP_164)_169>) 
            ) 
            (<L S[ng]\NP VBG VBG investigating S[ng]\NP_174>) 
          ) 
        ) 
        (<T S[dcl][conj] 1 2> 
          (<L , , , , ,>) 
          (<T S[dcl][conj] 1 2> 
            (<L conj CC CC and conj>) 
            (<T S[em] 0 2> 
              (<L S[em]/S[dcl] IN IN that S[em]/S[dcl]_181>) 
              (<T S[dcl] 1 2> 
                (<T NP 0 2> 
                  (<T NP 0 1> 
                    (<L N NN NN knowledge N>) 
                  ) 
                  (<T NP\NP 0 2> 
                    (<L (NP\NP)/NP IN IN of (NP_207\NP_207)/NP_208>) 
                    (<T NP 0 1> 
                      (<T N 1 2> 
                        (<L N/N JJR JJR more N_224/N_224>) 
                        (<T N 1 2> 
                          (<L N/N JJ JJ such N_217/N_217>) 
                          (<L N NNS NNS bids N>) 
                        ) 
                      ) 
                    ) 
                  ) 
                ) 
                (<T S[dcl]\NP 0 2> 
                  (<L (S[dcl]\NP)/(S[b]\NP) MD MD could (S[dcl]\NP_190)/(S[b]_191\NP_190:B)_191>) 
                  (<L S[b]\NP VB VB emerge S[b]\NP_196>) 
                ) 
              ) 
            ) 
          ) 
        ) 
      ) 
    ) 
  ) 
  (<L . . . . .>)
) 
'''
        pt = parse_ccg_derivation(txt)
        ccg = Ccg2Drs()
        rule = get_rule(Category.from_cache('conj'), Category.from_cache('S[em]'), Category.from_cache('S[dcl][conj]'))
        self.assertEqual(rule, RL_RPASS)
        ccg.build_execution_sequence(pt)
        # Check execution queue
        actual = [repr(x) for x in ccg.exeque]
        expected = [
            '<PushOp>:(Fujitsu, N, NNP)',
            '<PushOp>:(and, conj, CC)',
            '<PushOp>:(NEC, N, NNP)',
            '<ExecOp>:(2, RP N[conj])',
            '<ExecOp>:(2, RCONJ N)',
            '<ExecOp>:(1, LP NP)',
            '<PushOp>:(say, (S[dcl]\\NP)/S[dcl], VBD)',
            '<PushOp>:(they, NP, PRP)',
            '<PushOp>:(be, (S[dcl]\\NP)/(S[ng]\\NP), VBD)',
            '<PushOp>:(still, (S\\NP)\\(S\\NP), RB)',
            '<ExecOp>:(2, BX (S[dcl]\\NP)/(S[ng]\\NP))',
            '<PushOp>:(investigate, S[ng]\\NP, VBG)',
            '<ExecOp>:(2, FA S[dcl]\\NP)',
            '<ExecOp>:(2, BA S[dcl])',
            '<PushOp>:(,, ,, ,)',
            '<PushOp>:(and, conj, CC)',
            '<PushOp>:(that, S[em]/S[dcl], IN)',
            '<PushOp>:(knowledge, N, NN)',
            '<ExecOp>:(1, LP NP)',
            '<PushOp>:(of, (NP\\NP)/NP, IN)',
            '<PushOp>:(more, N/N, JJR)',
            '<PushOp>:(such, N/N, JJ)',
            '<PushOp>:(bids, N, NNS)',
            '<ExecOp>:(2, FA N)',
            '<ExecOp>:(2, FA N)',
            '<ExecOp>:(1, LP NP)',
            '<ExecOp>:(2, FA NP\\NP)',
            '<ExecOp>:(2, BA NP)',
            '<PushOp>:(could, (S\\NP)/(S\\NP), MD)',
            '<PushOp>:(emerge, S[b]\\NP, VB)',
            '<ExecOp>:(2, FA S[dcl]\\NP)',
            '<ExecOp>:(2, BA S[dcl])',
            '<ExecOp>:(2, FA S[em])',
            '<ExecOp>:(2, RP S[dcl][conj])',
            '<ExecOp>:(2, RP S[dcl][conj])',
            '<ExecOp>:(2, RCONJ S[dcl])',
            '<ExecOp>:(2, FA S[dcl]\\NP)',
            '<ExecOp>:(2, BA S[dcl])',
            '<PushOp>:(., ., .)',
            '<ExecOp>:(2, LP S[dcl])'
        ]
        self.assertListEqual(expected, actual)

    def test8_Wsj0004_3(self):
        txt = r'''
        (<T S[dcl] 0 2> (<T S[dcl] 1 2> (<T NP 0 1> (<T N 1 2> (<L N/N NN NN Compound N_309/N_309>) 
        (<L N NNS NNS yields N>) ) ) (<T S[dcl]\NP 0 2> (<L (S[dcl]\NP)/NP VBP VBP assume (S[dcl]\NP_236)/NP_237>) 
        (<T NP 0 2> (<T NP 0 2> (<T NP 0 1> (<L N NN NN reinvestment N>) ) (<T NP\NP 0 2> 
        (<L (NP\NP)/NP IN IN of (NP_248\NP_248)/NP_249>) (<T NP 0 1> (<L N NNS NNS dividends N>) ) ) ) (<T NP[conj] 1 2> 
        (<L conj CC CC and conj>) (<T S[em] 0 2> (<L S[em]/S[dcl] IN IN that S[em]/S[dcl]_257>) (<T S[dcl] 1 2> 
        (<T NP 1 2> (<L NP[nb]/N DT DT the NP[nb]_297/N_297>) (<T N 1 2> (<L N/N JJ JJ current N_292/N_292>) 
        (<L N NN NN yield N>) ) ) (<T S[dcl]\NP 0 2> (<L S[dcl]\NP VBZ VBZ continues S[dcl]\NP_262>) 
        (<T (S\NP)\(S\NP) 0 2> (<L ((S\NP)\(S\NP))/NP IN IN for ((S_275\NP_270)_275\(S_275\NP_270)_275)/NP_276>) 
        (<T NP 1 2> (<L NP[nb]/N DT DT a NP[nb]_283/N_283>) (<L N NN NN year N>) ) ) ) ) ) ) ) ) ) (<L . . . . .>) ) '''
        pt = parse_ccg_derivation(txt)
        ccg = Ccg2Drs()
        rule = get_rule(Category.from_cache('conj'), Category.from_cache('S[em]'), Category.from_cache('NP[conj]'))
        self.assertEqual(rule, RL_TC_ATOM)
        ccg.build_execution_sequence(pt)
        # Check execution queue
        actual = [repr(x) for x in ccg.exeque]
        expected = [
            '<PushOp>:(compound, N/N, NN)',
            '<PushOp>:(yields, N, NNS)',
            '<ExecOp>:(2, FA N)',
            '<ExecOp>:(1, LP NP)',
            '<PushOp>:(assume, (S[dcl]\\NP)/NP, VBP)',
            '<PushOp>:(reinvestment, N, NN)',
            '<ExecOp>:(1, LP NP)',
            '<PushOp>:(of, (NP\\NP)/NP, IN)',
            '<PushOp>:(dividends, N, NNS)',
            '<ExecOp>:(1, LP NP)',
            '<ExecOp>:(2, FA NP\\NP)',
            '<ExecOp>:(2, BA NP)',
            '<PushOp>:(and, conj, CC)',
            '<PushOp>:(that, S[em]/S[dcl], IN)',
            '<PushOp>:(the, NP[nb]/N, DT)',
            '<PushOp>:(current, N/N, JJ)',
            '<PushOp>:(yield, N, NN)',
            '<ExecOp>:(2, FA N)',
            '<ExecOp>:(2, FA NP)',
            '<PushOp>:(continue, S[dcl]\\NP, VBZ)',
            '<PushOp>:(for, ((S\\NP)\\(S\\NP))/NP, IN)',
            '<PushOp>:(a, NP[nb]/N, DT)',
            '<PushOp>:(year, N, NN)',
            '<ExecOp>:(2, FA NP)',
            '<ExecOp>:(2, FA (S\\NP)\\(S\\NP))',
            '<ExecOp>:(2, BA S[dcl]\\NP)',
            '<ExecOp>:(2, BA S[dcl])',
            '<ExecOp>:(2, FA S[em])',
            '<ExecOp>:(2, ATOM_TC NP[conj])',
            '<ExecOp>:(2, RCONJ NP)',
            '<ExecOp>:(2, FA S[dcl]\\NP)',
            '<ExecOp>:(2, BA S[dcl])',
            '<PushOp>:(., ., .)',
            '<ExecOp>:(2, LP S[dcl])',
        ]
        self.assertListEqual(expected, actual)
