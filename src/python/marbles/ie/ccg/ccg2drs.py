# -*- coding: utf-8 -*-
"""CCG to DRS Production Generator"""

import re
from nltk.stem import wordnet as wn
from nltk.stem.snowball import EnglishStemmer
from marbles.ie.ccg.ccgcat import Category, CAT_Sadj, CAT_N, CAT_NOUN, CAT_NP_N, CAT_DETERMINER, CAT_CONJ, CAT_EMPTY, \
    CAT_INFINITIVE, CAT_NP, CAT_LRB, CAT_RRB, CAT_LQU, CAT_RQU, CAT_ADJECTIVE, CAT_PREPOSITION, CAT_ADVERB, CAT_NPthr, \
    get_rule, RL_TC_CONJ, RL_TC_ATOM, RL_TCR_UNARY, RL_TCL_UNARY, \
    RL_TYPE_RAISE, RL_BA, RL_LPASS, RL_RPASS, \
    FEATURE_ADJ, FEATURE_PSS, FEATURE_TO, FEATURE_DCL
from marbles.ie.drt.compose import RT_ANAPHORA, RT_PROPERNAME, RT_ENTITY, RT_EVENT, RT_LOCATION, RT_DATE, RT_WEEKDAY, \
    RT_MONTH, RT_RELATIVE, RT_HUMAN, RT_MALE, RT_FEMALE, RT_PLURAL, RT_NUMBER, RT_1P, RT_2P, RT_3P
from marbles.ie.ccg.model import MODEL
from marbles.ie.drt.compose import ProductionList, FunctorProduction, DrsProduction, OrProduction, \
    DrsComposeError, Dependency, identity_functor, CO_DISABLE_UNIFY, CO_NO_VERBNET
from marbles.ie.drt.drs import DRS, DRSRef, Rel, Or, Imp, Box, Diamond, Prop, Neg, DRSRelation
from marbles.ie.drt.common import DRSConst, DRSVar
from marbles.ie.drt.utils import remove_dups, union, union_inplace, complement, intersect
from marbles.ie.parse import parse_drs
from marbles.ie.drt.drs import get_new_drsrefs
from marbles.ie.utils.cache import Cache, Freezable
from marbles.ie.kb.verbnet import VerbnetDB

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
    ('up',      '([e],[])', '([],[up(e),direction(e)])', RT_LOCATION),
    ('down',    '([e],[])', '([],[down(e),direction(e)])', RT_LOCATION),
    ('left',    '([e],[])', '([],[left(e),direction(e)])', RT_LOCATION),
    ('right',   '([e],[])', '([],[right(e),direction(e)])', RT_LOCATION),
]
_ADV = {}
for k,u,v,w in __adv:
    _ADV[k] = (parse_drs(v, 'nltk'), parse_drs(u, 'nltk').universe, w)

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
        elif word.endswith("’s"):
            return word.replace("’s", '')
    return word


class POS(Freezable):
    """Penn Treebank Part-Of-Speech."""
    _cache = Cache()

    def __init__(self, tag):
        super(POS, self).__init__()
        self._tag = tag

    def __eq__(self, other):
        if self._freeze and other.isfrozen:
            return self is other
        return self._tag == other.tag

    def __ne__(self, other):
        if self._freeze and other.isfrozen:
            return self is not other
        return self._tag != other.tag

    def __hash__(self):
        return hash(self._tag)

    def __str__(self):
        return self._tag

    def __repr__(self):
        return self._tag

    @property
    def tag(self):
        """Readonly access to POS tag."""
        return self._tag

    @classmethod
    def from_cache(cls, tag):
        """Get the cached POS tag"""
        if isinstance(tag, POS):
            tag = tag.tag
        try:
            return cls._cache[tag]
        except KeyError:
            pos = POS(tag)
            cls._cache[pos.tag] = pos
            pos.freeze()
            return pos


# Initialize POS cache
_tags = [
    'CC', 'CD', 'DT', 'EX', 'FW', 'IN', 'JJ', 'JJR', 'JJS', 'LS', 'MD', 'NN', 'NNS', 'NNP', 'NNPS',
    'PDT', 'POS', 'PRP', 'PRP$', 'RB', 'RBR', 'RBS', 'RP', 'SYM', 'TO', 'UH', 'VB', 'VBD', 'VBG', 'VBN',
    'VBP', 'VBZ', 'WDT', 'WP', 'WP$', 'WRB', 'UNKNOWN', ',', '.', ':', ';'
]
for _t in _tags:
    POS._cache.addinit((_t, POS(_t)))
for _t in _tags:
    POS.from_cache(_t).freeze()


# Useful tags
POS_DETERMINER = POS.from_cache('DT')
POS_LIST_PERSON_PRONOUN = [POS.from_cache('PRP'), POS.from_cache('PRP$')]
POS_LIST_PRONOUN = [POS.from_cache('PRP'), POS.from_cache('PRP$'), POS.from_cache('WP'), POS.from_cache('WP$')]
POS_LIST_VERB = [POS.from_cache('VB'), POS.from_cache('VBD'), POS.from_cache('VBN'), POS.from_cache('VBP'),
                 POS.from_cache('VBZ')]
POS_LIST_ADJECTIVE = [POS.from_cache('JJ'), POS.from_cache('JJR'), POS.from_cache('JJS')]
POS_GERUND = POS.from_cache('VBG')
POS_PROPER_NOUN = POS.from_cache('NNP')
POS_PROPER_NOUN_S = POS.from_cache('NNPS')
POS_NOUN = POS.from_cache('NN')
POS_NOUN_S = POS.from_cache('NNS')
POS_MODAL = POS.from_cache('MD')
POS_UNKNOWN = POS.from_cache('UNKNOWN')
POS_NUMBER = POS.from_cache('CD')
POS_PREPOSITION = POS.from_cache('IN')
POS_LIST_PUNCT = [POS.from_cache(','), POS.from_cache('.'), POS.from_cache(':'), POS.from_cache(';')]


class CcgTypeMapper(object):
    """Mapping from CCG types to DRS types."""
    _EventPredicates = ('.AGENT', '.THEME', '.EXTRA')
    _ToBePredicates = ('.AGENT', '.ATTRIBUTE', '.EXTRA')
    _TypeMonth = re.compile(r'^((Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?|January|February|March|April|June|July|August|September|October|November|December)$')
    _TypeWeekday = re.compile(r'^((Mon|Tue|Tues|Wed|Thur|Thurs|Fri|Sat|Sun)\.?|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)$')
    _Lemmatizer = wn.WordNetLemmatizer()
    _verbnetDB = VerbnetDB()

    def __init__(self, category, word, posTags=None, no_vn=False):
        self._no_vn = no_vn
        self._templ = None
        if isinstance(category, Category):
            self._ccgcat = category
        else:
            self._ccgcat = Category.from_cache(category)
        self._pos = POS.from_cache(posTags[0]) if posTags is not None else POS_UNKNOWN

        # We treat modal as verb modifiers - i.e. they don't get their own event
        if self._pos == POS_MODAL:
            tmpcat = self._ccgcat.remove_features().simplify()
            if tmpcat.ismodifier:
                self._ccgcat = tmpcat

        # TODO: should lookup nouns via conceptnet or wordnet
        wd = strip_apostrophe_s(word)
        if (self.category == CAT_NOUN or self._pos == POS_NOUN or self._pos == POS_NOUN_S) and wd.upper() == wd:
            # If all uppercase then keep it that way
            self._word = word.rstrip('?.,:;')
            self._stem = self._word
        elif self.isproper_noun:
            if wd.upper() == wd:
                self._word = word.rstrip('?.,:;')
            else:
                self._word = word.title().rstrip('?.,:;')
            self._stem = self._word
        else:
            self._word = word.lower().rstrip('?.,:;')
            if self._pos in POS_LIST_VERB or self._pos == POS_GERUND:
                # FIXME: move to python 3 so its all unicode
                self._stem = self._Lemmatizer.lemmatize(self._word.decode('utf-8'), pos='v').encode('utf-8')
            else:
                self._stem = self._word

        # Atomic types don't need a template
        if self.category.isfunctor and not MODEL.issupported(self.category) \
            and self.category != CAT_CONJ_CONJ and self.category != CAT_CONJCONJ:
            templ = MODEL.infer_template(self.category)
            if templ is not None and (self.category.result_category().isfunctor or
                                      self.category.argument_category().isfunctor):
                raise DrsComposeError('CCG type "%s" for word "%s" maps to unknown DRS production type "%s"' %
                                      (category, word, self.signature))

    def __repr__(self):
        return '<' + self._word + ' ' + str(self.partofspeech) + ' ' + self.signature + '>'

    @property
    def word(self):
        return self._stem

    @property
    def ispunct(self):
        """Test if the word attached to this category is a punctuation mark."""
        return self.partofspeech in POS_LIST_PUNCT

    @property
    def ispronoun(self):
        """Test if the word attached to this category is a pronoun."""
        return (self.partofspeech in POS_LIST_PRONOUN)  # or self._word in _PRON

    @property
    def ispreposition(self):
        """Test if the word attached to this category is a preposition."""
        return self.category == CAT_PREPOSITION

    @property
    def isadverb(self):
        """Test if the word attached to this category is an adverb."""
        return self.category == CAT_ADVERB

    @property
    def isverb(self):
        """Test if the word attached to this category is a verb."""
        # Verbs can behave as adjectives
        return (self.partofspeech in POS_LIST_VERB and self.category != CAT_ADJECTIVE) or \
               (self.category.result_category() == CAT_VPdcl and not self.category.ismodifier)

    @property
    def isgerund(self):
        """Test if the word attached to this category is a gerund."""
        return self.partofspeech == POS_GERUND

    @property
    def isproper_noun(self):
        """Test if the word attached to this category is a proper noun."""
        return self.partofspeech == POS_PROPER_NOUN or self.partofspeech == POS_PROPER_NOUN_S

    @property
    def isnumber(self):
        """Test if the word attached to this category is a number."""
        return self.partofspeech == POS_NUMBER

    @property
    def isadjective(self):
        """Test if the word attached to this category is an adjective."""
        return self.category == CAT_ADJECTIVE

    @property
    def partofspeech(self):
        """Get part of speech of the word attached to this category."""
        return self._pos

    @property
    def signature(self):
        """Get the CCG category signature."""
        return self._ccgcat.signature

    @property
    def category(self):
        """Get the CCG category."""
        return self._ccgcat

    @property
    def template(self):
        return self._templ

    def empty_production(self, ref=None):
        """Return the empty production `λx.[|]`.

        Args:
            ref: optional DRSRef to use as the referent.

        Returns:
            A DrsProduction instance.
        """
        d = DrsProduction(DRS([], []), category=self.category)
        if ref is None:
            ref = DRSRef('x1')
        d.set_lambda_refs([ref])
        return d

    def build_conditions(self, conds, refs, template):
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
            if isinstance(template.constructor_rule[0][1], DRSRef):
                x = [template.constructor_rule[0][1]]
            else:
                x = [template.constructor_rule[0][1][0]]
            x.extend(complement(refs, x))
            refs = x
            if self._TypeMonth.match(self._word):
                if self._word in _MONTHS:
                    conds.append(Rel(_MONTHS[self._word], [refs[0]]))
                else:
                    conds.append(Rel(self._word, [refs[0]]))
                if template.isfinalevent:
                    conds.append(Rel('.DATE', refs[0:2]))
                else:
                    conds.append(Rel('.DATE', refs))
            elif self._TypeWeekday.match(self._word):
                if self._word in _WEEKDAYS:
                    conds.append(Rel(_WEEKDAYS[self._word], [refs[0]]))
                else:
                    conds.append(Rel(self._word, [refs[0]]))
                if template.isfinalevent:
                    conds.append(Rel('.DATE', refs[0:2]))
                else:
                    conds.append(Rel('.DATE', refs))
            else:
                conds.append(Rel(self._word, [refs[0]]))
        elif self.isnumber:
            conds.append(Rel(self._word, [refs[0]]))
            conds.append(Rel('.NUM', refs))
        elif self.partofspeech == POS_PREPOSITION and not self.ispreposition:
            conds.append(Rel(self._word, refs))
        else:
            conds.append(Rel(self._word, [refs[0]]))
        return conds

    def get_composer(self):
        """Get the production model for this category.

        Returns:
            A Production instance.
        """
        try:
            # Special handling for prepositions
            if self.ispreposition and self._word in _PREPS:
                template = _PREPS[self._word]
            else:
                template = MODEL.lookup(self.category)
            compose = None if template is None else template.constructor_rule
        except Exception:
            template = None
            compose = None

        self._templ = template
        if compose is None:
            # Simple type
            # Handle prepositions
            if self.category in [CAT_CONJ, CAT_NPthr]:
                if self._word == ['or', 'nor']:
                    return OrProduction(negate=('n' in self._word))
                return self.empty_production()
            elif self.category in [CAT_CONJ_CONJ, CAT_CONJCONJ]:
                return identity_functor(self.category)
            elif self.ispronoun and self._word in _PRON:
                pron = _PRON[self._word]
                d = DrsProduction(pron[0], category=self.category,
                                  dep=Dependency(DRSRef('x1'), self._word, pron[1]))
                d.set_lambda_refs(pron[2])
                return d
            elif self.category == CAT_N:
                if self.isproper_noun:
                    dep = Dependency(DRSRef('x1'), self._word, RT_PROPERNAME)
                    d = DrsProduction(DRS([DRSRef('x1')], [Rel(self._word, [DRSRef('x1')])]), properNoun=True, dep=dep)
                else:
                    if self.partofspeech == POS_NOUN_S:
                        dep = Dependency(DRSRef('x1'), self._word, RT_ENTITY | RT_PLURAL)
                    else:
                        dep = Dependency(DRSRef('x1'), self._word, RT_ENTITY)
                    d = DrsProduction(DRS([DRSRef('x1')], [Rel(self._word, [DRSRef('x1')])]), dep=dep)
                d.set_category(self.category)
                d.set_lambda_refs([DRSRef('x1')])
                return d
            elif self.category == CAT_NOUN:
                if self.isnumber:
                    d = DrsProduction(DRS([DRSRef('x1')], [Rel(self._word, [DRSRef('x1')]), Rel('.NUM', [DRSRef('x1')])]),
                                      dep=Dependency(DRSRef('x1'), self._word, RT_NUMBER))
                elif self.partofspeech == POS_NOUN_S:
                    d = DrsProduction(DRS([DRSRef('x1')], [Rel(self._word, [DRSRef('x1')])]),
                                      dep=Dependency(DRSRef('x1'), self._word, RT_ENTITY | RT_PLURAL))
                else:
                    d = DrsProduction(DRS([DRSRef('x1')], [Rel(self._word, [DRSRef('x1')])]),
                                      dep=Dependency(DRSRef('x1'), self._word, RT_ENTITY))
                d.set_category(self.category)
                d.set_lambda_refs([DRSRef('x1')])
                return d
            elif self.category == CAT_CONJ_CONJ or self.category == CAT_CONJCONJ:
                return ProductionList(category=CAT_CONJ)
                #return identity_functor(self.category)
            elif self.isadverb and self._word in _ADV:
                adv = _ADV[self._word]
                d = DrsProduction(adv[0], [x for x in adv[1]])
                d.set_category(self.category)
                d.set_lambda_refs(d.drs.universe)
                return d
            else:
                d = DrsProduction(DRS([], [Rel(self._word, [DRSRef('x')])]))
                d.set_category(self.category)
                d.set_lambda_refs([DRSRef('x')])
                return d

        # else is functor

        # Production templates use tuples so we don't accidentally modify.
        if self.category == CAT_NP_N:    # NP*/N class
            # Ignore template in these cases
            # FIXME: these relations should be added as part of build_conditions()
            if self.ispronoun and self._word in _PRON:
                pron = _PRON[self._word]
                fn = DrsProduction(pron[0], category=CAT_NP,
                                   dep=Dependency(DRSRef('x1'), self._word, pron[1]))
                fn.set_lambda_refs(pron[2])
                return FunctorProduction(category=self.category, referent=pron[2], production=fn)

            else:
                if self.category == CAT_DETERMINER:
                    if self._word in ['a', 'an']:
                        fn = DrsProduction(DRS([], [Rel('.MAYBE', [DRSRef('x1')])]), category=CAT_NP)
                    elif self._word in ['the', 'thy']:
                        fn = DrsProduction(DRS([], [Rel('.EXISTS', [DRSRef('x1')])]), category=CAT_NP)
                    else:
                        fn = DrsProduction(DRS([], [Rel(self._word, [DRSRef('x1')])]), category=CAT_NP)
                elif self.partofspeech == POS_DETERMINER and self._word in ['the', 'thy', 'a', 'an']:
                    fn = DrsProduction(DRS([], []), category=CAT_NP)
                else:
                    fn = DrsProduction(DRS([], [Rel(self._word, [DRSRef('x1')])]), category=CAT_NP)
                fn.set_lambda_refs([DRSRef('x1')])
            return FunctorProduction(category=self.category, referent=DRSRef('x1'), production=fn)

        else:
            refs = []
            signatures = []
            s = self.category.remove_wildcards()
            for c in compose:
                signatures.append(s)
                if isinstance(c[1], tuple):
                    refs.extend(list(c[1]))
                else:
                    refs.append(c[1])
                s = s.result_category()

            refs.append(template.final_ref)
            refs.reverse()
            refs = remove_dups(refs)
            final_atom = template.final_atom.remove_wildcards()
            final_ref = template.final_ref

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
                    vnclasses = [] if self._no_vn else self._verbnetDB.name_index[self._stem]
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
                        conds.append(Imp(DRS([], [Rel(self._stem, [refs[0]])]), DRS([], [vncond])))
                    else:
                        conds.append(Rel(self._stem, [refs[0]]))

                except Exception:
                    conds.append(Rel(self._stem, [refs[0]]))
                    pass
                if (self.category.iscombinator and self.category.has_any_features(FEATURE_PSS | FEATURE_TO)) \
                            or self.category.ismodifier:

                    dep = None
                    if not self.category.ismodifier and self.category.has_all_features(FEATURE_TO | FEATURE_DCL):
                        conds.append(Rel('.EVENT', [refs[0]]))
                        dep=Dependency(refs[0], self._stem, RT_EVENT)

                    # passive case
                    if len(refs) > 1:
                        conds.append(Rel('.MOD', [refs[0], refs[-1]]))
                    fn = DrsProduction(DRS([], conds), dep=dep)

                elif self.category == CAT_MODAL_PAST:
                    conds.append(Rel('.MODAL', [refs[0]]))
                    fn = DrsProduction(DRS([], conds))

                elif self.category in CAT_COPULAR:
                    assert len(refs) == 3, "copular expects 3 referents"

                    # Special handling
                    if self._stem == 'be':
                        # Discard conditions
                        conds.extend([Rel('.EVENT', [refs[0]]), Rel('.AGENT', [refs[0], refs[1]]),
                                      Rel('.ROLE', [refs[0], refs[2]])])
                        d = DrsProduction(DRS([refs[0]], conds), category=final_atom,
                                          dep=Dependency(refs[0], self._stem, RT_EVENT))
                    else:
                        conds.append(Rel('.EVENT', [refs[0]]))
                        conds.append(Rel('.AGENT', [refs[0], refs[1]]))
                        conds.append(Rel('.ROLE', [refs[0], refs[2]]))
                        d = DrsProduction(DRS([refs[0]], conds), category=final_atom,
                                          dep=Dependency(refs[0], self._stem, RT_EVENT))
                    d.set_lambda_refs([refs[0]])
                    fn = template.create_empty_functor()
                    fn.pop()
                    fn.push(d)
                    #fn.rename_vars([(refs[2], refs[0])])
                    return fn

                elif self.category == CAT_VPdcl:

                    assert len(refs) == 2, "maybe_copular expects 2 referents"

                    conds.append(Rel('.EVENT', [refs[0]]))
                    #conds.append(Rel('.MAYBE_COPULAR', [refs[0]]))
                    conds.append(Rel('.AGENT', [refs[0], refs[1]]))

                    # Special handling
                    d = DrsProduction(DRS([refs[0]], conds), category=final_atom,
                                      dep=Dependency(refs[0], self._stem, RT_EVENT))
                    d.set_lambda_refs([refs[0]])
                    fn = template.create_empty_functor()
                    fn.pop()
                    fn.push(d)
                    return fn
                else:
                    # TODO: use verbnet to get semantics
                    if self._stem == 'be' and self.category.can_unify(CAT_TV):
                        # Discard conditions
                        conds.extend([Rel('.EVENT', [refs[0]]), Rel('.AGENT', [refs[0], refs[1]]),
                                      Rel('.ROLE', [refs[0], refs[2]]), Rel('.ATTRIBUTE', [refs[2], refs[1]])])
                    else:
                        conds.append(Rel('.EVENT', [refs[0]]))
                        pred = zip(refs[1:], self._EventPredicates)
                        for v, e in pred:
                            conds.append(Rel(e, [refs[0], v]))
                        if (len(refs)-1) > len(pred):
                            rx = [refs[0]]
                            rx.extend(refs[len(pred)+1:])
                            conds.append(Rel('.EXTRA', rx))
                    fn = DrsProduction(DRS([refs[0]], conds), dep=Dependency(refs[0], self._stem, RT_EVENT))

            elif self.isadverb and template.isfinalevent:
                if self._word in _ADV:
                    adv = _ADV[self._word]
                    fn = DrsProduction(adv[0])
                    rs = zip(adv[1], refs)
                    fn.rename_vars(rs)
                else:
                    fn = DrsProduction(DRS([], [Rel(self._word, refs[0])]))

            #elif self.partofspeech == POS_DETERMINER and self._word == 'a':

            elif self.ispronoun and self._word in _PRON:
                pron = _PRON[self._word]
                fn = DrsProduction(pron[0], category=self.category,
                                   dep=Dependency(DRSRef('x1'), self._word, pron[1]))
                ers = complement(fn.variables, pron[2])
                ors = intersect(refs, ers)
                if len(ors) != 0:
                    # Make disjoint
                    nrs = get_new_drsrefs(ors, union(ers, refs, pron[2]))
                    fn.rename_vars(zip(ors, nrs))
                if len(ers) != 0:
                    ers = complement(fn.variables, pron[2])
                    fn.rename_vars(zip([pron[2][0], ers[0]], refs))
                else:
                    fn.rename_vars([(pron[2][0], template.final_ref)])

            elif self.ispreposition:
                if template.construct_empty:
                    fn = DrsProduction(DRS([], []))
                else:
                    fn = DrsProduction(DRS([], [Rel(self._word, refs)]))

            elif self.partofspeech == POS_PREPOSITION and self.category.test_returns_modifier() \
                    and len(refs) > 1 and not self.category.ismodifier:
                fn = DrsProduction(DRS([], [Rel(self._word, [refs[0], refs[-1]])]))

            elif final_atom == CAT_Sadj and len(refs) > 1:
                if self.category == CAT_AP_PP or self.category.ismodifier or \
                        self.category.test_returns_modifier():
                    fn = DrsProduction(DRS([], [Rel(self._word, refs[0])]))
                else:
                    conds = [Rel(self._word, refs[0])]
                    for r in refs[1:]:
                        conds.append(Rel('.ATTRIBUTE', [refs[0], r]))
                    fn = DrsProduction(DRS([], conds))

            else:
                if self.isproper_noun:
                    dep = Dependency(refs[0], self._word, RT_PROPERNAME)
                elif final_atom == CAT_N and not self.category.ismodifier \
                        and not self.category.test_returns_modifier():
                    dep = Dependency(refs[0], self._word, (RT_ENTITY | RT_PLURAL)
                                     if self.partofspeech == POS_NOUN_S else RT_ENTITY)
                else:
                    dep = None
                if template.isfinalevent:
                    if self.category == CAT_INFINITIVE:
                        fn = DrsProduction(DRS([], []))
                    elif self.partofspeech == POS_MODAL:
                        fn = DrsProduction(DRS([], [Rel(self._stem, [refs[0]]),
                                                    Rel('.MODAL', [refs[0]])]))
                    else:
                        fn = DrsProduction(DRS([], self.build_conditions([], refs, template)),
                                           properNoun=self.isproper_noun, dep=dep)
                else:
                    fn = DrsProduction(DRS([], self.build_conditions([], refs, template)),
                                       properNoun=self.isproper_noun, dep=dep)

            fn.set_lambda_refs([final_ref])
            fn.set_category(final_atom)
            for c, s in zip(compose, signatures):
                fn = c[0](s, c[1], fn)
            return fn


class Ccg2Drs(object):
    """CCG to DRS Converter"""
    debugcount = 0

    def __init__(self, options=0):
        self.xid = 10
        self.eid = 10
        self.limit = 10
        self.options = options or 0

    def final_rename(self, d):
        """Rename to ensure:
            - indexes progress is 1,2,...
            - events are tagged e, others x

        Args:
            d: A DrsProduction instance.

        Returns:
            A renamed DrsProduction instance.
        """
        # Move names to 1:...
        v = set(filter(lambda x: not x.isconst, d.variables))
        ors = filter(lambda x: x.var.idx < len(v), v)
        if len(ors) != 0:
            mx = 1 + max([x.var.idx for x in v])
            idx = [i+mx for i in range(len(ors))]
            rs = map(lambda x: (x[0], DRSRef(DRSVar(x[0].var.name, x[1]))), zip(ors, idx))
            d.rename_vars(rs)
            v = set(filter(lambda x: not x.isconst, d.variables))
            ors = filter(lambda x: x.var.idx < len(v), v)
        idx = [i+1 for i in range(len(v))]
        rs = map(lambda x: (x[0], DRSRef(DRSVar(x[0].var.name, x[1]))), zip(v, idx))
        d.rename_vars(rs)
        # Ensure events are e? refs
        while True:
            v = set(filter(lambda x: not x.isconst, d.variables))
            for x in v:
                if x.var.name == 'x':
                    fc = d.drs.find_condition(Rel('.EVENT', [x]))
                    if fc is not None:
                        d.rename_vars([(x, DRSRef(DRSVar('e',x.var.idx)))])
            break
        return d

    def rename_vars(self, d):
        """Rename to ensure variable names are disjoint.

        Args:
            d: A DrsProduction instance.

        Returns:
            A renamed DrsProduction instance.
        """
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

    def _process_ccg_node(self, pt):
        """Internal helper for recursively processing the CCG parse tree.

        See Also:
            process_ccg_pt()
        """
        dbgorig = self.debugcount
        if pt[-1] == 'T':
            head = int(pt[0][1])
            count = int(pt[0][2])
            result = Category.from_cache(pt[0][0])
            if count > 2:
                raise DrsComposeError('Non-binary node %s in parse tree' % pt[0])

            tmp = []
            cats = []
            for nd in pt[1:-1]:
                d, c = self._process_ccg_node(nd)
                if d is None:
                    head = 0
                    continue
                cats.append(c)
                tmp.append(d)

            hd = None
            extra_options = 0
            if len(tmp) == 2:
                # Special handling for proper nouns
                if tmp[0].isunify_disabled:
                    if not tmp[1].isproper_noun:
                        tmp[0].set_options(tmp[1].compose_options ^ CO_DISABLE_UNIFY)
                        tmp[1].set_options(tmp[1].compose_options & ~CO_DISABLE_UNIFY)
                    else:
                        extra_options = CO_DISABLE_UNIFY
                        tmp[1].set_options(tmp[1].compose_options | CO_DISABLE_UNIFY)
                elif tmp[1].isunify_disabled:
                    if tmp[0].category == CAT_ADJECTIVE and tmp[0].isproper_noun:
                        tmp[1].proper_noun_promote()
                    tmp[1].set_options(tmp[1].compose_options ^ CO_DISABLE_UNIFY)

                hd = tmp[head].dep
                nd = tmp[1-head].dep
                if hd is not None:
                    assert hd.head is None
                    if nd is not None:
                        assert nd.head is None
                        nd.set_head(hd)
                elif nd is not None:
                    assert nd.head is None
                    hd = nd
            elif len(tmp) == 1:
                hd = tmp[0].dep
                if tmp[0].isunify_disabled:
                    tmp[0].set_options(tmp[0].compose_options ^ CO_DISABLE_UNIFY)
            else:
                return None, result

            for nd in tmp:
                nd.set_dependency(hd)

            cl2 = ProductionList(tmp, dep=hd)
            cl2.set_options(self.options | extra_options)
            cl2.set_category(result)

            if len(cats) == 1:
                rule = get_rule(cats[0], CAT_EMPTY, result)
                if rule is None:
                    # TODO: log a warning if we succeed on take 2
                    rule = get_rule(cats[0].simplify(), CAT_EMPTY, result)
                    if rule is None:
                        raise DrsComposeError('cannot discover production rule %s <- Rule?(%s)' % (result, cats[0]))

                if rule == RL_TYPE_RAISE:
                    d = self.rename_vars(safe_create_empty_functor(result))
                    d.set_dependency(hd)
                    cl2.push_right(d)
                elif rule == RL_TCL_UNARY:
                    rule = RL_BA
                    unary = MODEL.lookup_unary(result, cats[0])
                    if unary is None and result.ismodifier and result.result_category() == cats[0]:
                        unary = MODEL.infer_unary(result)
                    if unary is None:
                        unary = MODEL.lookup_unary(result, cats[0])
                        raise DrsComposeError('cannot find unary rule (%s)\\(%s)' % (result, cats[0]))
                    d = self.rename_vars(unary.get())
                    d.set_options(cl2.compose_options)
                    d.set_dependency(hd)
                    cl2.push_right(d)
                elif rule == RL_TC_ATOM:
                    rule = RL_BA
                    d = self.rename_vars(identity_functor(Category.combine(result, '\\', cats[0])))
                    d.set_dependency(hd)
                    d.set_options(cl2.compose_options)
                    cl2.push_right(d)

                cl2 = cl2.apply(rule).unify()
                assert cl2.verify() and cl2.category.can_unify(result)
                assert result.get_scope_count() == cl2.get_scope_count()
            elif len(cats) == 2:
                # Get the production rule
                rule = get_rule(cats[0], cats[1], result)
                if rule is None:
                    # TODO: log a warning if we succeed on take 2
                    rule = get_rule(cats[0].simplify(), cats[1].simplify(), result)
                    if rule is None:
                        raise DrsComposeError('cannot discover production rule %s <- Rule?(%s,%s)' % (result, cats[0], cats[1]))

                if rule == RL_TC_CONJ:
                    d = self.rename_vars(safe_create_empty_functor(result))
                    d.set_dependency(hd)
                    d.set_options(cl2.compose_options)
                    cl2.push_right(d)
                elif rule == RL_TCL_UNARY:
                    rule = RL_BA
                    unary = MODEL.lookup_unary(result, cats[0])
                    if unary is None and result.ismodifier and result.result_category() == cats[0]:
                        unary = MODEL.infer_unary(result)
                    if unary is None:
                        raise DrsComposeError('cannot find unary rule (%s)\\(%s)' % (result, cats[0]))
                    d = self.rename_vars(unary.get())
                    d.set_dependency(hd)
                    d.set_options(cl2.compose_options)
                    cl2.push_right(d)
                elif rule == RL_TCR_UNARY:
                    rule = RL_BA
                    unary = MODEL.lookup_unary(result, cats[1])
                    if unary is None and result.ismodifier and result.result_category() == cats[1]:
                        unary = MODEL.infer_unary(result)
                    if unary is None:
                        raise DrsComposeError('cannot find unary rule (%s)\\(%s)' % (result, cats[1]))
                    d = self.rename_vars(unary.get())
                    d.set_dependency(hd)
                    d.set_options(cl2.compose_options)
                    cl2.push_right(d)
                elif rule == RL_TC_ATOM:
                    # Special rule to change atomic type
                    rule = RL_BA
                    d = self.rename_vars(identity_functor(Category.combine(result, '\\', cats[0])))
                    d.set_dependency(hd)
                    d.set_options(cl2.compose_options)
                    cl2.push_right(d)

                cl2 = cl2.apply(rule)
                if not cl2.verify() or not cl2.category.can_unify(result):
                    U = cl2.verify()
                    V = cl2.category.can_unify(result)
                    pass
                assert cl2.verify() and cl2.category.can_unify(result), 'cl2.category=%s, result=%s' % (cl2.category, result)
                assert result.get_scope_count() == cl2.get_scope_count()

            cl2.set_dependency(hd)
            if (cl2.compose_options & self.options) != self.options:
                cl2.set_options(self.options)
            return cl2, result

        # L Node in parse tree
        assert pt[-1] == 'L'
        cat = Category.from_cache(pt[0])
        if pt[0] in [',', '.', ':', ';']:
            return DrsProduction(DRS([], []), category=cat), cat

        if pt[1] in ['for']:
            pass

        ccgt = CcgTypeMapper(category=cat, word=pt[1], posTags=pt[2:-1], no_vn=0 != (self.options & CO_NO_VERBNET))
        if ccgt.category in [CAT_LRB, CAT_RRB, CAT_LQU, CAT_RQU]:
            # FIXME: start new parse tree
            return None, cat
        fn = ccgt.get_composer()
        # Rename vars so they are disjoint on creation. This help dependency manager.
        self.rename_vars(fn)

        # Special handling for proper nouns
        if fn.category == CAT_ADJECTIVE and pt[1] == '&':
            fn.set_options(self.options | CO_DISABLE_UNIFY)
        else:
            fn.set_options(self.options)

        return fn, cat

    def process_ccg_pt(self, pt):
        """Process the CCG parse tree.

        Args:
            pt: The parse tree returned from marbles.ie.drt.parse.parse_ccg_derivation().
            options: None or marbles.ie.drt.compose.CO_REMOVE_UNARY_PROPS to simplify propositions.

        Returns:
            A DrsProduction instance.

        See Also:
            marbles.ie.drt.parse.parse_ccg_derivation()
        """
        if pt is None or len(pt) == 0:
            return None
        d, _ = self._process_ccg_node(pt)
        # Handle verbs with null left arg
        if d.isfunctor and d.isarg_left:
            d = d.apply_null_left().unify()
        if not isinstance(d, DrsProduction):
            raise DrsComposeError('failed to produce a DRS - %s' % repr(d))
        d = self.final_rename(d)
        d = d.resolve_anaphora()
        if not d.ispure:
            raise DrsComposeError('failed to produce pure DRS - %s' % repr(d))
        return d


## @ingroup gfn
def process_ccg_pt(pt, options=None):
    """Process the CCG parse tree.

    Args:
        pt: The parse tree returned from marbles.ie.drt.parse.parse_ccg_derivation().
        options: None or marbles.ie.drt.compose.CO_REMOVE_UNARY_PROPS to simplify propositions.

    Returns:
        A DrsProduction instance.

    See Also:
        marbles.ie.drt.parse.parse_ccg_derivation()
    """
    builder = Ccg2Drs(options)
    if isinstance(pt[-1], unicode):
        # Convert to utf-8
        stk = [pt]
        while len(stk) != 0:
            lst = stk.pop()
            for i in range(len(lst)):
                x = lst[i]
                if isinstance(x, list):
                    stk.append(x)
                elif isinstance(x, unicode):
                    lst[i] = x.encode('utf-8')
    return builder.process_ccg_pt(pt)


## @cond
def _pt_to_ccgbank_helper(pt, lst, pretty):
    if pretty > 0:
        indent = '  ' * pretty
        indent2 = '  ' * (pretty+1)
    else:
        indent = ''
        indent2 = indent

    if pt[-1] == 'T':
        pretty += 1
        head = int(pt[0][1])
        count = int(pt[0][2])
        result = Category.from_cache(pt[0][0])

        lst.append('%s(<T %s %d %d>' % (indent, pt[0][0], head, count))

        if count == 2:
            # For binary nodes we need to check if a unary rule before recursion
            cats = []
            for nd in pt[1:-1]:
                if nd[-1] == 'T':
                    cats.append(Category.from_cache(nd[0][0]))
                else:
                    cats.append(Category.from_cache(nd[0]))
            rule = get_rule(cats[0], cats[1], result)
            if rule is None:
                rule = get_rule(cats[0].simplify(), cats[1].simplify(), result)
                assert rule is not None

            if rule == RL_TCL_UNARY:
                unary = MODEL.lookup_unary(result, cats[0])
                if unary is None and result.ismodifier and result.result_category() == cats[0]:
                    unary = MODEL.infer_unary(result)
                assert unary is not None
                template = unary.template
                lst.append('%s(<T %s %d %d>' % (indent2, result.signature, 1, 2))
                _pt_to_ccgbank_helper(pt[1], lst, pretty+1)
                lst.append('%s(<L %s %s %s %s %s>)' % (indent2+'  ', template.clean_category, 'UNARY', 'UNARY',
                                                       '.UNARY', template.predarg_category.signature))
                lst.append('%s)' % indent2)
                _pt_to_ccgbank_helper(pt[2], lst, pretty)
            elif rule == RL_TCR_UNARY:
                unary = MODEL.lookup_unary(result, cats[1])
                if unary is None and result.ismodifier and result.result_category() == cats[1]:
                    unary = MODEL.infer_unary(result)
                assert unary is not None
                template = unary.template
                _pt_to_ccgbank_helper(pt[1], lst, pretty)
                lst.append('%s(<T %s %d %d>' % (indent2, result.signature, 1, 2))
                _pt_to_ccgbank_helper(pt[2], lst, pretty+1)
                lst.append('%s(<L %s %s %s %s %s>)' % (indent2+'  ', template.clean_category, 'UNARY', 'UNARY',
                                                       '.UNARY', template.predarg_category.signature))
                lst.append('%s)' % indent2)
            else:
                _pt_to_ccgbank_helper(pt[1], lst, pretty)
                _pt_to_ccgbank_helper(pt[2], lst, pretty)
        else:
            assert count == 1
            cat = _pt_to_ccgbank_helper(pt[1], lst, pretty)
            rule = get_rule(cat, CAT_EMPTY, result)
            if rule is None:
                rule = get_rule(cat.simplify(), CAT_EMPTY, result)
                assert rule is not None

            if rule == RL_TCL_UNARY:
                unary = MODEL.lookup_unary(result, cat)
                if unary is None and result.ismodifier and result.result_category() == cat:
                    unary = MODEL.infer_unary(result)
                assert unary is not None
                template = unary.template
                lst.append('%s(<L %s %s %s %s %s>)' % (indent2, template.clean_category, 'UNARY', 'UNARY',
                                                       '.UNARY', template.predarg_category.signature))
        lst.append('%s)' % indent)
        return result

    else:
        # CcgTypeMapper will infer template if it does not exist in MODEL
        ccgt = CcgTypeMapper(category=Category.from_cache(pt[0]), word=pt[1], posTags=pt[2:4])
        if ccgt.category in [CAT_LRB, CAT_RRB, CAT_LQU, CAT_RQU]:
            lst.append('%s(<L %s %s %s %s %s>)' % (indent, pt[0], pt[2], pt[3], pt[1], pt[4]))
            return ccgt.category
        template = MODEL.lookup(ccgt.category)
        if template is None:
            lst.append('%s(<L %s %s %s %s %s>)' % (indent, pt[0], pt[2], pt[3], pt[1], pt[4]))
            return ccgt.category
        # Leaf nodes contains six fields:
        # <L CCGcat mod_POS-tag orig_POS-tag word PredArgCat>
        lst.append('%s(<L %s %s %s %s %s>)' % (indent, pt[0], pt[2], pt[3], pt[1], template.predarg_category.signature))
        return template.clean_category
## @endcond


## @ingroup gfn
def pt_to_utf8(pt):
    """Convert a parse tree to utf-8.

    Args:
        pt: The parse tree returned from marbles.ie.drt.parse.parse_ccg_derivation().

    Returns:
        A utf-8 parse tree
    """
    if isinstance(pt[-1], unicode):
        # Convert to utf-8
        stk = [pt]
        while len(stk) != 0:
            lst = stk.pop()
            for i in range(len(lst)):
                x = lst[i]
                if isinstance(x, list):
                    stk.append(x)
                elif isinstance(x, unicode):
                    lst[i] = x.encode('utf-8')
    return pt


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
    lst = []
    _pt_to_ccgbank_helper(pt, lst, 0 if fmt else -1000000)
    if fmt:
        return '\n'.join(lst)
    return ''.join(lst)


## @cond
def _process_sentence_node(pt, s):
    if pt[-1] == 'T':
        for nd in pt[1:-1]:
            # FIXME: prefer tail end recursion
            _process_sentence_node(nd, s)
    else:
        s.append(pt[1])
## @endcond


## @ingroup gfn
def sentence_from_pt(pt):
    """Get the sentence from a CCG parse tree.

    Args:
        pt: The parse tree returned from marbles.ie.drt.parse.parse_ccg_derivation().

    Returns:
        A string
    """
    s = []
    _process_sentence_node(pt, s)
    return ' '.join(s).replace(' ,', ',').replace(' .', '.')


## @cond
def _extract_predarg_categories_node(pt, lst):
    global _PredArgIdx
    if pt[-1] == 'T':
        for nd in pt[1:-1]:
            _extract_predarg_categories_node(nd, lst)
    else:
        # Leaf nodes contains six fields:
        # <L CCGcat mod_POS-tag orig_POS-tag word PredArgCat>
        # PredArgCat example: (S[dcl]\NP_3)/(S[pt]_4\NP_3:B)_4>
        catkey = Category(pt[0])

        # Ignore atoms and conj rules. Conj rules are handled by CcgTypeMapper
        if not catkey.isfunctor or catkey.result_category() == CAT_CONJ or catkey.argument_category() == CAT_CONJ:
            return

        predarg = Category(pt[4])
        assert catkey == predarg.clean(True)
        lst.append(predarg)
## @endcond


## @ingroup gfn
def extract_predarg_categories_from_pt(pt, lst=None):
    """Extract the predicate-argument categories from a CCG parse tree.

    Args:
        pt: The parse tree returned from marbles.ie.drt.parse.parse_ccg_derivation().
        lst: An optional list of existing predicate categories.
    Returns:
        A list of Category instances.
    """
    pt = pt_to_utf8(pt)
    if lst is None:
        lst = []
    _extract_predarg_categories_node(pt, lst)
    return lst


## @cond
def _extract_lexicon_helper(pt, dictionary):
    if pt[-1] == 'T':
        for nd in pt[1:-1]:
            # FIXME: prefer tail end recursion
            _extract_lexicon_helper(nd, dictionary)
    else:
        # CcgTypeMapper will infer template if it does not exist in MODEL
        ccgt = CcgTypeMapper(category=Category.from_cache(pt[0]), word=pt[1], posTags=pt[2:4])
        if len(ccgt.word) == 0 or ccgt.category.isatom or ccgt.category in [CAT_LRB, CAT_RRB, CAT_LQU, CAT_RQU]:
            return

        if ccgt.category.ismodifier and len(set(ccgt.category.extract_unify_atoms(False))) == 1:
            return

        N = ccgt.word[0].upper()
        if N not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            return

        idx = ord(N) - 0x41
        fn = ccgt.get_composer()
        template = ccgt.template
        if template is None:
            return

        if len(fn.lambda_refs) == 1:
            return

        atoms = template.predarg_category.extract_unify_atoms(False)
        refs = fn.get_unify_scopes(False)
        d = fn.pop()
        d.rename_vars(zip(refs, map(lambda x: DRSRef(x.signature), atoms)))
        rel = DRSRelation(ccgt.word)
        c = filter(lambda x: isinstance(x, Rel) and x.relation == rel, d.drs.conditions)
        if len(c) == 1:
            c = repr(c[0]) + ': ' + template.predarg_category.signature
            if ccgt.word in dictionary:
                dictionary[idx][ccgt.word].add(c)
            else:
                dictionary[idx][ccgt.word] = {c}
## @endcond


## @ingroup gfn
def extract_lexicon_from_pt(pt, dictionary=None):
    """Extract the lexicon and templates from a CCG parse tree.

    Args:
        pt: The parse tree returned from marbles.ie.drt.parse.parse_ccg_derivation().
        dictionary: An optional dictionary of a existing lexicon.
    Returns:
        A dictionary of functor instances.
    """
    pt = pt_to_utf8(pt)
    if dictionary is None:
        dictionary = map(lambda x: {}, [None]*26)
    _extract_lexicon_helper(pt, dictionary)
    return dictionary




