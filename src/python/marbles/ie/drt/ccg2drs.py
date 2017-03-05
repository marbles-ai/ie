# -*- coding: utf-8 -*-

from drs import DRS, DRSRef, Prop, Imp, Rel, Neg, Box, Diamond, Or
from compose import CompositionList, FunctionComposition, DrsComposition, PropComposition, DrsComposeError
from compose import ArgRight, ArgLeft
from ccgcat import Category, CAT_N, CAT_NOUN, CAT_NP_N, CAT_DETERMINER, CAT_CONJ, RL_FA, RL_BA, RL_FC, RL_BX, get_rule

import re
from parse import parse_drs


## @cond
__pron = [
    # 1st person singular
    ('i',       '([x],[([],[i(x)])->([],[me(x)])])'),
    ('me',      '([x],[me(x)])'),
    ('myself',  '([x],[([],[myself(x)])->([],[me(x)])])'),
    ('mine',    '([],[([],[mine(x)])->([y],[me(y),owns(y,x)])])'),
    ('my',      '([],[([],[my(x)])->([y],[me(y),owns(y,x)])])'),
    # 2nd person singular
    ('you',     '([x],[you(x)])'),
    ('yourself','([x],[([],[yourself(x)])->([],[you(x)])])'),
    ('yours',   '([],[([],[yours(x)])->([y],[you(y),owns(y,x)])])'),
    ('your',    '([],[([],[your(x)])->([y],[you(y),owns(y,x)])])'),
    # 3rd person singular
    ('he',      '([x],[([],[he(x)])->([],[him(x)])])'),
    ('she',     '([x],[([],[she(x)])->([],[her(x)])])'),
    ('him',     '([x],[([],[him(x)])->([],[male(x)])])'),
    ('her',     '([x],[([],[her(x)])->([],[female(x)])])'),
    ('himself', '([x],[([],[himself(x)])->([],[him(x)])])'),
    ('herself', '([x],[([],[herself(x)])->([],[her(x)])])'),
    ('hisself', '([x],[([],[hisself(x)])->([],[himself(x)])])'),
    ('his',     '([],[([],[his(x)])->([y],[him(y),owns(y,x)])])'),
    ('hers',    '([],[([],[hers(x)])->([y],[her(y),owns(y,x)])])'),
    # 1st person plural
    ('we',      '([x],[([],[we(x)])->([],[us(x)])])'),
    ('us',      '([x],[us(x)])'),
    ('ourself', '([x],[([],[ourself(x)])->([],[our(x)])])'),
    ('ourselves','([x],[([],[ourselves(x)])->([],[our(x)])])'),
    ('ours',    '([],[([],[ours(x)])->([y],[us(y),owns(y,x)])])'),
    ('our',     '([],[([],[our(x)])->([y],[us(y),owns(y,x)])])'),
    # 2nd person plural
    ('yourselves', '([x],[([],[yourselves(x)])->([],[you(x),plural(x)])])'),
    # 3rd person plural
    ('they',    '([x],[([],[i(x)])->([],[them(x)])])'),
    ('them',    '([x],[them(x)])'),
    ('themself','([x],[([],[themself(x)])->([],[them(x)])])'),
    ('themselves','([x],[([],[themselves(x)])->([],[them(x)])])'),
    ('theirs',  '([x],[([],[theirs(x)])->([y],[them(y),owns(y,x)])])'),
    ('their',   '([],[([],[their(x)])->([y],[them(y),owns(y,x)])])'),
    # it
    ('it',      '([x],[it(x)])'),
    ('its',     '([x],[([],[its(x)])->([y],[it(y),owns(y,x)])])'),
    ('itself',  '([x],[([],[itself(x)])->([],[it(x)])])'),
]
_PRON = {}
for k,v in __pron:
    _PRON[k] = parse_drs(v, 'nltk')


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
         function, or a combinator. Functions are always constructed from outer types to inner types. For example:
         the application order for (S\T)/T is: /T, \T, S
       - Combinators: Rules which take a function as the argument and return a function of the same type. Combinators
         are always constructed from inner types to outer types. For example: the application order of (S/T)/(S/T) is:
         /T, S, /(S/T)
       - When applying combinators the resultant must produce a function, or combinator, where the DRS unifys are
         adjacent. For example:
         - (S/T)/(S/T) combinator:=λP.T[...];P(x) and (S/T) type:=λQ.R[...];Q(x)<br>
           => λQ.T[...];R[...];Q(x) which is OK<br>
         - (S/T)\(S/T) combinator:=λP.P(x);T[...] and (S/T) type:=λQ.R[...];Q(x)<br>
           => λQ.R[...];Q(x);T[...] which is not OK<br>
       - The CCG parse tree gives us the construction order so we don't need to differentiate between combinators and
         functions during composition.
    -# Lambda application:
       - λPλx.P(x) {P(x=x)=G[x|...]} == G[x|...]
       - λPλx.P(x) {P(x=y)=G[y|...])} == G[y|...]
    -# Lambda function composition
       - λPλx.P(x).λQλy.Q(y) == λPλQλxλy.P(x);Q(y) == read as P unify Q<br>
         iff x is a bound in DRS P and y is bound in DRS Q
       - λPλx.P(x).λQλy.Q(y) == λPλQλx.P(x);Q(x)<br>
         iff y is a free variable in DRS Q and x is bound, or free, in DRS P
       - λPλx.P(x).λQλy.Q(y) == λPλQλy.P(y);Q(y)<br>
         iff x is a free variable in DRS P and y is bound in DRS Q
    -# Merge is typically delayed until construction is complete, however we can do partial unify when all
       combinators have been applied at some point during the construction phase.<br>
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
        # Simple DRS functions
        # ====================
        r'Z/T':     [(PropComposition, DRSRef('p')), None],
        r'T/Z':     [(FunctionComposition, DRSRef('p')), None],
        r'T/T':     [(FunctionComposition, DRSRef('x')), None],
        r'T\T':     [(FunctionComposition, DRSRef('x')), None],
        r'(T\T)/T': [(FunctionComposition, DRSRef('y')), (FunctionComposition, DRSRef('x')), None],
        r'(T/T)/T': [(FunctionComposition, DRSRef('x')), (FunctionComposition, DRSRef('y')), None],
        r'(T/T)\T': [(FunctionComposition, DRSRef('x')), (FunctionComposition, DRSRef('y')), None],
        r'(T\T)\T': [(FunctionComposition, DRSRef('y')), (FunctionComposition, DRSRef('x')), None],
        r'(T\T)/Z': [(FunctionComposition, DRSRef('y')), (FunctionComposition, DRSRef('x')), None],
        r'(T/T)/Z': [(FunctionComposition, DRSRef('x')), (FunctionComposition, DRSRef('y')), None],
        # DRS Verb functions
        # ==================
        r'S/T':     [(FunctionComposition, DRSRef('x')), DRSRef('e')],
        r'S\T':     [(FunctionComposition, DRSRef('x')), DRSRef('e')],
        r'(S/T)/T': [(FunctionComposition, DRSRef('x')), (FunctionComposition, DRSRef('y')), DRSRef('e')],
        r'(S/T)\T': [(FunctionComposition, DRSRef('x')), (FunctionComposition, DRSRef('y')), DRSRef('e')],
        r'(S\T)/T': [(FunctionComposition, DRSRef('y')), (FunctionComposition, DRSRef('x')), DRSRef('e')],
        r'(S\T)\T': [(FunctionComposition, DRSRef('y')), (FunctionComposition, DRSRef('x')), DRSRef('e')],
        r'(S\T)/Z': [(FunctionComposition, DRSRef('y')), (FunctionComposition, DRSRef('x')), DRSRef('e')],
        r'(S/T)/Z': [(FunctionComposition, DRSRef('x')), (FunctionComposition, DRSRef('y')), DRSRef('e')],
        r'S\S':     [(FunctionComposition, DRSRef('x')), DRSRef('e')],
        r'S/S':     [(FunctionComposition, DRSRef('x'))],
        r'(((S\T)/Z)/T)/T': [(FunctionComposition, DRSRef('y')), (FunctionComposition, DRSRef('z')),
                             (FunctionComposition, DRSRef('p')), (FunctionComposition, DRSRef('x')), DRSRef('e')],
        r'((S\T)/Z)/T': [(FunctionComposition, DRSRef('y')), (FunctionComposition, DRSRef('z')),
                         (FunctionComposition, DRSRef('x')), DRSRef('e')],
        r'(S\S)\T': [(FunctionComposition, DRSRef('x')),
                     (FunctionComposition, DRSRef('e')), DRSRef('e')],
        # Mixtures: functions + combinators
        r'((S\T)\(S\T))/T': [(FunctionComposition, DRSRef('y')),
                             (FunctionComposition, [DRSRef('x'), DRSRef('e')]), DRSRef('e')],
        r'((S\T)\(S\T))\T': [(FunctionComposition, DRSRef('y')),
                             (FunctionComposition, [DRSRef('x'), DRSRef('e')]), DRSRef('e')],
        r'(((S\T)/(S\T))/(S\T))/T': [(FunctionComposition, DRSRef('y')),
                                     (FunctionComposition, DRSRef('x')), DRSRef('e')],
        r'(((S\T)/(S\T))/Z)/T': [(FunctionComposition, DRSRef('y')), (PropComposition, DRSRef('p')),
                                 (FunctionComposition, DRSRef('x')), DRSRef('e')],
        r'(((S\T)/S)/(S\T))/T': [(FunctionComposition, DRSRef('y')), (FunctionComposition, DRSRef('x')), DRSRef('e')],
        # Pure combinators
        r'(S\T)\(S\T)': [(FunctionComposition, [DRSRef('x'), DRSRef('e')]), DRSRef('e')],
        r'(S\T)/(S\T)': [(FunctionComposition, [DRSRef('x'), DRSRef('e')]), DRSRef('e')],
        r'((T/T)/(T/T))\(T\T)': [(FunctionComposition, DRSRef('x')), (FunctionComposition, DRSRef('y')), None],
        #r'(((S\T)/Z)/Z)/(S\T)':
    }
    _EventPredicates = ['agent', 'theme', 'extra']
    _TypeMonth = re.compile(r'^((Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?|January|February|March|April|June|July|August|September|October|November|December)$')
    _TypeWeekday = re.compile(r'^((Mon|Tue|Tues|Wed|Thur|Thurs|Fri|Sat|Sun)\.?|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)$')

    def __init__(self, ccgTypeName, word, posTags=None):
        self._ccgcat = Category(ccgTypeName)
        self._pos = posTags or []
        if self.isproper_noun:
            self._word = word.title().rstrip('?.,:;')
        else:
            self._word = word.lower().rstrip('?.,:;')
        self._drsSignature = self._ccgcat.drs_signature

        if self.drs_signature not in self._AllTypes:
            raise DrsComposeError('CCG type "%s" maps to unknown DRS composition type "%s"' %
                                  (ccgTypeName, self.drs_signature))

    def __repr__(self):
        return '<' + self._word + ' ' + self.partofspeech + ' ' + self.ccg_signature + '->' + self.drs_signature + '>'

    @classmethod
    def convert_model_categories(cls, ccg_categories):
        """Convert the list of CCG categories to DRS categories.

        Args:
            ccg_categories: The list of CCG categories. This can be obtained by reading the model
                categories at ext/easysrl/model/text/categories.

        Returns:
            A list of CCG categories that could not be converted or None.

        Remarks:
            Categories starting with # and empty categories are silently ignored.
        """
        results = []
        for ln in ccg_categories:
            c = ln.strip()
            if len(c) == 0 or c[0] == '#':
                continue
            # TODO: handle punctuation
            if c in ['.', '.', ':', ';']:
                continue
            category = Category(c)
            if category.drs_signature in cls._AllTypes:
                continue
        return None

    @classmethod
    def add_model_categories(cls, filename):
        """Add the CCG categories file and update the DRS types.

        Args:
            filename: The categories file from the model folder.

        Returns:
            A list of CCG categories that could not be added to the types dictionary or None.
        """
        with open(filename, 'r') as fd:
            lns = fd.readlines()

        lns_prev = []
        while lns is not None and len(lns_prev) != len(lns):
            lns_prev = lns
            lns = cls.convert_model_categories(lns)
        return lns

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

    def build_predicates(self, p_vars, refs, evt=None, conds=None):
        """Build the DRS conditions for a noun, noun phrase, or adjectival phrase. Do
        not use this for verbs or adverbs.

        Args:
            p_vars: DRSRef's used in the predicates.
            refs: lambda refs for curried function, excluding evt.
            evt: An optional event DRSRef.
            conds: A list of existing DRS conditions.

        Returns:
            A list if marbles.ie.drt.Rel instances.
        """
        assert p_vars is not None
        assert refs is not None
        if conds is None:
            conds = []
        if isinstance(p_vars, DRSRef):
            p_vars = [p_vars]
        evt_vars = None
        if evt is not None:
            evt_vars = []
            evt_vars.extend(p_vars)
            evt_vars.append(evt)

        if self.category.iscombinator:
            if evt is not None:
                refs.append(evt)
            conds.append(Rel(self._word, refs))
        elif self.isadjective:
            if evt_vars is not None:
                raise DrsComposeError('Adjective "%s" with signature "%s" does not expect an event variable'
                                      % (self._word, self.drs_signature))
            conds.append(Rel(self._word, refs))
        else:
            if self.isproper_noun:
                if self._TypeMonth.match(self._word):
                    if self._word in _MONTHS:
                        conds.append(Rel(_MONTHS[self._word], p_vars))
                    else:
                        conds.append(Rel(self._word, p_vars))
                    conds.append(Rel('is.date', p_vars))
                    if evt_vars is not None:
                        conds.append(Rel('event.date', evt_vars))
                        evt_vars = None
                elif self._TypeWeekday.match(self._word):
                    if self._word in _WEEKDAYS:
                        conds.append(Rel(_WEEKDAYS[self._word], p_vars))
                    else:
                        conds.append(Rel(self._word, p_vars))
                    conds.append(Rel('is.date', p_vars))
                    if evt_vars is not None:
                        conds.append(Rel('event.date', evt_vars))
                        evt_vars = None
                else:
                    conds.append(Rel(self._word, p_vars))
            elif self.isnumber:
                conds.append(Rel(self._word, p_vars))
                conds.append(Rel('is.number', p_vars))
            else:
                conds.append(Rel(self._word, refs))

            if evt_vars is not None:
                # Undefined relationship
                conds.append(Rel('event.related', evt_vars))
        return conds

    def get_composer(self):
        """Get the composition model for this category.

        Returns:
            A Composition instance.
        """
        compose = self._AllTypes[self.drs_signature]
        if compose is None:
            # Simple type
            # Handle prepositions 'Z'
            if self.category == CAT_CONJ:
                if self._word in ['or', 'nor']:
                    raise NotImplementedError
                return CompositionList()
            elif self.ispronoun:
                d = DrsComposition(_PRON[self._word])
                d.set_category(self.category)
                d.set_lambda_refs(d.drs.universe)
                return d
            elif self.category == CAT_N:
                d = DrsComposition(DRS([DRSRef('x')], [Rel(self._word, [DRSRef('x')])]), properNoun=self.isproper_noun)
                d.set_category(self.category)
                d.set_lambda_refs(d.drs.universe)
                return d
            elif self.category == CAT_NOUN:
                if self.isnumber:
                    d = DrsComposition(DRS([DRSRef('x')], [Rel(self._word, [DRSRef('x')]), Rel('is.number', [DRSRef('x')])]))
                else:
                    d = DrsComposition(DRS([DRSRef('x')], [Rel(self._word, [DRSRef('x')])]))
                d.set_category(self.category)
                d.set_lambda_refs(d.drs.universe)
                return d
            elif self.isadverb and self._word in _ADV:
                adv = _ADV[self._word]
                d = DrsComposition(adv[0], [x for x in adv[1]])
                d.set_category(self.category)
                d.set_lambda_refs(d.drs.universe)
                return d
            else:
                d = DrsComposition(DRS([], [Rel(self._word, [DRSRef('x')])]))
                d.set_category(self.category)
                d.set_lambda_refs(d.drs.universe)
                return d
        else:
            # Functions
            ev = compose[-1]
            if self.category == CAT_NP_N:    # NP*/N class
                # FIXME: these relations should be added as part of build_predicates()
                if self.category == CAT_DETERMINER:
                    if self._word in ['a', 'an']:
                        fn = FunctionComposition(ArgRight, DRSRef('x'), DRS([], [Rel('exists.maybe', [DRSRef('x')])]))
                    elif self._word in ['the', 'thy']:
                        fn = FunctionComposition(ArgRight, DRSRef('x'), DRS([], [Rel('exists', [DRSRef('x')])]))
                    else:
                        fn = FunctionComposition(ArgRight, DRSRef('x'), DRS([], [Rel(self._word, [DRSRef('x')])]))
                fn.set_category(self.category)
                if ev is not None:
                    fn.set_lambda_refs([ev])
                return fn
            if compose[0][0] == FunctionComposition:
                refs = []
                signatures = []
                s = self.category
                refs_without_combinator = None
                for c in compose[:-1]:
                    if refs_without_combinator is None and s.iscombinator:
                        refs_without_combinator = refs
                    signatures.append(s)
                    if s.isarg_right:
                        if isinstance(c[1], list):
                            refs.extend(c[1])
                        else:
                            refs.append(c[1])
                    else:
                        assert s.isarg_left
                        if isinstance(c[1], list):
                            r = [x for x in c[1]]
                        else:
                            r = [c[1]]
                        r.extend(refs)
                        refs = r
                    s = s.result_category

                refs_without_combinator = refs_without_combinator or refs
                if ev is not None and ev in refs:
                    refs = filter(lambda a: a != ev, refs)

                if self.isverb:
                    if ev is None:
                        raise DrsComposeError('Verb signature "%s" does not include event variable' % self.drs_signature)
                    elif self.category.iscombinator:
                        # passive case
                        refs.append(ev)
                        fn = DrsComposition(DRS([], [Rel(self._word, refs)]))
                    else:
                        # TODO: use verbnet to get semantics
                        conds = [Rel('event', [ev]), Rel(self._word, [ev])]
                        for v,e in zip(refs, self._EventPredicates):
                            conds.append(Rel('event.' + e, [ev, v]))
                        if len(refs) > len(self._EventPredicates):
                            for i in range(len(self._EventPredicates), len(refs)):
                                conds.append(Rel('event.extra.%d' % i, [ev, refs[i]]))
                        fn = DrsComposition(DRS([ev], conds))
                        fn.set_lambda_refs([ev])
                elif self.isadverb:
                    if ev is not None:
                        if _ADV.has_key(self._word):
                            adv = _ADV[self._word]
                            fn = DrsComposition(adv[0], [x for x in adv[1]])
                        else:
                            fn = DrsComposition(DRS([], self.build_predicates(compose[0][1], refs, ev)))
                        fn.set_lambda_refs([ev])
                    else:
                        fn = DrsComposition(DRS([], self.build_predicates(compose[0][1], refs)))
                else:
                    fn = DrsComposition(DRS([], self.build_predicates(compose[0][1], refs, ev)),
                                        properNoun=self.isproper_noun)
                    if ev is not None:
                        fn.set_lambda_refs([ev])

                fn.set_category(signatures[0].result_category)
                for c, s in zip(compose[:-1], signatures):
                    fn = c[0](s.isarg_right, c[1], fn)
                    fn.set_category(s)
                return fn
            else:
                assert compose[0][0] == PropComposition
                fn = compose[0][0](self.category.isarg_right, compose[0][1])
                fn.set_category(self.category)
                if ev is not None:
                    fn.set_lambda_refs([ev])
                return fn


def _process_ccg_node(pt, cl):
    """Internal helper for recursively processing the CCG parse tree.

    See Also:
        process_ccg_pt()
    """
    if pt[-1] == 'T':
        head = int(pt[0][1])
        count = int(pt[0][2])
        result = Category(pt[0][0]).simplify()
        cl2 = CompositionList()
        cl2.set_options(cl.compose_options)
        cl2.set_category(result)
        if count > 2:
            raise DrsComposeError('Non-binary node %s in parse tree' % pt[0])

        for nd in pt[1:-1]:
            # FIXME: prefer tail end recursion
            _process_ccg_node(nd, cl2)

        # Head should indicate the processing order however I have found it is not always correct.
        # Need to check signature and try again.
        # 1 => is right to left.
        if cl2.size == 1:
            cl2 = cl2.apply().unify()
        elif cl2.size == 2:
            cats = [x.category.simplify() if not x.isfunction else x.local_scope.category.simplify() for x in cl2.iterator()]
            rule = get_rule(cats[0], cats[1], result)
            if rule is None:
                raise DrsComposeError('cannot discover composition rule')
            cl2 = cl2.apply(rule[0]).unify()
        else:
            assert cl2.size == 0

        cl.push_right(cl2)
        return

    # L Node in parse tree
    assert pt[-1] == 'L'
    if pt[0] in [',', '.', ':', ';']:
        return  # TODO: handle punctuation
    ccgt = CcgTypeMapper(ccgTypeName=pt[0], word=pt[1], posTags=pt[2:-1])
    cl.push_right(ccgt.get_composer())


def process_ccg_pt(pt, options=None):
    """Process the CCG parse tree.

    Args:
        pt: The parse tree returned from marbles.ie.drt.parse.parse_ccg_derivation().
        options: None or marbles.ie.drt.compose.CO_REMOVE_UNARY_PROPS to simplify propositions.

    Returns:
        A DrsComposition instance.

    See Also:
        marbles.ie.drt.parse.parse_ccg_derivation()
    """
    if pt is None or len(pt) == 0:
        return None
    cl = CompositionList()
    if options is not None:
        cl.set_options(options)
    _process_ccg_node(pt, cl)
    d = cl.unify()
    # Handle verbs with null left arg
    if d.isfunction and d.isarg_left:
        d = d.apply_null_left().unify()
    if not isinstance(d, DrsComposition):
        raise DrsComposeError('composition failed to produce DRS - %s' % repr(d))
    d = d.purify()
    if not d.ispure:
        raise DrsComposeError('composition failed to produce pure DRS - %s' % repr(d))
    return d


