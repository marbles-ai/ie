#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import unittest


# Modify python path
projdir = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
pypath = os.path.join(projdir, 'src', 'python')
sys.path.insert(0, pypath)


from marbles.ie.ccg import test as ccg_test
from marbles.ie.drt import test as drs_test


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.discover(start_dir=os.path.join(pypath, 'marbles', 'ie', 'ccg'), pattern='*_test.py')
    unittest.TextTestRunner().run(suite)
    suite = unittest.defaultTestLoader.discover(start_dir=os.path.join(pypath, 'marbles', 'ie', 'drt'), pattern='*_test.py')
    unittest.TextTestRunner().run(suite)
