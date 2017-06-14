# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
from utils.cache import ConstString, Cache


CONSTITUENT_NP = ConstString('NP')
CONSTITUENT_VP = ConstString('VP')
CONSTITUENT_PP = ConstString('PP')
CONSTITUENT_ADVP = ConstString('ADVP')
CONSTITUENT_ADJP = ConstString('ADJP')
CONSTITUENT_SINF = ConstString('S_INF')
CONSTITUENT_TO = ConstString('TO')


Typeof = Cache()
Typeof.addinit((CONSTITUENT_NP.signature, CONSTITUENT_NP))
Typeof.addinit((CONSTITUENT_VP.signature, CONSTITUENT_VP))
Typeof.addinit((CONSTITUENT_PP.signature, CONSTITUENT_PP))
Typeof.addinit((CONSTITUENT_ADVP.signature, CONSTITUENT_ADVP))
Typeof.addinit((CONSTITUENT_ADJP.signature, CONSTITUENT_ADJP))
Typeof.addinit((CONSTITUENT_SINF.signature, CONSTITUENT_SINF))
Typeof.addinit((CONSTITUENT_TO.signature, CONSTITUENT_TO))

for k, v in Typeof:
    v.freeze()
