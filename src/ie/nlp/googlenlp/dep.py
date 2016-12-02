# Google Dependency tags
from . import tag

_GOOGLE_DEP_NAMES = [
    'UNKNOWN',      # Unknown
    'ABBREV',       # Abbreviation modifier
    'ACOMP',        # Adjectival complement
    'ADVCL',        # Adverbial clause modifier
    'ADVMOD',       # Adverbial modifier
    'ADVPHMOD',     # Adverbial phrase modifier
    'AMOD',         # Adjectival modifier of an NP
    'APPOS',        # Appositional modifier of an NP
    'ATTR',         # Attribute dependent of a copular verb
    'AUX',          # Auxiliary (non-main) verb
    'AUXPASS',      # Passive auxiliary
    'AUXCAUS',      # Causative auxiliary
    'AUXVV',        # Helper auxiliary
    'CC',           # Coordinating conjunction
    'CCOMP',        # Clausal complement of a verb or adjective
    'CONJ',         # Conjunct
    'COP',          # Copula
    'CSUBJ',        # Clausal subject
    'CSUBJPASS',    # Clausal passive subject
    'DEP',          # Dependency (unable to determine)
    'DET',          # Determiner
    'DISCOURSE',    # Discourse
    'DISLOCATED',   # Dislocated relation (for fronted/topicalized elements)
    'DOBJ',         # Direct object
    'DTMOD',        # Rentaishi (Prenominal modifier)
    'EXPL',         # Expletive
    'FOREIGN',      # Foreign words
    'GOESWITH',     # Goes with (part of a word in a text not well edited)
    'IOBJ',         # Indirect object
    'KW',           # Keyword
    'LIST',         # List for chains of comparable items
    'MARK',         # Marker (word introducing a subordinate clause)
    'MWE',          # Multi-word expression
    'MWV',          # Multi-word verbal expression
    'NEG',          # Negation modifier
    'NN',           # Noun compound modifier
    'NOMC',         # Nominalized clause
    'NOMCSUBJ',     # Nominalized clausal subject
    'NOMCSUBJPASS', # Nominalized clausal passive
    'NUMC',         # Compound of numeric modifier
    'NPADVMOD',     # Noun phrase used as an adverbial modifier
    'NSUBJ',        # Nominal subject
    'NSUBJPASS',    # Passive nominal subject
    'NUM',          # Numeric modifier of a noun
    'NUMBER',       # Element of compound number
    'P',            # Punctuation mark
    'PARATAXIS',    # Parataxis relation
    'PARTMOD',      # Participial modifier
    'PCOMP',        # The complement of a preposition is a clause
    'POBJ',         # Object of a preposition
    'POSS',         # Possession modifier
    'POSTNEG',      # Postverbal negative particle
    'PRECOMP',      # Predicate complement
    'PRECONJ',      # Preconjunt
    'PREDET',       # Predeterminer
    'PREF',         # Prefix
    'PREP',         # Prepositional modifier
    'PRONL',        # The relationship between a verb and verbal morpheme
    'PRT',          # Particle
    'PS',           # Associative or possessive marker
    'QUANTMOD',     # Quantifier phrase modifier
    'RCMOD',        # Relative clause modifier
    'RCMODREL',     # Complementizer in relative clause
    'RDROP',        # Ellipsis without a preceding predicate
    'REF',          # Referent
    'REMNANT',      # Remnant
    'REPARANDUM',   # Reparandum
    'ROOT',         # Root
    'SNUM',         # Suffix specifying a unit of number
    'SUFF',         # Suffix
    'SUFFIX',       # Name suffix
    'TITLE',        # Name title
    'TMOD',         # Temporal modifier
    'TOPIC',        # Topic marker
    'VMOD',         # Clause headed by an infinite form of the verb that modifies a noun
    'VOCATIVE',     # Vocative
    'XCOMP'         # Open clausal complement
]


DEP_LOWER_BOUND = 100
DEP_UPPER_BOUND = 100 - 1 + len(_GOOGLE_DEP_NAMES)


for i in range(len(_GOOGLE_DEP_NAMES)):
    exec('%s = tag.ConstantTag(%i, _GOOGLE_DEP_NAMES[%i])' % (_GOOGLE_DEP_NAMES[i], i+100, i))


TAG = {}
for i in range(len(_GOOGLE_DEP_NAMES)):
    exec('TAG[ _GOOGLE_DEP_NAMES[%i] ] = %s' % (i, _GOOGLE_DEP_NAMES[i]))



