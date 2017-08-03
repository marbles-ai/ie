# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import unittest
from marbles.ie import grpc
from marbles.ie.ccg import parse_ccg_derivation2 as parse_ccg_derivation
from marbles.ie.drt.drs import Rel
from marbles.ie.semantics.ccg import process_ccg_pt, pt_to_ccg_derivation
from marbles.ie.core.constants import *
from marbles.ie.utils.text import preprocess_sentence
from marbles.test import dprint


class PossessiveTest(unittest.TestCase):
    def setUp(self):
        self.svc = grpc.CcgParserService('easysrl')
        self.stub = self.svc.open_client()

    def tearDown(self):
        self.svc.shutdown()

    def test10_Brutus(self):
        text = "Ceasar was stabbed by Brutus"
        derivation = grpc.ccg_parse(self.stub, text, grpc.DEFAULT_SESSION)
        pt = parse_ccg_derivation(derivation)
        sentence = process_ccg_pt(pt, CO_NO_VERBNET|CO_NO_WIKI_SEARCH)
        d = sentence.get_drs()
        dprint(pt_to_ccg_derivation(pt))
        dprint(d)
        fnps = sentence.get_np_nominals()
        nps = [sp.text for r, sp in fnps]
        #self.assertTrue('Average maturity' in nps)
        self.assertTrue('Brutus' in nps)
        self.assertTrue('Ceasar' in nps)
        fvps = sentence.get_vp_nominals()
        vps = [sp.text for r, sp in fvps]
        self.assertTrue('was stabbed' in vps)
        E = filter(lambda x: x[1].text == "was stabbed", fvps)[0][0]
        A1 = filter(lambda x: x[1].text == "Brutus", fnps)[0][0]
        A0 = filter(lambda x: x[1].text == "Ceasar", fnps)[0][0]
        self.assertTrue(d.find_condition(Rel('_ARG0', [E, A0])) is not None)
        self.assertTrue(d.find_condition(Rel('_ARG1', [E, A1])) is not None)



if __name__ == '__main__':
    unittest.main()


if __name__ == '__main__':
    unittest.main()
