# -*- coding: utf-8 -*-
"""CCG to DRS Production Generator"""

from __future__ import unicode_literals, print_function
import collections
import inflect
import re
from nltk.stem import wordnet as wn

from ccg import *
from ccg.model import MODEL
import constituent_types
from compose import ProductionList, FunctorProduction, DrsProduction, DrsComposeError, identity_functor
from drt.common import DRSVar, SHOW_LINEAR, SHOW_SET, Showable
from drt.drs import DRS, DRSRef, Rel, Or, Imp, DRSRelation
from drt.drs import get_new_drsrefs
from drt.utils import remove_dups, union, complement, intersect
from kb.verbnet import VERBNETDB
from parse import parse_drs
from utils.vmap import VectorMap, dispatchmethod, default_dispatchmethod
from sentence import UnboundSentence, IndexSpan, Constituent
from marbles import safe_utf8_decode, safe_utf8_encode, future_string, native_string
from constants import *


## @cond
# The pronouns must always be referent x1
__pron = [
    # 1st person singular
    ('i',       '([x1],[])',    '([],[i(x1)])', RT_HUMAN|RT_1P),
    ('me',      '([x1],[])',    '([],[i(x1)])', RT_HUMAN|RT_1P),
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
    ('him',     '([x1],[])',    '([],[he(x1)])', RT_HUMAN|RT_MALE|RT_ANAPHORA|RT_3P),
    ('her',     '([x1],[])',    '([],[she(x1)])', RT_HUMAN|RT_FEMALE|RT_ANAPHORA|RT_3P),
    ('himself', '([x1],[])',    '([],[he(x1),.REFLEX(x1)])', RT_HUMAN|RT_MALE|RT_ANAPHORA|RT_3P),
    ('herself', '([x1],[])',    '([],[she(x1),.REFLEX(x1)])', RT_HUMAN|RT_FEMALE|RT_ANAPHORA|RT_3P),
    ('hisself', '([x1],[])',    '([],[he(x1),.REFLEX(x1)])', RT_HUMAN|RT_MALE|RT_ANAPHORA|RT_3P),
    ('his',     '([x2],[])',    '([],[he(x1),.POSS(x1,x2)])', RT_HUMAN|RT_MALE|RT_ANAPHORA|RT_3P),
    ('hers',    '([x2],[])',    '([],[she(x1),.POSS(x1,x2)])', RT_HUMAN|RT_FEMALE|RT_ANAPHORA|RT_3P),
    # 1st person plural
    ('we',      '([x1],[])',    '([],[we(x1)])', RT_HUMAN|RT_PLURAL|RT_1P),
    ('us',      '([x1],[])',    '([],[we(x1)])', RT_HUMAN|RT_PLURAL|RT_1P),
    ('ourself', '([x1],[])',    '([],[we(x1),.REFLEX(x1)])', RT_HUMAN|RT_PLURAL|RT_1P),
    ('ourselves','([x1],[])',   '([],[we(x1),.REFLEX(x1)])', RT_HUMAN|RT_PLURAL|RT_1P),
    ('ours',    '([x2],[])',    '([],[we(x1),.POSS(x1,x2)])', RT_HUMAN|RT_PLURAL|RT_1P),
    ('our',     '([x2],[])',    '([],[we(x1),.POSS(x1,x2)])', RT_HUMAN|RT_PLURAL|RT_1P),
    # 2nd person plural
    ('yourselves', '([x1],[])', '([],[([],[yourselves(x1)])->([],[you(x1)])])', RT_HUMAN|RT_PLURAL|RT_2P),
    # 3rd person plural
    ('they',    '([x1],[])',    '([],[they(x1)])', RT_HUMAN|RT_PLURAL|RT_3P),
    ('them',    '([x1],[])',    '([],[they(x1)])', RT_HUMAN|RT_PLURAL|RT_3P),
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
# EasySRL prepositions
CAT_ESRL_PP = Category.from_cache(r'(NP\NP)/NP')
CAT_PP_ADVP = Category.from_cache(r'((S\NP)\(S\NP))/NP')
CAT_VP_MOD = Category.from_cache(r'(S\NP)\(S\NP)')
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

FEATURE_VARG = FEATURE_PSS | FEATURE_NG | FEATURE_EM | FEATURE_DCL | FEATURE_TO | FEATURE_B | FEATURE_BEM
FEATURE_VRES = FEATURE_NG | FEATURE_EM | FEATURE_DCL | FEATURE_B |FEATURE_BEM
CAT_VPMODX = Category.from_cache(r'(S[X]\NP)/(S[X]\NP)')
CAT_VP_MODX = Category.from_cache(r'(S[X]\NP)\(S[X]\NP)')
CAT_VPX = Category.from_cache(r'S[X]\NP')
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
        elif isinstance(word, unicode):
            if word.endswith(u"’s"):
                return word.replace(u"’s", u'')
        else:
            uword = safe_utf8_decode(word)
            if uword.endswith(u"’s"):
                return safe_utf8_encode(uword.replace(u"’s", u''))
    return word


class Lexeme(object):

    _EventPredicates = ('.AGENT', '.THEME', '.EXTRA')
    _ToBePredicates = ('.AGENT', '.ATTRIBUTE', '.EXTRA')
    _TypeMonth = re.compile(r'^((Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?|January|February|March|April|June|July|August|September|October|November|December)$')
    _TypeWeekday = re.compile(r'^((Mon|Tue|Tues|Wed|Thur|Thurs|Fri|Sat|Sun)\.?|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)$')
    _Punct= '?.,:;'
    _wnl = wn.WordNetLemmatizer()
    _p = inflect.engine()

    def get_json(self):
        return {
            'word': self.word,
            'stem': self.stem,
            'pos': self.pos.tag,
            'head': self.head,
            'idx': self.idx,
            'mask': self.mask,
            'refs': [r.var.to_string() for r in self.refs],
            'drs': 'none' if not self.drs
                          else reduce(lambda s, kv: s.replace(*kv),
                                      {Showable.opNeg:u'!', Showable.opImp:u' -> ',
                                       Showable.opOr:u' or '}.iteritems(), self.drs.show(SHOW_SET)),
            'category': self.category.signature
        }

    def __init__(self, category, word, pos_tags, idx=0):

        self.head = idx
        self.idx = idx
        #self.variables = None
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
                    if isinstance(stem, unicode):
                        self.stem = self._wnl.lemmatize(stem, pos='v')
                    else:
                        self.stem = self._wnl.lemmatize(stem.decode('utf-8'), pos='v').encode('utf-8')
                else:
                    self.stem = stem

    def __repr__(self):
        if self.drs:
            return b'<Lexeme>:(%s, %s, %s)' % (safe_utf8_encode(self.word), self.drs, self.category)
        return b'<Lexeme>:(%s, %s, %s)' % (safe_utf8_encode(self.word), self.stem, self.category)

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
        d = DrsProduction(self.drs.universe, self.drs.freerefs, span=span)
        d.set_lambda_refs(map(lambda x: nvrs[x.var.to_string()], sample[2]))
        # refs[0] is always the final_ref (atom)
        self.refs = d.lambda_refs
        xtra = filter(lambda x: x not in self.refs, nvrs.itervalues())
        self.refs.extend(xtra)
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
                vnclasses = []
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
                rcat = self.category.test_return_and_get(CAT_VPMODX, False)
                if rcat is not None and rcat.argument_category().has_any_features(FEATURE_VARG) \
                        and rcat.result_category().has_any_features(FEATURE_VRES):
                    conds.append(Rel('.EVENT', [refs[0]]))
                    pred = zip(refs[1:], self._EventPredicates)
                    for v, e in pred[0:2]:
                        conds.append(Rel(e, [refs[0], v]))
                    self.mask |= RT_EVENT
                    self.vnclasses = vnclasses
                    self.drs = DRS([refs[0]], conds)
                    d = DrsProduction([], self.refs, span=span)

                elif rcat is not None and (rcat.has_any_features(FEATURE_PSS | FEATURE_TO) or rcat.ismodifier):
                    if len(refs) > 1:
                        # passive case
                        self.mask |= RT_EVENT_ATTRIB
                        conds.append(Rel('.MOD', [refs[0], refs[-1]]))
                        self.drs = DRS([], conds)
                    d = DrsProduction([], self.refs, span=span)

                elif self.category == CAT_MODAL_PAST:
                    self.mask |= RT_EVENT_MODAL
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
                    # Make sure we have one freeref. For functors it is a bad idea to use an empty DrsProduction
                    # as the spans can be deleted by ProductionList.flatten().
                    d = DrsProduction([], [refs[0]], span=span)
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
                        # Make sure we have one freeref. For functors it is a bad idea to use an empty DrsProduction
                        # as the spans can be deleted by ProductionList.flatten().
                        d = DrsProduction([], [self.refs[0]], span=span)
                        # Having a DRS prevents deletion of TO constituent
                        self.drs = DRS([], [])
                    elif self.pos == POS_MODAL:
                        self.mask |= RT_EVENT_MODAL
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
        return b'<PushOp>:(%s, %s, %s)' % (safe_utf8_encode(self.lexeme.stem), self.lexeme.category, self.lexeme.pos)

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
        return b'<ExecOp>:(%d, %s %s)' % (len(self.sub_ops), self.rule, self.category)

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
            ucat = fn.category
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
            ucat = fn.category
            fn.set_options(self.options)
            stk.append(fn)
            self._dispatch_ba(op, stk)
        self._mark_if_adjunct(ucat, stk[-1])

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
        ucat = fn.category
        fn.set_options(self.options)
        stk.append(fn)
        self._dispatch_ba(op, stk)

        nlst = ProductionList()
        nlst.set_options(self.options)
        nlst.set_category(op.category)
        nlst.push_right(stk.pop())
        nlst.push_right(stk.pop())
        stk.append(nlst.flatten().unify())
        self._mark_if_adjunct(ucat, stk[-1])

    @dispatchmethod(dispatchmap, RL_TC_CONJ)
    def _dispatch_tcconj(self, op, stk):
        # Special type change rules. See section 3.7-3.8 of LDC 2005T13 manual.
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
        prevcat = fn.category
        stk.append(self._update_constituents(fn.apply(d), prevcat))

    @dispatchmethod(dispatchmap, RL_BA)
    def _dispatch_ba(self, op, stk):
        # Backward application.
        fn = stk.pop()   # arg1
        d = stk.pop()    # arg0
        prevcat = fn.category
        stk.append(self._update_constituents(fn.apply(d), prevcat))

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
            stk.append(self._update_constituents(d.flatten().unify(), d.category))
        else:
            stk.append(self._update_constituents(d.unify(), d.category))

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

    def _mark_if_adjunct(self, ucat, d):
        # ucat is the unary type change catgory
        # d is the result of the type change
        if ucat.argument_category().simplify() == CAT_S_NP \
                and (ucat.test_returns_entity_modifier() or ucat.test_return(CAT_ADVERB, exact=True)
                     or ucat.test_return(CAT_MODAL, exact=True)):
            # Mark clausal adjunct
            for lex in d.span:
                lex.mask |= RT_ADJUNCT
            self.constituents.append(Constituent(d.category, d.span.clone(), constituent_types.CONSTITUENT_ADVP))

    def _update_constituents(self, d, cat_before_rule):
        vntype = None

        if isinstance(d, (FunctorProduction, DrsProduction)):
            if d.category == CAT_NP:
                refs = set()
                for lex in d.span:
                    # Adverbial phrases are removed from NP's at a later point
                    if 0 == (lex.mask & (RT_ADJUNCT | RT_PP)):
                        refs = refs.union(lex.refs)
                vntype = constituent_types.CONSTITUENT_NP if len(refs) == 1 else None
            elif cat_before_rule is CAT_ESRL_PP:
                vntype = constituent_types.CONSTITUENT_PP
                if Constituent(d.category, d.span, vntype).get_head().pos != POS_PREPOSITION:
                    vntype = None
            elif cat_before_rule is CAT_PP_ADVP and d.category is CAT_VP_MOD and not d.span.isempty:
                hd = Constituent(d.category, d.span, constituent_types.CONSTITUENT_ADVP).get_head()
                if hd.pos == POS_PREPOSITION and hd.stem in ['for']:
                    vntype = constituent_types.CONSTITUENT_ADVP
            else:
                vntype = Constituent.vntype_from_category(d.category)
                if vntype is None and cat_before_rule.argument_category().remove_features() == CAT_N \
                        and (cat_before_rule.test_return(CAT_VPMODX) or cat_before_rule.test_return(CAT_VP_MODX)):
                    # (S\NP)/(S\NP)/N[X]
                    vntype = constituent_types.CONSTITUENT_NP

            if vntype is not None and vntype not in [constituent_types.CONSTITUENT_VP,
                                                     constituent_types.CONSTITUENT_SINF,
                                                     constituent_types.CONSTITUENT_TO]:
                c = Constituent(d.category, d.span, vntype)
                #if vntype is constituent_types.CONSTITUENT_NP:
                    #for lex in d.span:
                    #    lex.mask |= RT_PP

                while len(self.constituents) != 0 and self.constituents[-1].vntype is c.vntype \
                        and self.constituents[-1] in c:
                    self.constituents.pop()
                self.constituents.append(c)
        return d
    
    def _refine_constituents(self):

        # Add verb phrases
        verbrefs = {}
        for lex in self.lexque:
            # TODO: Add compose option to allow VP visibility in adjuncts
            if 0 != (lex.mask & RT_EVENT) and 0 == (lex.mask & RT_ADJUNCT):
                verbrefs.setdefault(lex.refs[0], []).append(lex.idx)
        for lex in self.lexque:
            if 0 != (lex.mask & (RT_EVENT_MODAL | RT_EVENT_ATTRIB)) or lex.category == CAT_INFINITIVE:
                if lex.refs[0] in verbrefs:
                    verbrefs[lex.refs[0]].append(lex.idx)
        for r, idxs in verbrefs.iteritems():
            category = self.lexque[idxs[0]].category
            vntype = constituent_types.CONSTITUENT_SINF if category.test_return(CAT_VPb) \
                        else constituent_types.CONSTITUENT_VP
            self.constituents.append(Constituent(category, IndexSpan(self, idxs), vntype))

        constituents = sorted(set(self.constituents))

        # Fixup phrases containing clausal adjuncts
        adjuncts = []
        for i in range(len(constituents)):
            c = constituents[i]
            # Split ADVP - not sure if this is required anymore
            indexes = filter(lambda i: 0 != (self.lexque[i].mask & RT_ADJUNCT), c.span.get_indexes())
            if len(indexes) != 0:
                advp = IndexSpan(self, indexes)
                dspan = c.span.difference(advp)
                if not dspan.isempty:
                    c.span = dspan
                    adjuncts.append(Constituent(c.category, advp, constituent_types.CONSTITUENT_ADVP))
                elif c.vntype == constituent_types.CONSTITUENT_VP:
                    c.vntype = constituent_types.CONSTITUENT_ADVP

        if len(adjuncts):
            constituents.extend(adjuncts)

        # Finalize NP constituents, split VP's
        to_remove = set()
        constituents = sorted(set(constituents))
        advp = None
        iadvp = 0
        allspan = IndexSpan(self)
        for i in range(len(constituents)):
            c = constituents[i]
            allspan = allspan.union(c.span)
            # FIXME: rank wikipedia search results
            if all(map(lambda x: x.category in [CAT_DETERMINER, CAT_POSSESSIVE_PRONOUN, CAT_PREPOSITION] or
                            x.pos in POS_LIST_PERSON_PRONOUN or x.pos in POS_LIST_PUNCT or
                            x.pos in [POS_PREPOSITION, POS_DETERMINER], c.span)):
                to_remove.add(i)
                continue
            elif c.vntype is not constituent_types.CONSTITUENT_NP and 0 != (c.get_head().mask & RT_ADJUNCT):
                if advp:
                    if c in advp:
                        to_remove.add(i)
                    elif advp in c:
                        to_remove.add(iadvp)
                        advp = c
                        iadvp = i
                    else:
                        advp = c
                        iadvp = i
                else:
                    advp = c
                    iadvp = i
                continue
            elif c.vntype is not constituent_types.CONSTITUENT_NP:
                continue

            if 0 != (self.options & CO_NO_WIKI_SEARCH):
                continue

            result = c.search_wikipedia()
            if result is not None:
                subspan = c.span.get_subspan_from_wiki_search(result)
                if subspan == c.span:
                    c.set_wiki_entry(result[0])
                elif subspan:
                    dspan = c.span.difference(subspan)
                    if all(map(lambda x: x.category in [CAT_DETERMINER, CAT_POSSESSIVE_PRONOUN,
                                                        CAT_PREPOSITION, CAT_ADJECTIVE] or
                            x.category.test_returns_entity_modifier() or
                                    x.pos in POS_LIST_PERSON_PRONOUN or x.pos in POS_LIST_PUNCT or
                                    x.pos in [POS_PREPOSITION, POS_DETERMINER], dspan)):
                        c.set_wiki_entry(result[0])
                    elif all(map(lambda x: x.pos in [POS_PROPER_NOUN, POS_PROPER_NOUN_S], dspan)):
                        # FIXME: This is not a good strategy. For example Consolidated-Gold-Fields *PLC*.
                        # Search page for these words
                        summary = result[0].summary.lower()
                        if all(map(lambda x: x.stem.lower() in summary, dspan)):
                            c.set_wiki_entry(result[0])
                        else:
                            content = result[0].content
                            if all(map(lambda x: x.stem.lower() in content, dspan)):
                                c.set_wiki_entry(result[0])

        # Remove irrelevent entries
        if len(to_remove) != 0:
            filtered_constituents = [constituents[i] for i in
                                     filter(lambda k: k not in to_remove, range(len(constituents)))]
            constituents = filtered_constituents

        # Split VP's that accidently got combined.
        split_vps = []
        for i in range(len(constituents)):
            c = constituents[i]
            if c.vntype is constituent_types.CONSTITUENT_VP:
                cindexes = c.span.get_indexes()
                findexes = c.span.fullspan().get_indexes()
                if len(cindexes) == len(findexes):
                    continue
                splits = []
                while len(cindexes) != 0:
                    contig_span = map(lambda y: y[0], filter(lambda x: x[1] == x[0], zip(findexes, cindexes)))
                    contig = Constituent(c.category, IndexSpan(self, contig_span), constituent_types.CONSTITUENT_VP)
                    if 0 != (contig.get_head().mask & RT_EVENT):
                        contig.category = contig.get_head().category
                        splits.append(contig)
                    cnew = IndexSpan(self, set(cindexes).difference(contig_span))
                    cindexes = cnew.get_indexes()
                    findexes = cnew.fullspan().get_indexes()
                if len(splits) >= 1:
                    constituents[i] = splits[0]
                    split_vps.extend(splits[1:])

        if len(split_vps) != 0:
            constituents.extend(split_vps)
            constituents = sorted(set(constituents))

        # And finally remove any constituent that contains only punctuation
        constituents = filter(lambda x: len(x.span) != 1 or not x.span[0].ispunct, constituents)

        # If a constituent head and its category is N/N or a noun modifier and it is an RT_ATTRIBUTE
        # then all direct descendents are also attributes
        for c in constituents:
            hd = c.get_head()
            if 0 != (hd.mask & RT_ATTRIBUTE) and (hd.category in [CAT_ADJECTIVE, CAT_AP]
                                                  or hd.category.test_returns_entity_modifier()):
                for lex in c.span:
                    lex.mask |= RT_ATTRIBUTE
        self.constituents = constituents

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

        # Refine constituents
        self._refine_constituents()

        # And finally set constituent heads
        # Lexme head index is always in constituent so use it map between the two.
        i2c = {}
        for i in range(len(self.constituents)):
            c = self.constituents[i]
            lexhd = c.get_head()
            if lexhd.idx in i2c:
                pass
            assert lexhd.idx not in i2c
            i2c[lexhd.idx] = i

        for i in range(len(self.constituents)):
            c = self.constituents[i]
            lexhd = c.get_head()
            if lexhd.head in i2c:
                c.chead = i2c[lexhd.head]
            else:
                while lexhd.head not in i2c and lexhd.head != lexhd.idx:
                    lexhd = self.lexque[lexhd.head]
                if lexhd.head in i2c:
                    c.chead = i2c[lexhd.head]

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

        if 0 == (self.options & CO_KEEP_PUNCT):
            to_remove = IndexSpan(self, filter(lambda i: self.lexque[i].drs is None or self.lexque[i].ispunct,
                                               range(len(self.lexque))))
        else:
            to_remove = IndexSpan(self)

        for c in self.constituents:
            c.span = c.span.difference(to_remove)
            if c.span.isempty:
                continue
            if c.vntype is constituent_types.CONSTITUENT_NP and c.get_head().isproper_noun:
                spans = []
                lastref = DRSRef('$$$$')
                startIdx = -1
                endIdx = -1
                for i in range(len(c.span)):
                    lexeme = c.span[i]
                    if lexeme.refs is None or len(lexeme.refs) == 0:
                        ref = DRSRef('$$$$')
                    else:
                        ref = lexeme.refs[0]

                    if startIdx >= 0:
                        if ref == lastref and (lexeme.isproper_noun or lexeme.category == CAT_N or \
                                (lexeme.word == '&' and (i+1) < len(c.span) and c.span[i+1].isproper_noun)):
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
                    # Preserve heads
                    ctmp = Constituent(c.category, c.span[s:e+1], c.vntype)
                    lexeme = ctmp.get_head()
                    ref = lexeme.refs[0]
                    word = '-'.join([c.span[i].word for i in range(s, e+1)])
                    stem = '-'.join([c.span[i].stem for i in range(s, e+1)])
                    fca = lexeme.drs.find_condition(Rel(lexeme.stem, [ref]))
                    if fca is None:
                        continue
                    fca.cond.relation.rename(stem)
                    lexeme.stem = stem
                    lexeme.word = word
                    to_remove = to_remove.union(IndexSpan(self, filter(lambda y: y != lexeme.idx, [x.idx for x in ctmp.span])))

        if not to_remove.isempty:
            # Python 2.x does not support nonlocal keyword for the closure
            class context:
                i = 0
            def counter(inc=1):
                idx = context.i
                context.i += inc
                return idx

            # Remove constituents and remap indexes.
            context.i = 0
            self.constituents = map(lambda c: Constituent(c.category, c.span.difference(to_remove), c.vntype, c.chead),
                                    self.constituents)
            idxs_to_del = set(filter(lambda i: self.constituents[i].span.isempty, range(len(self.constituents))))
            if len(idxs_to_del) != 0:
                idxmap = map(lambda x: -1 if x in idxs_to_del else counter(), range(len(self.constituents)))
                self.constituents = map(lambda y: self.constituents[y], filter(lambda x: idxmap[x] >= 0,
                                                                               range(len(idxmap))))
                for c in self.constituents:
                    if c.chead >= 0:
                        c.chead = idxmap[c.chead]
                        assert c.chead >= 0

            # Remove lexemes and remap indexes.
            context.i = 0
            idxs_to_del = set(to_remove.get_indexes())
            # Reparent heads marked for deletion
            for lex in self.lexque:
                lasthead = -1
                while lex.head in idxs_to_del and lex.head != lasthead:
                    lasthead = lex.head
                    lex.head = self.lexque[lex.head].head

            idxmap = map(lambda x: -1 if x in idxs_to_del else counter(), range(len(self.lexque)))
            for c in self.constituents:
                c.span = IndexSpan(self, map(lambda y: idxmap[y],
                                             filter(lambda x: idxmap[x] >= 0, c.span.get_indexes())))
            self.lexque = map(lambda y: self.lexque[y], filter(lambda x: idxmap[x] >= 0, range(len(idxmap))))
            for i in range(len(self.lexque)):
                lexeme = self.lexque[i]
                lexeme.idx = i
                lexeme.head = idxmap[lexeme.head]
                assert lexeme.head >= 0

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
                    nlst.append('%s(<T %s %d %d>' % (indent, op.category, 1, 2))
                    b = stk.pop()
                    a = stk.pop()
                    nlst.append(a)
                    nlst.append(b)
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
def process_ccg_pt(pt, options=0):
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
    if future_string != unicode:
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
    if future_string != unicode:
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
    if future_string != unicode:
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


class TestSentence(UnboundSentence):
    def __init__(self, lst):
        self.lst = lst

    def __len__(self):
        return len(self.lst)

    def at(self, i):
        return self.lst[i]

    def get_constituents(self):
        raise []


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

    if future_string != unicode:
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
            fn = lexeme.get_production(TestSentence([lexeme]), options=CO_NO_VERBNET)
            if lexeme.drs is None or len(fn.lambda_refs) == 1:
                continue

            atoms = template.predarg_category.extract_unify_atoms(False)
            refs = fn.get_unify_scopes(False)
            # This will rename lexeme.drs
            fn.rename_vars(zip(refs, map(lambda x: DRSRef(x.signature), atoms)))
            rel = DRSRelation(lexeme.stem)
            c = filter(lambda x: isinstance(x, Rel) and x.relation == rel, lexeme.drs.conditions)
            if len(c) == 1:
                c = future_string(c[0]) + ': ' + template.predarg_category.signature
                di = dictionary[idx].setdefault(lexeme.stem, {})
                si = di.setdefault(c, set())
                si.add(uid)

    return dictionary

