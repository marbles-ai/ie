from spacy.en import English  # NLP with spaCy https://spacy.io
from spacy.symbols import IDS as SPACY_IDS
from clausefinder.googlenlp.dep import _GOOGLE_DEP_NAMES

NLP = English() # will take some time to load


_NO_GOOGLE_DEP_EQUIV = [
    'agent',
    'complm',
    'hyph',
    'hmod',
    'infmod',
    'intj',
    'meta',
    'nmod',
    'oprd',
    'possessive',
    'compound',
]

_GOOGLE_DEP_EQUIV = {
    'UNKNOWN': None,
    'ABBREV': None,
    'ADVPHMOD': None,
    'AUXCAUS': None,
    'AUXVV': None,
    'COP': None,
    'DISCOURSE': None,
    'DISLOCATED': None,
    'DTMOD': None,
    'FOREIGN': None,
    'GOESWITH': None,
    'KW': None,
    'LIST': None,
    'MWE': None,
    'MWV': None,
    'NOMC': None,
    'NOMCSUBJ': None,
    'NOMCSUBJPASS': None,
    'NUMC': None,
    'P': 'punct',
    'POSTNEG': None,
    'PRECOMP': None,
    'PREDET': None,
    'PREF': None,
    'PRONL': None,
    'PS': None,
    'RCMODREL': None,
    'RDROP': None,
    'REF': None,
    'REMNANT': None,
    'REPARANDUM': None,
    'SNUM': None,
    'SUFF': None,
    'SUFFIX': None,
    'TITLE': None,
    'TMOD': None,
    'TOPIC': None,
    'VMOD': 'acl',
    'VOCATIVE': None
}

DEP_LOWER_BOUND = 0x7fffffff
DEP_UPPER_BOUND = 0

for depname in _GOOGLE_DEP_NAMES:
    dn = depname.lower()
    try:
        if SPACY_IDS.has_key(dn):
            idx = NLP.vocab.strings[dn]
            DEP_LOWER_BOUND = min(DEP_LOWER_BOUND, idx)
            DEP_UPPER_BOUND = max(DEP_UPPER_BOUND, idx)
            exec ('%s = %i' % (depname, idx))
        elif _GOOGLE_DEP_EQUIV.has_key(depname) and _GOOGLE_DEP_EQUIV[depname] is not None:
            idx = NLP.vocab.strings[ _GOOGLE_DEP_EQUIV[depname] ]
            DEP_LOWER_BOUND = min(DEP_LOWER_BOUND, idx)
            DEP_UPPER_BOUND = max(DEP_UPPER_BOUND, idx)
            exec ('%s = %i' % (depname, idx))
    except:
        pass


# See issue: https://github.com/explosion/spaCy/issues/607
ROOT = NLP.vocab.strings['ROOT']


# These have no google equivalent
for dn in _NO_GOOGLE_DEP_EQUIV:
    idx = NLP.vocab.strings[dn]
    exec ('%s = %i' % (dn.upper(), idx))
