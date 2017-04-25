# -*- coding: utf-8 -*-

import os
import unittest
from marbles.ie.kb import verbnet


class VNTest(unittest.TestCase):

    def test1_Load(self):
        db = verbnet.VerbnetDB()
        names = db.names