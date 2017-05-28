# -*- coding: utf-8 -*-
"""CCG to DRS Production Generator"""

import collections
import inflect
import re
from nltk.stem import wordnet as wn

from marbles.ie.ccg import *
from marbles.ie.ccg.model import MODEL
from marbles.ie.compose import ProductionList, FunctorProduction, DrsProduction, \
    DrsComposeError, identity_functor, CO_NO_VERBNET, CO_FAST_RENAME
from marbles.ie.drt.common import DRSVar, SHOW_LINEAR
from marbles.ie.drt.drs import DRS, DRSRef, Rel, Or, Imp, DRSRelation
from marbles.ie.drt.drs import get_new_drsrefs
from marbles.ie.drt.utils import remove_dups, union, complement, intersect
from marbles.ie.kb.verbnet import VERBNETDB
from marbles.ie.parse import parse_drs
from marbles.ie.utils.vmap import VectorMap, dispatchmethod, default_dispatchmethod
from marbles.ie.doc import UnboundSentence, IndexSpan, Constituent

## @{
## @ingroup gconst
## @defgroup reftypes DRS Referent Types

RT_PROPERNAME    = 0x0000000000000001
RT_ENTITY        = 0x0000000000000002
RT_EVENT         = 0x0000000000000004
RT_LOCATION      = 0x0000000000000008
RT_DATE          = 0x0000000000000010
RT_WEEKDAY       = 0x0000000000000020
RT_MONTH         = 0x0000000000000040
RT_HUMAN         = 0x0000000000000080
RT_ANAPHORA      = 0x0000000000000100
RT_NUMBER        = 0x0000000000000200
RT_UNION         = 0x0000000000000400
RT_NEGATE        = 0x0000000000000800
RT_EVENT_MOD     = 0x0000000000001000
RT_ATTRIBUTE     = 0x0000000000002000

RT_RELATIVE      = 0x8000000000000000
RT_PLURAL        = 0x4000000000000000
RT_MALE          = 0x2000000000000000
RT_FEMALE        = 0x1000000000000000
RT_1P            = 0x0800000000000000
RT_2P            = 0x0400000000000000
RT_3P            = 0x0200000000000000
## @}




## @cond
# The pronouns must always be referent x1
__pron = [
    # 1st person singular
    ('i',       '([x1],[])',    '([],[i(x1)])', RT_HUMAN|RT_1P),
    ('me',      '([x1],[])',    '([],[i(x1),.OBJ(x1)])', RT_HUMAN|RT_1P),
    ('myself',  '([x1],[])',    '([],[i(x1),.REFLEX(x1)])', RT_HUMAN|RT_1P),
    ('mine',    '([x2],[])',    '([],[i(x1),.POSS(x1,x2)])', RT_HUMAN|RT_1P),
    ('my',      '([x2],[])',    '([],[i(x1),.POSS(x1,x2)])', RT_HUMAN|RT_1P),
    # 2nd person singular
    ('you',     '([x1],[])',    '([],[you(x1)])', RT_HUMAN|RT_2P),
    ('yourself','([x1],[])',    '([],[you(x1),.REFLEX(x1)])', RT_HUMAN|RT_2P),
    ('yours',   '([x2],[])',    '([],[you(x1),.OWN(x1,x2)])', RT_HUMAN|RT_2P),
    ('your',    '([x2],[])',    '([],[you(x1),.POSS(x1,x2)])', RT_HUMAN|RT_2P),
    # 3rd person singular
    ('he',      '([x1],[])',    '([],[he(x1)])', RT_HUMAN|RT_MALE|RT_ANAPHORA|RT_3P),
    ('she',     '([x1],[])',    '([],[she(x1)])', RT_HUMAN|RT_FEMALE|RT_ANAPHORA|RT_3P),
    ('him',     '([x1],[])',    '([],[he(x1),.OBJ(x1)])', RT_HUMAN|RT_MALE|RT_ANAPHORA|RT_3P),
    ('her',     '([x1],[])',    '([],[she(x1),.OBJ(x1)])', RT_HUMAN|RT_FEMALE|RT_ANAPHORA|RT_3P),
    ('himself', '([x1],[])',    '([],[he(x1),.REFLEX(x1)])', RT_HUMAN|RT_MALE|RT_ANAPHORA|RT_3P),
    ('herself', '([x1],[])',    '([],[she(x1),.REFLEX(x1)])', RT_HUMAN|RT_FEMALE|RT_ANAPHORA|RT_3P),
    ('hisself', '([x1],[])',    '([],[he(x1),.REFLEX(x1)])', RT_HUMAN|RT_MALE|RT_ANAPHORA|RT_3P),
    ('his',     '([x2],[])',    '([],[he(x1),.POSS(x1,x2)])', RT_HUMAN|RT_MALE|RT_ANAPHORA|RT_3P),
    ('hers',    '([x2],[])',    '([],[she(x1),.POSS(x1,x2)])', RT_HUMAN|RT_FEMALE|RT_ANAPHORA|RT_3P),
    # 1st person plural
    ('we',      '([x1],[])',    '([],[we(x1)])', RT_HUMAN|RT_PLURAL|RT_1P),
    ('us',      '([x1],[])',    '([],[we(x1),.OBJ(x1)])', RT_HUMAN|RT_PLURAL|RT_1P),
    ('ourself', '([x1],[])',    '([],[we(x1),.REFLEX(x1)])', RT_HUMAN|RT_PLURAL|RT_1P),
    ('ourselves','([x1],[])',   '([],[we(x1),.REFLEX(x1)])', RT_HUMAN|RT_PLURAL|RT_1P),
    ('ours',    '([x2],[])',    '([],[we(x1),.POSS(x1,x2)])', RT_HUMAN|RT_PLURAL|RT_1P),
    ('our',     '([x2],[])',    '([],[we(x1),.POSS(x1,x2)])', RT_HUMAN|RT_PLURAL|RT_1P),
    # 2nd person plural
    ('yourselves', '([x1],[])', '([],[([],[yourselves(x1)])->([],[you(x1)])])', RT_HUMAN|RT_PLURAL|RT_2P),
    # 3rd person plural
    ('they',    '([x1],[])',    '([],[they(x1)])', RT_HUMAN|RT_PLURAL|RT_3P),
    ('them',    '([x1],[])',    '([],[they(x1),.OBJ(x1)])', RT_HUMAN|RT_PLURAL|RT_3P),
    ('themself','([x1],[])',    '([],[they(x1),.REFLEX(x1)])', RT_HUMAN|RT_PLURAL|RT_3P),
    ('themselves','([x1],[])',  '([],[they(x1),.REFLEX(x1)])', RT_HUMAN|RT_PLURAL|RT_3P),
    ('theirs',  '([x2],[])',    '([],[they(x1),.POSS(x1,x2)])', RT_HUMAN|RT_PLURAL|RT_3P),
    ('their',   '([x2],[])',    '([],[they(x1),.POSS(x1,x2)])', RT_HUMAN|RT_PLURAL|RT_3P),
    # it
    ('it',      '([x1],[])',    '([],[it(x1)])', RT_ANAPHORA|RT_3P),
    ('its',     '([x2],[])',    '([],[it(x1),.POSS(x1,x2)])', RT_ANAPHORA|RT_3P),
    ('itself',  '([x1],[])',    '([],[it(x1),.REFLEX(x1)])', RT_ANAPHORA|RT_3P),
]
_PRON = {}
for k,r,v,u in __pron:
    _PRON[k] = (parse_drs(v, 'nltk'), u, parse_drs(r, 'nltk').universe)


# Order of referents is lambda_ref binding order
__adv = [
    ('up',      '([e1],[])', '([],[up(e1),direction(e1)])', RT_LOCATION),
    ('down',    '([e1],[])', '([],[down(e1),direction(e1)])', RT_LOCATION),
    ('left',    '([e1],[])', '([],[left(e1),direction(e1)])', RT_LOCATION),
    ('right',   '([e1],[])', '([],[right(e1),direction(e1)])', RT_LOCATION),
]
_ADV = {}
for k,r,v,u in __adv:
    _ADV[k] = (parse_drs(v, 'nltk'), u, parse_drs(r, 'nltk').universe)

# Special behavior for prepositions
_PREPS = {
    'of':           MODEL.build_template(r'PP_1002/NP_2002', construct_empty=False)[1],
    'on':           MODEL.build_template(r'PP_1002/NP_2002', construct_empty=False)[1],
}


_MONTHS = {
    'Jan':  'January',
    'Feb':  'February',
    'Mar':  'March',
    'Apr':  'April',
    'May':  'May',
    'Jun':  'June',
    'Jul':  'July',
    'Aug':  'August',
    'Sep':  'September',
    'Sept': 'September',
    'Oct':  'October',
    'Nov':  'November',
    'Dec:': 'December',
}

_WEEKDAYS = {
    'Mon':  'Monday',
    'Tue':  'Tuesday',
    'Tues': 'Tuesday',
    'Wed':  'Wednesday',
    'Thur': 'Thursday',
    'Thurs':'Thursday',
    'Fri':  'Friday',
    'Sat':  'Saturday',
    'Sun':  'Sunday'
}

# Copular verbs
_COPULAR = [
    'act', 'appear', 'be', 'become', 'bleed', 'come', 'come out', 'constitute', 'end up', 'die', 'get', 'go', 'grow',
    'fall', 'feel', 'freeze', 'keep', 'look', 'prove', 'remain', 'run', 'seem', 'shine', 'smell', 'sound', 'stay',
    'taste', 'turn', 'turn up', 'wax'
]

# To indicate time order
_TIME_ORDER = [
    'in the past', 'before', 'earlier', 'previously', 'formerly', 'yesterday', 'recently', 'not long ago',
    'at present', 'presently', 'currently', 'now', 'by now', 'until', 'today', 'immediately', 'simultaneously',
    'at the same time', 'during', 'all the while', 'in the future', 'tomorrow', 'henceforth', 'after',
    'after a short time', 'after a while', 'soon', 'later', 'later on', 'following'
]

# To indicate how or when something occurs in time
_TIME_OCCURRENCE = [
    'suddenly', 'all at once', 'instantly', 'immediately', 'quickly', 'directly', 'soon', 'as soon as', 'just then',
    'when', 'sometimes', 'some of the time', 'in the meantime', 'occasionally', 'rarely', 'seldom', 'infrequently',
    'temporarily', 'periodically', 'gradually', 'eventually', 'little by little', 'slowly', 'while', 'meanwhile',
    'always', 'all of the time', 'without exception', 'at the same time', 'repeatedly', 'often', 'frequently',
    'generally', 'usually', 'as long as', 'never', 'not at all'
]

# To indicate sequence
_SEQUENCE = [
    'first', 'in the first place', 'at first', 'once', 'once upon time', 'to begin with', 'at the beginning',
    'starting with', 'initially', 'from this point', 'earlier', 'second', 'secondly', 'in the second place', 'next',
    'the next time', 'the following week', 'then', 'after that', 'following that', 'subsequently',
    'on the next occasion', 'so far', 'later on', 'third', 'in the third place', 'last', 'last of all', 'at last',
    'at the end', 'in the end', 'final finally', 'to finish', 'to conclude', 'in conclusion', 'consequently'
]

# To repeat
_REPEAT = [
    'all in all', 'altogether', 'in brief', 'in short', 'in fact', 'in particular', 'that is', 'in simpler terms',
    'to put it differently', 'in other words', 'again', 'once more', 'again and again', 'over and over', 'to repeat',
    'as stated', 'that is to say', 'to retell', 'to review', 'to rephrase', 'to paraphrase', 'to reconsider',
    'to clarify', 'to explain', 'to outline', 'to summarize'
]

# To provide an example
_EXAMPLE = [
    'for example', 'as an example', 'for instance', 'in this case', 'to illustrate', 'to show', 'to demonstrate',
    'to explain', 'suppose that', 'specifically', 'to be exact', 'in particular', 'such as', 'namely', 'for one thing',
    'indeed', 'in other words', 'to put it in another way', 'thus'
]

# To concede
_CONCEDE = [
    'of course', 'after all', 'no doubt', 'naturally', 'unfortunately', 'while it is true', 'although this may be true',
    'although', 'to admit', 'to confess', 'to agree'
]

# To conclude or to summarize
_SUMMARIZE = [
    'to conclude', 'in conclusion', 'to close', 'last of all', 'finally', 'to end', 'to complete', 'to bring to an end',
    'thus', 'hence', 'therefore', 'as a consequence of', 'as a result', 'in short', 'to sum up', 'to summarize',
    'to recapitulate'
]

# To add a point
_POINT = [
    'also', 'too', 'as well as', 'besides', 'equally important', 'first of all', 'furthermore', 'in addition (to)',
    'moreover', 'likewise', 'above all', 'most of all', 'least of all', 'and', 'either…or', 'neither…nor', 'however',
    'yet', 'but', 'nevertheless', 'still', 'to continue'
]

# To compare
_COMPARE = [
    'As', 'as well as', 'like', 'in much the same way', 'resembling', 'parallel to', 'same as', 'identically',
    'of little difference', 'equally', 'matching', 'also', 'exactly', 'similarly', 'similar to',
    'in comparison', 'in relation to'
]

# To contrast
_CONTRAST = [
    'though', 'although', 'and yet', 'but', 'despite', 'despite this fact', 'in spite of', 'even so', 'for all that',
    'however', 'in contrast', 'by contrast', 'on one hand', 'on the other hand', 'on the contrary', 'in one way',
    'in another way', 'although this may be true', 'nevertheless', 'nonetheless', 'still', 'yet', 'to differ from',
    'a striking difference', 'another distinction', 'otherwise', 'after all', 'instead', 'unlike', 'opposite',
    'to oppose', 'in opposition to', 'versus', 'against'
]

# To emphasise or to intensify
_EMPHASIZE = [
    'above all', 'after all', 'indeed', 'as a matter of fact', 'chiefly', 'especially', 'actually',
    'more important', 'more importantly', 'most important of all', 'most of all', 'moreover', 'furthermore',
    'significantly', 'the most significant', 'more and more', 'of major interest', 'the chief characteristic',
    'the major point', 'the main problem (issue)', 'the most necessary', 'extremely', 'to emphasize', 'to highlight',
    'to stress', 'by all means', 'undoubtedly', 'without a doubt', 'certainly', 'to be sure', 'surely', 'absolutely',
    'obviously', 'to culminate', 'in truth', 'the climax of', 'to add to that', 'without question', 'unquestionably',
    'as a result'
]

# To generalize
_GENERALIZE = [
    'On the whole', 'in general', 'as a rule', 'in most cases', 'broadly speaking', 'to some extent', 'mostly'
]

# Showing our attitude to what we are saying
_ATTITUDE = [
    'Frankly', 'honestly', 'I think', 'I suppose', 'after all', 'no doubt', 'I’m afraid', 'actually',
    'as a matter of fact', 'to tell the truth', 'unfortunately'
]


# Special categories
CAT_CONJ_CONJ = Category.from_cache(r'conj\conj')
CAT_CONJCONJ = Category.from_cache(r'conj/conj')
# Transitive verb
CAT_TV = Category.from_cache(r'(S\NP)/NP')
# Ditransitive verb
CAT_DTV = Category.from_cache(r'(S\NP)/NP/NP')
# Verb phrase
CAT_VP = Category.from_cache(r'S\NP')
CAT_VPdcl = Category.from_cache(r'S[dcl]\NP')
CAT_VPb = Category.from_cache(r'S[b]\NP')
CAT_VPto = Category.from_cache(r'S[to]\NP')
# Copular verb
CAT_COPULAR = [Category.from_cache(r'(S[dcl]\NP)/(S[adj]\NP)'),
               Category.from_cache(r'(S[b]\NP)/(S[adj]\NP)')]
# CAT_AP
# Adjectival phrase
CAT_AP = Category.from_cache(r'S[adj]\NP')
# Adjectival prepositional phrase
CAT_AP_PP = Category.from_cache(r'(S[adj]\NP)/PP')
# Past participle
CAT_MODAL_PAST = Category.from_cache(r'(S[dcl]\NP)/(S[pt]\NP)')
# If then
CAT_IF_THEN = Category.from_cache(r'(S/S)/S[dcl]')

POS_POSSESSIVE = POS.from_cache('POS')
## @endcond




## @ingroup gfn
def safe_create_empty_functor(category):
    """Lookup model templates and create an empty functor. If the template
    does not exits attempt to infer from existing templates.

    Args:
        category: The functor category.

    Returns:
        A functor or None.
    """
    templ = MODEL.lookup(category)
    if templ is None:
        if category.isfunctor:
            if category != CAT_CONJ_CONJ and category != CAT_CONJCONJ:
                templ = MODEL.infer_template(category)
                if templ is not None:
                    return templ.create_empty_functor()
            else:
                return identity_functor(category)
    else:
        return templ.create_empty_functor()
    return None


## @ingroup gfn
def create_empty_drs_production(category, ref=None):
    """Return the empty DRS production `λx.[|]`.

    Args:
        category: A marbles.ie.ccg.ccgcat.Category instance.
        ref: optional DRSRef to use as the referent.

    Returns:
        A DrsProduction instance.
    """
    d = DrsProduction([], [], category=category)
    if ref is None:
        ref = DRSRef('x1')
    d.set_lambda_refs([ref])
    return d


## @ingroup gfn
def strip_apostrophe_s(word):
    """Strip trailing 's from nouns.

    Args:
        word: An ascii or utf-8 string.

    Returns:
        The stripped word.
    """
    # Must support utf-8
    if len(word) > 2:
        if word.endswith("'s"):
            return word[0:-2]
        else:
            uword = word.decode('utf-8')
            if uword.endswith(u"’s"):
                return uword.replace(u"’s", u'').encode('utf-8')
    return word


class Lexeme(object):

    _EventPredicates = ('.AGENT', '.THEME', '.EXTRA')
    _ToBePredicates = ('.AGENT', '.ATTRIBUTE', '.EXTRA')
    _TypeMonth = re.compile(r'^((Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?|January|February|March|April|June|July|August|September|October|November|December)$')
    _TypeWeekday = re.compile(r'^((Mon|Tue|Tues|Wed|Thur|Thurs|Fri|Sat|Sun)\.?|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)$')
    _Punct= '?.,:;'
    _wnl = wn.WordNetLemmatizer()
    _p = inflect.engine()

    def __init__(self, category, word, pos_tags, idx=0):

        self.head = idx
        self.dep = -1
        self.idx = idx
        self.variables = None
        self.conditions = None
        self.mask = 0
        self.refs = []
        self.wnsynsets = None
        self.vnclasses = None
        self.drs = None

        if not isinstance(category, Category):
            self.category = Category.from_cache(category)
        else:
            self.category = category
        self.pos = POS.from_cache(pos_tags[0]) if pos_tags is not None else POS_UNKNOWN

        # We treat modal as verb modifiers - i.e. they don't get their own event
        if self.pos == POS_MODAL:
            tmpcat = self.category.remove_features().simplify()
            if tmpcat.ismodifier:
                self.category = tmpcat

        if word in self._Punct:
            self.word = word
            self.stem = word
        else:
            # TODO: should lookup nouns via conceptnet or wordnet
            self.word = word
            wd = strip_apostrophe_s(word)
            if (self.category == CAT_NOUN or self.pos == POS_NOUN or self.pos == POS_NOUN_S) and wd.upper() == wd:
                # If all uppercase then keep it that way
                self.stem = word.rstrip(self._Punct)
            elif self.pos == POS_PROPER_NOUN or self.pos == POS_PROPER_NOUN_S:
                # Proper noun
                if wd.upper() == wd:
                    self.stem = word.rstrip(self._Punct)
                else:
                    self.stem = word.title().rstrip(self._Punct)
            else:
                stem = word.lower().rstrip(self._Punct)
                if self.pos in POS_LIST_VERB or self.pos == POS_GERUND:
                    # FIXME: move to python 3 so its all unicode
                    self.stem = self._wnl.lemmatize(stem.decode('utf-8'), pos='v').encode('utf-8')
                else:
                    self.stem = stem

    def __repr__(self):
        if self.drs:
            return '<Lexeme>:(%s, %s, %s)' % (self.word, self.drs.show(SHOW_LINEAR).encode('utf-8'), self.category)
        return '<Lexeme>:(%s, %s, %s)' % (self.word, self.stem, self.category)

    @property
    def ispunct(self):
        """Test if the word attached to this lexeme is a punctuation mark."""
        return self.pos in POS_LIST_PUNCT

    @property
    def ispronoun(self):
        """Test if the word attached to this lexeme is a pronoun."""
        return (self.pos in POS_LIST_PRONOUN)  # or self._word in _PRON

    @property
    def ispreposition(self):
        """Test if the word attached to this lexeme is a preposition."""
        return self.category == CAT_PREPOSITION

    @property
    def isadverb(self):
        """Test if the word attached to this lexeme is an adverb."""
        return self.category == CAT_ADVERB

    @property
    def isverb(self):
        """Test if the word attached to this lexeme is a verb."""
        # Verbs can behave as adjectives
        return (self.pos in POS_LIST_VERB and self.category != CAT_ADJECTIVE) or \
               (self.category.result_category() == CAT_VPdcl and not self.category.ismodifier)

    @property
    def isgerund(self):
        """Test if the word attached to this lexeme is a gerund."""
        return self.pos == POS_GERUND

    @property
    def isproper_noun(self):
        """Test if the word attached to this lexeme is a proper noun."""
        return self.pos == POS_PROPER_NOUN or self.pos == POS_PROPER_NOUN_S

    @property
    def isnumber(self):
        """Test if the word attached to this lexeme is a number."""
        return self.pos == POS_NUMBER

    @property
    def isadjective(self):
        """Test if the word attached to this lexeme is an adjective."""
        return self.category == CAT_ADJECTIVE

    def get_template(self):
        """Get the functor template for the lexeme.

        Returns:
            A marbles.ie.ccg.model.FunctorTemplate instance or None if the self.category is an atom or a simple
            functor. Simple functors are functors where the argument and result categories are both atoms.

        Raises:
            DrsComposeError
            
        See Also:
            marbles.ie.ccg.category.Category
        """
        if self.category.isfunctor and self.category != CAT_CONJ_CONJ and self.category != CAT_CONJCONJ:
            try:
                # Special handling for prepositions
                if self.category == CAT_PREPOSITION and self.word in _PREPS:
                    template = _PREPS[self.word]
                else:
                    template = MODEL.lookup(self.category)
            except Exception:
                template = MODEL.infer_template(self.category)
                # Simple functors are not templated.
                if template is None and (self.category.result_category().isfunctor or
                                             self.category.argument_category().isfunctor):
                    raise DrsComposeError('CCG type "%s" for word "%s" maps to unknown DRS production' %
                                          (self.category, self.word))
            return template
        return None

    def _build_conditions(self, conds, refs, template):
        """Refs are reversed, refs[0] is the functor return value.

        Args:
            conds: The existing DRS conditions.
            refs: The referents, where refs[0] is the functor return value.
            template: A FunctorTemplate instance.

        Returns:
            The modified conditions.
        """

        # Note. Proper noun handling requires any extra predicates appear after the noun.
        if self.isproper_noun:
            # If we are a functor and a proper noun then argument type if the
            # correct referent for the noun
            if self._TypeMonth.match(self.stem):
                self.mask |= RT_DATE
                if self.stem in _MONTHS:
                    conds.append(Rel(_MONTHS[self.stem], [self.refs[0]]))
                else:
                    conds.append(Rel(self.stem, [self.refs[0]]))
                if template.isfinalevent:
                    conds.append(Rel('.DATE', self.refs[0:2]))
                else:
                    conds.append(Rel('.DATE', self.refs))
            elif self._TypeWeekday.match(self.stem):
                self.mask |= RT_DATE
                if self.stem in _WEEKDAYS:
                    conds.append(Rel(_WEEKDAYS[self.stem], [self.refs[0]]))
                else:
                    conds.append(Rel(self.stem, [self.refs[0]]))
                if template.isfinalevent:
                    conds.append(Rel('.DATE', self.refs[0:2]))
                else:
                    conds.append(Rel('.DATE', self.refs))
            else:
                conds.append(Rel(self.stem, [self.refs[0]]))
        elif self.isnumber:
            self.mask |= RT_NUMBER
            conds.append(Rel(self.stem, [self.refs[0]]))
            conds.append(Rel('.NUM', self.refs))
        elif self.pos == POS_PREPOSITION and not self.ispreposition:
            conds.append(Rel(self.stem, self.refs))
        else:
            conds.append(Rel(self.stem, [self.refs[0]]))
        return conds

    def _copy_production_from_sample(self, sample, span):
        # Deepcopy but ensure variables only get one python reference - makes renaming fast
        self.mask |= sample[1]
        ovrs = set(sample[0].freerefs).union(sample[0].referents)
        nvrs = {}
        for x in ovrs:
            nvrs[x.var.to_string()] = DRSRef(DRSVar(x.var.name, x.var.idx))
        conds = []
        for c in sample[0].conditions:
            assert isinstance(c, Rel)
            conds.append(Rel(c.relation, map(lambda x: nvrs[x.var.to_string()], c.referents)))
        refs = map(lambda x: nvrs[x.var.to_string()], sample[0].referents)
        self.drs = DRS(refs, conds)
        self.refs = [v for k, v in nvrs]
        d = DrsProduction(self.drs.universe, self.drs.freerefs, span=span)
        d.set_lambda_refs(map(lambda x: nvrs[x.var.to_string()], sample[2]))
        #self.refs = d.variables
        return d

    def _get_noun_drs(self, span):
        if not self.isproper_noun and not self.pos == POS_POSSESSIVE:
            # TODO: cache nouns
            # pattern.en.pluralize(self.stem)
            # or use inflect https://pypi.python.org/pypi/inflect
            if self.stem == "'s":
                pass
            sp = self._p.plural(self.stem)
            self.wnsynsets = wn.wordnet.synsets(self._wnl.lemmatize(self.stem.lower(), 'n'), pos='n')
            if False and self.stem != sp:
                rp = DRSRef(DRSVar('x', len(self.refs)+1))
                self.drs = DRS([self.refs[0], rp],
                               [Rel(self.stem, [self.refs[0]]), Rel(sp, [rp]), Rel('.ISMEMBER', [self.refs[0], rp])])
                d = DrsProduction([self.refs[0], rp], self.refs[1:], category=self.category, span=span)
                d.set_lambda_refs([self.refs[0]])
                return d

        self.drs = DRS([self.refs[0]], [Rel(self.stem, [self.refs[0]])])
        d = DrsProduction([self.refs[0]], self.refs[1:], category=self.category, span=span)
        d.set_lambda_refs([self.refs[0]])
        return d

    def get_production(self, sentence, options=0):
        """Get the production model for this category.

        Returns:
            A Production instance.
        """
        no_vn = 0 != (CO_NO_VERBNET & options)
        span = IndexSpan(sentence, [self.idx])
        template = self.get_template()

        # Ensure we only have one instance for each referent name. FunctorTemplate's guarantee
        # this. This allows fast renaming by changing the DRSVar embedded in the DRSRef.
        #
        # To take advantage of fast renaming we need to do one rename post functor creation
        # since template DRSRefs are global and we never want to modify these.

        if template is None:
            # Simple type
            # Handle prepositions
            if self.category in [CAT_CONJ, CAT_NPthr]:
                self.refs = [DRSRef(DRSVar('x', 1))]
                if self.stem == 'or':
                    self.mask |= RT_UNION
                elif self.stem == 'nor':
                    self.mask |= RT_UNION | RT_NEGATE
                return create_empty_drs_production(self.category, self.refs[0])
            elif self.category in [CAT_CONJ_CONJ, CAT_CONJCONJ]:
                self.refs = [DRSRef(DRSVar('x', 1))]
                return identity_functor(self.category, self.refs[0])
            elif self.ispronoun and self.stem in _PRON:
                d = self._copy_production_from_sample(_PRON[self.stem], span)
                d.set_category(self.category)
                return d
            elif self.category == CAT_N:
                self.refs = [DRSRef(DRSVar('x', 1))]
                if self.isproper_noun:
                    self.mask |= RT_PROPERNAME
                elif self.pos == POS_NOUN_S:
                    self.mask |= RT_ENTITY | RT_PLURAL
                else:
                    self.mask |= RT_ENTITY
                return self._get_noun_drs(span)
            elif self.category == CAT_NOUN:
                self.refs = [DRSRef(DRSVar('x', 1))]
                if self.isnumber:
                    self.mask |= RT_NUMBER
                elif self.pos == POS_NOUN_S:
                    self.mask |= RT_ENTITY | RT_PLURAL
                else:
                    self.mask |= RT_ENTITY
                return self._get_noun_drs(span)
            elif self.category == CAT_CONJ_CONJ or self.category == CAT_CONJCONJ:
                self.refs = [DRSRef(DRSVar('x', 1))]
                return create_empty_drs_production(CAT_CONJ, self.refs[0])
                #return identity_functor(self.category)
            elif self.isadverb and self.stem in _ADV:
                d = self._copy_production_from_sample(_ADV[self.stem], span)
                d.set_category(self.category)
                return d
            else:
                self.refs = [DRSRef(DRSVar('x', 1))]
                self.drs = DRS([], [Rel(self.stem, [self.refs[0]])])
                d = DrsProduction([], self.refs, category=self.category, span=span)
                d.set_lambda_refs([self.refs[0]])
                return d

        # else is functor

        # Production templates use tuples so we don't accidentally modify.
        if self.category == CAT_NP_N:    # NP*/N class
            # Ignore template in these cases
            # FIXME: these relations should be added as part of _build_conditions()
            if self.ispronoun and self.stem in _PRON:
                d = self._copy_production_from_sample(_PRON[self.stem], span)
                d.set_category(CAT_NP)
                return FunctorProduction(self.category, d.lambda_refs, d)

            else:
                nref = DRSRef(DRSVar('x', 1))
                self.refs = [nref]
                if self.category == CAT_DETERMINER:
                    if self.stem in ['a', 'an']:
                        self.drs = DRS([], [Rel('.MAYBE', [nref])])
                        fn = DrsProduction([], [nref], category=CAT_NP, span=span)
                    elif self.stem in ['the', 'thy']:
                        self.drs = DRS([], [Rel('.EXISTS', [nref])])
                        fn = DrsProduction([], [nref], category=CAT_NP, span=span)
                    else:
                        self.drs = DRS([], [Rel(self.stem, [nref])])
                        fn = DrsProduction([], [nref], category=CAT_NP, span=span)
                elif self.pos == POS_DETERMINER and self.stem in ['the', 'thy', 'a', 'an']:
                    fn = DrsProduction([], [], category=CAT_NP, span=span)
                else:
                    self.drs = DRS([], [Rel(self.stem, [nref])])
                    fn = DrsProduction([], [nref], category=CAT_NP, span=span)
                fn.set_lambda_refs([nref])
            return FunctorProduction(category=self.category, referent=nref, production=fn)

        else:
            compose = None if template is None else template.constructor_rule
            refs = []
            rule_map = template.create_constructor_rule_map()
            rstk = []
            lstk = []
            argcat = self.category
            for c in compose:
                stk = lstk if argcat.isarg_left else rstk
                if isinstance(c[1], tuple):
                    stk.extend([rule_map[x] for x in c[1]])
                else:
                    stk.append(rule_map[c[1]])
                argcat = argcat.result_category()

            refs.append(rule_map[template.final_ref])
            refs.extend(reversed(lstk))
            refs.extend(rstk)
            refs = remove_dups(refs)
            final_atom = template.final_atom.remove_wildcards()
            final_ref = refs[0]
            self.refs = refs

            # Verbs can also be adjectives so check event
            isverb = self.isverb
            if self.isgerund:
                result = self.category
                while not isverb and not result.isatom:
                    isverb = result.can_unify(CAT_TV)
                    result = result.result_category()
                    # TODO: Add predicate for NG or change predarg attachments

            if isverb and template.isfinalevent:
                conds = []
                vncond = None
                try:
                    vnclasses = [] if no_vn else VERBNETDB.name_index[self.stem]
                    if len(vnclasses) == 1:
                        vncond = Rel('.VN.' + vnclasses[0].ID.encode('utf-8'), [refs[0]])
                    elif len(vnclasses) >= 2:
                        xconds = [Rel('.VN.' + vnclasses[-1].ID.encode('utf-8'), [refs[0]])] \
                            if len(vnclasses) & 0x1 else []

                        # TODO: for vn classes A,B,C should really have (A&!B&!C)|(!A&B&!C)|(!A&!B&C)
                        for vna, vnb in zip(vnclasses[0::2],vnclasses[1::2]):
                            xconds.append(Or(DRS([], [Rel('.VN.' + vna.ID.encode('utf-8'), [refs[0]])]),
                                             DRS([], [Rel('.VN.' + vnb.ID.encode('utf-8'), [refs[0]])])))
                        while len(xconds) != 1:
                            c2 = xconds.pop()
                            c1 = xconds.pop()
                            xconds.append(Or(DRS([], [c1]), DRS([], [c2])))
                        vncond = xconds[0]
                        xconds = None

                    if vncond is not None:
                        # Add implication
                        conds.append(Imp(DRS([], [Rel(self.stem, [refs[0]])]), DRS([], [vncond])))
                    else:
                        conds.append(Rel(self.stem, [refs[0]]))

                except Exception:
                    conds.append(Rel(self.stem, [refs[0]]))
                    pass
                if (self.category.iscombinator and self.category.has_any_features(FEATURE_PSS | FEATURE_TO)) \
                        or self.category.ismodifier:

                    if not self.category.ismodifier and self.category.has_all_features(FEATURE_TO | FEATURE_DCL):
                        conds.append(Rel('.EVENT', [refs[0]]))
                        self.vnclasses = vnclasses

                    # passive case
                    if len(refs) > 1:
                        self.mask |= RT_EVENT_MOD
                        conds.append(Rel('.MOD', [refs[0], refs[-1]]))

                    self.drs = DRS([], conds)
                    d = DrsProduction([], self.refs, span=span)

                elif self.category == CAT_MODAL_PAST:
                    self.mask |= RT_EVENT_MOD
                    conds.append(Rel('.MODAL', [refs[0]]))
                    self.drs = DRS([], conds)
                    d = DrsProduction([], self.refs, span=span)

                elif self.category in CAT_COPULAR:
                    if len(refs) != 3:
                        pass
                    assert len(refs) == 3, "copular expects 3 referents"

                    # Special handling
                    self.mask |= RT_EVENT
                    self.vnclasses = vnclasses
                    if self.stem == 'be':
                        # Discard conditions
                        conds.extend([Rel('.EVENT', [refs[0]]), Rel('.AGENT', [refs[0], refs[1]]),
                                      Rel('.ROLE', [refs[0], refs[2]])])

                    else:
                        conds.append(Rel('.EVENT', [refs[0]]))
                        conds.append(Rel('.AGENT', [refs[0], refs[1]]))
                        conds.append(Rel('.ROLE', [refs[0], refs[2]]))
                    self.drs = DRS([refs[0]], conds)
                    d = DrsProduction([refs[0]], refs[1:], category=final_atom, span=span)
                elif self.category == CAT_VPdcl:
                    if len(refs) != 2:
                        pass
                    assert len(refs) == 2, "VP[dcl] expects 2 referents"

                    conds.append(Rel('.EVENT', [refs[0]]))
                    conds.append(Rel('.AGENT', [refs[0], refs[1]]))
                    self.mask |= RT_EVENT
                    self.vnclasses = vnclasses

                    # Special handling
                    self.drs = DRS([refs[0]], conds)
                    d = DrsProduction([refs[0]], self.refs[1:], category=final_atom, span=span)

                else:
                    # TODO: use verbnet to get semantics
                    self.mask |= RT_EVENT
                    self.vnclasses = vnclasses
                    if self.stem == 'be' and self.category.can_unify(CAT_TV):
                        # Discard conditions
                        conds.extend([Rel('.EVENT', [refs[0]]), Rel('.AGENT', [refs[0], refs[1]]),
                                      Rel('.ROLE', [refs[0], refs[2]])])
                        sentence.attributes.append((refs[2], refs[1]))
                    else:
                        conds.append(Rel('.EVENT', [refs[0]]))
                        pred = zip(refs[1:], self._EventPredicates)
                        for v, e in pred:
                            conds.append(Rel(e, [refs[0], v]))
                        if (len(refs)-1) > len(pred):
                            rx = [refs[0]]
                            rx.extend(refs[len(pred)+1:])
                            conds.append(Rel('.EXTRA', rx))
                    self.drs = DRS([refs[0]], conds)
                    d = DrsProduction([refs[0]], refs[1:], span=span)

            elif self.isadverb and template.isfinalevent:
                if self.stem in _ADV:
                    d = self._copy_production_from_sample(_ADV[self.stem], span)
                    rs = zip(d.variables, refs)
                    d.rename_vars(rs)
                else:
                    self.drs = DRS([], [Rel(self.stem, refs[0])])
                    d = DrsProduction([], self.refs, span=span)

            #elif self.pos == POS_DETERMINER and self.stem == 'a':

            elif self.ispronoun and self.stem in _PRON:
                pron = _PRON[self.stem]
                d = self._copy_production_from_sample(pron, span)
                ers = complement(d.variables, pron[2])
                ors = intersect(refs, ers)
                if len(ors) != 0:
                    # Make disjoint
                    nrs = get_new_drsrefs(ors, union(ers, refs, pron[2]))
                    d.rename_vars(zip(ors, nrs))
                if len(ers) != 0:
                    ers = complement(d.variables, pron[2])
                    d.rename_vars(zip([pron[2][0], ers[0]], refs))
                else:
                    d.rename_vars([(pron[2][0], final_ref)])

            elif self.ispreposition:
                if template.construct_empty:
                    d = DrsProduction([], [], span=span)
                else:
                    self.drs = DRS([], [Rel(self.stem, refs)])
                    d = DrsProduction([], self.refs, span=span)

            elif self.pos == POS_PREPOSITION and self.category.test_returns_modifier() \
                    and len(refs) > 1 and not self.category.ismodifier:
                self.drs = DRS([], [Rel(self.stem, [refs[0], refs[-1]])])
                d = DrsProduction([], self.refs, span=span)

            elif final_atom == CAT_Sadj and len(refs) > 1:
                if self.category == CAT_AP_PP or self.category.ismodifier or \
                        self.category.test_returns_modifier():
                    self.drs = DRS([], [Rel(self.stem, refs[0])])
                    d = DrsProduction([], self.refs, span=span)
                else:
                    self.mask |= RT_ATTRIBUTE
                    for r in refs[1:]:
                        sentence.attributes.append((r, refs[0]))
                    self.drs = DRS([], [Rel(self.stem, refs[0])])
                    d = DrsProduction([], self.refs, span=span)

            else:
                if self.isproper_noun:
                    self.mask |= RT_PROPERNAME
                elif final_atom == CAT_N and not self.category.ismodifier \
                        and not self.category.test_returns_modifier():
                    self.mask |= (RT_ENTITY | RT_PLURAL) if self.pos == POS_NOUN_S else RT_ENTITY
                elif len(self.refs) == 1 and final_atom == CAT_N \
                    and (self.category.ismodifier or self.category.test_returns_modifier()):
                    self.mask |= RT_ATTRIBUTE

                if template.isfinalevent:
                    if self.category == CAT_INFINITIVE:
                        d = DrsProduction([], [], span=span)
                    elif self.pos == POS_MODAL:
                        self.mask |= RT_EVENT_MOD
                        self.drs = DRS([], [Rel(self.stem, [refs[0]]), Rel('.MODAL', [refs[0]])])
                        d = DrsProduction([], self.refs, span=span)
                    else:
                        self.drs = DRS([], self._build_conditions([], refs, template))
                        d = DrsProduction([], self.refs, span=span)
                else:
                    self.drs = DRS([], self._build_conditions([], refs, template))
                    d = DrsProduction([], self.refs, span=span)

            d.set_lambda_refs([final_ref])
            d.set_category(final_atom)
            fn = template.create_functor(rule_map, d)
            return fn


class AbstractOperand(object):

    def __init__(self, idx, depth):
        self.idx = idx
        self.depth = depth

    @property
    def category(self):
        raise NotImplementedError


class PushOp(AbstractOperand):

    def __init__(self, lexeme, idx, depth):
        super(PushOp, self).__init__(idx, depth)
        self.lexeme = lexeme

    def __repr__(self):
        return '<PushOp>:(%s, %s, %s)' % (self.lexeme.stem, self.lexeme.category, self.lexeme.pos)

    @property
    def category(self):
        return self.lexeme.category


class ExecOp(AbstractOperand):

    def __init__(self, idx, sub_ops, head, result_category, rule, lex_range, op_range, depth):
        super(ExecOp, self).__init__(idx, depth)
        self.rule = rule
        self.result_category = result_category
        self.sub_ops = sub_ops
        self.head = head
        self.lex_range = lex_range
        self.op_range = op_range

    def __repr__(self):
        return '<ExecOp>:(%d, %s %s)' % (len(self.sub_ops), self.rule, self.category)

    @property
    def category(self):
        return self.result_category


CcgArgSep = re.compile(r'/|\\')
TType = re.compile(r'((?:[()/\\]|(?:(?:S|NP|N)(?:\[[Xa-z]+\])?)|conj|[A-Z]+\$?|-[A-Z]+-)*)')
LPosType = re.compile(r'([A-Z$:-]+|[.,:;])(?=\s+[^>\s]+\s+[^>\s]+(?:\s|[>]))')
LWord = re.compile(r'[^>\s]+(?=\s)')
CcgComplexTypeBegin = re.compile(r'([()/\\]|(?:(?:S|NP|N)(?:\[[Xa-z]+\])?)|conj|[A-Z]+|[.,:;])+(?=\s)')
CcgComplexTypeEnd = re.compile(r'([()/\\]|(?:(?:S|NP|N)(?:\[[Xa-z]+\])?)|conj|[A-Z]+|[.,:;]|_\d+)+(?=[>])')
PosInt = re.compile(r'\d+')


class Ccg2Drs(UnboundSentence):
    """CCG to DRS Converter"""
    dispatchmap = VectorMap(Rule.rule_count())
    debugcount = 0

    def __init__(self, options=0):
        self.xid = 10
        self.eid = 10
        self.limit = 10
        self.options = options or 0
        self.exeque = []
        self.lexque = []
        self.depth = -1
        self.final_prod = None
        self.constituents = []

    def __len__(self):
        # Required by UnboundSentence
        return len(self.lexque)

    def at(self, i):
        """Get the lexeme at index i."""
        # Required by UnboundSentence
        return self.lexque[i]

    def get_constituents(self):
        """Get the constituents."""
        # Required by UnboundSentence
        return self.constituents

    def get_constituent_at(self, i):
        """Get the constituent at index i."""
        # Required by UnboundSentence
        return self.constituents[i]

    @dispatchmethod(dispatchmap, RL_TCL_UNARY)
    def _dispatch_lunary(self, op, stk):
        if len(op.sub_ops) == 2:
            assert len(stk) >= 2
            unary = MODEL.lookup_unary(op.category, op.sub_ops[0].category)
            if unary is None and op.category.ismodifier and op.category.result_category() == op.sub_ops[0].category:
                unary = MODEL.infer_unary(op.category)
            assert unary is not None
            fn = self.rename_vars(unary.get())
            fn.set_options(self.options)
            d2 = stk.pop()
            d1 = stk.pop()
            stk.append(d1)
            self._dispatch_ba(op, stk)

            nlst = ProductionList()
            nlst.set_options(self.options)
            nlst.set_category(op.category)
            nlst.push_right(stk.pop())
            nlst.push_right(d2)
            stk.append(nlst.flatten().unify())
        else:
            unary = MODEL.lookup_unary(op.category, op.sub_ops[0].category)
            if unary is None and op.category.ismodifier and op.category.result_category() == op.sub_ops[0].category:
                unary = MODEL.infer_unary(op.category)
            assert unary is not None
            fn = self.rename_vars(unary.get())
            fn.set_options(self.options)
            stk.append(fn)
            self._dispatch_ba(op, stk)

    @dispatchmethod(dispatchmap, RL_TCR_UNARY)
    def _dispatch_runary(self, op, stk):
        assert len(op.sub_ops) == 2
        assert len(stk) >= 2
        unary = MODEL.lookup_unary(op.category, op.sub_ops[1].category)
        if unary is None and op.category.ismodifier and op.category.result_category() == op.sub_ops[1].category:
            unary = MODEL.infer_unary(op.category)
        # TODO: remove debug code below
        '''
        if unary is None:
            pass
        '''
        assert unary is not None
        fn = self.rename_vars(unary.get())
        fn.set_options(self.options)
        stk.append(fn)
        self._dispatch_ba(op, stk)

        nlst = ProductionList()
        nlst.set_options(self.options)
        nlst.set_category(op.category)
        nlst.push_right(stk.pop())
        nlst.push_right(stk.pop())
        stk.append(nlst.flatten().unify())

    @dispatchmethod(dispatchmap, RL_TC_CONJ)
    def _dispatch_tcconj(self, op, stk):
        # Special type change rules. See section 3.7-3.8 of LDC 2005T13 manual.
        # These rules are required to process the CCG conversion of the Penn Treebank.
        # They are not required for EasySRL or EasyCCG.
        if len(op.sub_ops) == 2:
            fn = self.rename_vars(safe_create_empty_functor(op.category))
            if op.sub_ops[0].category == CAT_CONJ:
                vp_or_np = stk.pop()
                d = stk.pop()
            else:
                d = stk.pop()
                vp_or_np = stk.pop()

            nlst = ProductionList()
            nlst.push_right(fn.type_change_np_snp(vp_or_np))
            nlst.push_right(d)
            nlst.set_options(self.options)
            nlst.set_category(op.category)
            stk.append(nlst.flatten().unify())
        else:
            fn = self.rename_vars(safe_create_empty_functor(op.category))
            vp_or_np = stk.pop()
            stk.append(fn.type_change_np_snp(vp_or_np))

    @dispatchmethod(dispatchmap, RL_TC_ATOM)
    def _dispatch_tcatom(self, op, stk):
        assert len(op.sub_ops) == 1
        # Special rule to change atomic type
        fn = self.rename_vars(identity_functor(Category.combine(op.category, '\\', stk[-1].category)))
        fn.set_options(self.options)
        stk.append(fn)
        self._dispatch_ba(op, stk)  # backward application

    @dispatchmethod(dispatchmap, RL_TYPE_RAISE)
    def _dispatch_typeraise(self, op, stk):
        ## Forward   X:np => T/(T\X): λxf.f(np)
        ## Backward  X:np => T\(T/X): λxf.f(np)
        assert len(op.sub_ops) == 1
        f = self.rename_vars(safe_create_empty_functor(op.category))
        g = stk.pop()
        stk.append(f.type_raise(g))

    @dispatchmethod(dispatchmap, RL_FA)
    def _dispatch_fa(self, op, stk):
        # Forward application.
        d = stk.pop()   # arg1
        fn = stk.pop()  # arg0
        stk.append(self._update_constituents(fn.apply(d)))

    @dispatchmethod(dispatchmap, RL_BA)
    def _dispatch_ba(self, op, stk):
        # Backward application.
        fn = stk.pop()   # arg1
        d = stk.pop()    # arg0
        stk.append(self._update_constituents(fn.apply(d)))

    @dispatchmethod(dispatchmap, RL_FC, RL_FX)
    def _dispatch_fc(self, op, stk):
        # CALL[X/Y](Y|Z)
        # Forward Composition           X/Y:f Y/Z:g => X/Z: λx􏰓.f(g(x))
        # Forward Crossing Composition  X/Y:f Y\Z:g => X\Z: λx􏰓.f(g(x))
        g = stk.pop()   # arg1
        f = stk.pop()   # arg0
        stk.append(f.compose(g))

    @dispatchmethod(dispatchmap, RL_GFC, RL_GFX)
    def _dispatch_gfc(self, op, stk):
        # CALL[X/Y](Y|Z)$
        # Generalized Forward Composition           X/Y:f (Y/Z)/$ => (X/Z)/$
        # Generalized Forward Crossing Composition  X/Y:f (Y\Z)$: => (X\Z)$
        g = stk.pop()   # arg1
        f = stk.pop()   # arg0
        stk.append(f.generalized_compose(g))

    @dispatchmethod(dispatchmap, RL_BC, RL_BX)
    def _dispatch_bc(self, op, stk):
        # CALL[X\Y](Y|Z)
        # Backward Composition          Y\Z:g X\Y:f => X\Z: λx􏰓.f(g(x))
        # Backward Crossing Composition Y/Z:g X\Y:f => X/Z: λx􏰓.f(g(x))
        f = stk.pop()
        g = stk.pop()
        stk.append(f.compose(g))

    @dispatchmethod(dispatchmap, RL_GBC, RL_GBX)
    def _dispatch_gbc(self, op, stk):
        # CALL[X\Y](Y|Z)$
        # Generalized Backward Composition          (Y\Z)$  X\Y:f => (X\Z)$
        # Generalized Backward Crossing Composition (Y/Z)/$ X\Y:f => (X/Z)/$
        f = stk.pop()
        g = stk.pop()
        stk.append(f.generalized_compose(g))

    @dispatchmethod(dispatchmap, RL_FS, RL_FXS)
    def _dispatch_fs(self, op, stk):
        # CALL[(X/Y)|Z](Y|Z)
        # Forward Substitution          (X/Y)/Z:f Y/Z:g => X/Z: λx􏰓.fx􏰨(g􏰨(x􏰩􏰩))
        # Forward Crossing Substitution (X/Y)\Z:f Y\Z:g => X\Z: λx􏰓.fx􏰨(g􏰨(x􏰩􏰩))
        g = stk.pop()   # arg1
        f = stk.pop()   # arg0
        stk.append(f.substitute(g))

    @dispatchmethod(dispatchmap, RL_BS, RL_BXS)
    def _dispatch_bs(self, op, stk):
        # CALL[(X\Y)|Z](Y|Z)
        # Backward Substitution             Y\Z:g (X\Y)\Z:g => X/Z: λx􏰓.fx􏰨(g􏰨(x􏰩􏰩))
        # Backward Crossing Substitution    Y/Z:g (X\Y)/Z:f => X/Z: λx􏰓.fx􏰨(g􏰨(x􏰩􏰩))
        f = stk.pop()   # arg1
        g = stk.pop()   # arg0
        stk.append(f.substitute(g))

    @dispatchmethod(dispatchmap, RL_LCONJ, RL_RCONJ)
    def _dispatch_conj(self, op, stk):
        # Conjoin of like types.
        g = stk.pop()
        f = stk.pop()
        if f.isfunctor:
            stk.append(f.conjoin(g, False))
        elif g.isfunctor:
            stk.append(g.conjoin(f, True))
        else:
            d = ProductionList(f)
            d.push_right(g)
            d = d.unify()
            stk.append(d)
            d.set_category(f.category)

    @dispatchmethod(dispatchmap, RL_RPASS, RL_LPASS, RL_RNUM)
    def _dispatch_pass(self, op, stk):
        d = ProductionList()
        d.set_options(self.options)
        d.set_category(op.category)
        for i in range(len(op.sub_ops)):
            d.push_left(stk.pop())
        if d.contains_functor:
            # Bit of a hack, flatten() gets rid of empty productions
            stk.append(self._update_constituents(d.flatten().unify()))
        else:
            stk.append(self._update_constituents(d.unify()))

    @default_dispatchmethod(dispatchmap)
    def _dispatch_default(self, op, stk):
        # All rules must have a handler
        assert False

    def _dispatch(self, op, stk):
        """Dispatch a rule.

        Args:
            op: The ExecOp. The dispatch is based on op.rule.
            stk. The execution stack.
        """
        method = self.dispatchmap.lookup(op.rule)
        method(self, op, stk)

    def _update_constituents(self, d):
        if isinstance(d, (FunctorProduction, DrsProduction)):
            if d.category == CAT_NP:
                refs = set()
                for lex in d.span:
                    refs = refs.union(lex.refs)
                vntype = Constituent.vntype_from_category(d.category) if len(refs) == 1 else None
            else:
                vntype = Constituent.vntype_from_category(d.category)

            if vntype is not None:
                if vntype != 'ADJP' and d.category.extract_unify_atoms(False)[-1] == CAT_Sany:
                    # TODO: move identification of event constituents to post compose_drs()
                    r = d.get_unify_scopes(False)[-1]
                    span = IndexSpan(d.span.sentence)
                    for lex in d.span:
                        if 0 != (lex.mask & (RT_EVENT | RT_EVENT_MOD)):
                            span.add(lex.idx)
                    assert len(span) != 0
                    c = Constituent(d.category, span, vntype)
                else:
                    c = Constituent(d.category, d.span, vntype)

                while len(self.constituents) != 0 and self.constituents[-1].vntype == c.vntype \
                        and self.constituents[-1] in c:
                    self.constituents.pop()
                self.constituents.append(c)
        return d

    def create_drs(self):
        """Create a DRS from the execution queue. Must call build_execution_sequence() first."""
        # First create all productions up front
        prods = [None] * len(self.lexque)
        for i in range(len(self.lexque)):
            lexeme = self.lexque[i]
            if lexeme.category.ispunct:
                prod = DrsProduction([], [], category=lexeme.category, span=IndexSpan(self))
                prod.set_lambda_refs([DRSRef(DRSVar('x', self.xid+1))])
                self.xid += 1
                prod.set_options(self.options)
            elif lexeme.category in [CAT_LRB, CAT_RRB, CAT_LQU, CAT_RQU]:
                prod = DrsProduction([], [], category=CAT_EMPTY, span=IndexSpan(self))
                prod.set_lambda_refs([DRSRef(DRSVar('x', self.xid+1))])
                self.xid += 1
            else:
                prod = self.rename_vars(lexeme.get_production(self, self.options))
            prod.set_options(self.options)
            prods[i] = prod
        # TODO: Defer special handling of proper nouns

        # Process exec queue
        stk = []
        for op in self.exeque:
            if isinstance(op, PushOp):
                stk.append(prods[op.lexeme.idx])
            else:
                # ExecOp dispatch based on rule
                self._dispatch(op, stk)

            # TODO: remove debug code
            '''
            if op.category.get_scope_count() != stk[-1].get_scope_count():
                pass

            if not stk[-1].verify():
                stk[-1].verify()
                pass

            if not stk[-1].category.can_unify(op.category):
                stk[-1].category.can_unify(op.category)
                pass
            '''
            assert stk[-1].verify() and stk[-1].category.can_unify(op.category)
            assert op.category.get_scope_count() == stk[-1].get_scope_count(), "result-category=%s, prod=%s" % \
                                                                               (op.category, stk[-1])
        # Get final DrsProduction
        assert len(stk) == 1
        d = stk[0]
        if d.isfunctor and d.isarg_left and d.category.argument_category().isatom:
            d = d.apply_null_left().unify()
        self.final_prod = d

        # Finalize constituents
        for c in self.constituents:
            result = c.search_wikipedia()
            if result is not None:
                subspan = c.span.get_subspan_from_wiki_search(result)
                if subspan == c.span:
                    c.set_wiki_entry(result)
        self.constituents = sorted(self.constituents)
        # If a constituent head and its category is N/N or a noun modifier and it is an RT_ATTRIBUTE
        # then all direct descendents are also attributes
        for c in self.constituents:
            hd = c.get_head()
            if 0 != (hd.mask & RT_ATTRIBUTE) and (hd.category in [CAT_ADJECTIVE, CAT_AP]
                                                  or hd.category.test_returns_entity_modifier()):
                for lex in c.span:
                    lex.mask |= RT_ATTRIBUTE

    def get_vn_frames(self):
        i2c = {}
        attribs = set()
        # find head of the constituents
        for c in self.constituents:
            hd = c.get_head()
            i2c[hd.idx] = c
            if 0 != (hd.mask & RT_ATTRIBUTE):
                attribs.add(hd.idx)
        # If a head is an RT_ATTRIBUTE then all direct NP descendents are also attributes

    def resolve_proper_names(self):
        """Merge proper names."""

        # find spans of nouns with same referent
        spans = []
        lastref = DRSRef('$$$$')
        startIdx = -1
        endIdx = -1
        for i in range(len(self.lexque)):
            lexeme = self.lexque[i]
            if lexeme.refs is None or len(lexeme.refs) == 0:
                ref = DRSRef('$$$$')
            else:
                ref = lexeme.refs[0]

            if startIdx >= 0:
                if ref == lastref and (lexeme.isproper_noun or lexeme.category == CAT_N or \
                        (lexeme.word == '&' and (i+1) < len(self.lexque) and self.lexque[i+1].isproper_noun)):
                    endIdx = i
                    continue
                else:
                    if startIdx != endIdx:
                        spans.append((startIdx, endIdx))
                    startIdx = -1

            if lexeme.isproper_noun:
                startIdx = i
                endIdx = i
                lastref = ref

        if startIdx >= 0:
            spans.append((startIdx, endIdx))

        for s, e in spans:
            lexeme = self.lexque[s]
            ref = lexeme.refs[0]
            names = [lexeme.stem]
            fca = lexeme.drs.find_condition(Rel(lexeme.stem, [ref]))
            if fca is None:
                continue
            for i in range(s+1, e+1):
                lexeme = self.lexque[i]
                fc = lexeme.drs.find_condition(Rel(self.lexque[i].stem, [ref]))
                if fc is not None:
                    names.append(self.lexque[i].stem)
                    lexeme.drs.remove_condition(fc)
            nm = '-'.join(names)
            fca.cond.relation.rename(nm)

    def get_drs(self):
        refs = []
        conds = []
        for w in self.lexque:
            if w.drs:
                refs.extend(w.drs.universe)
                conds.extend(w.drs.conditions)

        return DRS(refs, conds)

    def final_rename(self):
        """Rename to ensure:
            - indexes progress is 1,2,...
            - events are tagged e, others x
        """
        vx = set(filter(lambda x: not x.isconst, self.final_prod.variables))
        ors = filter(lambda x: x.var.idx < len(vx), vx)
        if len(ors) != 0:
            # Move names to > len(vx)
            mx = 1 + max([x.var.idx for x in vx])
            idx = [i+mx for i in range(len(ors))]
            rs = map(lambda x: (x[0], DRSRef(DRSVar(x[0].var.name, x[1]))), zip(ors, idx))
            self.final_prod.rename_vars(rs)
            vx = set(filter(lambda x: not x.isconst, self.final_prod.variables))

        # Attempt to order by first occurence
        v = []
        for t in self.lexque:
            if t.drs:
                v.extend(t.drs.universe)

        v = remove_dups(v)
        if len(vx) != len(v):
            f = set(vx).difference(v)
            v.extend(f)

        # Map variables to type
        vtype = dict(map(lambda y: (y.refs[0], y.mask), filter(lambda x: x.drs and len(x.drs.universe) != 0, self.lexque)))

        # Move names to 1:...
        idx = [i+1 for i in range(len(v))]
        #rs = map(lambda x: (x[0], DRSRef(DRSVar(x[0].var.name, x[1]))), zip(v, idx))
        rs = []
        for u, i in zip(v, idx):
            mask = vtype.setdefault(u, 0)
            if 0 != (mask & RT_EVENT):
                # ensure events are prefixed 'e'
                rs.append((u, DRSRef(DRSVar('e', i))))
            else:
                rs.append((u, DRSRef(DRSVar('x', i))))

        self.final_prod.rename_vars(rs)
        self.xid = self.limit
        self.eid = self.limit

    def rename_vars(self, d):
        """Rename to ensure variable names are disjoint. This should be called immediately after
        creating a production.

        Args:
            d: A DrsProduction instance.

        Returns:
            A renamed DrsProduction instance.
        """
        if len(filter(lambda x: x.isconst, d.variables)) != 0:
            pass
        assert len(filter(lambda x: x.isconst, d.variables)) == 0
        v = set(filter(lambda x: not x.isconst, d.variables))
        xlimit = 0
        elimit = 0
        for i in range(10):
            if DRSRef(DRSVar('x', 1+i)) in v:
                xlimit = 1 + i
                if DRSRef(DRSVar('e', 1+i)) in v:
                    elimit = 1 + i
            elif DRSRef(DRSVar('e', 1+i)) in v:
                elimit = 1 + i
            else:
                break
        rs = []
        if self.xid == 0:
            self.xid = xlimit
        else:
            for i in range(xlimit):
                rs.append((DRSRef(DRSVar('x', 1+i)), DRSRef(DRSVar('x', 1+i+self.xid))))
            self.xid += xlimit
        if self.eid == 0:
            self.eid = elimit
        else:
            for i in range(elimit):
                rs.append((DRSRef(DRSVar('e', 1+i)), DRSRef(DRSVar('e', 1+i+self.eid))))
            self.eid += elimit
        if len(rs) != 0:
            rs.reverse()
            d.rename_vars(rs)
        return d

    def build_execution_sequence(self, pt):
        """Build the execution sequence from a ccgbank parse tree.

        Args:
            pt: The parse tree.
        """
        # FIXME: Remove recursion from this function
        self.depth += 1
        if pt[-1] == 'T':
            head = int(pt[0][1])
            count = int(pt[0][2])
            assert head == 1 or head == 0, 'ccgbank T node head=%d, count=%d' % (head, count)
            result = Category.from_cache(pt[0][0])

            idxs = []
            lex_begin = len(self.lexque)
            op_begin = len(self.exeque)
            op_end = []
            for nd in pt[1:-1]:
                idxs.append(self.build_execution_sequence(nd))
                op_end.append(len(self.exeque)-1)

            assert count == len(idxs)
            # Ranges allow us to schedule work to a thread pool
            op_range = (op_begin, len(self.exeque))
            lex_range = (lex_begin, len(self.lexque))

            if count == 2:
                subops = [self.exeque[op_end[0]], self.exeque[-1]]
                cats = map(lambda x: CAT_EMPTY if x.category in [CAT_LRB, CAT_RRB, CAT_LQU, CAT_RQU] else x.category,
                           subops)
                rule = get_rule(cats[0], cats[1], result)
                if rule is None:
                    rule = get_rule(cats[0].simplify(), cats[1].simplify(), result)
                    # TODO: remove debug code below
                    '''
                    if rule is None:
                        rule = get_rule(cats[0].simplify(), cats[1].simplify(), result)
                        pass
                    '''
                    assert rule is not None

                # Head resolved to lexque indexes
                self.lexque[idxs[1-head]].head = idxs[head]
                self.exeque.append(ExecOp(len(self.exeque), subops, head, result, rule, lex_range, op_range,
                                          self.depth))
                self.depth -= 1
                return idxs[head]
            else:
                assert count == 1
                subops = [self.exeque[-1]]
                cats = map(lambda x: CAT_EMPTY if x.category in [CAT_LRB, CAT_RRB, CAT_LQU, CAT_RQU] else x.category,
                           subops)
                rule = get_rule(cats[0], CAT_EMPTY, result)
                if rule is None:
                    rule = get_rule(cats[0].simplify(), CAT_EMPTY, result)
                    assert rule is not None

                # No need to set head, Lexeme defaults to self is head
                self.exeque.append(ExecOp(len(self.exeque), subops, head, result, rule, lex_range, op_range,
                                          self.depth))
                self.depth -= 1
                return idxs[head]
        else:
            lexeme = Lexeme(Category.from_cache(pt[0]), pt[1], pt[2:4], len(self.lexque))
            self.lexque.append(lexeme)
            self.exeque.append(PushOp(lexeme, len(self.exeque), self.depth))
            self.depth -= 1
            return lexeme.idx

    def get_predarg_ccgbank(self, pretty):
        """Return a ccgbank representation with predicate-argument tagged categories. See LDC 2005T13 for details.

        Args:
            pretty: Pretty format, else one line string.

        Returns:
            A ccgbank string.
        """
        assert len(self.exeque) != 0 and len(self.lexque) != 0
        assert isinstance(self.exeque[0], PushOp)

        # Process exec queue
        stk = collections.deque()
        sep = '\n' if pretty else ' '
        for op in self.exeque:
            indent = '  ' * op.depth if pretty else ''
            if isinstance(op, PushOp):
                # Leaf nodes contain 5 fields:
                # <L CCGcat mod_POS-tag orig_POS-tag word PredArgCat>
                if op.lexeme.category in [CAT_LRB, CAT_RRB, CAT_LQU, CAT_RQU]:
                    stk.append('%s(<L %s %s %s %s %s>)' % (indent, op.lexeme.category, op.lexeme.pos, op.lexeme.pos,
                                                           op.lexeme.word, op.lexeme.category))
                else:
                    template = op.lexeme.get_template()
                    if template is None:
                        stk.append('%s(<L %s %s %s %s %s>)' % (indent, op.lexeme.category, op.lexeme.pos, op.lexeme.pos,
                                                               op.lexeme.word, op.lexeme.category))
                    else:
                        stk.append('%s(<L %s %s %s %s %s>)' % (indent, op.lexeme.category, op.lexeme.pos, op.lexeme.pos,
                                                               op.lexeme.word, template.predarg_category))
            elif len(op.sub_ops) == 2:
                assert len(stk) >= 2
                if op.rule == RL_TCL_UNARY:
                    unary = MODEL.lookup_unary(op.category, op.sub_ops[0].category)
                    if unary is None and op.category.ismodifier and op.category.result_category() == op.sub_ops[0].category:
                        unary = MODEL.infer_unary(op.category)
                    assert unary is not None
                    template = unary.template
                    nlst = collections.deque()
                    # reverse order
                    nlst.append('%s(<T %s %d %d>' % (indent, op.category, 1, 2))
                    nlst.append(stk.pop())
                    nlst.append('%s  (<L %s %s %s %s %s>)' % (indent, template.clean_category, 'UNARY', 'UNARY',
                                                              '.UNARY', template.predarg_category))
                    nlst.append('%s)')
                    stk.append(sep.join(nlst))
                elif op.rule == RL_TCR_UNARY:
                    unary = MODEL.lookup_unary(op.category, op.sub_ops[1].category)
                    if unary is None and op.category.ismodifier and op.category.result_category() == op.sub_ops[1].category:
                        unary = MODEL.infer_unary(op.category)
                    assert unary is not None
                    template = unary.template
                    nlst = collections.deque()
                    nlst.append(stk.pop())
                    nlst.append('%s(<T %s %d %d>' % (indent, op.category, 1, 2))
                    nlst.append(stk.pop())
                    nlst.append('%s  (<L %s %s %s %s %s>)' % (indent, template.clean_category, 'UNARY', 'UNARY',
                                                              '.UNARY', template.predarg_category.signature))
                    nlst.append('%s)' % indent)
                    stk.append(sep.join(nlst))
                else:
                    nlst = collections.deque()
                    nlst.appendleft(stk.pop())  # arg1
                    nlst.appendleft(stk.pop())  # arg0
                    nlst.appendleft('%s(<T %s %d %d>' % (indent, op.category, op.head, 2))
                    nlst.append('%s)' % indent)
                    stk.append(sep.join(nlst))
            elif op.rule == RL_TCL_UNARY:
                unary = MODEL.lookup_unary(op.category, op.sub_ops[0].category)
                if unary is None and op.category.ismodifier and op.category.result_category() == op.sub_ops[0].category:
                    unary = MODEL.infer_unary(op.category)
                assert unary is not None
                template = unary.template
                nlst = collections.deque()
                # reverse order
                nlst.append('%s(<T %s %d %d>' % (indent, op.category, 0, 2))
                nlst.append(stk.pop())
                nlst.append('%s  (<L %s %s %s %s %s>)' % (indent, template.clean_category, 'UNARY', 'UNARY',
                                                          '.UNARY', template.predarg_category))
                nlst.append('%s)' % indent)
                stk.append(sep.join(nlst))
            else:
                nlst = collections.deque()
                nlst.appendleft(stk.pop())  # arg0
                nlst.appendleft('%s(<T %s %d %d>' % (indent, op.category, 0, 1))
                nlst.append('%s)' % indent)
                stk.append(sep.join(nlst))

        assert len(stk) == 1
        return stk[0]

    def get_span(self):
        """Get a span of the entire sentence.

        Returns:
            A IndexSpan instance.
        """
        # TODO: support span with start and length
        return IndexSpan(self, range(len(self.lexque)))



## @ingroup gfn
def process_ccg_pt(pt, options=None):
    """Process the CCG parse tree.

    Args:
        pt: The parse tree returned from marbles.ie.drt.parse.parse_ccg_derivation().
        options: None or marbles.ie.drt.compose.CO_REMOVE_UNARY_PROPS to simplify propositions.

    Returns:
        A Ccg2Drs instance. Call Ccg2Drs.get_drs() to obtain the DRS.

    See Also:
        marbles.ie.drt.parse.parse_ccg_derivation()
    """
    ccg = Ccg2Drs(options | CO_FAST_RENAME)
    pt = pt_to_utf8(pt)
    ccg.build_execution_sequence(pt)
    ccg.create_drs()
    ccg.final_rename()
    ccg.resolve_proper_names()
    # TODO: resolve anaphora
    return ccg


## @ingroup gfn
def pt_to_ccgbank(pt, fmt=True):
    """Process the CCG parse tree, add predicate argument tags, and return the ccgbank string.

    Args:
        pt: The parse tree returned from marbles.ie.drt.parse.parse_ccg_derivation().
        fmt: If True format for pretty print.
    Returns:
        A string
    """
    pt = pt_to_utf8(pt)
    ccg = Ccg2Drs()
    ccg.build_execution_sequence(pt)
    s = ccg.get_predarg_ccgbank(fmt)
    return s


## @ingroup gfn
def extract_predarg_categories_from_pt(pt, lst=None):
    """Extract the predicate-argument categories from a CCG parse tree.

    Args:
        pt: The parse tree returned from marbles.ie.drt.parse.parse_ccg_derivation().
        lst: An optional list of existing predicate categories.
    Returns:
        A list of Category instances.
    """
    global _PredArgIdx
    pt = pt_to_utf8(pt)
    if lst is None:
        lst = []

    stk = [pt]
    while len(stk) != 0:
        pt = stk.pop()
        if pt[-1] == 'T':
            stk.extend(pt[1:-1])
        else:
            # Leaf nodes contains six fields:
            # <L CCGcat mod_POS-tag orig_POS-tag word PredArgCat>
            # PredArgCat example: (S[dcl]\NP_3)/(S[pt]_4\NP_3:B)_4>
            catkey = Category(pt[0])

            # Ignore atoms and conj rules.
            if not catkey.isfunctor or catkey.result_category() == CAT_CONJ or catkey.argument_category() == CAT_CONJ:
                continue

            predarg = Category(pt[4])
            assert catkey == predarg.clean(True)
            lst.append(predarg)
    return lst


## @ingroup gfn
def extract_lexicon_from_pt(pt, dictionary=None, uid=None):
    """Extract the lexicon and templates from a CCG parse tree.

    Args:
        pt: The parse tree returned from marbles.ie.drt.parse.parse_ccg_derivation().
        dictionary: An optional dictionary of a existing lexicon.
        uid: A unique identifier string for the sentence.
    Returns:
        A dictionary of functor instances.
    """
    pt = pt_to_utf8(pt)
    if dictionary is None:
        dictionary = map(lambda x: {}, [None]*26)
    if uid is None:
        uid = ''

    stk = [pt]
    while len(stk) != 0:
        pt = stk.pop()
        if pt[-1] == 'T':
            stk.extend(pt[1:-1])
        else:
            # Lexeme will infer template if it does not exist in MODEL
            lexeme = Lexeme(category=pt[0], word=pt[1], pos_tags=pt[2:4])
            if len(lexeme.stem) == 0 or lexeme.category.isatom or lexeme.category in [CAT_LRB, CAT_RRB, CAT_LQU, CAT_RQU]:
                continue

            if lexeme.category.ismodifier and len(set(lexeme.category.extract_unify_atoms(False))) == 1:
                continue

            N = lexeme.stem[0].upper()
            if N not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                continue

            idx = ord(N) - 0x41
            template = lexeme.get_template()
            if template is None:
                continue
            fn = lexeme.get_production(UnboundSentence([lexeme]))
            if lexeme.drs is None or len(fn.lambda_refs) == 1:
                continue

            atoms = template.predarg_category.extract_unify_atoms(False)
            refs = fn.get_unify_scopes(False)
            # This will rename lexeme.drs
            fn.rename_vars(zip(refs, map(lambda x: DRSRef(x.signature), atoms)))
            rel = DRSRelation(lexeme.stem)
            c = filter(lambda x: isinstance(x, Rel) and x.relation == rel, lexeme.drs.conditions)
            if len(c) == 1:
                c = repr(c[0]) + ': ' + template.predarg_category.signature
                if lexeme.stem in dictionary:
                    lst = dictionary[idx][lexeme.stem]
                    lst[0].add(c)
                    lst[1].add(uid)
                else:
                    dictionary[idx][lexeme.stem] = [{c}, {uid}]

    return dictionary

