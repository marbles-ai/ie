# -*- coding: utf-8 -*-
"""CCG to DRS Production Generator"""

import re
import collections
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
# Useful tags
from pos import POS_DETERMINER, POS_LIST_PERSON_PRONOUN, POS_LIST_PRONOUN, POS_LIST_VERB, POS_LIST_ADJECTIVE, \
                POS_GERUND, POS_PROPER_NOUN, POS_PROPER_NOUN_S, POS_NOUN, POS_NOUN_S, POS_MODAL, POS_UNKNOWN, \
                POS_NUMBER, POS_PREPOSITION, POS_LIST_PUNCT, POS

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


def create_empty_drs_production(category, ref=None):
    """Return the empty DRS production `λx.[|]`.

    Args:
        category: A marbles.ie.ccg.ccgcat.Category instance.
        ref: optional DRSRef to use as the referent.

    Returns:
        A DrsProduction instance.
    """
    d = DrsProduction(DRS([], []), category=category)
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
        elif word.endswith("’s"):
            return word.replace("’s", '')
    return word


class Lexeme(object):

    _EventPredicates = ('.AGENT', '.THEME', '.EXTRA')
    _ToBePredicates = ('.AGENT', '.ATTRIBUTE', '.EXTRA')
    _TypeMonth = re.compile(r'^((Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?|January|February|March|April|June|July|August|September|October|November|December)$')
    _TypeWeekday = re.compile(r'^((Mon|Tue|Tues|Wed|Thur|Thurs|Fri|Sat|Sun)\.?|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)$')
    _Lemmatizer = wn.WordNetLemmatizer()
    _verbnetDB = VerbnetDB()
    _Punct= '?.,:;'

    def __init__(self, category, word, pos_tags, idx=0):

        self.head = idx
        self.dep = -1
        self.idx = idx
        self.prod = None
        self.mask = 0

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
                    self.stem = self._Lemmatizer.lemmatize(stem.decode('utf-8'), pos='v').encode('utf-8')
                else:
                    self.stem = stem

    def __repr__(self):
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
            if self._TypeMonth.match(self.stem):
                if self.stem in _MONTHS:
                    conds.append(Rel(_MONTHS[self.stem], [refs[0]]))
                else:
                    conds.append(Rel(self.stem, [refs[0]]))
                if template.isfinalevent:
                    conds.append(Rel('.DATE', refs[0:2]))
                else:
                    conds.append(Rel('.DATE', refs))
            elif self._TypeWeekday.match(self.stem):
                if self.stem in _WEEKDAYS:
                    conds.append(Rel(_WEEKDAYS[self.stem], [refs[0]]))
                else:
                    conds.append(Rel(self.stem, [refs[0]]))
                if template.isfinalevent:
                    conds.append(Rel('.DATE', refs[0:2]))
                else:
                    conds.append(Rel('.DATE', refs))
            else:
                conds.append(Rel(self.stem, [refs[0]]))
        elif self.isnumber:
            conds.append(Rel(self.stem, [refs[0]]))
            conds.append(Rel('.NUM', refs))
        elif self.pos == POS_PREPOSITION and not self.ispreposition:
            conds.append(Rel(self.stem, refs))
        else:
            conds.append(Rel(self.stem, [refs[0]]))
        return conds

    def get_production(self):
        """Get the production model for this category.

        Returns:
            A Production instance.
        """
        template = self.get_template()
        compose = None if template is None else template.constructor_rule

        if compose is None:
            # Simple type
            # Handle prepositions
            if self.category in [CAT_CONJ, CAT_NPthr]:
                if self.stem == ['or', 'nor']:
                    return OrProduction(negate=('n' in self.stem))
                return create_empty_drs_production(self.category)
            elif self.category in [CAT_CONJ_CONJ, CAT_CONJCONJ]:
                return identity_functor(self.category)
            elif self.ispronoun and self.stem in _PRON:
                pron = _PRON[self.stem]
                d = DrsProduction(pron[0], category=self.category,
                                  dep=Dependency(DRSRef('x1'), self.stem, pron[1]))
                d.set_lambda_refs(pron[2])
                return d
            elif self.category == CAT_N:
                if self.isproper_noun:
                    dep = Dependency(DRSRef('x1'), self.stem, RT_PROPERNAME)
                    d = DrsProduction(DRS([DRSRef('x1')], [Rel(self.stem, [DRSRef('x1')])]), properNoun=True, dep=dep)
                else:
                    if self.pos == POS_NOUN_S:
                        dep = Dependency(DRSRef('x1'), self.stem, RT_ENTITY | RT_PLURAL)
                    else:
                        dep = Dependency(DRSRef('x1'), self.stem, RT_ENTITY)
                    d = DrsProduction(DRS([DRSRef('x1')], [Rel(self.stem, [DRSRef('x1')])]), dep=dep)
                d.set_category(self.category)
                d.set_lambda_refs([DRSRef('x1')])
                return d
            elif self.category == CAT_NOUN:
                if self.isnumber:
                    d = DrsProduction(DRS([DRSRef('x1')], [Rel(self.stem, [DRSRef('x1')]), Rel('.NUM', [DRSRef('x1')])]),
                                      dep=Dependency(DRSRef('x1'), self.stem, RT_NUMBER))
                elif self.pos == POS_NOUN_S:
                    d = DrsProduction(DRS([DRSRef('x1')], [Rel(self.stem, [DRSRef('x1')])]),
                                      dep=Dependency(DRSRef('x1'), self.stem, RT_ENTITY | RT_PLURAL))
                else:
                    d = DrsProduction(DRS([DRSRef('x1')], [Rel(self.stem, [DRSRef('x1')])]),
                                      dep=Dependency(DRSRef('x1'), self.stem, RT_ENTITY))
                d.set_category(self.category)
                d.set_lambda_refs([DRSRef('x1')])
                return d
            elif self.category == CAT_CONJ_CONJ or self.category == CAT_CONJCONJ:
                return ProductionList(category=CAT_CONJ)
                #return identity_functor(self.category)
            elif self.isadverb and self.stem in _ADV:
                adv = _ADV[self.stem]
                d = DrsProduction(adv[0], [x for x in adv[1]])
                d.set_category(self.category)
                d.set_lambda_refs(d.drs.universe)
                return d
            else:
                d = DrsProduction(DRS([], [Rel(self.stem, [DRSRef('x')])]))
                d.set_category(self.category)
                d.set_lambda_refs([DRSRef('x')])
                return d

        # else is functor

        # Production templates use tuples so we don't accidentally modify.
        if self.category == CAT_NP_N:    # NP*/N class
            # Ignore template in these cases
            # FIXME: these relations should be added as part of build_conditions()
            if self.ispronoun and self.stem in _PRON:
                pron = _PRON[self.stem]
                fn = DrsProduction(pron[0], category=CAT_NP,
                                   dep=Dependency(DRSRef('x1'), self.stem, pron[1]))
                fn.set_lambda_refs(pron[2])
                return FunctorProduction(category=self.category, referent=pron[2], production=fn)

            else:
                if self.category == CAT_DETERMINER:
                    if self.stem in ['a', 'an']:
                        fn = DrsProduction(DRS([], [Rel('.MAYBE', [DRSRef('x1')])]), category=CAT_NP)
                    elif self.stem in ['the', 'thy']:
                        fn = DrsProduction(DRS([], [Rel('.EXISTS', [DRSRef('x1')])]), category=CAT_NP)
                    else:
                        fn = DrsProduction(DRS([], [Rel(self.stem, [DRSRef('x1')])]), category=CAT_NP)
                elif self.pos == POS_DETERMINER and self.stem in ['the', 'thy', 'a', 'an']:
                    fn = DrsProduction(DRS([], []), category=CAT_NP)
                else:
                    fn = DrsProduction(DRS([], [Rel(self.stem, [DRSRef('x1')])]), category=CAT_NP)
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
                    vnclasses = [] if self._no_vn else self._verbnetDB.name_index[self.stem]
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

                    dep = None
                    if not self.category.ismodifier and self.category.has_all_features(FEATURE_TO | FEATURE_DCL):
                        conds.append(Rel('.EVENT', [refs[0]]))
                        dep=Dependency(refs[0], self.stem, RT_EVENT)

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
                    if self.stem == 'be':
                        # Discard conditions
                        conds.extend([Rel('.EVENT', [refs[0]]), Rel('.AGENT', [refs[0], refs[1]]),
                                      Rel('.ROLE', [refs[0], refs[2]])])
                        d = DrsProduction(DRS([refs[0]], conds), category=final_atom,
                                          dep=Dependency(refs[0], self.stem, RT_EVENT))
                    else:
                        conds.append(Rel('.EVENT', [refs[0]]))
                        conds.append(Rel('.AGENT', [refs[0], refs[1]]))
                        conds.append(Rel('.ROLE', [refs[0], refs[2]]))
                        d = DrsProduction(DRS([refs[0]], conds), category=final_atom,
                                          dep=Dependency(refs[0], self.stem, RT_EVENT))
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
                                      dep=Dependency(refs[0], self.stem, RT_EVENT))
                    d.set_lambda_refs([refs[0]])
                    fn = template.create_empty_functor()
                    fn.pop()
                    fn.push(d)
                    return fn
                else:
                    # TODO: use verbnet to get semantics
                    if self.stem == 'be' and self.category.can_unify(CAT_TV):
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
                    fn = DrsProduction(DRS([refs[0]], conds), dep=Dependency(refs[0], self.stem, RT_EVENT))

            elif self.isadverb and template.isfinalevent:
                if self.stem in _ADV:
                    adv = _ADV[self.stem]
                    fn = DrsProduction(adv[0])
                    rs = zip(adv[1], refs)
                    fn.rename_vars(rs)
                else:
                    fn = DrsProduction(DRS([], [Rel(self.stem, refs[0])]))

            #elif self.pos == POS_DETERMINER and self.stem == 'a':

            elif self.ispronoun and self.stem in _PRON:
                pron = _PRON[self.stem]
                fn = DrsProduction(pron[0], category=self.category,
                                   dep=Dependency(DRSRef('x1'), self.stem, pron[1]))
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
                    fn = DrsProduction(DRS([], [Rel(self.stem, refs)]))

            elif self.pos == POS_PREPOSITION and self.category.test_returns_modifier() \
                    and len(refs) > 1 and not self.category.ismodifier:
                fn = DrsProduction(DRS([], [Rel(self.stem, [refs[0], refs[-1]])]))

            elif final_atom == CAT_Sadj and len(refs) > 1:
                if self.category == CAT_AP_PP or self.category.ismodifier or \
                        self.category.test_returns_modifier():
                    fn = DrsProduction(DRS([], [Rel(self.stem, refs[0])]))
                else:
                    conds = [Rel(self.stem, refs[0])]
                    for r in refs[1:]:
                        conds.append(Rel('.ATTRIBUTE', [refs[0], r]))
                    fn = DrsProduction(DRS([], conds))

            else:
                if self.isproper_noun:
                    dep = Dependency(refs[0], self.stem, RT_PROPERNAME)
                elif final_atom == CAT_N and not self.category.ismodifier \
                        and not self.category.test_returns_modifier():
                    dep = Dependency(refs[0], self.stem, (RT_ENTITY | RT_PLURAL)
                    if self.pos == POS_NOUN_S else RT_ENTITY)
                else:
                    dep = None
                if template.isfinalevent:
                    if self.category == CAT_INFINITIVE:
                        fn = DrsProduction(DRS([], []))
                    elif self.pos == POS_MODAL:
                        fn = DrsProduction(DRS([], [Rel(self.stem, [refs[0]]),
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


class CcgTypeMapper(object):
    """Mapping from CCG types to DRS types."""
    _EventPredicates = ('.AGENT', '.THEME', '.EXTRA')
    _ToBePredicates = ('.AGENT', '.ATTRIBUTE', '.EXTRA')
    _TypeMonth = re.compile(r'^((Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?|January|February|March|April|June|July|August|September|October|November|December)$')
    _TypeWeekday = re.compile(r'^((Mon|Tue|Tues|Wed|Thur|Thurs|Fri|Sat|Sun)\.?|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)$')
    _Lemmatizer = wn.WordNetLemmatizer()
    _verbnetDB = VerbnetDB()

    def __init__(self, lexeme, no_vn=False):
        self._no_vn = no_vn
        self._templ = None
        self._lexeme = lexeme

        # Atomic types don't need a template
        if lexeme.category.isfunctor and not MODEL.issupported(lexeme.category) \
            and lexeme.category != CAT_CONJ_CONJ and lexeme.category != CAT_CONJCONJ:
            templ = MODEL.infer_template(lexeme.category)
            if templ is not None and (lexeme.category.result_category().isfunctor or
                                      lexeme.category.argument_category().isfunctor):
                raise DrsComposeError('CCG type "%s" for word "%s" maps to unknown DRS production type' %
                                      (lexeme.category, lexeme.word))

    def __repr__(self):
        return '<' + self._lexeme.word + ' ' + str(self.partofspeech) + ' ' + self.signature + '>'

    @property
    def word(self):
        return self._lexeme.stem

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
        return self._lexeme.pos

    @property
    def signature(self):
        """Get the CCG category signature."""
        return self._lexeme.category.signature

    @property
    def category(self):
        """Get the CCG category."""
        return self._lexeme.category

    @property
    def template(self):
        return self._templ

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
            if self._TypeMonth.match(self._lexeme.stem):
                if self._lexeme.stem in _MONTHS:
                    conds.append(Rel(_MONTHS[self._lexeme.stem], [refs[0]]))
                else:
                    conds.append(Rel(self._lexeme.stem, [refs[0]]))
                if template.isfinalevent:
                    conds.append(Rel('.DATE', refs[0:2]))
                else:
                    conds.append(Rel('.DATE', refs))
            elif self._TypeWeekday.match(self._lexeme.stem):
                if self._lexeme.stem in _WEEKDAYS:
                    conds.append(Rel(_WEEKDAYS[self._lexeme.stem], [refs[0]]))
                else:
                    conds.append(Rel(self._lexeme.stem, [refs[0]]))
                if template.isfinalevent:
                    conds.append(Rel('.DATE', refs[0:2]))
                else:
                    conds.append(Rel('.DATE', refs))
            else:
                conds.append(Rel(self._lexeme.stem, [refs[0]]))
        elif self.isnumber:
            conds.append(Rel(self._lexeme.stem, [refs[0]]))
            conds.append(Rel('.NUM', refs))
        elif self.partofspeech == POS_PREPOSITION and not self.ispreposition:
            conds.append(Rel(self._lexeme.stem, refs))
        else:
            conds.append(Rel(self._lexeme.stem, [refs[0]]))
        return conds

    def get_composer(self):
        """Get the production model for this category.

        Returns:
            A Production instance.
        """
        try:
            # Special handling for prepositions
            if self.ispreposition and self._lexeme.stem in _PREPS:
                template = _PREPS[self._lexeme.stem]
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
                if self._lexeme.stem == ['or', 'nor']:
                    return OrProduction(negate=('n' in self._lexeme.stem))
                return create_empty_drs_production(self.category)
            elif self.category in [CAT_CONJ_CONJ, CAT_CONJCONJ]:
                return identity_functor(self.category)
            elif self.ispronoun and self._lexeme.stem in _PRON:
                pron = _PRON[self._lexeme.stem]
                d = DrsProduction(pron[0], category=self.category,
                                  dep=Dependency(DRSRef('x1'), self._lexeme.stem, pron[1]))
                d.set_lambda_refs(pron[2])
                return d
            elif self.category == CAT_N:
                if self.isproper_noun:
                    dep = Dependency(DRSRef('x1'), self._lexeme.stem, RT_PROPERNAME)
                    d = DrsProduction(DRS([DRSRef('x1')], [Rel(self._lexeme.stem, [DRSRef('x1')])]), properNoun=True, dep=dep)
                else:
                    if self.partofspeech == POS_NOUN_S:
                        dep = Dependency(DRSRef('x1'), self._lexeme.stem, RT_ENTITY | RT_PLURAL)
                    else:
                        dep = Dependency(DRSRef('x1'), self._lexeme.stem, RT_ENTITY)
                    d = DrsProduction(DRS([DRSRef('x1')], [Rel(self._lexeme.stem, [DRSRef('x1')])]), dep=dep)
                d.set_category(self.category)
                d.set_lambda_refs([DRSRef('x1')])
                return d
            elif self.category == CAT_NOUN:
                if self.isnumber:
                    d = DrsProduction(DRS([DRSRef('x1')], [Rel(self._lexeme.stem, [DRSRef('x1')]), Rel('.NUM', [DRSRef('x1')])]),
                                      dep=Dependency(DRSRef('x1'), self._lexeme.stem, RT_NUMBER))
                elif self.partofspeech == POS_NOUN_S:
                    d = DrsProduction(DRS([DRSRef('x1')], [Rel(self._lexeme.stem, [DRSRef('x1')])]),
                                      dep=Dependency(DRSRef('x1'), self._lexeme.stem, RT_ENTITY | RT_PLURAL))
                else:
                    d = DrsProduction(DRS([DRSRef('x1')], [Rel(self._lexeme.stem, [DRSRef('x1')])]),
                                      dep=Dependency(DRSRef('x1'), self._lexeme.stem, RT_ENTITY))
                d.set_category(self.category)
                d.set_lambda_refs([DRSRef('x1')])
                return d
            elif self.category == CAT_CONJ_CONJ or self.category == CAT_CONJCONJ:
                return ProductionList(category=CAT_CONJ)
                #return identity_functor(self.category)
            elif self.isadverb and self._lexeme.stem in _ADV:
                adv = _ADV[self._lexeme.stem]
                d = DrsProduction(adv[0], [x for x in adv[1]])
                d.set_category(self.category)
                d.set_lambda_refs(d.drs.universe)
                return d
            else:
                d = DrsProduction(DRS([], [Rel(self._lexeme.stem, [DRSRef('x')])]))
                d.set_category(self.category)
                d.set_lambda_refs([DRSRef('x')])
                return d

        # else is functor

        # Production templates use tuples so we don't accidentally modify.
        if self.category == CAT_NP_N:    # NP*/N class
            # Ignore template in these cases
            # FIXME: these relations should be added as part of build_conditions()
            if self.ispronoun and self._lexeme.stem in _PRON:
                pron = _PRON[self._lexeme.stem]
                fn = DrsProduction(pron[0], category=CAT_NP,
                                   dep=Dependency(DRSRef('x1'), self._lexeme.stem, pron[1]))
                fn.set_lambda_refs(pron[2])
                return FunctorProduction(category=self.category, referent=pron[2], production=fn)

            else:
                if self.category == CAT_DETERMINER:
                    if self._lexeme.stem in ['a', 'an']:
                        fn = DrsProduction(DRS([], [Rel('.MAYBE', [DRSRef('x1')])]), category=CAT_NP)
                    elif self._lexeme.stem in ['the', 'thy']:
                        fn = DrsProduction(DRS([], [Rel('.EXISTS', [DRSRef('x1')])]), category=CAT_NP)
                    else:
                        fn = DrsProduction(DRS([], [Rel(self._lexeme.stem, [DRSRef('x1')])]), category=CAT_NP)
                elif self.partofspeech == POS_DETERMINER and self._lexeme.stem in ['the', 'thy', 'a', 'an']:
                    fn = DrsProduction(DRS([], []), category=CAT_NP)
                else:
                    fn = DrsProduction(DRS([], [Rel(self._lexeme.stem, [DRSRef('x1')])]), category=CAT_NP)
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
                    vnclasses = [] if self._no_vn else self._verbnetDB.name_index[self._lexeme.stem]
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
                        conds.append(Imp(DRS([], [Rel(self._lexeme.stem, [refs[0]])]), DRS([], [vncond])))
                    else:
                        conds.append(Rel(self._lexeme.stem, [refs[0]]))

                except Exception:
                    conds.append(Rel(self._lexeme.stem, [refs[0]]))
                    pass
                if (self.category.iscombinator and self.category.has_any_features(FEATURE_PSS | FEATURE_TO)) \
                            or self.category.ismodifier:

                    dep = None
                    if not self.category.ismodifier and self.category.has_all_features(FEATURE_TO | FEATURE_DCL):
                        conds.append(Rel('.EVENT', [refs[0]]))
                        dep=Dependency(refs[0], self._lexeme.stem, RT_EVENT)

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
                    if self._lexeme.stem == 'be':
                        # Discard conditions
                        conds.extend([Rel('.EVENT', [refs[0]]), Rel('.AGENT', [refs[0], refs[1]]),
                                      Rel('.ROLE', [refs[0], refs[2]])])
                        d = DrsProduction(DRS([refs[0]], conds), category=final_atom,
                                          dep=Dependency(refs[0], self._lexeme.stem, RT_EVENT))
                    else:
                        conds.append(Rel('.EVENT', [refs[0]]))
                        conds.append(Rel('.AGENT', [refs[0], refs[1]]))
                        conds.append(Rel('.ROLE', [refs[0], refs[2]]))
                        d = DrsProduction(DRS([refs[0]], conds), category=final_atom,
                                          dep=Dependency(refs[0], self._lexeme.stem, RT_EVENT))
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
                                      dep=Dependency(refs[0], self._lexeme.stem, RT_EVENT))
                    d.set_lambda_refs([refs[0]])
                    fn = template.create_empty_functor()
                    fn.pop()
                    fn.push(d)
                    return fn
                else:
                    # TODO: use verbnet to get semantics
                    if self._lexeme.stem == 'be' and self.category.can_unify(CAT_TV):
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
                    fn = DrsProduction(DRS([refs[0]], conds), dep=Dependency(refs[0], self._lexeme.stem, RT_EVENT))

            elif self.isadverb and template.isfinalevent:
                if self._lexeme.stem in _ADV:
                    adv = _ADV[self._lexeme.stem]
                    fn = DrsProduction(adv[0])
                    rs = zip(adv[1], refs)
                    fn.rename_vars(rs)
                else:
                    fn = DrsProduction(DRS([], [Rel(self._lexeme.stem, refs[0])]))

            #elif self.partofspeech == POS_DETERMINER and self._lexeme.stem == 'a':

            elif self.ispronoun and self._lexeme.stem in _PRON:
                pron = _PRON[self._lexeme.stem]
                fn = DrsProduction(pron[0], category=self.category,
                                   dep=Dependency(DRSRef('x1'), self._lexeme.stem, pron[1]))
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
                    fn = DrsProduction(DRS([], [Rel(self._lexeme.stem, refs)]))

            elif self.partofspeech == POS_PREPOSITION and self.category.test_returns_modifier() \
                    and len(refs) > 1 and not self.category.ismodifier:
                fn = DrsProduction(DRS([], [Rel(self._lexeme.stem, [refs[0], refs[-1]])]))

            elif final_atom == CAT_Sadj and len(refs) > 1:
                if self.category == CAT_AP_PP or self.category.ismodifier or \
                        self.category.test_returns_modifier():
                    fn = DrsProduction(DRS([], [Rel(self._lexeme.stem, refs[0])]))
                else:
                    conds = [Rel(self._lexeme.stem, refs[0])]
                    for r in refs[1:]:
                        conds.append(Rel('.ATTRIBUTE', [refs[0], r]))
                    fn = DrsProduction(DRS([], conds))

            else:
                if self.isproper_noun:
                    dep = Dependency(refs[0], self._lexeme.stem, RT_PROPERNAME)
                elif final_atom == CAT_N and not self.category.ismodifier \
                        and not self.category.test_returns_modifier():
                    dep = Dependency(refs[0], self._lexeme.stem, (RT_ENTITY | RT_PLURAL)
                                     if self.partofspeech == POS_NOUN_S else RT_ENTITY)
                else:
                    dep = None
                if template.isfinalevent:
                    if self.category == CAT_INFINITIVE:
                        fn = DrsProduction(DRS([], []))
                    elif self.partofspeech == POS_MODAL:
                        fn = DrsProduction(DRS([], [Rel(self._lexeme.stem, [refs[0]]),
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


OP_NOP = 0
OP_PUSH = 1
OP_EXEC = 2

class AbstractOperand(object):

    def __init__(self, operation, idx, depth):
        self.op = operation
        self.idx = idx
        self.depth = depth

    @property
    def category(self):
        raise NotImplementedError


class PushOp(AbstractOperand):

    def __init__(self, lexeme, idx, depth):
        super(PushOp, self).__init__(OP_PUSH, idx, depth)
        self.lexeme = lexeme

    def __repr__(self):
        if self.lexeme.prod:
            return '<PushOp>:(%s, %s, %s)' % (repr(self.lexeme.prod), self.lexeme.category, self.lexeme.pos)
        return '<PushOp>:(%s, %s, %s)' % (self.lexeme.stem, self.lexeme.category, self.lexeme.pos)

    @property
    def category(self):
        return self.lexeme.category


class ExecOp(AbstractOperand):

    def __init__(self, idx, sub_ops, head, result_category, rule, lex_range, op_range, depth):
        super(ExecOp, self).__init__(OP_EXEC, idx, depth)
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


class Ccg2Drs(object):
    """CCG to DRS Converter"""
    debugcount = 0
    _verbnetDB = VerbnetDB()

    def __init__(self, options=0):
        self.xid = 10
        self.eid = 10
        self.limit = 10
        self.options = options or 0
        self.exeque = []
        self.lexque = []
        self.depth = -1

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

    def create_drs(self):

        # First create all productions up front
        prods = []
        for lexeme in self.lexque:
            if lexeme.category.ispunct:
                lexeme.prod = DrsProduction(DRS([], []), category=lexeme.category)
                lexeme.prod.set_lambda_refs([DRSRef(DRSVar('x', self.xid+1))])
                self.xid += 1
                lexeme.prod.set_options(self.options)
            elif lexeme.category in [CAT_LRB, CAT_RRB, CAT_LQU, CAT_RQU]:
                lexeme.prod = DrsProduction(DRS([], []), category=CAT_EMPTY)
                lexeme.prod.set_lambda_refs([DRSRef(DRSVar('x', self.xid+1))])
                self.xid += 1
                lexeme.prod.set_options(self.options)
            else:
                lexeme.prod = self.rename_vars(lexeme.get_production())
                lexeme.prod.set_options(self.options)

        # TODO: Defer special handling of proper nouns

        # Process exec queue
        stk = []
        for op in self.exeque:
            if isinstance(op, PushOp):
                stk.append(op.lexeme.prod)
            elif len(op.sub_ops) == 2:
                assert len(stk) >= 2
                if op.rule == RL_TCL_UNARY:
                    unary = MODEL.lookup_unary(op.category, op.sub_ops[0].category)
                    if unary is None and op.category.ismodifier and op.category.result_category() == op.sub_ops[0].category:
                        unary = MODEL.infer_unary(op.category)
                    assert unary is not None
                    nlst = ProductionList()
                    nlst.set_options(self.options)
                    nlst.push_right(stk.pop())      # arg 1
                    nlst.push_right(stk.pop())      # arg 0
                    fn = self.rename_vars(unary.get())
                    fn.set_options(self.options)
                    nlst.push_right(fn)
                    nlst.set_category(op.category)
                    stk.append(nlst.apply(RL_BA))

                elif op.rule == RL_TCR_UNARY:
                    unary = MODEL.lookup_unary(op.category, op.sub_ops[1].category)
                    if unary is None and op.category.ismodifier and op.category.result_category() == op.sub_ops[1].category:
                        unary = MODEL.infer_unary(op.category)
                    assert unary is not None
                    nlst = ProductionList()
                    nlst.set_options(self.options)
                    nlst.push_left(stk.pop())  # arg 1
                    nlst.push_left(stk.pop())  # arg 0
                    fn = self.rename_vars(unary.get())
                    fn.set_options(self.options)
                    nlst.push_right(fn)
                    nlst.set_category(op.category)
                    stk.append(nlst.apply(RL_BA))

                elif op.rule == RL_TC_CONJ:
                    fn = self.rename_vars(safe_create_empty_functor(op.category))
                    nlst = ProductionList()
                    nlst.set_options(self.options)
                    nlst.set_category(op.category)
                    if op.sub_ops[0].category == CAT_CONJ:
                        nlst.push_left(stk.pop())  # arg1
                        nlst.push_left(stk.pop())  # arg0
                    else:
                        nlst.push_right(stk.pop())  # arg1
                        nlst.push_right(stk.pop())  # arg0

                    nlst.push_right(fn)
                    stk.append(nlst.apply(op.rule))

                elif op.rule == RL_TC_ATOM:
                    # Special rule to change atomic type
                    assert False
                else:
                    nlst = ProductionList()
                    nlst.set_options(self.options)
                    nlst.set_category(op.category)
                    nlst.push_left(stk.pop())   # arg1
                    nlst.push_left(stk.pop())   # arg0
                    stk.append(nlst.apply(op.rule))

            # Unary rules
            elif op.rule == RL_TCL_UNARY:
                unary = MODEL.lookup_unary(op.category, op.sub_ops[0].category)
                if unary is None and op.category.ismodifier and op.category.result_category() == op.sub_ops[0].category:
                    unary = MODEL.infer_unary(op.category)
                assert unary is not None
                nlst = ProductionList()
                nlst.set_options(self.options)
                # reverse order
                nlst.push_right(stk.pop())
                fn = self.rename_vars(unary.get())
                fn.set_options(self.options)
                nlst.push_right(fn)
                nlst.set_category(op.category)
                stk.append(nlst.apply(RL_BA))

            elif op.rule == RL_TC_ATOM:
                # Special rule to change atomic type
                d = stk.pop()
                fn = self.rename_vars(identity_functor(Category.combine(op.category, '\\', d.category)))
                fn.set_options(self.options)
                nlst = ProductionList()
                nlst.set_options(self.options)
                nlst.set_category(op.category)
                nlst.push_right(d)
                nlst.push_right(fn)
                stk.append(nlst.apply(RL_BA))

            elif op.rule == RL_TC_CONJ:
                fn = self.rename_vars(safe_create_empty_functor(op.category))
                nlst = ProductionList()
                nlst.set_options(self.options)
                nlst.set_category(op.category)
                nlst.push_right(stk.pop())
                nlst.push_right(fn)
                stk.append(nlst.apply(op.rule))

            elif op.rule == RL_TYPE_RAISE:
                fn = self.rename_vars(safe_create_empty_functor(op.category))
                nlst = ProductionList()
                nlst.set_options(self.options)
                nlst.set_category(op.category)
                nlst.push_right(stk.pop())
                nlst.push_right(fn)
                stk.append(nlst.apply(op.rule))

            else:
                nlst = ProductionList()
                nlst.set_options(self.options)
                nlst.set_category(op.category)
                nlst.push_right(stk.pop())
                stk.append(nlst.apply(op.rule))

            assert stk[-1].verify() and stk[-1].category.can_unify(op.category)
            assert op.category.get_scope_count() == stk[-1].get_scope_count(), "result-category=%s, prod=%s" % \
                                                                               (op.category, stk[-1])

        assert len(stk) == 1
        if stk[0].isfunctor and stk[0].isarg_left:
            return stk[0].apply_null_left().unify()
        return stk[0]

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

        lexeme = Lexeme(category=cat, word=pt[1], pos_tags=pt[2:4])
        ccgt = CcgTypeMapper(lexeme, no_vn=0 != (self.options & CO_NO_VERBNET))
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

    def build_execution_sequence(self, pt):
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
        assert len(self.exeque) != 0 and len(self.lexque) != 0
        assert isinstance(self.exeque[0], PushOp)

        # Process exec queue
        stk = collections.deque()
        indent = '  ' if pretty else ''
        sep = '\n' if pretty else ' '
        for op in self.exeque:
            indent = '  ' * op.depth if pretty else ''
            if isinstance(op, PushOp):

                # Leaf nodes contain six fields:
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
                    nlst.append('(%s<T %s %d %d>' % (indent, op.category, 1, 2))
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
    ccg = Ccg2Drs(options)
    pt = pt_to_utf8(pt)
    ccg.build_execution_sequence(pt)
    d = ccg.create_drs()
    d = ccg.final_rename(d)
    return d.resolve_anaphora()


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
        lexeme = Lexeme(category=pt[0], word=pt[1], pos_tags=pt[2:4])
        ccgt = CcgTypeMapper(lexeme)
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
    ccg = Ccg2Drs()
    ccg.build_execution_sequence(pt)
    s = ccg.get_predarg_ccgbank(fmt)
    return s
    '''
    lst = []
    _pt_to_ccgbank_helper(pt, lst, 0 if fmt else -1000000)
    if fmt:
        return '\n'.join(lst)
    return ''.join(lst)
    '''


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
class LexiconExtractor(object):
    def __init__(self, dictionary, uid):
        self.dictionary = dictionary
        self.uid = uid

    def run(self, pt):
        if pt[-1] == 'T':
            for nd in pt[1:-1]:
                # FIXME: prefer tail end recursion
                self.run(nd)
        else:
            # CcgTypeMapper will infer template if it does not exist in MODEL
            lexeme = Lexeme(category=pt[0], word=pt[1], pos_tags=pt[2:4])
            ccgt = CcgTypeMapper(lexeme)
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
                if ccgt.word in self.dictionary:
                    lst = self.dictionary[idx][ccgt.word]
                    lst[0].add(c)
                    lst[1].add(self.uid)
                else:
                    self.dictionary[idx][ccgt.word] = [{c}, {self.uid}]
## @endcond


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
    extractor = LexiconExtractor(dictionary, uid or '')
    extractor.run(pt)
    return dictionary


