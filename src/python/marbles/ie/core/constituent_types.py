# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
from marbles.ie.utils.cache import ConstString, Cache


CONSTITUENT_NP = ConstString('NP')
CONSTITUENT_VP = ConstString('VP')
CONSTITUENT_PP = ConstString('PP')
CONSTITUENT_ADVP = ConstString('ADVP')
CONSTITUENT_ADJP = ConstString('ADJP')
CONSTITUENT_SINF = ConstString('S_INF')
CONSTITUENT_TO = ConstString('TO')
CONSTITUENT_SDCL = ConstString('S_DCL')
CONSTITUENT_SEM = ConstString('S_EM')
CONSTITUENT_SQ = ConstString('S_Q')
CONSTITUENT_SWQ = ConstString('S_WQ')
CONSTITUENT_S = ConstString('S')


_CT = Cache()
_CT.addinit((CONSTITUENT_NP.signature, CONSTITUENT_NP))
_CT.addinit((CONSTITUENT_VP.signature, CONSTITUENT_VP))
_CT.addinit((CONSTITUENT_PP.signature, CONSTITUENT_PP))
_CT.addinit((CONSTITUENT_ADVP.signature, CONSTITUENT_ADVP))
_CT.addinit((CONSTITUENT_ADJP.signature, CONSTITUENT_ADJP))
_CT.addinit((CONSTITUENT_SINF.signature, CONSTITUENT_SINF))
_CT.addinit((CONSTITUENT_TO.signature, CONSTITUENT_TO))
_CT.addinit((CONSTITUENT_SDCL.signature, CONSTITUENT_SDCL))
_CT.addinit((CONSTITUENT_SEM.signature, CONSTITUENT_SEM))
_CT.addinit((CONSTITUENT_SQ.signature, CONSTITUENT_SQ))
_CT.addinit((CONSTITUENT_SWQ.signature, CONSTITUENT_SWQ))
_CT.addinit((CONSTITUENT_S.signature, CONSTITUENT_S))
for k, v in _CT:
    v.freeze()


def from_cache(typestr):
    """Get a constituent type from its type string."""
    try:
        return _CT[typestr]
    except KeyError:
        _CT[typestr] = ConstString(typestr)
