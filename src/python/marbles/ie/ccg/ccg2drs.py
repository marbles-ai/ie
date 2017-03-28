# -*- coding: utf-8 -*-
"""CCG to DRS Production Generator"""

import os
import pickle
import re

from marbles.ie.ccg.ccgcat import Category, CAT_Sadj, CAT_N, CAT_NOUN, CAT_NP_N, CAT_DETERMINER, CAT_CONJ, CAT_EMPTY, CAT_INFINITIVE, \
    CAT_Sany, CAT_NP, CAT_LRB, CAT_RRB, CAT_LQU, CAT_RQU, CAT_ADJECTIVE, CAT_PREPOSITION, CAT_ADVERB, get_rule, RL_TC_CONJ, RL_TC_ATOM, RL_TCR_UNARY, RL_TCL_UNARY, \
    RL_TYPE_RAISE, RL_BA
from marbles.ie.drt.common import DRSVar
from marbles.ie.drt.compose import ProductionList, FunctorProduction, DrsProduction, PropProduction, OrProduction, DrsComposeError
from marbles.ie.drt.drs import DRS, DRSRef, Rel
from marbles.ie.drt.parse import parse_drs
from marbles.ie.drt.utils import remove_dups, union, union_inplace, complement

## @cond
__pron = [
    # 1st person singular
    ('i',       '([],[([],[i(x1)])->([],[me(x1),.PRON(x1)])])'),
    ('me',      '([],[me(x1),.PRON(x1)])'),
    ('myself',  '([],[([],[myself(x1)])->([],[me(x1),.PRON(x1)])])'),
    ('mine',    '([],[([],[mine(x1)])->([],[me(x2),.PRON(x2),owns(x2,x1)])])'),
    ('my',      '([],[([],[my(x1)])->([],[me(x2),.PRON(x2),owns(x2,x1)])])'),
    # 2nd person singular
    ('you',     '([],[you(x1),.PRON(x1)])'),
    ('yourself','([],[([],[yourself(x1)])->([],[you(x1),.PRON(x1)])])'),
    ('yours',   '([],[([],[yours(x1)])->([],[you(x2),.PRON(x2),owns(x2,x1)])])'),
    ('your',    '([],[([],[your(x1)])->([],[you(x2),.PRON(x2),owns(x2,x1)])])'),
    # 3rd person singular
    ('he',      '([],[([],[he(x1)])->([],[him(x1),.PRON(x1)])])'),
    ('she',     '([],[([],[she(x1),.PRON(x1)])->([],[her(x1)])])'),
    ('him',     '([],[([],[him(x1),.PRON(x1)])->([],[male(x1)])])'),
    ('her',     '([],[([],[her(x1),.PRON(x1)])->([],[female(x1)])])'),
    ('himself', '([],[([],[himself(x1)])->([],[him(x1),.PRON(x1)])])'),
    ('herself', '([],[([],[herself(x1)])->([],[her(x1),.PRON(x1)])])'),
    ('hisself', '([],[([],[hisself(x1)])->([],[himself(x1),.PRON(x1)])])'),
    ('his',     '([],[([],[his(x1)])->([],[him(x2),owns(x2,x1)])])'),
    ('hers',    '([],[([],[hers(x1)])->([],[her(x2),.PRON(x2),owns(x2,x1)])])'),
    # 1st person plural
    ('we',      '([],[([],[we(x1)])->([],[us(x1),.PRON(x1)])])'),
    ('us',      '([],[us(x1)])'),
    ('ourself', '([],[([],[ourself(x1)])->([],[our(x1),.PRON(x1)])])'),
    ('ourselves','([],[([],[ourselves(x1)])->([],[our(x1),.PRON(x1)])])'),
    ('ours',    '([],[([],[ours(x1)])->([],[us(x2),.PRON(x2),owns(x2,x1)])])'),
    ('our',     '([],[([],[our(x1)])->([],[us(x2),.PRON(x2),owns(x2,x1)])])'),
    # 2nd person plural
    ('yourselves', '([],[([],[yourselves(x1)])->([],[you(x1),.PRON(x1),is.plural(x1)])])'),
    # 3rd person plural
    ('they',    '([],[([],[they(x1)])->([],[them(x1),.PRON(x1)])])'),
    ('them',    '([],[them(x1),.PRON(x1)])'),
    ('themself','([],[([],[themself(x1)])->([],[them(x1),.PRON(x1)])])'),
    ('themselves','([],[([],[themselves(x1)])->([],[them(x1),.PRON(x1)])])'),
    ('theirs',  '([],[([],[theirs(x1)])->([],[them(x2),.PRON(x2),owns(x2,x1)])])'),
    ('their',   '([],[([],[their(x1)])->([],[them(x2),.PRON(x2),owns(x2,x1)])])'),
    # it
    ('it',      '([],[it(x1),.PRON(x1)])'),
    ('its',     '([],[([],[its(x1)])->([],[it(x2),.PRON(x2),owns(x2,x1)])])'),
    ('itself',  '([],[([],[itself(x1)])->([],[it(x1),.PRON(x1)])])'),
]
_PRON = {}
for k,v in __pron:
    _PRON[k] = parse_drs(v, 'nltk')


# Order of referents is lambda_ref binding order
__adv = [
    ('up',      '([e],[])', '([],[up(e),direction(e)])'),
    ('down',    '([e],[])', '([],[down(e),direction(e)])'),
    ('left',    '([e],[])', '([],[left(e),direction(e)])'),
    ('right',   '([e],[])', '([],[right(e),direction(e)])'),
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


def identity_functor(category, ref=None):
    """Return the identity functor `λx.P(x)`.

    Args:
        category: A functor category where the result and argument are atoms.
        ref: optional DRSRef to use as identity referent.

    Returns:
        A FunctorProduction instance.

    Remarks:
        This can be used for atomic unary rules.
    """
    assert category.result_category.isatom
    assert category.argument_category.isatom
    d = DrsProduction(DRS([], []), category=category.result_category)
    if ref is None:
        ref = DRSRef('x1')
    d.set_lambda_refs([ref])
    return FunctorProduction(category, ref, d)


class FunctorTemplateGeneration(object):
    """Template Generation Variables"""

    def __init__(self):
        self.ei = 0
        self.xi = 0
        self.tags = {}

    def next_ei(self):
        self.ei += 1
        return self.ei

    def next_xi(self):
        self.xi += 1
        return self.xi

    def istagged(self, key):
        return key in self.tags

    def get_tag(self, key):
        return self.tags[key]

    def tag(self, key, v):
        self.tags[key] = v


class FunctorTemplate(object):
    """Template for functor generation."""
    _names = ['f', 'g', 'h', 'm', 'n', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w']
    _PredArgIdx = re.compile(r'^.*_(?P<idx>\d+)$')

    def __init__(self, rule, category, finalRef, finalAtom):
        """Constructor.

        Args:
            rule: The production constructor rule.
            category: A predarg category.
            finalRef: The final referent result.
            finalAtom: The final atomic category result.
        """
        self._constructor_rule = rule
        self._category = category
        self._final_ref = finalRef
        self._final_atom = finalAtom

    @property
    def constructor_rule(self):
        """Read only access to constructor rule."""
        return self._constructor_rule

    def __repr__(self):
        """Return the model as a string."""
        return self.category.clean(True).signature + ':' + self.__str__()

    def __str__(self):
        """Return the model as a string."""
        line = []
        for i in range(len(self.constructor_rule)):
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
        if self.final_ref is None:
            line.append('none')
        else:
            line.append(self.final_ref.var.to_string())
        return ''.join(line)

    @property
    def category(self):
        """Read only access to category."""
        return self._category

    @property
    def final_ref(self):
        """Read only access to final DRS referent."""
        return self._final_ref

    @property
    def final_atom(self):
        """Read only access to final atom category."""
        return self._final_atom

    @property
    def isfinalevent(self):
        """Test if the final return referent is an event."""
        return self._final_atom != CAT_Sadj and self._final_atom == CAT_Sany

    @classmethod
    def create_from_category(cls, predarg, final_atom=None, gen=None):
        """Create a functor template from a predicate-argument category.

        Args:
            predarg: The predicate-argument category.
            final_atom: for special Z|Z and T|T rules where we override the unify scope.
            gen: Optional FunctorTemplateGeneration instance. Required for unary rule generation.

        Returns:
            A FunctorTemplate instance or None if predarg is an atomic category.
        """
        # Ignore atoms and conj rules. Conj rules are handled by CcgTypeMapper
        catclean = predarg.clean(True)  # strip all pred-arg tags
        if not catclean.isfunctor or catclean.result_category == CAT_CONJ or catclean.argument_category == CAT_CONJ:
            return None

        if gen is None:
            gen = FunctorTemplateGeneration()

        predarg, final_tag = predarg.trim_functor_tag()
        predarg = predarg.clean()       # strip functor tags
        predargOrig = predarg

        fn = []
        while predarg.isfunctor:
            atoms = predarg.argument_category.extract_unify_atoms(False)
            predarg = predarg.result_category
            refs = []
            for a in atoms:
                key = None
                m = cls._PredArgIdx.match(a.signature)
                if m is not None:
                    key = m.group('idx')
                if key is None or not gen.istagged(key):
                    acln = a.clean(True)
                    if (acln == CAT_Sany and acln != CAT_Sadj) or acln.signature[0] == 'Z':
                        r = DRSRef(DRSVar('e', gen.next_ei()))
                    else:
                        r = DRSRef(DRSVar('x', gen.next_xi()))
                    if key is not None:
                        gen.tag(key, r)
                else:
                    r = gen.get_tag(key)
                refs.append(r)

            if len(refs) == 1:
                fn.append((FunctorProduction, refs[0]))
            else:
                fn.append((FunctorProduction, tuple(refs)))

        # Handle return atom
        acln = predarg.clean(True)
        key = None
        m = cls._PredArgIdx.match(predarg.signature)
        if m is not None:
            key = m.group('idx')

        if key is None or not gen.istagged(key):
            if acln == CAT_Sany and acln != CAT_Sadj:
                r = DRSRef(DRSVar('e', gen.next_ei()))
            else:
                r = DRSRef(DRSVar('x', gen.next_xi()))
            if key is not None:
                gen.tag(key, r)
        else:
            r = gen.get_tag(key)

        # If the functor is tagged then modify the final_ref
        if final_tag is not None and gen.istagged(final_tag):
            r = gen.get_tag(final_tag)

        return FunctorTemplate(tuple(fn), predargOrig, r, acln if final_atom is None else final_atom)

    def create_empty_functor(self):
        """Create a FunctorProduction with an empty inner DrsProduction

        Returns:
            A FunctorProduction.
        """
        fn = DrsProduction(drs=DRS([], []), category=self.final_atom.remove_wildcards())
        fn.set_lambda_refs([self.final_ref])
        category = self.category.clean(True).remove_wildcards()
        for c in self._constructor_rule:
            assert not category.isempty
            assert category.isfunctor
            fn = c[0](category, c[1], fn)
            category = category.result_category
        assert category.isatom
        return fn


class UnaryRule(object):
    """A unary rule."""

    def __init__(self, result, argument):
        """Constructor for unary rule `result <- argument`.

        Args:
            result: The result category.
            argument: The argument category.

        Remarks:
            Both categories must include predarg tags.
        """
        if not isinstance(result, Category):
            raise TypeError('UnaryRule expects a result Category')
        if not isinstance(argument, Category):
            raise TypeError('UnaryRule expects a argument Category')
        self._template = FunctorTemplate.create_from_category(Category.combine(result.clean(), '\\', argument.clean()))

    @staticmethod
    def create_key(result, argument):
        """Create a rule key from result and argument categories.

        Args:
            result: The result category.
            argument: The argument category.

        Returns:
            A string.

        Remarks:
            Both categories must NOT include predarg tags. To remove tags do Category.clean(True).
        """
        if not isinstance(result, Category):
            raise TypeError('UnaryRule.create_key() expects a Category instance ')
        if not isinstance(argument, Category):
            raise TypeError('UnaryRule.create_key() expects a Category instance')
        return Category.combine(result, '\\', argument).signature

    def getkey(self):
        """Get the dictionary key for this rule.

        Returns:
            A string.
        """
        return self._template.category.clean(True).signature

    def get(self):
        """Get a unary functor that can be applied using function application.

        Returns:
            A FunctorProduction instance.
        """
        return self._template.create_empty_functor()


class Model(object):
    """CCG Model"""
    _Feature = re.compile(r'\[[a-z]+\]')

    def __init__(self, templates=None, unary_rules=None):
        """Constructor.

        Args:
            templates: A dictionary of FunctorTemplates keyed by category signature.
            unary_rules: A dictionary of UnaryRules keyed by category signature
        """
        if templates is None:
            templates = {}
        if unary_rules is None:
            unary_rules = {}
        self._TEMPLATES = templates
        self._UNARY = unary_rules

    @classmethod
    def load(cls, filepath):
        with open(filepath, 'rb') as fd:
            dict = pickle.load(fd)
        return Model(dict)

    def save(self, filepath):
        with open(filepath, 'wb') as fd:
            pickle.dump(self, fd)

    def add_template(self, cat, replace=False, final_atom=None):
        """Add a template to the model.

        Args:
            cat: A Category instance or a category signature string.
            replace: Optional flag to overwrite existing entry. Existing entry is preserved by default.
            final_atom: Optional final atom category for functor template.
        """
        if isinstance(cat, str):
            cat = Category(cat)
        elif not isinstance(cat, Category):
            raise TypeError('Model.add_template() expects signature or Category')
        key = cat.clean(True).signature
        if key not in self._TEMPLATES or replace:
            templ = FunctorTemplate.create_from_category(cat, final_atom)
            self._TEMPLATES[key] = templ
            return templ
        return

    def add_unary_rule(self, result, argument, replace=False):
        """Add a unary rule."""
        if isinstance(result, str):
            result = Category(result)
        elif not isinstance(result, Category):
            raise TypeError('Model.add_unary_rule() expects signature or Category result')
        if isinstance(argument, str):
            argument = Category(argument)
        elif not isinstance(argument, Category):
            raise TypeError('Model.add_unary_rule() expects signature or Category argument')

        rule = UnaryRule(result, argument)
        key = rule.getkey()
        if key not in self._UNARY or replace:
            self._UNARY[key] = rule
            return rule
        return None

    def infer_unary(self, category):
        """Attempt to build a unary modifier from existing templates if possible."""
        if category.ismodifier:
            template = self.lookup(category.result_category)
            if template is not None:
                taggedcat = template.category.complete_tags()
                return self.add_unary_rule(Category.combine(taggedcat, category.slash, taggedcat),
                                           taggedcat)
        return None
    
    def infer_template(self, category):
        """Attempt to build a template from existing templates if possible."""
        if category.isfunctor and not self.issupported(category):
            catArgArg = category.argument_category.argument_category
            catResult = category.result_category
            if category.istype_raised and (self.issupported(catResult) or catResult.isatom) \
                    and (self.issupported(catArgArg) or catArgArg.isatom):
                # If the catgeory is type raised then check if result type exists and build now.
                # TODO: This should be sent to a log
                print('Adding type-raised category %s to TEMPLATES' % category.signature)
                # Template categories contain predarg info so build new from these
                if catResult.isfunctor:
                    catResult = self.lookup(catResult).category.complete_tags()
                else:
                    catResult = Category(catResult.signature + '_999')  # synthesize pred-arg info
                if catArgArg.isfunctor:
                    # FIXME: Should really check predarg info does not overlap with catResult. Chances are low.
                    catArgArg = self.lookup(catArgArg).category.complete_tags()
                else:
                    catArgArg = Category(catArgArg.signature + '_998')  # synthesize pred-arg info
                newcat = Category.combine(catResult, category.slash,
                                          Category.combine(catResult, category.argument_category.slash, catArgArg))
                # FIXME: This is not thread safe. Should add to separate synchronized dictionary.
                return self.add_template(newcat.signature)
            elif category.ismodifier and self.issupported(category.result_category):
                # FIXME: This is not thread safe. Should add to separate synchronized dictionary.
                predarg = self.lookup(category.result_category).category.complete_tags()
                newcat = Category.combine(predarg, category.slash, predarg)
                return self.add_template(newcat.signature)
        return None

    def lookup_unary(self, result, argument):
        if isinstance(result, str):
            result = Category(result)
        elif not isinstance(result, Category):
            raise TypeError('Model.lookup_unary() expects signature or Category result')
        if isinstance(argument, str):
            argument = Category(argument)
        elif not isinstance(argument, Category):
            raise TypeError('Model.lookup_unary() expects signature or Category argument')
        key = UnaryRule.create_key(result, argument)
        if key in self._UNARY:
            return self._UNARY[key]
        # Perform wildcard replacements
        wc = self._Feature.sub('[X]', key)
        if wc in self._UNARY:
            return self._UNARY[wc]
        return None

    def lookup(self, category):
        """Lookup a FunctorTemplate with key=category."""
        # TODO: use two dictionaries, readonly and thread-safe.
        if category.signature in self._TEMPLATES:
            return self._TEMPLATES[category.signature]
        # Perform wildcard replacements
        if category.isfunctor:
            wc = self._Feature.sub('[X]', category.signature)
            if wc in self._TEMPLATES:
                return self._TEMPLATES[wc]
        return None

    def issupported(self, category):
        """Test a FunctorTemplate is in TEMPLATES with key=category."""
        if category.signature in self._TEMPLATES:
            return True
        # Perform wildcard replacements
        if category.isfunctor:
            wc = self._Feature.sub('[X]', category.signature)
            return wc in self._TEMPLATES
        return False


# Special categories
CAT_CONJ_CONJ = Category(r'conj\conj')
CAT_CONJCONJ = Category(r'conj/conj')


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
    _EventPredicates = ('.AGENT', '.THEME', '.EXTRA')
    _TypeMonth = re.compile(r'^((Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?|January|February|March|April|June|July|August|September|October|November|December)$')
    _TypeWeekday = re.compile(r'^((Mon|Tue|Tues|Wed|Thur|Thurs|Fri|Sat|Sun)\.?|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)$')

    # Run scripts/make_functor_templates.py to create templates file
    try:
        MODEL = Model.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'functor_templates.dat'))
        # For some reason, some rules generated by EasySRL are missing from LDC CCGBANK
        MODEL.add_template(r'((S[adj]_2\NP_1)\NP_2)_1', replace=True)
        MODEL.add_template(r'PP_1/NP_2', replace=True)
        MODEL.add_template(r'N_1/PP_1', replace=True)
        MODEL.add_template(r'NP_1/PP_1', replace=True)
        MODEL.add_template(r'NP/N')
        MODEL.add_template(r'NP_1/(N_2/PP_2)')

        MODEL.add_template(r'S[dcl]_1/S[dcl]_2')
        MODEL.add_template(r'S[dcl]_1\S[dcl]_2')
        MODEL.add_template(r'S_1/(S_1\NP)')
        MODEL.add_template(r'S_1\(S_1/NP)')
        MODEL.add_template(r'(S_2\NP_1)/((S_2\NP_1)\PP)')
        MODEL.add_template(r'(S_1\NP_2)\((S_1\NP_2)/PP)')
        MODEL.add_template(r'(N_1\N_1)/(S[dcl]\NP_1)')
        MODEL.add_template(r'(S[dcl]_1\NP_2)/((S[dcl]_1\NP_2)\PP)')

        MODEL.add_template(r'S[X]_1/S[X]_2')
        MODEL.add_template(r'S[X]_1\S[X]_2')
        MODEL.add_template(r'((S[dcl]\NP_2)/NP_1)/PR')
        MODEL.add_template(r'(NP_1\NP_1)\(S[dcl]\NP_1)')
        MODEL.add_template(r'(NP_1/NP_1)\(S[adj]\NP_1)')
        MODEL.add_template(r'(NP/N)\NP')

        MODEL.add_template(r'((N_1\N_1)/S[dcl])\((N_1\N_1)/NP)')

        MODEL.add_unary_rule(r'NP_1', r'N_1')
        MODEL.add_unary_rule(r'NP_1\NP_1', r'NP_1')
        # Wildcards incur more string processing so cover main rules
        MODEL.add_unary_rule(r'N_1\N_1', r'S[pss]_2\NP_1')
        MODEL.add_unary_rule(r'N_1\N_1', r'S[adj]_2\NP_1')
        MODEL.add_unary_rule(r'N_1\N_1', r'S[dcl]_2\NP_1')
        MODEL.add_unary_rule(r'N_1\N_1', r'S[ng]_2\NP_1')
        MODEL.add_unary_rule(r'N_1\N_1', r'S_2\NP_1')
        MODEL.add_unary_rule(r'N_1\N_1', r'S[X]_2\NP_1')

        MODEL.add_unary_rule(r'S_1/S_1', r'S[pss]_1\NP')
        MODEL.add_unary_rule(r'S_1/S_1', r'S[to]_1\NP')
        MODEL.add_unary_rule(r'S_1/S_1', r'S[ng]_1\NP')
        MODEL.add_unary_rule(r'S_1/S_1', r'S[X]_1\NP')
        MODEL.add_unary_rule(r'S_1/S_1', r'S_1\NP')

        MODEL.add_unary_rule(r'S_1\S_1', r'S[X]_1\NP')
        MODEL.add_unary_rule(r'PP_1/PP_1', r'PP_1')
        MODEL.add_unary_rule(r'PP_1\PP_1', r'PP_1')
        MODEL.add_unary_rule(r'(N_1\N_1)\(N_1\N_1)', r'(N_1\N_1)')

        MODEL.add_unary_rule(r'(S[X]_1\NP_2)\(S[X]_1\NP_2)', 'S[X]_1\NP_2')
        MODEL.add_unary_rule(r'((S[X]_1\NP_2)/NP_3)\((S[X]_1\NP_2)/NP_3)', '(S[X]_1\NP_2)/NP_3')
        MODEL.add_unary_rule(r'((S[dcl]_3\NP_2)_3/((S_3\NP_2)_3\(S_3\NP_2)_3)_1)_3', r'(S[dcl]_3\NP_2)_3')
        MODEL.add_unary_rule(r'((S[pss]_3\NP_2)_3/((S_3\NP_2)_3\(S_3\NP_2)_3)_1)_3', r'(S[pss]_3\NP_2)_3')
        MODEL.add_unary_rule(r'((S[b]_3\NP_2)_3/((S_3\NP_2)_3\(S_3\NP_2)_3)_1)_3', r'(S[b]_3\NP_2)_3')
        MODEL.add_unary_rule(r'((S[ng]_3\NP_2)_3/((S_3\NP_2)_3\(S_3\NP_2)_3)_1)_3', r'(S[ng]_3\NP_2)_3')

        MODEL.add_unary_rule(r'((S_1\NP_2)\(S_1\NP_2))\((S_1\NP_2)\(S_1\NP_2))', '(S_1\NP_2)\(S_1\NP_1)')
        MODEL.add_unary_rule(r'((S[dcl]_1\NP_2)/(S[b]_1\NP_2))\((S[dcl]_1\NP_2)/(S[b]_1\NP_2))', '(S_1\NP_2)/(S_1\NP_2)')

        MODEL.add_unary_rule(r'(S[pss]_1\NP_1)\(S[pss]_1\NP_2)', 'S_1\NP_2')
        MODEL.add_unary_rule(r'(S[dcl]_1\NP_2)\(S[dcl]_1\NP_2)', 'S_1\NP_2')
        MODEL.add_unary_rule(r'(S[em]_1\NP_2)\(S[em]_1\NP_2)', 'S_1\NP_2')
        MODEL.add_unary_rule(r'(S_1\NP_2)\(S_1\NP_2)', 'S[ng]_1\NP_2')
        MODEL.add_unary_rule(r'(S[X]_1\NP_2)\(S[X]_1\NP_2)', 'S_1\NP_2')
        MODEL.add_unary_rule(r'(S_1\NP_1)\(S_1\NP_1)', 'S_1\NP_1')
        MODEL.add_unary_rule(r'(N_1/N_1)\(N_1/N_1)', 'N_1/N_1')
        MODEL.add_unary_rule(r'S[X]_1\S[X]_1', r'S[X]_1')
        MODEL.add_unary_rule(r'S[dcl]_1\S[dcl]_1', r'S_1')
        MODEL.add_unary_rule(r'S[X]_1\S[X]_1', r'S_1')
        MODEL.add_unary_rule(r'(S_1\NP_2)/(S_1\NP_2)', r'S[dcl]_1/S[dcl]_1')
        MODEL.add_unary_rule(r'S_1\S_1', 'S_1')
        MODEL.add_unary_rule(r'((S[dcl]_1\NP_2)/NP_3)\((S[dcl]_1\NP_2)/NP_3)', r'(S_1\NP_2)/NP_3')

        MODEL.add_unary_rule(r'(N_2/PP_1)\(N_2/PP_1)', r'N_2/PP_1')
        MODEL.add_unary_rule(r'(S_2/S_1)\(S_2/S_1)', r'S_2/S_1')
        MODEL.add_unary_rule(r'S_1/S_1', r'S[ng]_1\NP_2')

        MODEL.add_unary_rule(r'NP_1', r'S[ng]_1\NP_2')
        MODEL.add_unary_rule(r'NP_1', r'S_1\NP_2')
        MODEL.add_unary_rule(r'NP_1', r'S[X]_1\NP_2')


        MODEL.add_unary_rule(r'NP_1\NP_1', r'S[pss]_2\NP_1')
        MODEL.add_unary_rule(r'NP_1\NP_1', r'S[adj]_2\NP_1')
        MODEL.add_unary_rule(r'NP_1\NP_1', r'S[dcl]_2\NP_1')
        MODEL.add_unary_rule(r'NP_1\NP_1', r'S[ng]_2\NP_1')
        MODEL.add_unary_rule(r'NP_1\NP_1', r'S_2\NP_1')
        MODEL.add_unary_rule(r'NP_1\NP_1', r'S_2/NP_1')
        MODEL.add_unary_rule(r'NP_1\NP_1', r'S[X]_2\NP_1')
        MODEL.add_unary_rule(r'(S_1\NP_2)/(S_1\NP_2)', 'S[ng]_1\NP_2')
        MODEL.add_unary_rule(r'(S_1\NP_2)\(S_1\NP_2)', 'S[to]_1\NP_2')
        MODEL.add_unary_rule(r'(S_1\NP_2)\(S_1\NP_2)', 'S[X]_1\NP_2')
        MODEL.add_unary_rule(r'(S_1\NP_2)\(S_1\NP_2)', 'NP_2')
        MODEL.add_unary_rule(r'NP_1\NP_1', 'S[dcl]_1')


    except Exception as e:
        print(e)
        # Allow module to load else we cannot create the dat file.
        MODEL = Model()

    def __init__(self, ccgTypeName, word, posTags=None):
        if isinstance(ccgTypeName, Category):
            self._ccgcat = ccgTypeName
        else:
            self._ccgcat = Category(ccgTypeName)
        self._pos = posTags or ['UNKNOWN']

        # We treat modal as verb modifiers - i.e. they don't get their own event
        if self._pos[0] == 'MD':
            tmpcat = self._ccgcat.remove_features().simplify()
            if tmpcat.ismodifier:
                self._ccgcat = tmpcat

        if self.isproper_noun:
            self._word = word.title().rstrip('?.,:;')
        else:
            self._word = word.lower().rstrip('?.,:;')

        # Atomic types don't need a template
        if self.category.isfunctor and not self.MODEL.issupported(self.category) \
            and self.category != CAT_CONJ_CONJ and self.category != CAT_CONJCONJ:
            templ = self.MODEL.infer_template(self.category)
            if templ is not None:
                raise DrsComposeError('CCG type "%s" for word "%s" maps to unknown DRS production type "%s"' %
                                      (ccgTypeName, word, self.signature))

    def __repr__(self):
        return '<' + self._word + ' ' + self.partofspeech + ' ' + self.signature + '>'

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
        #return self.partofspeech == 'IN'
        return self.category == CAT_PREPOSITION

    @property
    def isadverb(self):
        """Test if the word attached to this category is an adverb."""
        #return self.partofspeech in ['RB', 'RBR', 'RBS']
        return self.category == CAT_ADVERB

    @property
    def isverb(self):
        """Test if the word attached to this category is a verb."""
        # Verbs can behave as adjectives
        return self.partofspeech in ['VB', 'VBD', 'VBN', 'VBP', 'VBZ'] and self.category != CAT_ADJECTIVE

    @property
    def isconj(self):
        """Test if the word attached to this category is a conjoin."""
        return self.signature == 'conj'

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
        #return self.partofspeech == 'JJ' or
        return self.category == CAT_ADJECTIVE

    @property
    def partofspeech(self):
        """Get part of speech of the word attached to this category."""
        return self._pos[0] if self._pos is not None else 'UNKNOWN'

    @property
    def signature(self):
        """Get the CCG category signature."""
        return self._ccgcat.signature

    @property
    def category(self):
        """Get the CCG category."""
        return self._ccgcat

    @classmethod
    def lookup_unary(cls, result, argument):
        return cls.MODEL.lookup_unary(result, argument)

    @classmethod
    def lookup(cls, category):
        return cls.MODEL.lookup(category)

    @classmethod
    def get_empty_functor(cls, category, key=None):
        """Get a functor with an empty DRS. The functor must exist in the class templates
        else an exception will be raised.

        Args:
            category: A category.
            key: A signature string. If none then defaults to category signature.

        Returns:
            A FunctionProduction instance.

        Raises:
            KeyError

        Remarks:
            Used for special type shift rules.
        """
        template = cls.MODEL.lookup(category if key is None else key)
        compose = template.constructor_rule
        fn = DrsProduction(DRS([], []))
        fn.set_lambda_refs([template.final_ref])
        fn.set_category(template.final_atom)
        for c in compose:
            fn = c[0](category, c[1], fn)
            category = category.result_category
        return fn

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
        else:
            conds.append(Rel(self._word, [refs[0]]))
        return conds

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
                    conds.append(Rel(self._word, [x for x in refs]))
                elif len(refs) == 2:
                    conds.append(Rel(self._word, [x for x in refs]))
                elif len(refs) > 2:
                    conds.append(Rel(self._word, [x for x in refs]))
                refs.reverse() # for caller
            else:
                conds.append(Rel(self._word, [x for x in refs]))    # shallow copy refs
        elif self.isadjective:
            if evt_vars is not None:
                raise DrsComposeError('Adjective "%s" with signature "%s" does not expect an event variable'
                                      % (self._word, self.signature))
            conds.append(Rel(self._word, [x for x in refs]))    # shallow copy refs
        else:
            if self.isproper_noun:
                if len(p_vars) != 1:
                    pass
                assert len(p_vars) == 1
                if self._TypeMonth.match(self._word):
                    conds.append(Rel('.DATE', p_vars))
                    if evt_vars is not None:
                        conds.append(Rel('.EDATE', evt_vars))
                    if self._word in _MONTHS:
                        conds.append(Rel(_MONTHS[self._word], p_vars))
                    else:
                        conds.append(Rel(self._word, p_vars))
                elif self._TypeWeekday.match(self._word):
                    conds.append(Rel('.DATE', p_vars))
                    if evt_vars is not None:
                        conds.append(Rel('.EDATE', evt_vars))
                    if self._word in _WEEKDAYS:
                        conds.append(Rel(_WEEKDAYS[self._word], p_vars))
                    else:
                        conds.append(Rel(self._word, p_vars))
                else:
                    if evt_vars is not None:
                        conds.append(Rel('.RELATED', evt_vars))
                    conds.append(Rel(self._word, p_vars))
            elif self.isnumber:
                assert len(p_vars) == 1
                conds.append(Rel('.NUM', p_vars))
                if evt_vars is not None:
                    conds.append(Rel('.RELATED', evt_vars))
                conds.append(Rel(self._word, p_vars))
            elif evt_vars is not None and len(p_vars) != 0:
                conds.append(Rel('.RELATED', evt_vars))
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
            template = self.MODEL.lookup(self.category)
            compose = template.constructor_rule
        except:
            template = None
            compose = None

        if compose is None:
            # Simple type
            # Handle prepositions
            if self.isconj:
                if self._word == ['or', 'nor']:
                    return OrProduction(negate=('n' in self._word))
                return ProductionList(category=CAT_CONJ)
            elif self.ispronoun and self._word in _PRON:
                d = DrsProduction(_PRON[self._word], category=self.category)
                d.set_lambda_refs(union(d.drs.universe, d.drs.freerefs))
                return d
            elif self.category == CAT_N:
                d = DrsProduction(DRS([DRSRef('x1')], [Rel(self._word, [DRSRef('x1')])]), properNoun=self.isproper_noun)
                d.set_category(self.category)
                d.set_lambda_refs([DRSRef('x1')])
                return d
            elif self.category == CAT_NOUN:
                if self.isnumber:
                    d = DrsProduction(DRS([DRSRef('x1')], [Rel(self._word, [DRSRef('x1')]), Rel('.NUM', [DRSRef('x1')])]))
                else:
                    d = DrsProduction(DRS([DRSRef('x1')], [Rel(self._word, [DRSRef('x1')])]))
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
            # FIXME: these relations should be added as part of build_predicates()
            if self.category == CAT_DETERMINER:
                if self._word in ['a', 'an']:
                    fn = DrsProduction(DRS([], [Rel('.MAYBE', [DRSRef('x1')])]), category=CAT_NP)
                elif self._word in ['the', 'thy']:
                    fn = DrsProduction(DRS([], [Rel('.EXISTS', [DRSRef('x1')])]), category=CAT_NP)
                else:
                    fn = DrsProduction(DRS([], [Rel(self._word, [DRSRef('x1')])]), category=CAT_NP)
            elif self.partofspeech == 'DT' and self._word in ['the', 'thy']:
                fn = DrsProduction(DRS([], [Rel('.EXISTS', [DRSRef('x1')])]), category=CAT_NP)
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

            refs.append(template.final_ref)
            refs.reverse()
            refs = remove_dups(refs)
            final_atom = template.final_atom.remove_wildcards()

            # Verbs can also be adjectives so check event
            if self.isverb and template.isfinalevent:
                if self.category.iscombinator or self.category.ismodifier:
                    # passive case
                    if len(refs) > 1:
                        fn = DrsProduction(DRS([], [Rel(self._word, [refs[0]]), Rel('.MOD', refs)]))
                    else:
                        fn = DrsProduction(DRS([], [Rel(self._word, [refs[0]])]))
                else:
                    # TODO: use verbnet to get semantics
                    rrf = [x for x in reversed(refs[1:])]
                    conds = [Rel('.EVENT', [refs[0]]), Rel(self._word, [refs[0]])]
                    pred = zip(rrf, self._EventPredicates)
                    for v, e in pred:
                        conds.append(Rel(e, [refs[0], v]))
                    if len(rrf) > len(pred):
                        rx = [refs[0]]
                        rx.extend(rrf[len(pred):])
                        conds.append(Rel('.EXTRA', rx))
                    fn = DrsProduction(DRS([refs[0]], conds))
            elif self.isadverb and template.isfinalevent:
                if self._word in _ADV:
                    adv = _ADV[self._word]
                    fn = DrsProduction(adv[0], [x for x in adv[1]])
                    rs = zip(adv[1], refs)
                    fn.rename_vars(rs)
                else:
                    fn = DrsProduction(DRS([], [Rel(self._word, refs[0])]))

            elif self.ispreposition or (final_atom == CAT_Sadj and len(refs) > 1):
                fn = DrsProduction(DRS([], [Rel(self._word, refs)]))

            else:
                if template.isfinalevent:
                    if self.category == CAT_INFINITIVE:
                        fn = DrsProduction(DRS([], []))
                    elif self.partofspeech == 'MD':
                        fn = DrsProduction(DRS([], [Rel(self._word, [refs[0]]),
                                                    Rel('.MODAL', [refs[0]])]))
                    else:
                        fn = DrsProduction(DRS([], self.build_conditions([], refs, template)),
                                           properNoun=self.isproper_noun)
                else:
                    fn = DrsProduction(DRS([], self.build_conditions([], refs, template)),
                                       properNoun=self.isproper_noun)

            fn.set_lambda_refs([template.final_ref])
            fn.set_category(final_atom)
            for c, s in zip(compose, signatures):
                fn = c[0](s, c[1], fn)
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
            if cats[0] == Category('S[ng]\\NP') and result == Category('(S\\NP)\\(S\\NP)'):
                pass
            rule = get_rule(cats[0], CAT_EMPTY, result)
            if rule is None:
                # TODO: log a warning if we succeed on take 2
                rule = get_rule(cats[0].simplify(), CAT_EMPTY, result)
                if rule is None:
                    raise DrsComposeError('cannot discover production rule %s <- Rule?(%s)' % (result, cats[0]))

            if rule == RL_TYPE_RAISE:
                ccgt = CcgTypeMapper(ccgTypeName=result, word='$$$$')
                cl2.push_right(ccgt.get_composer())
            elif rule == RL_TCL_UNARY:
                rule = RL_BA
                unary = CcgTypeMapper.lookup_unary(result, cats[0])
                if unary is None and result.ismodifier and result.result_category == cats[0]:
                    unary = CcgTypeMapper.MODEL.infer_unary(result)
                if unary is None:
                    raise DrsComposeError('cannot find unary rule (%s)\\(%s)' % (result, cats[0]))
                cl2.push_right(unary.get())
            elif rule == RL_TC_ATOM:
                rule = RL_BA
                cl2.push_right(identity_functor(Category.combine(result, '\\', cats[0])))

            cl2 = cl2.apply(rule).unify()
            if not cl2.verify() or not cl2.category.can_unify(result):
                pass
            if result.get_scope_count() != cl2.get_scope_count():
                pass
        elif len(cats) == 2:
            # Get the production rule
            if cats[0] == Category(r'S/(S\NP)') and \
                            cats[1] == Category(r'(S[dcl]\NP)/NP') and \
                            result == Category(r'S[dcl]/NP'):
                pass
            rule = get_rule(cats[0], cats[1], result)
            if rule is None:
                # TODO: log a warning if we succeed on take 2
                rule = get_rule(cats[0].simplify(), cats[1].simplify(), result)
                if rule is None:
                    raise DrsComposeError('cannot discover production rule %s <- Rule?(%s,%s)' % (result, cats[0], cats[1]))

            if rule == RL_TC_CONJ:
                ccgt = CcgTypeMapper(ccgTypeName=result, word='$$$$')
                cl2.push_right(ccgt.get_composer())
            elif rule == RL_TCL_UNARY:
                rule = RL_BA
                unary = CcgTypeMapper.lookup_unary(result, cats[0])
                if unary is None and result.ismodifier and result.result_category == cats[0]:
                    unary = CcgTypeMapper.MODEL.infer_unary(result)
                if unary is None:
                    raise DrsComposeError('cannot find unary rule (%s)\\(%s)' % (result, cats[0]))
                cl2.push_right(unary.get())
            elif rule == RL_TCR_UNARY:
                rule = RL_BA
                unary = CcgTypeMapper.lookup_unary(result, cats[1])
                if unary is None and result.ismodifier and result.result_category == cats[1]:
                    unary = CcgTypeMapper.MODEL.infer_unary(result)
                if unary is None:
                    raise DrsComposeError('cannot find unary rule (%s)\\(%s)' % (result, cats[1]))
                cl2.push_right(unary.get())
            elif rule == RL_TC_ATOM:
                # Special rule to change atomic type
                rule = RL_BA
                cl2.push_right(identity_functor(Category.combine(result, '\\', cats[0])))

            cl2 = cl2.apply(rule)
            if not cl2.verify() or not cl2.category.can_unify(result):
                pass
            if result.get_scope_count() != cl2.get_scope_count():
                pass
        else:
            # Parse tree is a binary tree
            assert len(cats) == 0

        cl.push_right(cl2)
        return

    # L Node in parse tree
    assert pt[-1] == 'L'
    if pt[0] in [',', '.', ':', ';']:
        cl.push_right(DrsProduction(DRS([], []), category=Category(pt[0])))
        return

    if pt[1] in ['as']:
        pass
    ccgt = CcgTypeMapper(ccgTypeName=pt[0], word=pt[1], posTags=pt[2:-1])
    if ccgt.category in [CAT_LRB, CAT_RRB, CAT_LQU, CAT_RQU]:
        # FIXME: start new parse tree
        return
    fn = ccgt.get_composer()
    if not fn.verify():
        pass
    cl.push_right(fn)


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

