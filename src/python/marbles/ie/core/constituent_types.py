# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
from marbles.ie.utils.cache import ConstString, Cache

ConstituentType = ConstString

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
CONSTITUENT_NODE = ConstString('UNK')


CT = Cache()
CT.addinit((CONSTITUENT_NP.signature, CONSTITUENT_NP))
CT.addinit((CONSTITUENT_VP.signature, CONSTITUENT_VP))
CT.addinit((CONSTITUENT_PP.signature, CONSTITUENT_PP))
CT.addinit((CONSTITUENT_ADVP.signature, CONSTITUENT_ADVP))
CT.addinit((CONSTITUENT_ADJP.signature, CONSTITUENT_ADJP))
CT.addinit((CONSTITUENT_SINF.signature, CONSTITUENT_SINF))
CT.addinit((CONSTITUENT_TO.signature, CONSTITUENT_TO))
CT.addinit((CONSTITUENT_SDCL.signature, CONSTITUENT_SDCL))
CT.addinit((CONSTITUENT_SEM.signature, CONSTITUENT_SEM))
CT.addinit((CONSTITUENT_SQ.signature, CONSTITUENT_SQ))
CT.addinit((CONSTITUENT_SWQ.signature, CONSTITUENT_SWQ))
CT.addinit((CONSTITUENT_S.signature, CONSTITUENT_S))
CT.addinit((CONSTITUENT_NODE.signature, CONSTITUENT_NODE))


# Universal tags
_postags = {
    'CC':'CONJ',    'CD':'NUM',     'DT':'DET',     'EX':'ADV',
    'FW':'X',       'IN':'ADP',     'JJ':'ADJ',     'JJR':'ADJ',
    'JJS':'ADJ',    'LS':'PUNCT',   'MD':'VERB',    'NN':'NOUN',
    'NNS':'NOUN',   'NNP':'PROPN',  'NNPS':'PROPN', 'PDT':'DET',
    'POS':'PART',   'PRP':'PRON',   'PRP$':'DET',   'RB':'ADV',
    'RBR':'ADV',    'RBS':'ADV',    'RP':'PART',    'SYM':'SYM',
    'TO':'PART',    'UH':'X',       'VB':'VERB',    'VBD':'VERB',
    'VBG':'VERB',   'VBN':'VERB',   'VBP':'VERB',   'VBZ':'VERB',
    'WDT':'DET',    'WP':'PRON',    'WP$':'DET',    'WRB':'ADV',
}

# Ensure we get a single instance for each universal tag
_utags = {}
for pos, unv in _postags.items():
    unv = _utags.setdefault(unv, ConstString(unv))
    CT.addinit((pos, unv))              # pos alias
    CT.addinit((unv.signature, unv))    # actual

# Free memory
_utags = None
_postags = None


CONSTITUENT_PUNCT = CT['LS']
CONSTITUENT_CONJ = CT['CC']
CONSTITUENT_VERB = CT['VBZ']
CONSTITUENT_ADP = CT['IN']


for k, v in CT:
    v.freeze()


def from_cache(typestr):
    """Get a constituent type from its type string."""
    try:
        return CT[typestr]
    except KeyError:
        CT[typestr] = ConstString(typestr)
