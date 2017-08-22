# -*- coding: utf-8 -*-
"""CCG to DRS Production Generator"""

from __future__ import unicode_literals, print_function

import inflect
from nltk.stem import wordnet as wn

from marbles.ie.ccg import *
from marbles.ie.ccg.model import MODEL
from marbles.ie.drt.common import DRSVar, SHOW_SET, Showable
from marbles.ie.drt.drs import DRS, DRSRef, Rel, Or, Imp
from marbles.ie.drt.drs import get_new_drsrefs
from marbles.ie.drt.utils import remove_dups, union, complement, intersect
from marbles.ie.kb.verbnet import VERBNETDB
from marbles import safe_utf8_decode, safe_utf8_encode
from marbles.ie.core.constants import *
from marbles.ie.core.exception import TemplateRuleError, _UNDEFINED_TEMPLATES
from marbles.ie.core.sentence import Span, AbstractLexeme
from marbles.ie.semantics.compose import FunctorProduction, DrsProduction, DrsComposeError, identity_functor
from marbles.ie.parse import parse_drs


FEATURE_VARG = FEATURE_PSS | FEATURE_NG | FEATURE_EM | FEATURE_DCL | FEATURE_TO | FEATURE_B | FEATURE_BEM
FEATURE_VRES = FEATURE_NG | FEATURE_EM | FEATURE_DCL | FEATURE_B |FEATURE_BEM


## @cond
# The pronouns must always be referent X1
__pron = [
    # word          final       DRS             Properties
    #               referent
    # 1st person singular
    ('i',           'X1',       '([],[i(X1)])', RT_HUMAN|RT_1P),
    ('me',          'X1',       '([],[i(X1)])', RT_HUMAN|RT_1P),
    ('myself',      'X1',       '([],[i(X1),_REFLEX(X1)])', RT_HUMAN|RT_1P),
    ('mine',        'X2',       '([],[i(X1),_POSS(X1,X2)])', RT_HUMAN|RT_1P|RT_POSSESSIVE),
    ('my',          'X2',       '([],[i(X1),_POSS(X1,X2)])', RT_HUMAN|RT_1P|RT_POSSESSIVE),
    # 2nd person singular
    ('you',         'X1',       '([],[you(X1)])', RT_HUMAN|RT_2P),
    ('yourself',    'X1',       '([],[you(X1),_REFLEX(X1)])', RT_HUMAN|RT_2P),
    ('yours',       'X2',       '([],[you(X1),_OWN(X1,X2)])', RT_HUMAN|RT_2P),
    ('your',        'X2',       '([],[you(X1),_POSS(X1,X2)])', RT_HUMAN|RT_2P|RT_POSSESSIVE),
    # 3rd person singular
    ('he',          'X1',       '([],[he(X1)])', RT_HUMAN|RT_MALE|RT_ANAPHORA|RT_3P),
    ('she',         'X1',       '([],[she(X1)])', RT_HUMAN|RT_FEMALE|RT_ANAPHORA|RT_3P),
    ('him',         'X1',       '([],[he(X1)])', RT_HUMAN|RT_MALE|RT_ANAPHORA|RT_3P),
    ('her',         'X1',       '([],[she(X1)])', RT_HUMAN|RT_FEMALE|RT_ANAPHORA|RT_3P),
    ('himself',     'X1',       '([],[he(X1),_REFLEX(X1)])', RT_HUMAN|RT_MALE|RT_ANAPHORA|RT_3P),
    ('herself',     'X1',       '([],[she(X1),_REFLEX(X1)])', RT_HUMAN|RT_FEMALE|RT_ANAPHORA|RT_3P),
    ('hisself',     'X1',       '([],[he(X1),_REFLEX(X1)])', RT_HUMAN|RT_MALE|RT_ANAPHORA|RT_3P),
    ('his',         'X2',       '([],[he(X1),_POSS(X1,X2)])', RT_HUMAN|RT_MALE|RT_ANAPHORA|RT_3P|RT_POSSESSIVE),
    ('hers',        'X2',       '([],[she(X1),_POSS(X1,X2)])', RT_HUMAN|RT_FEMALE|RT_ANAPHORA|RT_3P|RT_POSSESSIVE),
    # 1st person plural
    ('we',          'X1',       '([],[we(X1)])', RT_HUMAN|RT_PLURAL|RT_1P),
    ('us',          'X1',       '([],[we(X1)])', RT_HUMAN|RT_PLURAL|RT_1P),
    ('ourself',     'X1',       '([],[we(X1),_REFLEX(X1)])', RT_HUMAN|RT_PLURAL|RT_1P),
    ('ourselves',   'X1',       '([],[we(X1),_REFLEX(X1)])', RT_HUMAN|RT_PLURAL|RT_1P),
    ('ours',        'X2',       '([],[we(X1),_POSS(X1,X2)])', RT_HUMAN|RT_PLURAL|RT_1P|RT_POSSESSIVE),
    ('our',         'X2',       '([],[we(X1),_POSS(X1,X2)])', RT_HUMAN|RT_PLURAL|RT_1P|RT_POSSESSIVE),
    # 2nd person plural
    ('yourselves',  'X1',       '([],[you(X1),_REFLEX(X1)])', RT_HUMAN|RT_PLURAL|RT_2P),
    # 3rd person plural
    ('they',        'X1',       '([],[they(X1)])', RT_HUMAN|RT_PLURAL|RT_3P),
    ('them',        'X1',       '([],[they(X1)])', RT_HUMAN|RT_PLURAL|RT_3P),
    ('themself',    'X1',       '([],[they(X1),_REFLEX(X1)])', RT_HUMAN|RT_PLURAL|RT_3P),
    ('themselves',  'X1',       '([],[they(X1),_REFLEX(X1)])', RT_HUMAN|RT_PLURAL|RT_3P),
    ('theirs',      'X2',       '([],[they(X1),_POSS(X1,X2)])', RT_HUMAN|RT_PLURAL|RT_3P|RT_POSSESSIVE),
    ('their',       'X2',       '([],[they(X1),_POSS(X1,X2)])', RT_HUMAN|RT_PLURAL|RT_3P|RT_POSSESSIVE),
    # it
    ('it',          'X1',       '([],[it(X1)])', RT_ANAPHORA|RT_3P),
    ('its',         'X2',       '([],[it(X1),_POSS(X1,X2)])', RT_ANAPHORA|RT_3P|RT_POSSESSIVE),
    ('itself',      'X1',       '([],[it(X1),_REFLEX(X1)])', RT_ANAPHORA|RT_3P),
]
_PRON = {}
for k,r,v,u in __pron:
    _PRON[k] = (parse_drs(v, 'nltk'), u, [DRSRef(r)])


__adv = [
    # word      final       DRS                                 Properties
    #           referent
    ('up',      'E1',       '([],[up(E1),direction(E1)])',      RT_LOCATION),
    ('down',    'E1',       '([],[down(E1),direction(E1)])',    RT_LOCATION),
    ('left',    'E1',       '([],[left(E1),direction(E1)])',    RT_LOCATION),
    ('right',   'E1',       '([],[right(E1),direction(E1)])',   RT_LOCATION),
]
_ADV = {}
for k,r,v,u in __adv:
    _ADV[k] = (parse_drs(v, 'nltk'), u, [DRSRef(r)])

# Special behavior for prepositions
_PREPS = {
    'of':           MODEL.build_template(r'PP_1002/NP_2002', construct_empty=False)[1],
    'on':           MODEL.build_template(r'PP_1002/NP_2002', construct_empty=False)[1],
    'between':      MODEL.build_template(r'PP_1002/NP_2002', construct_empty=False)[1],
    'with':         MODEL.build_template(r'PP_1002/NP_2002', construct_empty=False)[1],
    'without':      MODEL.build_template(r'PP_1002/NP_2002', construct_empty=False)[1],
    'about':        MODEL.build_template(r'PP_1002/NP_2002', construct_empty=False)[1],
    'among':        MODEL.build_template(r'PP_1002/NP_2002', construct_empty=False)[1],
    'despite':      MODEL.build_template(r'PP_1002/NP_2002', construct_empty=False)[1],
    'except':       MODEL.build_template(r'PP_1002/NP_2002', construct_empty=False)[1],
    'regarding':    MODEL.build_template(r'PP_1002/NP_2002', construct_empty=False)[1],
}


_RELPRON = {
    'that', 'when', 'which', 'whichever', 'whichsoever', 'who', 'whoever',
    'whosoever', 'whom', 'whomever', 'whomsoever', 'whose', 'whosesoever',
    'whatever', 'whatsoever'
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
    'Dec':  'December',
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

CAT_NPnbN_NP = Category.from_cache(r'(NP[nb]/N)\NP')
CAT_NPN_NP = Category.from_cache(r'(NP/N)\NP')
CAT_NPP = Category.from_cache(r'N/PP')

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


## @ingroup gfn
def create_empty_drs_production(category, ref=None, span=None):
    """Return the empty DRS production `λx.[|]`.

    Args:
        category: A marbles.ie.ccg.ccgcat.Category instance.
        ref: optional DRSRef to use as the referent.

    Returns:
        A DrsProduction instance.
    """
    d = DrsProduction([], [], category=category, span=span)
    if ref is None:
        ref = DRSRef('X1')
    d.set_lambda_refs([ref])
    return d

EventPredicates = ('_ARG0', '_ARG1', '_ARG2', '_ARG3', '_ARG4', '_ARG5')
_TypeMonth = re.compile(r'^((Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?|January|February|March|April|June|July|August|September|October|November|December)$')
_TypeWeekday = re.compile(r'^((Mon|Tue|Tues|Wed|Thur|Thurs|Fri|Sat|Sun)\.?|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)$')
_Punct= '?.,:;'
_Wnl = wn.WordNetLemmatizer()
_Ieng = inflect.engine()

class Lexeme(AbstractLexeme):

    def get_json(self):
        result = {
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
        if self.wiki_data:
            result['wiki'] = self.wiki_data.get_json()
        return result

    def __init__(self, category, word, pos_tags, idx=0):
        global _Punct, _Ieng, _Wnl
        if isinstance(Category, Lexeme):
            super(Lexeme, self).__init__(category)
            self.conditions = None
            self.wnsynsets = None
            self.vnclasses = None

            return
        else:
            super(Lexeme, self).__init__()
        self.head = idx
        self.idx = idx
        #self.variables = None
        self.conditions = None
        self.wnsynsets = None
        self.vnclasses = None
        # Done in base class
        #self.mask = 0
        #self.refs = []
        #self.drs = None

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
        elif word == "'s" and self.pos is not POS_POSSESSIVE \
                and not self.category.ismodifier and self.category.test_return(CAT_VP):
            word = 'is'
        elif word == "'nt":
            word = 'not'

        if word in _Punct:
            self.word = word
            self.stem = word
        else:
            # TODO: should lookup nouns via conceptnet or wordnet
            self.word = word
            wd = strip_apostrophe_s(word)
            if (self.category == CAT_NOUN or self.pos == POS_NOUN or self.pos == POS_NOUN_S) and wd.upper() == wd:
                # If all uppercase then keep it that way
                self.stem = word.rstrip(_Punct)
            elif self.pos == POS_PROPER_NOUN or self.pos == POS_PROPER_NOUN_S:
                # Proper noun
                if wd.upper() == wd:
                    self.stem = word.rstrip(_Punct)
                else:
                    self.stem = word.title().rstrip(_Punct)
            else:
                stem = word.lower().rstrip(_Punct)
                if self.pos in POS_LIST_VERB or self.pos == POS_GERUND:
                    # FIXME: move to python 3 so its all unicode
                    if isinstance(stem, unicode):
                        self.stem = _Wnl.lemmatize(stem, pos='v')
                    else:
                        self.stem = _Wnl.lemmatize(stem.decode('utf-8'), pos='v').encode('utf-8')
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
        return self.category.test_return(CAT_PP, True) or self.category.test_return(CAT_Sfor, True)
        #return self.category == CAT_PREPOSITION

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

    def promote_to_propernoun(self):
        """Promote an entity to a proper noun."""
        if 0 == (self.mask & RT_PROPERNAME):
            self.stem = self.word.title()
            self.mask &= ~RT_ENTITY
            self.mask |= RT_PROPERNAME
            self.drs = DRS(self.drs.referents, [Rel(self.stem, self.drs.referents)])

    def clone(self):
        return Lexeme(self, None, None)

    def get_template(self):
        """Get the functor template for the lexeme.

        Returns:
            A marbles.ie.ccg.model.FunctorTemplate instance or None if the self.category is an atom or a simple
            functor. Simple functors are functors where the argument and result categories are both atoms.

        Raises:
            DrsComposeError

        See Also:
            marbles.ie.ccg.Category
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

    def _build_conditions(self, conds, binary, template):
        """Refs are reversed, refs[0] is the functor return value.

        Args:
            conds: The existing DRS conditions.
            binary: Binary refs
            template: A FunctorTemplate instance.

        Returns:
            The modified conditions.
        """

        # Note. Proper noun handling requires any extra predicates appear after the noun.
        global _TypeMonth, _TypeWeekday
        if self.isproper_noun:
            # If we are a functor and a proper noun then argument type if the
            # correct referent for the noun
            if _TypeMonth.match(self.stem):
                self.mask |= RT_DATE
                if self.stem in _MONTHS:
                    conds.append(Rel(_MONTHS[self.stem], [self.refs[0]]))
                else:
                    conds.append(Rel(self.stem, [self.refs[0]]))
                #if template.isfinalevent:
                #    conds.append(Rel('_DATE', self.refs[0:2]))
                #else:
                #    conds.append(Rel('_DATE', self.refs[0]))
                conds.append(Rel('_DATE', self.refs[0]))
            elif _TypeWeekday.match(self.stem):
                self.mask |= RT_DATE
                if self.stem in _WEEKDAYS:
                    conds.append(Rel(_WEEKDAYS[self.stem], [self.refs[0]]))
                else:
                    conds.append(Rel(self.stem, [self.refs[0]]))
                #if template.isfinalevent:
                #    conds.append(Rel('_DATE', self.refs[0:2]))
                #else:
                #    conds.append(Rel('_DATE', self.refs[0]))
                conds.append(Rel('_DATE', self.refs[0]))
            else:
                conds.append(Rel(self.stem, [self.refs[0]]))
        elif self.isnumber:
            self.mask |= RT_NUMBER
            conds.append(Rel(self.stem, [self.refs[0]]))
            conds.append(Rel('_NUM', self.refs[0]))
        elif self.ispunct:
            if binary is not None:
                if self.word == ':':
                    conds.append(Rel('_IE', binary))
                elif self.word == ';':
                    conds.append(Rel('_LINK', binary))
        #elif self.pos == POS_PREPOSITION and not self.ispreposition:
        #    if len(self.refs) > 1:
        #        conds.append(Rel(self.stem, [self.refs[0], self.refs[-1]]))
        #    else:
        #        conds.append(Rel(self.stem, self.refs))
        elif binary is not None:
            if self.pos == POS_POSSESSIVE:
                self.mask |= RT_POSSESSIVE
                conds.append(Rel('_POSS', binary))
            else:
                conds.append(Rel(self.stem, binary))
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
        global _Wnl, _Ieng
        if not self.isproper_noun and not self.pos == POS_POSSESSIVE:
            # TODO: cache nouns
            # pattern.en.pluralize(self.stem)
            # or use inflect https://pypi.python.org/pypi/inflect
            if self.stem == "'s":
                sp = self.stem
            # inflect will generate an exception for single character nouns. This can happen for
            # bad pos tagging (like EasySRL)
            elif len(self.stem) > 1:
                sp = _Ieng.plural(self.stem)
            self.wnsynsets = wn.wordnet.synsets(_Wnl.lemmatize(self.stem.lower(), 'n'), pos='n')
            if False and self.stem != sp:
                # TODO: track these
                rp = DRSRef(DRSVar('X', len(self.refs)+1))
                self.drs = DRS([self.refs[0], rp],
                               [Rel(self.stem, [self.refs[0]]), Rel(sp, [rp]), Rel('_ISMEMBER', [self.refs[0], rp])])
                d = DrsProduction([self.refs[0], rp], self.refs[1:], category=self.category, span=span)
                d.set_lambda_refs([self.refs[0]])
                return d

        self.drs = DRS([self.refs[0]], [Rel(self.stem, [self.refs[0]])])
        d = DrsProduction([self.refs[0]], self.refs[1:], category=self.category, span=span)
        d.set_lambda_refs([self.refs[0]])
        return d

    def _set_noun_mask(self):
        if self.isnumber:
            self.mask |= RT_NUMBER
        elif self.isproper_noun:
            self.mask |= RT_PROPERNAME
        elif self.pos == POS_NOUN_S:
            self.mask |= RT_ENTITY | RT_PLURAL
        else:
            self.mask |= RT_ENTITY
        if self.pos == POS_POSSESSIVE:
            self.mask |= RT_POSSESSIVE

    def get_production(self, sentence, options=0):
        """Get the production model for this category.

        Returns:
            A Production instance.
        """
        global EventPredicates
        no_vn = 0 != (CO_NO_VERBNET & options)
        span = Span(sentence, [self.idx])
        template = self.get_template()

        # Ensure we only have one instance for each referent name. FunctorTemplate's guarantee
        # this. This allows fast renaming by changing the DRSVar embedded in the DRSRef.
        #
        # To take advantage of fast renaming we need to do one rename post functor creation.

        if template is None:
            if self.category.isfunctor and self.category not in [CAT_CONJ_CONJ, CAT_CONJCONJ]:
                _UNDEFINED_TEMPLATES.add(self.category)
                raise TemplateRuleError('missing template for category %s' % self.category)
            # Simple type
            # Handle prepositions
            if self.category in [CAT_CONJ, CAT_NPthr]:
                self.refs = [DRSRef('X1')]
                if self.stem == 'or':
                    self.mask |= RT_UNION
                elif self.stem == 'nor':
                    self.mask |= RT_UNION | RT_NEGATE
                elif self.stem == 'and':
                    self.mask |= RT_INTERSECTION
                # If self.drs is None then we don't include in constituents
                self.drs = DRS([], [])
                return create_empty_drs_production(self.category, self.refs[0], span=span)
            elif self.category in [CAT_CONJ_CONJ, CAT_CONJCONJ]:
                self.refs = [DRSRef('X1')]
                return identity_functor(self.category, self.refs[0])
            elif self.ispronoun and self.stem in _PRON:
                d = self._copy_production_from_sample(_PRON[self.stem], span)
                d.set_category(self.category)
                return d
            elif self.category == CAT_N:
                self.refs = [DRSRef('X1')]
                # Relative pronouns don't get a universe. This can happen for cases such as 'That which is...'
                if self.stem in _RELPRON:
                    self.mask |= RT_ENTITY
                    self.drs = DRS([], [Rel(self.stem, [self.refs[0]])])
                    d = DrsProduction([], self.refs, category=self.category, span=span)
                    d.set_lambda_refs([self.refs[0]])
                    return d
                else:
                    self._set_noun_mask()
                    return self._get_noun_drs(span)
            elif self.category == CAT_NOUN:
                self.refs = [DRSRef('X1')]
                self._set_noun_mask()
                return self._get_noun_drs(span)
            elif self.category == CAT_CONJ_CONJ or self.category == CAT_CONJCONJ:
                self.refs = [DRSRef('X1')]
                return create_empty_drs_production(CAT_CONJ, self.refs[0])
                #return identity_functor(self.category)
            elif self.isadverb and self.stem in _ADV:
                d = self._copy_production_from_sample(_ADV[self.stem], span)
                d.set_category(self.category)
                return d
            else:
                self.refs = [DRSRef('X1')]
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
                nref = DRSRef('X1')
                self.refs = [nref]
                if self.stem in ['a', 'an']:
                    #self.drs = DRS([], [Rel('_EXISTS', [nref])])
                    self.drs = DRS([], [])
                    fn = DrsProduction([], [nref], category=CAT_NP, span=span)
                elif self.stem in ['the', 'thy']:
                    self.drs = DRS([], [])
                    fn = DrsProduction([], [nref], category=CAT_NP, span=span)
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

            final_ref = rule_map[template.final_ref]
            final_atom = template.final_atom.remove_wildcards()
            refs.append(final_ref)
            refs.extend(reversed(lstk))
            refs.extend(rstk)
            refs = remove_dups(refs)
            # refs[0] is always final_ref
            self.refs = refs

            brefs = [final_ref]
            brefs.extend(rstk)
            brefs = remove_dups(brefs)
            binary = None
            if len(brefs) > 1 and (self.pos == POS_PREPOSITION or
                    self.word in [':', ';'] or
                    self.category in [CAT_NPnbN_NP, CAT_NPN_NP] or
                    (self.category.test_returns_entity_modifier() and self.category.argument_category().isatom)):
                # Right attachment
                binary = [brefs[0], brefs[1]]
            elif len(brefs) == 1 and len(rstk) == 1 and len(lstk) >= 1 and lstk[0] != brefs[0]:
                # Left attachment
                binary = [lstk[0], brefs[0]]

            # Verbs can also be adjectives so check event
            isverb = self.isverb
            arg_offs = 0
            if self.isgerund:
                scat = self.category.simplify()
                if not scat.ismodifier:
                    if scat.test_return(CAT_S_NP_S_NP) or scat.test_return(CAT_S_NPS_NP) \
                            or scat.test_return(CAT_S_S) or scat.test_return(CAT_SS):
                        if len(rstk) != 0:
                            arg_offs = 1
                            refs = [refs[0]]
                            refs.extend(rstk)
                            refs = remove_dups(refs)[0:2]
                            self.refs = refs
                            isverb = True
                        else:
                            isverb = False
                    else:
                        isverb = scat.can_unify(CAT_VP) or scat.test_return(CAT_VP)
                else:
                    isverb = False

            #if self.isgerund:
            #    result = self.category
            #    while not isverb and not result.isatom:
            #        isverb = result.can_unify(CAT_TV)
            #        result = result.result_category()
            #        # TODO: Add predicate for NG or change predarg attachments

            if isverb and template.isfinalevent:
                conds = []
                vncond = None
                vnclasses = []
                try:
                    vnclasses = [] if no_vn else VERBNETDB.name_index[self.stem]
                    if len(vnclasses) == 1:
                        vncond = Rel('_vn_' + vnclasses[0].ID.encode('utf-8'), [refs[0]])
                    elif len(vnclasses) >= 2:
                        xconds = [Rel('_vn_' + vnclasses[-1].ID.encode('utf-8'), [refs[0]])] \
                            if len(vnclasses) & 0X1 else []

                        # TODO: for vn classes A,B,C should really have (A&!B&!C)|(!A&B&!C)|(!A&!B&C)
                        for vna, vnb in zip(vnclasses[0::2],vnclasses[1::2]):
                            xconds.append(Or(DRS([], [Rel('_vn_' + vna.ID.encode('utf-8'), [refs[0]])]),
                                             DRS([], [Rel('_vn_' + vnb.ID.encode('utf-8'), [refs[0]])])))
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
                if self.isgerund:
                    conds.append(Rel('_EVENT', [refs[0]]))
                    pred = zip(refs[1:], EventPredicates[arg_offs:])
                    for v, e in pred[0:2]:
                        conds.append(Rel(e, [refs[0], v]))
                    self.mask |= RT_EVENT
                    self.vnclasses = vnclasses
                    self.drs = DRS([refs[0]], conds)
                    d = DrsProduction([refs[0]], self.refs[1:], span=span)
                    #d = DrsProduction([], self.refs, span=span)
                elif rcat is not None and rcat.argument_category().has_any_features(FEATURE_VARG) \
                        and rcat.result_category().has_any_features(FEATURE_VRES):
                    conds.append(Rel('_EVENT', [refs[0]]))
                    pred = zip(refs[1:], EventPredicates)
                    for v, e in pred[0:2]:
                        conds.append(Rel(e, [refs[0], v]))
                    self.mask |= RT_EVENT
                    self.vnclasses = vnclasses
                    self.drs = DRS([refs[0]], conds)
                    d = DrsProduction([refs[0]], self.refs[1:], span=span)
                    #d = DrsProduction([], self.refs, span=span)

                elif rcat is not None and (rcat.has_any_features(FEATURE_PSS | FEATURE_TO) or rcat.ismodifier):
                    if len(refs) > 1:
                        # passive case
                        if rcat.ismodifier or self.stem in ['be', 'get']:
                            self.mask |= RT_EVENT_ATTRIB
                            conds.append(Rel('_MOD', [refs[0], refs[-1]]))
                            self.drs = DRS([], conds)
                            d = DrsProduction([], self.refs, span=span)
                        else:
                            conds.append(Rel('_EVENT', [refs[0]]))
                            pred = zip(refs[1:], EventPredicates)
                            for v, e in pred[0:2]:
                                conds.append(Rel(e, [refs[0], v]))
                            self.mask |= RT_EVENT
                            self.vnclasses = vnclasses
                            self.drs = DRS([refs[0]], conds)
                            d = DrsProduction([refs[0]], self.refs[1:], span=span)
                            #d = DrsProduction([], self.refs, span=span)
                    else:
                        d = DrsProduction([], self.refs, span=span)

                elif self.category == CAT_MODAL_PAST:
                    self.mask |= RT_EVENT_MODAL
                    conds.append(Rel('_MODAL', [refs[0]]))
                    self.drs = DRS([], conds)
                    d = DrsProduction([], self.refs, span=span)

                elif self.category in CAT_COPULAR:
                    if len(refs) != 3:
                        pass
                    assert len(refs) == 3, "copular expects 3 referents"

                    # Special handling - ARG1 is a ROLE?
                    self.mask |= RT_EVENT
                    self.vnclasses = vnclasses
                    if self.stem == 'be':
                        # Discard conditions
                        conds.extend([Rel('_EVENT', [refs[0]]), Rel('_ARG0', [refs[0], refs[1]]),
                                      Rel('_ARG1', [refs[0], refs[2]])])

                    else:
                        conds.append(Rel('_EVENT', [refs[0]]))
                        conds.append(Rel('_ARG0', [refs[0], refs[1]]))
                        conds.append(Rel('_ARG1', [refs[0], refs[2]]))
                    self.drs = DRS([refs[0]], conds)
                    d = DrsProduction([refs[0]], refs[1:], category=final_atom, span=span)
                    #d = DrsProduction([], refs, category=final_atom, span=span)
                elif self.category == CAT_VPdcl:
                    if len(refs) != 2:
                        pass
                    assert len(refs) == 2, "VP[dcl] expects 2 referents"

                    conds.append(Rel('_EVENT', [refs[0]]))
                    conds.append(Rel('_ARG0', [refs[0], refs[1]]))
                    self.mask |= RT_EVENT
                    self.vnclasses = vnclasses

                    # Special handling
                    self.drs = DRS([refs[0]], conds)
                    d = DrsProduction([refs[0]], self.refs[1:], category=final_atom, span=span)
                    #d = DrsProduction([], self.refs, category=final_atom, span=span)

                else:
                    # TODO: use verbnet to get semantics
                    self.mask |= RT_EVENT
                    self.vnclasses = vnclasses
                    if self.stem == 'be' and self.category.can_unify(CAT_TV):
                        # Discard conditions - ARG1 is a ROLE?
                        conds.extend([Rel('_EVENT', [refs[0]]), Rel('_ARG0', [refs[0], refs[1]]),
                                      Rel('_ARG1', [refs[0], refs[2]])])
                    else:
                        conds.append(Rel('_EVENT', [refs[0]]))
                        pred = zip(refs[1:], EventPredicates)
                        for v, e in pred:
                            conds.append(Rel(e, [refs[0], v]))
                    self.drs = DRS([refs[0]], conds)
                    d = DrsProduction([refs[0]], refs[1:], span=span)
                    #d = DrsProduction([], refs, span=span)

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
                    d.rename_vars([(pron[2][0], refs[0])])

            elif self.ispreposition:
                if template.construct_empty:
                    # Make sure we have one freeref. For functors it is a bad idea to use an empty DrsProduction
                    # as the spans can be deleted by ProductionList.flatten().
                    d = DrsProduction([], [self.refs[0]], span=span)
                else:
                    if binary is not None:
                        self.refs = binary
                        self.drs = DRS([], [Rel(self.stem, binary)])
                    else:
                        self.refs = [self.refs[0]]
                        self.drs = DRS([], [Rel(self.stem, self.refs)])
                    d = DrsProduction([], self.refs, span=span)

            elif self.pos == POS_PREPOSITION and binary is not None:
                self.drs = DRS([], [Rel(self.stem, binary)])
                self.refs = binary
                d = DrsProduction([], self.refs, span=span)

            elif final_atom == CAT_Sadj and len(refs) > 1:
                if self.category == CAT_AP_PP or self.category.ismodifier or \
                        self.category.test_returns_modifier():
                    self.drs = DRS([], [Rel(self.stem, refs[0])])
                    d = DrsProduction([], self.refs, span=span)
                elif self.category.test_return(CAT_AP) and self.category.isarg_right and \
                        self.category.argument_category() == CAT_NP:
                    self.mask |= RT_ATTRIBUTE
                    self.drs = DRS([], [Rel(self.stem, [refs[0], refs[-1]])])
                    d = DrsProduction([], self.refs, span=span)
                else:
                    self.mask |= RT_ATTRIBUTE
                    self.drs = DRS([], [Rel(self.stem, refs[0])])
                    d = DrsProduction([], self.refs, span=span)

            else:
                if self.category == CAT_NPP:
                    # Treat as noun
                    universe = [self.refs[0]]
                    freerefs = []
                else:
                    universe = []
                    freerefs = self.refs

                if self.isproper_noun:
                    #universe.append(self.refs[0])
                    #freerefs = self.refs[1:]
                    self.mask |= RT_PROPERNAME
                elif final_atom == CAT_N and not self.category.ismodifier \
                        and not self.category.test_returns_modifier():
                    #universe.append(self.refs[0])
                    #freerefs = self.refs[1:]
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
                        self.drs = DRS([], [Rel(self.stem, [refs[0]]), Rel('_MODAL', [refs[0]])])
                        d = DrsProduction([], self.refs, span=span)
                    else:
                        self.drs = DRS([], self._build_conditions([], binary, template))
                        d = DrsProduction([], self.refs, span=span)
                else:
                    self.drs = DRS(universe, self._build_conditions([], binary, template))
                    d = DrsProduction(universe, freerefs, span=span)

            d.set_lambda_refs([final_ref])
            d.set_category(final_atom)
            fn = template.create_functor(rule_map, d)
            return fn

    def get_variables(self):
        """Safe access to DRS variables."""
        return [] if self.drs is None or self.drs.isempty else self.drs.variables
