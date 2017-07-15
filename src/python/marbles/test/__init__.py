# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import inspect


def isdebugging():
    for frame in inspect.stack():
        if frame[1].endswith("pydevd.py"):
            return True
    return False


DPRINT_ON = False or isdebugging()


def dprint(*args, **kwargs):
    global DPRINT_ON
    if DPRINT_ON:
        print(*args, **kwargs)
