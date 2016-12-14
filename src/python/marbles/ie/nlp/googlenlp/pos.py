# Google Part Of Speech tags
from . import tag

_GOOGLE_POS_NAMES = [
     # Google specific tags
    'UNKNOWN',  # Unknown
    'PRT',      # Particle or other function word
    'AFFIX',    # Affix
    # Universal tags
    'NOUN',     # Noun (common and proper)
    'ADJ',      # Adjective
    'ADP',      # Adposition (preposition and postposition)
    'ADV',      # Adverb
    'CONJ',     # Conjunction
    'DET',      # Determiner
    'NUM',      # Cardinal number
    'PRON',     # Pronoun
    'PUNCT',    # Punctuation
    'VERB',     # Verb (all tenses and modes)
    'X'         # Other: foreign words, abbreviations
]

POS_LOWER_BOUND = 50
POS_UPPER_BOUND = 50 - 1 + len(_GOOGLE_POS_NAMES)

for i in range(len(_GOOGLE_POS_NAMES)):
    exec('%s = tag.ConstantTag(%i, _GOOGLE_POS_NAMES[%i])' % (_GOOGLE_POS_NAMES[i], i+50, i))


TAG = {}
for i in range(len(_GOOGLE_POS_NAMES)):
    exec('TAG[ _GOOGLE_POS_NAMES[%i] ] = %s' % (i, _GOOGLE_POS_NAMES[i]))


# SpaCy specific tags
'''
'AUX': '',
'INTJ': '',
'PART': '',  # Same as Google PRT
'PROPN': '',  # Same as Google NOUN
'SCONJ': '',
'SYM': '',
'EOLN': '',
'SPACE': '''
