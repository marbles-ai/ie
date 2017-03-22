# -*- coding: utf-8 -*-
"""CCG to DRS Production Generator"""

from drs import DRS, DRSRef, Prop, Imp, Rel, Neg, Box, Diamond, Or
from common import DRSConst, DRSVar
from compose import ProductionList, FunctorProduction, DrsProduction, PropProduction, OrProduction, DrsComposeError
from ccgcat import Category, CAT_Sadj, CAT_N, CAT_NOUN, CAT_NP_N, CAT_DETERMINER, CAT_CONJ, CAT_EMPTY, CAT_INFINITIVE, \
    CAT_Sany, CAT_PP, CAT_PPNP, \
    get_rule, RL_TYPE_CHANGE_VPMOD, RL_TYPE_CHANGE_NP_NP, RL_TYPE_CHANGE_MOD, RL_TYPE_CHANGE_SNP
from utils import remove_dups, union, union_inplace, complement, intersect, rename_var
from parse import parse_drs
import re
import pickle
import os


## @cond
__pron = [
    # 1st person singular
    ('i',       '([],[([],[i(x1)])->([],[me(x1),is.anaphora(x1)])])'),
    ('me',      '([],[me(x1),is.anaphora(x1)])'),
    ('myself',  '([],[([],[myself(x1)])->([],[me(x1),is.anaphora(x1)])])'),
    ('mine',    '([],[([],[mine(x1)])->([],[me(x2),is.anaphora(x2),owns(x2,x1)])])'),
    ('my',      '([],[([],[my(x1)])->([],[me(x2),is.anaphora(x2),owns(x2,x1)])])'),
    # 2nd person singular
    ('you',     '([],[you(x1),is.anaphora(x1)])'),
    ('yourself','([],[([],[yourself(x1)])->([],[you(x1),is.anaphora(x1)])])'),
    ('yours',   '([],[([],[yours(x1)])->([],[you(x2),is.anaphora(x2),owns(x2,x1)])])'),
    ('your',    '([],[([],[your(x1)])->([],[you(x2),is.anaphora(x2),owns(x2,x1)])])'),
    # 3rd person singular
    ('he',      '([],[([],[he(x1)])->([],[him(x1),is.anaphora(x1)])])'),
    ('she',     '([],[([],[she(x1),is.anaphora(x1)])->([],[her(x1)])])'),
    ('him',     '([],[([],[him(x1),is.anaphora(x1)])->([],[male(x1)])])'),
    ('her',     '([],[([],[her(x1),is.anaphora(x1)])->([],[female(x1)])])'),
    ('himself', '([],[([],[himself(x1)])->([],[him(x1),is.anaphora(x1)])])'),
    ('herself', '([],[([],[herself(x1)])->([],[her(x1),is.anaphora(x1)])])'),
    ('hisself', '([],[([],[hisself(x1)])->([],[himself(x1),is.anaphora(x1)])])'),
    ('his',     '([],[([],[his(x1)])->([],[him(x2),owns(x2,x1)])])'),
    ('hers',    '([],[([],[hers(x1)])->([],[her(x2),is.anaphora(x2),owns(x2,x1)])])'),
    # 1st person plural
    ('we',      '([],[([],[we(x1)])->([],[us(x1),is.anaphora(x1)])])'),
    ('us',      '([],[us(x1)])'),
    ('ourself', '([],[([],[ourself(x1)])->([],[our(x1),is.anaphora(x1)])])'),
    ('ourselves','([],[([],[ourselves(x1)])->([],[our(x1),is.anaphora(x1)])])'),
    ('ours',    '([],[([],[ours(x1)])->([],[us(x2),is.anaphora(x2),owns(x2,x1)])])'),
    ('our',     '([],[([],[our(x1)])->([],[us(x2),is.anaphora(x2),owns(x2,x1)])])'),
    # 2nd person plural
    ('yourselves', '([],[([],[yourselves(x1)])->([],[you(x1),is.anaphora(x1),is.plural(x1)])])'),
    # 3rd person plural
    ('they',    '([],[([],[they(x1)])->([],[them(x1),is.anaphora(x1)])])'),
    ('them',    '([],[them(x1),is.anaphora(x1)])'),
    ('themself','([],[([],[themself(x1)])->([],[them(x1),is.anaphora(x1)])])'),
    ('themselves','([],[([],[themselves(x1)])->([],[them(x1),is.anaphora(x1)])])'),
    ('theirs',  '([],[([],[theirs(x1)])->([],[them(x2),is.anaphora(x2),owns(x2,x1)])])'),
    ('their',   '([],[([],[their(x1)])->([],[them(x2),is.anaphora(x2),owns(x2,x1)])])'),
    # it
    ('it',      '([],[it(x1),is.anaphora(x1)])'),
    ('its',     '([],[([],[its(x1)])->([],[it(x2),is.anaphora(x2),owns(x2,x1)])])'),
    ('itself',  '([],[([],[itself(x1)])->([],[it(x1),is.anaphora(x1)])])'),
]
_PRON = {}
for k,v in __pron:
    _PRON[k] = parse_drs(v, 'nltk')


# Order of referents is lambda_ref binding order
__adv = [
    ('up',      '([x,e],[])', '([],[up(e),direction(e)])'),
    ('down',    '([x,e],[])', '([],[down(e),direction(e)])'),
    ('left',    '([x,e],[])', '([],[left(e),direction(e)])'),
    ('right',   '([x,e],[])', '([],[right(e),direction(e)])'),
]
_ADV = {}
for k,u,v in __adv:
    _ADV[k] = (parse_drs(v, 'nltk'), parse_drs(u, 'nltk').universe)
## endcond


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


class FunctorTemplate(object):
    """Template for functor generation."""
    _names = ['f', 'g', 'h', 'm', 'n', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w']
    _PredArgIdx = re.compile(r'^.*_(?P<idx>\d+)$')

    def __init__(self, rule, category):
        """Constructor.

        Args:
            rule: The production constructor rule.
            category: A predarg category.
        """
        self.constructor_rule = rule
        self.category = category

    def __repr__(self):
        """Return the model as a string."""
        return self.category.clean(True).ccg_signature + ':' + self.__str__()

    def __str__(self):
        """Return the model as a string."""
        line = []
        for i in range(len(self.constructor_rule)-1):
            fn = self.constructor_rule[i]
            if isinstance(fn[1], tuple):
                if fn[0] == PropProduction:
                    line.append(self._names[i].upper() + '(')
                else:
                    line.append(self._names[i] + '(')
                line.append(','.join([x.var.to_string() for x in fn[1]]))
                line.append(').')
            else:
                if fn[0] == PropProduction:
                    line.append(self._names[i].upper() + '(' + fn[1].var.to_string() + ').')
                else:
                    line.append(self._names[i] + '(' + fn[1].var.to_string() + ').')
        if self.constructor_rule[-1] is None:
            line.append('none')
        else:
            line.append(self.constructor_rule[-1].var.to_string())
        return ''.join(line)

    @classmethod
    def create_from_category(cls, predarg):
        """Create a functor template from a predicate-argument category.

        Args:
            predarg: The predicate-argument category.

        Returns:
            A FunctorTemplate instance or None if predarg is an atomic category.
        """
        # Ignore atoms and conj rules. Conj rules are handled by CcgTypeMapper
        catclean = predarg.clean(True)  # strip all tags
        if not predarg.isfunctor or catclean.result_category == CAT_CONJ or catclean.argument_category == CAT_CONJ:
            return None

        # Handle special cases
        if catclean == CAT_PPNP:
            return FunctorTemplate(((PropProduction, DRSRef('x1')), None), predarg)

        predargOrig = predarg
        predarg = predargOrig.clean()   # strip functor tags

        pvars = {}
        ei = 0
        xi = 0
        fn = []
        while predarg.isfunctor:
            atoms = predarg.argument_category.extract_unify_atoms(False)
            predarg = predarg.result_category
            refs = []
            for a in atoms:
                key = a.ccg_signature
                m = cls._PredArgIdx.match(key)
                if m is not None:
                    key = m.group('idx')
                if key not in pvars:
                    acln = a.clean(True)
                    if acln == CAT_Sany and acln != CAT_Sadj:
                        ei += 1
                        r = DRSRef(DRSVar('e', ei))
                    else:
                        xi += 1
                        r = DRSRef(DRSVar('x', xi))
                    pvars[key] = r
                else:
                    # TODO: deep copy?
                    r = pvars[key]
                refs.append(r)

            if len(refs) == 1:
                fn.append((FunctorProduction, refs[0]))
            else:
                fn.append((FunctorProduction, tuple(refs)))

        # Handle return atom
        if predarg.ccg_signature[0] == 'S' and predarg.clean(True) != CAT_Sadj:
            key = predarg.ccg_signature
            m = cls._PredArgIdx.match(key)
            if m is not None:
                key = m.group('idx')

            if key not in pvars:
                ei += 1
                r = DRSRef(DRSVar('e', ei))
            else:
                r = pvars[key]
            fn.append(r)
        else:
            fn.append(None)

        return FunctorTemplate(tuple(fn), predargOrig)


def _add_missing_template(signature, dict):
    if signature not in dict:
        dict[signature] = FunctorTemplate.create_from_category(Category(signature))


class CcgTypeMapper(object):
    """Mapping from CCG types to DRS types and the construction rules.

    Construction Rules:
    -# We have two levels of construction.
        - Lambda construction rules apply to DRS, i.e. variables are DRS, not referents.
        - DRS construction is via unify operation, infix operator ';'
          Merge works like application in lambda calculus, i.e. right to left.
          <b>Note:</b> This is not the unify function in our python DRS implementation.
    -# We have two levels of binding.
       - Referents in the lambda definition.
         Given λPλx.P(x) with DRS P, x is always free in the lambda declaration
         but x can be a free variable in DRS P, or bound in P
       - Do not support free DRS in the lambda definition<br>
         i.e. λPλxλy.P(x);G(y) is not supported,<br>
         λPλGλxλy.P(x);G(y) is OK
    -# DRS constructions rules can be separated into class:
       - Functions: Rules which take DRS base types (T,Z) as arguments. Functions can return a base type, another
         function, or a combinator. Functions are always constructed from inner types to outer types. For example:
         the application order for (S\T)/T is: /T, \T, S
       - Combinators: Rules which take a function as the argument and return a function of the same type.
       - When applying combinators the resultant must produce a function, or combinator, where the DRS unifys are
         adjacent. For example:
         - (S/T)/(S/T) combinator:=λP.T[...];P(x) and (S/T) type:=λQ.R[...];Q(x)<br>
           => λQ.T[...];R[...];Q(x) which is OK<br>
         - (S/T)\(S/T) combinator:=λP.P(x);T[...] and (S/T) type:=λQ.R[...];Q(x)<br>
           => λQ.R[...];Q(x);T[...] which is not OK<br>
       - The CCG parse tree gives us the construction order so we don't need to differentiate between combinators and
         functions during production.
    -# Lambda application:
       - λPλx.P(x) {P(x=x)=G[x|...]} == G[x|...]
       - λPλx.P(x) {P(x=y)=G[y|...])} == G[y|...]
    -# Lambda function production
       - λPλx.P(x).λQλy.Q(y) == λPλQλxλy.P(x);Q(y) == read as P unify Q<br>
         iff x is a bound in DRS P and y is bound in DRS Q
       - λPλx.P(x).λQλy.Q(y) == λPλQλx.P(x);Q(x)<br>
         iff y is a free variable in DRS Q and x is bound, or free, in DRS P
       - λPλx.P(x).λQλy.Q(y) == λPλQλy.P(y);Q(y)<br>
         iff x is a free variable in DRS P and y is bound in DRS Q
    -# We do partial unification when all functors have been applied at some point during the construction phase.<br>
       P[x|...];Q[x|...] := unify(P[x|...],Q[x|...])
    -# Promotion to a proposition. This is done to ensure the number of referents agree in a lambda definition.<br>
       λPλx.P(x);Q[x|...] {P=R[x,y|...]} := [u|u:R[x,y|...]];Q[u|...]<br>
       λQλx.P[x|...];Q(x) {Q=R[x,y|...]} := P[u|...];[u|u:R[x,y|...]]
    -# Proposition simplification.<br>
       [p|p:Q[x|...]] can be simplified to Q(x=p) if p is the only bound referent.
    """
    _AllTypes = {
        # DRS base types
        # ==============
        'Z':            None,
        'T':            None,
        'conj':         None,

        # NP,PP
        r'Z/T': ((PropProduction, DRSRef('x1')), None),
        r'T/Z': ((FunctorProduction, DRSRef('x1')), None),
        r'(T\T)/T': ((FunctorProduction, DRSRef('x2')), (FunctorProduction, DRSRef('x1')), None),
        r'(T/T)/T': ((FunctorProduction, DRSRef('x1')), (FunctorProduction, DRSRef('x2')), None),
        r'(T/T)\T': ((FunctorProduction, DRSRef('x1')), (FunctorProduction, DRSRef('x2')), None),
        r'(T\T)\T': ((FunctorProduction, DRSRef('x2')), (FunctorProduction, DRSRef('x1')), None),
        r'(T\T)/Z': ((FunctorProduction, DRSRef('x2')), (FunctorProduction, DRSRef('x1')), None),
        r'(T/T)/Z': ((FunctorProduction, DRSRef('x1')), (FunctorProduction, DRSRef('x2')), None),

        # DRS Verb functions
        r'S/T': ((FunctorProduction, DRSRef('x1')), DRSRef('e1')),
        r'S\T': ((FunctorProduction, DRSRef('x1')), DRSRef('e1')),
        r'(S/T)/T': ((FunctorProduction, DRSRef('x1')), (FunctorProduction, DRSRef('x2')), DRSRef('e1')),
        r'(S/T)\T': ((FunctorProduction, DRSRef('x1')), (FunctorProduction, DRSRef('x2')), DRSRef('e1')),
        r'(S\T)/T': ((FunctorProduction, DRSRef('x2')), (FunctorProduction, DRSRef('x1')), DRSRef('e1')),
        r'(S\T)\T': ((FunctorProduction, DRSRef('x2')), (FunctorProduction, DRSRef('x1')), DRSRef('e1')),
        r'(S\T)/Z': ((FunctorProduction, DRSRef('x2')), (FunctorProduction, DRSRef('x1')), DRSRef('e1')),
        r'(S/T)/Z': ((FunctorProduction, DRSRef('x1')), (FunctorProduction, DRSRef('x2')), DRSRef('e1')),
        r'T/S':     ((FunctorProduction, DRSRef('e1')), DRSRef('x1')),
        r'(((S\T)/Z)/T)/T': ((FunctorProduction, DRSRef('x2')), (FunctorProduction, DRSRef('x3')),
                             (FunctorProduction, DRSRef('x4')), (FunctorProduction, DRSRef('x1')), DRSRef('e1')),
        r'((S\T)/Z)/T': ((FunctorProduction, DRSRef('x2')), (FunctorProduction, DRSRef('x3')),
                         (FunctorProduction, DRSRef('x1')), DRSRef('e1')),
        r'(S\T)/S': ((FunctorProduction, DRSRef('e2')), (FunctorProduction, DRSRef('x1')), DRSRef('e1')),

        # Modifiers
        r'T/T': ((FunctorProduction, DRSRef('x1')), None),
        r'T\T': ((FunctorProduction, DRSRef('x1')), None),
        r'S\S': ((FunctorProduction, DRSRef('e2')), DRSRef('e1')),
        r'S/S': ((FunctorProduction, DRSRef('e2')), DRSRef('e1')),
        r'(S\T)\(S\T)': ((FunctorProduction, (DRSRef('x1'), DRSRef('e2'))),
                         (FunctorProduction, DRSRef('x1')), DRSRef('e1')),
        r'(S\T)/(S\T)': ((FunctorProduction, (DRSRef('x1'), DRSRef('e2'))),
                         (FunctorProduction, DRSRef('x1')), DRSRef('e1')),
        r'(T/T)/(T/T)': ((FunctorProduction, DRSRef('x1')), (FunctorProduction, DRSRef('x1')), None),
        r'(T\T)/(T\T)': ((FunctorProduction, DRSRef('x1')), (FunctorProduction, DRSRef('x1')), None),

        # Mixtures: functions + modifiers
        r'(S\S)\T': ((FunctorProduction, DRSRef('x1')),
                     (FunctorProduction, DRSRef('e2')), DRSRef('e1')),
        r'((S\T)\(S\T))/T': ((FunctorProduction, DRSRef('x2')),
                             (FunctorProduction, (DRSRef('x1'), DRSRef('e2'))),
                             (FunctorProduction, DRSRef('x1')), DRSRef('e1')),
        r'((S\T)\(S\T))\T': ((FunctorProduction, DRSRef('x2')),
                             (FunctorProduction, (DRSRef('x1'), DRSRef('e2'))),
                             (FunctorProduction, DRSRef('x1')), DRSRef('e1')),
        r'(((S\T)/(S\T))/(S\T))/T': ((FunctorProduction, DRSRef('x2')),
                                     (FunctorProduction, (DRSRef('x1'), DRSRef('e3'))),
                                     (FunctorProduction, (DRSRef('x1'), DRSRef('e2'))),
                                     (FunctorProduction, DRSRef('x1')), DRSRef('e1')),
        r'(((S\T)/(S\T))/Z)/T': ((FunctorProduction, DRSRef('x3')), (FunctorProduction, DRSRef('x2')),
                                 (FunctorProduction, (DRSRef('x1'), DRSRef('e2'))),
                                 (FunctorProduction, DRSRef('x1')), DRSRef('e1')),
        r'(((S\T)/S)/(S\T))/T': ((FunctorProduction, DRSRef('x2')),
                                 (FunctorProduction, (DRSRef('x1'), DRSRef('e2'))),
                                 (FunctorProduction, DRSRef('e1')),
                                 (FunctorProduction, DRSRef('x1')), DRSRef('e1')),
        # ((NP2\NP2)/S)\((NP1\NP1)/NP2)
        r'((T\T)/S)\((T\T)/T)': ((FunctorProduction, (DRSRef('x2'), DRSRef('x1'))),
                                 (FunctorProduction, DRSRef('e1')),
                                 (FunctorProduction, DRSRef('x1')), None),
        r'((S\T)\(S\T))/Z': ((FunctorProduction, DRSRef('x2')),
                             (FunctorProduction, (DRSRef('x1'), DRSRef('e2'))),
                             (FunctorProduction, DRSRef('x1')), DRSRef('e1')),
        r'(T\T)/(S\T)': ((FunctorProduction, (DRSRef('x1'), DRSRef('e1'))),
                         (FunctorProduction, DRSRef('x1')), DRSRef('e1')),
        r'((T/T)/(T/T))\(T\T)': ((FunctorProduction, DRSRef('x1')),
                                 (FunctorProduction, DRSRef('x2')),
                                 (FunctorProduction, DRSRef('x2')), None),
        r'((S\T)\(S\T))/S': ((FunctorProduction, DRSRef('e3')),
                             (FunctorProduction, (DRSRef('x1'), DRSRef('e2'))),
                             (FunctorProduction, DRSRef('x1')), DRSRef('e1')),
        r'(S/S)/S': ((FunctorProduction, DRSRef('e3')), (FunctorProduction, DRSRef('e2')), DRSRef('e1')),
        #r'(((S\T)/Z)/Z)/(S\T)':
    }
    _EventPredicates = ('agent', 'theme', 'extra')
    _TypeMonth = re.compile(r'^((Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?|January|February|March|April|June|July|August|September|October|November|December)$')
    _TypeWeekday = re.compile(r'^((Mon|Tue|Tues|Wed|Thur|Thurs|Fri|Sat|Sun)\.?|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)$')

    # Run scripts/make_functor_templates.py to create templates file
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'functor_templates.dat'), 'rb') as fd:
            _TEMPLATES = pickle.load(fd)
        # For some reason, some rules generated by EasySRL are missing from LDC CCGBANK
        _add_missing_template('NP/N', _TEMPLATES)
        _add_missing_template('S[dcl]/S[dcl]', _TEMPLATES)
        _add_missing_template('S[dcl]\S[dcl]', _TEMPLATES)
    except Exception as e:
        print(e)
        # Allow module to load else we cannot create the dat file.
        _TEMPLATES = {}

    def __init__(self, ccgTypeName, word, posTags=None):
        if isinstance(ccgTypeName, Category):
            self._ccgcat = ccgTypeName
        else:
            self._ccgcat = Category(ccgTypeName)
        self._pos = posTags or ['UNKNOWN']

        # We treat modal as verb modifiers - i.e. they don't get their own event
        if self._pos[0] == 'MD':
            self._ccgcat = self._ccgcat.simplify()
            assert self._ccgcat.ismodifier

        if self.isproper_noun:
            self._word = word.title().rstrip('?.,:;')
        else:
            self._word = word.lower().rstrip('?.,:;')
        self._drsSignature = self._ccgcat.drs_signature

        # Atomic types don't need a template
        if self.category.isfunctor and self.category.ccg_signature not in self._TEMPLATES:
            raise DrsComposeError('CCG type "%s" for word "%s" maps to unknown DRS production type "%s",' %
                                  (ccgTypeName, word, self.ccg_signature))

    def __repr__(self):
        return '<' + self._word + ' ' + self.partofspeech + ' ' + self.ccg_signature + '->' + self.drs_signature + '>'

    @property
    def ispunct(self):
        """Test if the word attached to this category is a punctuation mark."""
        return self.partofspeech in [',', '.', ':', ';']

    @property
    def ispronoun(self):
        """Test if the word attached to this category is a pronoun."""
        return (self.partofspeech in ['PRP', 'PRP$', 'WP', 'WP$']) or self._word in _PRON

    @property
    def ispreposition(self):
        """Test if the word attached to this category is a preposition."""
        return self.partofspeech == 'IN'

    @property
    def isadverb(self):
        """Test if the word attached to this category is an adverb."""
        return self.partofspeech in ['RB', 'RBR', 'RBS']

    @property
    def isverb(self):
        """Test if the word attached to this category is a verb."""
        return self.partofspeech in ['VB', 'VBD', 'VBN', 'VBP', 'VBZ']

    @property
    def isconj(self):
        """Test if the word attached to this category is a conjoin."""
        return self.ccg_signature == 'conj'

    @property
    def isgerund(self):
        """Test if the word attached to this category is a gerund."""
        return self.partofspeech == 'VBG'

    @property
    def isproper_noun(self):
        """Test if the word attached to this category is a proper noun."""
        return self.partofspeech == 'NNP'

    @property
    def isnumber(self):
        """Test if the word attached to this category is a number."""
        return self.partofspeech == 'CD'

    @property
    def isadjective(self):
        """Test if the word attached to this category is an adjective."""
        return self.partofspeech == 'JJ'

    @property
    def partofspeech(self):
        """Get part of speech of the word attached to this category."""
        return self._pos[0] if self._pos is not None else 'UNKNOWN'

    @property
    def ccg_signature(self):
        """Get the CCG category signature."""
        return self._ccgcat.ccg_signature

    @property
    def category(self):
        """Get the CCG category."""
        return self._ccgcat

    @property
    def drs_signature(self):
        """Get the DRS category signature."""
        return self._drsSignature

    def rename_template_vars(self, templ):
        """Event variables depend on whether S types can be unified. For example: (S\NP)/(S[dcl]\NP) only requires
        single event variable because S can unify with S[dcl]. However (S[to]\NP)/(S[dcl]\NP) requires two event
        variables because S[to] cannot unify with S[dcl].

        The templates in our dictionary assume no unification is possible. Now we must fix up if that assumption is
        incorrect. I have done it this way for expedience, otherwise I need a dictionary entry for every category in the
        LDC ccg-bank.

        Args:
            templ: The original template.

        Returns:
            The renamed template.
        """
        if templ is not None and templ[-1] is not None:

            lambda_scope = map(lambda x: [x[1]] if isinstance(x[1], DRSRef) else list(x[-1]), templ[:-1])
            if isinstance(templ[-1], tuple):
                lambda_scope.append(list(templ[-1]))
            else:
                lambda_scope.append([templ[-1]])
            atom_scope = self.category.extract_unify_atoms()   # ordering will be same as lambda_scope
            if len(atom_scope) != len(lambda_scope):
                pass
            assert len(atom_scope) == len(lambda_scope)
            scopes = zip(atom_scope, lambda_scope)
            ev_scope = []
            for atoms, lrefs in scopes:
                if len(atoms) != len(lrefs):
                    pass
                assert len(atoms) == len(lrefs)
                eva = filter(lambda x: x[0] == CAT_Sany, zip(atoms, lrefs))
                if len(eva) != 0:
                    ev_scope.append(eva)

            rs = []
            seen = set()
            while len(ev_scope) != 0:
                eva = ev_scope.pop()
                for evb in ev_scope:
                    for a, ra in eva:
                        for b, rb in evb:
                            if b.can_unify(a) and rb not in seen:
                                rs.append((rb, ra))
                                seen.add(rb)
            if len(rs) == 0:
                return templ
            for r in rs:
                for scope in lambda_scope:
                    for i in range(len(scope)):
                        scope[i] = rename_var(scope[i], rs)
            ntempl = []
            for s, t in zip(lambda_scope, templ[:-1]):
                ntempl.append((t[0], tuple(s) if len(s) > 1 else s[0]))
            if isinstance(templ[-1], tuple):
                ntempl.append(tuple(lambda_scope[-1]))
            else:
                ntempl.append(lambda_scope[-1][0])
            return tuple(ntempl)
        return templ

    def build_predicates(self, p_vars, refs, evt_vars=None, conds=None):
        """Build the DRS conditions for a noun, noun phrase, or adjectival phrase. Do
        not use this for verbs or adverbs.

        Args:
            p_vars: DRSRef's used in the predicates.
            refs: lambda refs for curried function, excluding evt.
            evt: An optional event DRSRef.
            conds: A list of existing DRS conditions.

        Returns:
            A list if marbles.ie.drt.drs.Rel instances.

        Remarks:
            Also modifies refs to be lambda vars
        """
        assert p_vars is not None
        assert refs is not None
        if conds is None:
            conds = []
        if isinstance(p_vars, DRSRef):
            p_vars = [p_vars]
        elif isinstance(p_vars, tuple):
            # Production templates are stored as tuples to prevent modification
            p_vars = list(p_vars)

        if evt_vars is not None:
            if isinstance(evt_vars, DRSRef):
                evt_vars = [evt_vars]
            else:
                if isinstance(evt_vars, tuple):
                    evt_vars = list(evt_vars)
                else:
                    evt_vars = [x for x in evt_vars]    # shallow copy
                evt_vars.reverse()
            #evt_vars = union_inplace(p_vars, evt_vars)
            if len(evt_vars) == 1:
                # p_vars = [e], evt_vars = [e]
                evt_vars = None
            else:
                p_vars = complement(p_vars, evt_vars)

        if self.category.ismodifier or self.category.iscombinator:
            if evt_vars is not None:
                evt_vars.reverse()
                refs.reverse()
                refs = union_inplace(evt_vars, refs)
                # shallow copy refs
                if len(refs) == 1:
                    conds.append(Rel('event.modifier.' + self._word, [x for x in refs]))
                elif len(refs) == 2:
                    conds.append(Rel('event.attribute.' + self._word, [x for x in refs]))
                elif len(refs) > 2:
                    conds.append(Rel('event.related.' + self._word, [x for x in refs]))
                refs.reverse() # for caller
            else:
                conds.append(Rel(self._word, [x for x in refs]))    # shallow copy refs
        elif self.isadjective:
            if evt_vars is not None:
                raise DrsComposeError('Adjective "%s" with signature "%s" does not expect an event variable'
                                      % (self._word, self.drs_signature))
            conds.append(Rel(self._word, [x for x in refs]))    # shallow copy refs
        else:
            if self.isproper_noun:
                if len(p_vars) != 1:
                    pass
                assert len(p_vars) == 1
                if self._TypeMonth.match(self._word):
                    conds.append(Rel('is.date', p_vars))
                    if evt_vars is not None:
                        conds.append(Rel('event.date', evt_vars))
                    if self._word in _MONTHS:
                        conds.append(Rel(_MONTHS[self._word], p_vars))
                    else:
                        conds.append(Rel(self._word, p_vars))
                elif self._TypeWeekday.match(self._word):
                    conds.append(Rel('is.date', p_vars))
                    if evt_vars is not None:
                        conds.append(Rel('event.date', evt_vars))
                    if self._word in _WEEKDAYS:
                        conds.append(Rel(_WEEKDAYS[self._word], p_vars))
                    else:
                        conds.append(Rel(self._word, p_vars))
                else:
                    if evt_vars is not None:
                        conds.append(Rel('event.related', evt_vars))
                    conds.append(Rel(self._word, p_vars))
            elif self.isnumber:
                assert len(p_vars) == 1
                conds.append(Rel('is.number', p_vars))
                if evt_vars is not None:
                    conds.append(Rel('event.related', evt_vars))
                conds.append(Rel(self._word, p_vars))
            elif evt_vars is not None and len(p_vars) != 0:
                conds.append(Rel('event.related', evt_vars))
                conds.append(Rel(self._word, p_vars))
            elif len(refs) != 0:
                conds.append(Rel(self._word, [x for x in refs]))    # shallow copy refs
        return conds

    @staticmethod
    def remove_events_from_template(templ):
        """Remove events from a production template."""

        # r'((S\T)\(S\T))/T': ((FunctorProduction, DRSRef('y')),
        #                     (FunctorProduction, (DRSRef('x'), DRSRef('e'))), DRSRef('e')),
        result = []
        for t in templ[:-1]:
            if isinstance(t[1], tuple):
                #result.append((t[0],t[1][0:-1] if t[1] is not None else None))
                if isinstance(t[1], tuple):
                    if len(t[1]) > 2:
                        result.append((t[0],t[1][0:-1]))
                    else:
                        result.append((t[0],t[1][0]))
                else:
                    result.append(t)
            else:
                result.append(t)
        result.append(None)
        return tuple(result)

    def get_composer(self):
        """Get the production model for this category.

        Returns:
            A Production instance.
        """
        try:
            template = self._TEMPLATES[self.ccg_signature]
            compose = template.constructor_rule
        except:
            template = None
            compose = None
            #compose = self.rename_template_vars(self._AllTypes[self.drs_signature])

        if compose is None:
            # Simple type
            # Handle prepositions
            if self.isconj:
                if self._word == ['or', 'nor']:
                    return OrProduction(negate=('n' in self._word))
                return ProductionList(category=CAT_CONJ)
            elif self.ispronoun:
                d = DrsProduction(_PRON[self._word], category=self.category)
                d.set_lambda_refs(union(d.drs.universe, d.drs.freerefs))
                assert len(d.lambda_refs) == 1
                return d
            elif self.category == CAT_N:
                d = DrsProduction(DRS([DRSRef('x1')], [Rel(self._word, [DRSRef('x1')])]), properNoun=self.isproper_noun)
                d.set_category(self.category)
                d.set_lambda_refs([DRSRef('x1')])
                return d
            elif self.category == CAT_NOUN:
                if self.isnumber:
                    d = DrsProduction(DRS([DRSRef('x1')], [Rel('is.number', [DRSRef('x1')]), Rel(self._word, [DRSRef('x1')])]))
                else:
                    d = DrsProduction(DRS([DRSRef('x1')], [Rel(self._word, [DRSRef('x1')])]))
                d.set_category(self.category)
                d.set_lambda_refs([DRSRef('x1')])
                return d
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
        else:
            # Functor

            # Production templates use tuples so we don't accidentally modify.
            # Shallow copy of event vars from template
            ev = compose[-1] if compose[-1] is None or isinstance(compose[-1], DRSRef) else [x for x in compose[-1]]
            if self.category == CAT_NP_N:    # NP*/N class
                # FIXME: these relations should be added as part of build_predicates()
                if self.category == CAT_DETERMINER:
                    if self._word in ['a', 'an']:
                        fn = FunctorProduction(self.category, DRSRef('x1'), DRS([], [Rel('exists.maybe', [DRSRef('x1')])]))
                    elif self._word in ['the', 'thy']:
                        fn = FunctorProduction(self.category, DRSRef('x1'), DRS([], [Rel('exists', [DRSRef('x1')])]))
                    else:
                        fn = FunctorProduction(self.category, DRSRef('x1'), DRS([], [Rel(self._word, [DRSRef('x1')])]))
                elif self.partofspeech == 'DT' and self._word in ['the', 'thy']:
                    fn = FunctorProduction(self.category, DRSRef('x1'), DRS([], [Rel('exists', [DRSRef('x1')])]))
                else:
                    fn = FunctorProduction(self.category, DRSRef('x1'), DRS([], [Rel(self._word, [DRSRef('x1')])]))
                if ev is not None:
                    fn.set_lambda_refs([ev])
                else:
                    fn.set_lambda_refs([DRSRef('x1')])
                return fn
            if compose[0][0] == FunctorProduction:
                refs = []
                signatures = []
                s = self.category
                for c in compose[:-1]:
                    signatures.append(s)
                    if s.isarg_right:
                        if isinstance(c[1], tuple):
                            refs.extend(list(c[1]))
                        else:
                            refs.append(c[1])
                    else:
                        assert s.isarg_left
                        if isinstance(c[1], tuple):
                            r = list(c[1])
                        else:
                            r = [c[1]]
                        r.extend(refs)
                        refs = r
                    s = s.result_category

                if ev is not None:
                    ev = [ev] if isinstance(ev, DRSRef) else ev
                    refs.extend(ev)
                    refs.reverse()
                    refs = remove_dups(refs)
                    refs.reverse()
                    refs = complement(refs, ev)
                else:
                    refs.reverse()
                    refs = remove_dups(refs)
                    refs.reverse()

                if self.isverb:
                    if ev is None:
                        raise DrsComposeError('Verb signature "%s" does not include event variable' % self.drs_signature)
                    elif self.category.iscombinator or self.category.ismodifier:
                        # passive case
                        fn = DrsProduction(DRS([], self.build_predicates(compose[0][1], refs, ev)))
                    elif len(ev) != 1:
                        # TODO: use verbnet to get semantics
                        conds = [Rel('event', ev[-1]), Rel('event.verb.' + self._word, ev[-1])]
                        for v,e in zip(ev[0:-1], self._EventPredicates):
                            conds.append(Rel('event.' + e, [ev[-1], v]))
                        if len(refs) > len(self._EventPredicates):
                            for i in range(len(self._EventPredicates), len(refs)):
                                conds.append(Rel('event.extra.%d' % i, [ev[-1], refs[i]]))
                        fn = DrsProduction(DRS(ev, conds))
                    else:
                        # TODO: use verbnet to get semantics
                        conds = [Rel('event', ev), Rel('event.verb.' + self._word, ev)]
                        for v, e in zip(refs, self._EventPredicates):
                            conds.append(Rel('event.' + e, [ev[0], v]))
                        if len(refs) > len(self._EventPredicates):
                            for i in range(len(self._EventPredicates), len(refs)):
                                conds.append(Rel('event.extra.%d' % i, [ev[0], refs[i]]))
                        fn = DrsProduction(DRS(ev, conds))
                    fn.set_lambda_refs(ev)
                elif self.isadverb and ev is not None and self._word in _ADV:
                    adv = _ADV[self._word]
                    fn = DrsProduction(adv[0], [x for x in adv[1]])
                    fn.set_lambda_refs(ev)
                    r = refs
                    r.extend(ev)
                    rs = zip(adv[1], r)
                    fn.rename_vars(rs)

                elif self.ispreposition:
                    # Don't attach to event's
                    c = self.remove_events_from_template(compose)
                    compose = c
                    fn = DrsProduction(DRS([], self.build_predicates(compose[0][1], refs, ev)),
                                       properNoun=self.isproper_noun)
                else:
                    scat = self.category.simplify() # removes features [?]
                    fn = None
                    if scat.ismodifier:
                        if self.partofspeech == 'TO' and self.category == CAT_INFINITIVE:
                            assert self.category.argument_category.issentence
                            assert self.category.result_category.issentence
                            assert ev is not None
                            assert len(ev) == 1
                            fn = DrsProduction(DRS([], [Rel('event.is.infinitive', ev)]))
                        elif self.isgerund and scat.result_category.issentence:
                            fn = DrsProduction(DRS([], [Rel('event', ev), Rel('event.is.gerund', ev),
                                                        Rel('event.verb.' + self._word, ev),
                                                        Rel('event.attribute', [ev[0], refs[-1]])]))
                        elif self.partofspeech == 'MD':
                            assert len(refs) == 1
                            fn = DrsProduction(DRS([], [Rel('event.is.modal', ev),
                                                        Rel('event.modal.' + self._word, [ev[0], refs[0]])]))
                    if not fn:
                        fn = DrsProduction(DRS([], self.build_predicates(compose[0][1], refs, ev)),
                                            properNoun=self.isproper_noun)
                    if ev is not None:
                        fn.set_lambda_refs(ev)

                fn.set_category(signatures[0].result_category)
                for c, s in zip(compose[:-1], signatures):
                    fn = c[0](s, c[1], fn)

                # For functions with no event, ensure after function production we have lambda refs.
                comp = fn.inner_scope._comp
                if ev is None and len(comp.lambda_refs) == 0:
                    comp.set_lambda_refs(fn._lambda_refs.universe)
                return fn
            else:
                assert compose[0][0] == PropProduction
                fn = compose[0][0](self.category, compose[0][1])
                if ev is not None:
                    fn.set_lambda_refs(ev)
                return fn


debugcount = 0
def _process_ccg_node(pt, cl):
    """Internal helper for recursively processing the CCG parse tree.

    See Also:
        process_ccg_pt()
    """
    global debugcount
    dbgorig = debugcount
    if pt[-1] == 'T':
        head = int(pt[0][1])
        count = int(pt[0][2])
        result = Category(pt[0][0])
        cl2 = ProductionList()
        cl2.set_options(cl.compose_options)
        cl2.set_category(result)
        if result == Category(r'S[dcl]\NP'):
            pass
        if count > 2:
            raise DrsComposeError('Non-binary node %s in parse tree' % pt[0])

        for nd in pt[1:-1]:
            # FIXME: prefer tail end recursion
            _process_ccg_node(nd, cl2)

        debugcount += 1
        if debugcount == 170:
            pass
        cats = [x.category for x in cl2.iterator()]
        if len(cats) == 1:
            if cats[0] == Category('NP') and result == Category('NP'):
                pass
            rule = get_rule(cats[0], CAT_EMPTY, result)
            if rule is None:
                raise DrsComposeError('cannot discover production rule %s:=Rule?(%s)' % (result, cats[0]))
            if rule in [RL_TYPE_CHANGE_VPMOD, RL_TYPE_CHANGE_NP_NP, RL_TYPE_CHANGE_MOD, RL_TYPE_CHANGE_SNP]:
                ccgt = CcgTypeMapper(ccgTypeName=result, word='$$$$')
                cl2.push_right(ccgt.get_composer())
            cl2 = cl2.apply(rule).unify()
            if result.isfunctor and not cl2.isfunctor:
                pass
        elif len(cats) == 2:
            # Get the production rule
            if cats[0] == Category(r'S[dcl]\NP') and \
                            cats[1] == Category('(S\\NP)\\(S\\NP)') and \
                            result == Category('S[dcl]\\NP'):
                pass
            rule = get_rule(cats[0], cats[1], result)
            if rule is None:
                raise DrsComposeError('cannot discover production rule %s:=Rule?(%s,%s)' % (result, cats[0], cats[1]))
            elif rule in [RL_TYPE_CHANGE_VPMOD, RL_TYPE_CHANGE_NP_NP, RL_TYPE_CHANGE_MOD, RL_TYPE_CHANGE_SNP]:
                ccgt = CcgTypeMapper(ccgTypeName=result, word='$$$$')
                cl2.push_right(ccgt.get_composer())
            cl2 = cl2.apply(rule)
            if result.isfunctor and not cl2.isfunctor:
                pass
        else:
            # Parse tree is a binary tree
            assert len(cats) == 0

        cl.push_right(cl2)
        return

    # L Node in parse tree
    assert pt[-1] == 'L'
    if pt[0] in [',', '.', ':', ';']:
        return  # TODO: handle punctuation
    if pt[1] in ['will', 'Nov.', 'up.']:
        pass
    ccgt = CcgTypeMapper(ccgTypeName=pt[0], word=pt[1], posTags=pt[2:-1])
    cl.push_right(ccgt.get_composer())


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
    if pt is None or len(pt) == 0:
        return None
    cl = ProductionList()
    if options is not None:
        cl.set_options(options)
    _process_ccg_node(pt, cl)
    d = cl.unify()
    # Handle verbs with null left arg
    if d.isfunctor and d.isarg_left:
        d = d.apply_null_left().unify()
    if not isinstance(d, DrsProduction):
        raise DrsComposeError('failed to produce a DRS - %s' % repr(d))
    d = d.resolve_anaphora()
    if not d.ispure:
        raise DrsComposeError('failed to produce pure DRS - %s' % repr(d))
    return d


def _process_sentence_node(pt, s):
    if pt[-1] == 'T':
        for nd in pt[1:-1]:
            # FIXME: prefer tail end recursion
            _process_sentence_node(nd, s)
    else:
        s.append(pt[1])


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
        if not catkey.isfunctor or catkey.result_category == CAT_CONJ or catkey.argument_category == CAT_CONJ:
            return

        predarg = Category(pt[4])
        assert catkey == predarg.clean(True)
        lst.append(predarg)


def extract_predarg_categories_from_pt(pt, lst=None):
    """Extract the predicate-argument categories from a CCG parse tree.

    Args:
        pt: The parse tree returned from marbles.ie.drt.parse.parse_ccg_derivation().
        lst: An optional list of existing predicate categories.
    Returns:
        A list of Category instances.
    """
    if lst is None:
        lst = []
    _extract_predarg_categories_node(pt, lst)
    return lst

