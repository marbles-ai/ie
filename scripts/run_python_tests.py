#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import os
import sys
import unittest


# Modify python path
projdir = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
pypath = os.path.join(projdir, 'src', 'python')
sys.path.insert(0, pypath)


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.discover(start_dir=os.path.join(pypath, 'marbles'), pattern='*_test.py')
    unittest.TextTestRunner().run(suite)
