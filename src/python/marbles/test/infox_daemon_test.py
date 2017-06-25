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


class InfoxTest(unittest.TestCase):

    def setUp(self):
        self.ccgparser = grpc.CcgParserService('easysrl')
        self.daemon = subprocess.Popen([os.path.join(PROJDIR, 'src', 'python', 'services', 'infox', 'infox.py'),
                                        '--port', '50000', '--log-level', 'debug'])
        # Wait for model to load otherwise port will not be available
        time.sleep(20)
        # Check if success
        os.kill(self.daemon.pid, 0)

    def tearDown(self):
        os.kill(self.daemon.pid, signal.SIGINT)
        time.sleep(5)
        self.ccgparser.shutdown()

    def test1_parse(self):
        stub, _ = grpc.get_infox_client_transport('localhost', 50000)
        gtext = grpc.GText()
        gtext.text = 'The boy wants to believe the girl'
        gtext.options = CO_VERIFY_SIGNATURES | CO_NO_VERBNET | CO_NO_WIKI_SEARCH
        sentence = stub.parse(gtext)
        xwords = [
            'The',
            'boy',
            'wants',
            'to',
            'believe',
            'the',
            'girl'
        ]
        awords = [lex.word for lex in sentence.lexemes]
        self.assertListEqual(xwords, awords)
        xconstituents = [
            [0, 1, 2, 3, 4, 5, 6],
            [0, 1],
            [3, 4, 5, 6],
            [4, 5, 6],
            [5, 6]
        ]
        aconstituents = []
        for c in sentence.constituents:
            aconstituents.append([x for x in c.span])
        self.assertListEqual(xconstituents, aconstituents)

if __name__ == '__main__':
    unittest.main()
