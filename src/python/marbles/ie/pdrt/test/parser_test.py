import unittest
from ..pdrs import *
from ..parse import parse_pdrs


class ParserTest(unittest.TestCase):

    def test0_PDRTHaskellFormat(self):
        #   1    2    3    4           5
        s = u"<1,{},{ (1,not <5,{(2,x)},{(2,man(x)),(5,happy(x))}, {(5,2)}>) }, {}>"
        parse_pdrs(s)
        pass