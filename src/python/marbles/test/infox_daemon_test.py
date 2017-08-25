# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import unittest
import subprocess
import os
import signal
import time
from marbles import PROJDIR
from marbles.ie import grpc
from marbles.ie.core.constants import *
from marbles.ie.core.marshal import marshal_sentence
from marbles.test import dprint, DPRINT_ON


def get_constituents_string_list(sent):
    s = []
    for i in range(len(sent.constituents)):
        c = sent.constituents[i]
        headword = c.head.idx
        txt = [lex.word if headword != lex.idx else '#'+lex.word for lex in c.span()]
        s.append('%s(%s)' % (c.vntype.signature, ' '.join(txt)))
    return s


def get_constituent_string(sent, ch=' '):
    s = get_constituents_string_list(sent)
    return ch.join(s)


class InfoxTest(unittest.TestCase):

    def setUp(self):
        self.ccgparser = grpc.CcgParserService('easysrl')
        self.daemon = subprocess.Popen([os.path.join(PROJDIR, 'src', 'python', 'services', 'infox', 'infox.py'),
                                        '--port', '50000', '--log-level', 'debug'])
        # Wait for model to load otherwise port will not be available
        time.sleep(40)
        # Check if success
        os.kill(self.daemon.pid, 0)

    def tearDown(self):
        os.kill(self.daemon.pid, signal.SIGINT)
        time.sleep(5)
        self.ccgparser.shutdown()

    def test1_parse(self):
        # PWG: grpc.GText needs to be marshalled into core.sentence
        #
        # Minimal calls are:
        # 1.Get transport to endpoint
        #   stub, _ = grpc.get_infox_client_transport('localhost')
        # 2:Call infox service endpoint
        #   gtext = grpc.GText()
        #   gtext.text = 'The boy wants to believe the girl'
        #   gtext.options = CO_VERIFY_SIGNATURES | CO_NO_VERBNET | CO_NO_WIKI_SEARCH
        #   gsentence = stub.parse(gtext)
        # 3.Marshal into core.sentence
        #   sent = marshal_sentence(gsentence)
        #

        stub, _ = grpc.get_infox_client_transport('localhost', 50000)
        gtext = grpc.GText()
        gtext.text = 'The boy wants to believe the girl'
        gtext.options = CO_VERIFY_SIGNATURES | CO_NO_VERBNET | CO_NO_WIKI_SEARCH
        gsentence = stub.parse(gtext)
        xwords = [
            'The',
            'boy',
            'wants',
            'to',
            'believe',
            'the',
            'girl'
        ]
        awords = [lex.word for lex in gsentence.lexemes]
        self.assertListEqual(xwords, awords)
        xconstituents = [
            [0, 1, 2, 3, 4, 5, 6],
            [0, 1],
            [3, 4, 5, 6],
            [4, 5, 6],
            [5, 6]
        ]
        aconstituents = []
        for c in gsentence.constituents:
            aconstituents.append([x for x in c.span()])
        self.assertListEqual(xconstituents, aconstituents)

        sent = marshal_sentence(gsentence)
        s = get_constituent_string(sent)
        self.assertEqual('S_DCL(The boy #wants to believe the girl) NP(#The boy) S_INF(#to believe the girl) S_INF(#believe the girl) NP(#the girl)', s)


if __name__ == '__main__':
    unittest.main()
