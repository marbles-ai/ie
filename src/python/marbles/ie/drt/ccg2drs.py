# -*- coding: utf-8 -*-

from drs import DRS, DRSRef, Prop, Imp, Rel, Neg, Box, Diamond, Or
from compose import CompositionList, FunctionComposition, DrsComposition, PropComposition, DrsComposeError
from compose import ArgRight, ArgLeft
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


class CcgTypeMapper(object):
    """Mapping from CCG types to DRS types and the construction rules.

    Construction Rules:
    -# We have two levels of construction.
        - Lambda construction rules apply to DRS, i.e. variables are DRS, not referents.
        - DRS construction is via merge operation, infix operator ';'
          Merge works like application in lambda calculus, i.e. right to left.
          <b>Note:</b> This is not the merge function in our python DRS implementation.
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
       - When applying combinators the resultant must produce a function, or combinator, where the DRS merges are
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
       - λPλx.P(x).λQλy.Q(y) == λPλQλxλy.P(x);Q(y) == read as P merge Q<br>
         iff x is a bound in DRS P and y is bound in DRS Q
       - λPλx.P(x).λQλy.Q(y) == λPλQλx.P(x);Q(x)<br>
         iff y is a free variable in DRS Q and x is bound, or free, in DRS P
       - λPλx.P(x).λQλy.Q(y) == λPλQλy.P(y);Q(y)<br>
         iff x is a free variable in DRS P and y is bound in DRS Q
    -# Merge is typically delayed until construction is complete, however we can do partial merge when all
       combinators have been applied at some point during the construction phase.<br>
       P[x|...];Q[x|...] := merge(P[x|...],Q[x|...])
    -# Promotion to a proposition. This is done to ensure the number of referents agree in a lambda definition.<br>
       λPλx.P(x);Q[x|...] {P=R[x,y|...]} := [u|u:R[x,y|...]];Q[u|...]<br>
       λQλx.P[x|...];Q(x) {Q=R[x,y|...]} := P[u|...];[u|u:R[x,y|...]]
    -# Proposition simplification.<br>
       [p|p:Q[x|...]] can be simplified to Q(x=p) if p is the only bound referent.
    """
    # FIXME: variable names set ordering in get_composer(). Should use left/right arg position to determine order.
    _AllTypes = {
        # DRS base types
        # ==============
        'Z':            None,
        'T':            None,
        'conj':         None,
        # Simple DRS functions
        # ====================
        r'Z/T':         [(PropComposition, ArgRight, DRSRef('p')), None],
        r'T/Z':         [(FunctionComposition, ArgRight, DRSRef('p')), None],
        r'T/T':         [(FunctionComposition, ArgRight, DRSRef('x')), None],
        r'T\T':         [(FunctionComposition, ArgLeft, DRSRef('x')), None],
        r'(T\T)/T':     [(FunctionComposition, ArgRight, DRSRef('y')), (FunctionComposition, ArgLeft, DRSRef('x')), None],
        r'(T/T)/T':     [(FunctionComposition, ArgRight, DRSRef('x')), (FunctionComposition, ArgRight, DRSRef('y')), None],
        r'(T/T)\T':     [(FunctionComposition, ArgLeft, DRSRef('x')), (FunctionComposition, ArgRight, DRSRef('y')), None],
        r'(T\T)\T':     [(FunctionComposition, ArgLeft, DRSRef('y')), (FunctionComposition, ArgLeft, DRSRef('x')), None],
        r'(T\T)/Z':     [(FunctionComposition, ArgRight, DRSRef('y')), (FunctionComposition, ArgLeft, DRSRef('x')), None],
        r'(T/T)/Z':     [(FunctionComposition, ArgRight, DRSRef('x')), (FunctionComposition, ArgRight, DRSRef('y')), None],
        # DRS Verb functions
        # ==================
        r'S/T':         [(FunctionComposition, ArgRight, DRSRef('x')), DRSRef('e')],
        r'S\T':         [(FunctionComposition, ArgLeft, DRSRef('x')), DRSRef('e')],
        r'(S/T)/T':     [(FunctionComposition, ArgRight, DRSRef('x')),
                         (FunctionComposition, ArgRight, DRSRef('y')), DRSRef('e')],
        r'(S/T)\T':     [(FunctionComposition, ArgLeft, DRSRef('x')),
                         (FunctionComposition, ArgRight, DRSRef('y')), DRSRef('e')],
        r'(S\T)/T':     [(FunctionComposition, ArgRight, DRSRef('y')),
                         (FunctionComposition, ArgLeft, DRSRef('x')), DRSRef('e')],
        r'(S\T)\T':     [(FunctionComposition, ArgLeft, DRSRef('y')),
                         (FunctionComposition, ArgLeft, DRSRef('x')), DRSRef('e')],
        r'(S\T)/Z':     [(FunctionComposition, ArgRight, DRSRef('y')),
                         (FunctionComposition, ArgLeft, DRSRef('x')), DRSRef('e')],
        r'(S/T)/Z':     [(FunctionComposition, ArgRight, DRSRef('x')),
                         (FunctionComposition, ArgRight, DRSRef('y')), DRSRef('e')],
        r'S\S':         [(FunctionComposition, ArgLeft, DRSRef('x')), DRSRef('e')],
        r'S/S':         [(FunctionComposition, ArgRight, DRSRef('x'))],
        r'(((S\T)/Z)/T)/T': [(FunctionComposition, ArgRight, DRSRef('y')),
                             (FunctionComposition, ArgRight, DRSRef('z')),
                             (FunctionComposition, ArgRight, DRSRef('p')),
                             (FunctionComposition, ArgLeft, DRSRef('x')), DRSRef('e')],
        r'((S\T)/Z)/T': [(FunctionComposition, ArgRight, DRSRef('y')), (FunctionComposition, ArgRight, DRSRef('z')),
                             (FunctionComposition, ArgLeft, DRSRef('x')), DRSRef('e')],
        r'((S\T)\(S\T))/T': [(FunctionComposition, ArgRight, DRSRef('y')), (FunctionComposition, ArgLeft,
                                                                            [DRSRef('x'), DRSRef('e')]), DRSRef('e')],
        # Simple combinators
        # ==================
        # S\T:=λQλx.Q(x);U[...], combinator(S\T)\(S\T):=λPλx.P(x);T[...]
        # => λQλx.Q(x);U[...];T[...]
        r'(S\T)\(S\T)': [(FunctionComposition, ArgLeft, [DRSRef('x'), DRSRef('e')]), DRSRef('e')],
        r'(S\T)/(S\T)': [(FunctionComposition, ArgRight, [DRSRef('x'), DRSRef('e')]), DRSRef('e')],
        # S\T:=λQλx.Q(x);U[...], combinator(S\T)/(S\T):=λPλx.T[...];P(x) => λQλx.T[...];Q(x);U[...]
        # combinator((S\T)/(S\T))/((S\T)/(S\T)):=λP'λx.T'[...];P'(x) => λQλx.T'[...];T[...];Q(x);U[...]
        # combinator(((S\T)/(S\T))/((S\T)/(S\T)))/(((S\T)/(S\T))/((S\T)/(S\T))):=λP''λx.T''[...];P''(x)
        # => λQλx.T''[...];T'[...];T[...];Q(x);U[...]
        # r'(((S\T)/(S\T))/((S\T)/(S\T)))/(((S\T)/(S\T))/((S\T)/(S\T)))': [(Combinator, ArgRight, DRSRef('x'))],
        # Functions returning combinators
        # ===============================
        # (((S\T)/(S\T))/(S\T))/T
        # (*)/T:=λx.U[...];Q(x), S\T:=λQ'λx.Q'(x);U'[...]
        # combinator(*)/(S\T):=λPλx.T[...];P(x) => λQ'λx.T[...];Q'(x);U'[...]
        # combinator(S\T)/(S\T):=λP'λx.T'[...];P'(x) => λQ'λx.T'[...];T[...];Q'(x);U'[...]

        r'(((S\T)/(S\T))/(S\T))/T': [(FunctionComposition, ArgRight, DRSRef('y')), (FunctionComposition, ArgRight,
                                                                                    DRSRef('x')), DRSRef('e')],
        r'(((S\T)/(S\T))/Z)/T': [(FunctionComposition, ArgRight, DRSRef('y')), (PropComposition, ArgRight, DRSRef('p')),
                                 (FunctionComposition, ArgRight, DRSRef('x')), DRSRef('e')],
        r'(((S\T)/S)/(S\T))/T': [(FunctionComposition, ArgRight, DRSRef('y')), (FunctionComposition, ArgRight,
                                                                                DRSRef('x')), DRSRef('e')],
        #r'(((S\T)/Z)/Z)/(S\T)':
    }
    _EventPredicates = ['agent', 'theme', 'extra']
    _TypeChangerAll = re.compile(r'S\[adj\]|NP(?:\[[a-z]+\])?|N(?:\[[a-z]+\])?|PP')
    _TypeChangerNoPP = re.compile(r'S\[adj\]|NP(?:\[[a-z]+\])?|N(?:\[[a-z]+\])?')
    _TypeSimplyS = re.compile(r'S(?!\[adj\])(?:\[[a-z]+\])?')
    _TypeSimplyN = re.compile(r'N(?:\[[a-z]+\])?')
    _TypeMonth = re.compile(r'^((Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?|January|February|March|April|June|July|August|September|October|December)$')

    def __init__(self, ccgTypeName, word, posTags=None):
        self._ccgTypeName = ccgTypeName
        self._pos  = posTags or []
        self._drsTypeName = self.get_drs_typename(ccgTypeName)
        if self.isproper_noun:
            self._word = word.title().rstrip('?.,:;')
        else:
            self._word = word.lower().rstrip('?.,:;')

        if not self._AllTypes.has_key(self._drsTypeName):
            raise DrsComposeError('CCG type "%s" maps to unknown DRS composition type "%s"' %
                                  (ccgTypeName, self._drsTypeName))

    def __repr__(self):
        return '<' + self._word + ' ' + self.partofspeech + ' ' + self._ccgTypeName + '->' + self._drsTypeName + '>'

    @staticmethod
    def iscombinator_signature(signature):
        """Test if a DRS, or CCG type, is a combinator. A combinator expects a function as the argument and returns a
        function.

        Args:
            signature: The DRS signature.

        Returns:
            True if the signature is a combinator
        """
        return signature[-1] == ')' and signature[0] == '('

    @staticmethod
    def isfunction_signature(signature):
        """Test if a DRS, or CCG type, is a function.
r
        Args:
            signature: The DRS signature.

        Returns:
            True if the signature is a function.
        """
        return len(signature.replace('\\', '/').split('/')) > 1

    @staticmethod
    def split_signature(signature):
        """Split a DRS, or CCG type, into argument and return types.

        Args:
            signature: The DRS signature.

        Returns:
            A 3-tuple of <return type>, [\/], <argument type>
        """
        b = 0
        for i in reversed(range(len(signature))):
            if signature[i] == ')':
                b += 1
            elif signature[i] == '(':
                b -= 1
            elif b == 0 and signature[i] in ['/', '\\']:
                ret = signature[0:i]
                arg = signature[i+1:]
                if ret[-1] == ')' and ret[0] == '(':
                    ret = ret[1:-1]
                if arg[-1] == ')' and arg[0] == '(':
                    arg = arg[1:-1]
                return ret, signature[i], arg
        return None

    @staticmethod
    def join_signature(sig):
        """Join a split signature.

        Args:
            sig: The split signature tuple returned from split_signature().

        Returns:
            A signature string.

        See Also:
            split_signature()
        """
        assert len(sig) == 3 and isinstance(sig, tuple)
        fr = CcgTypeMapper.isfunction_signature(sig[0])
        fa = CcgTypeMapper.isfunction_signature(sig[2])
        if fr and fa:
            return '(%s)%s(%s)' % sig
        elif fr:
            return '(%s)%s%s' % sig
        elif fa:
            return '%s%s(%s)' % sig
        else:
            return '%s%s%s' % sig

    @classmethod
    def get_drs_typename(cls, ccgTypeName):
        """Get the DRS type from a CCG type.

        Args:
            ccgTypeName: A CCG type.

        Returns:
            A DRS type.
        """
        return cls._TypeChangerAll.sub('Z', cls._TypeChangerNoPP.sub('T', cls._TypeSimplyS.sub('S', ccgTypeName)))

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
            d = cls.get_drs_typename(c)
            if d in cls._AllTypes:
                continue
            if cls.iscombinator_signature(d):
                sig = cls.split_signature(d)
                if sig[0] == sig[2]:
                    if sig[0] in cls._AllTypes:
                        cls._AllTypes[d] = cls._AllTypes[sig[0]]
                        continue

                elif len(sig[0]) < len(sig[2]) and sig[0] in sig[2] and cls.iscombinator_signature(sig[0]):
                    sig2 = cls.split_signature(sig[2])
                    if sig2[0] == sig[0] and sig2[2] == sig[0]:
                        if sig[0] in cls._AllTypes:
                            cls._AllTypes[d] = cls._AllTypes[sig[0]]
                            continue
                elif len(sig[2]) < len(sig[0]) and sig[2] in sig[0] and cls.iscombinator_signature(sig[2]):
                    sig0 = cls.split_signature(sig[0])
                    if sig0[0] == sig[2] and sig0[2] == sig[2]:
                        if sig[2] in cls._AllTypes:
                            cls._AllTypes[d] = cls._AllTypes[sig[2]]
                            continue
            results.append(c)
        return results if len(results) != 0 else None

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
    def ispronoun(self):
        """Test if the word attached to this category is a pronoun."""
        return (self._pos is not None and self._pos and self._pos[0] in ['PRP', 'PRP$', 'WP', 'WP$']) or \
                    _PRON.has_key(self._word)
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
        return self._ccgTypeName == 'conj'

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
    def ccgtype(self):
        """Get the CCG category type."""
        return self._ccgTypeName

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

        if self.iscombinator_signature(self._drsTypeName):
            if evt is not None:
                refs.append(evt)
            conds.append(Rel(self._word, refs))
        elif self.isadjective:
            if evt_vars is not None:
                raise DrsComposeError('Adjective "%s" with signature "%s" does not expect an event variable'
                                      % (self._word, self._drsTypeName))
            conds.append(Rel(self._word, refs))
        else:
            conds.append(Rel(self._word, p_vars))
            if self.isproper_noun:
                if self._TypeMonth.match(self._word):
                    conds.append(Rel('is.date', p_vars))
                    if evt_vars is not None:
                        conds.append(Rel('event.date', evt_vars))
                        evt_vars = None
            elif self.isnumber:
                conds.append(Rel('is.number', p_vars))

            if evt_vars is not None:
                # Undefined relationship
                conds.append(Rel('event.related', evt_vars))
        return conds

    def get_composer(self):
        """Get the composition model for this category.

        Returns:
            A Composition instance.
        """
        compose = self._AllTypes[self._drsTypeName]
        if compose is None:
            # Simple type
            # Handle prepositions 'Z'
            if self.isconj:
                if self._word in ['or', 'nor']:
                    raise NotImplementedError
                return CompositionList()
            elif self.ispronoun:
                d = DrsComposition(_PRON[self._word])
                d.set_lambda_refs(d.drs.universe)
                return d
            elif self._ccgTypeName == 'N':
                d = DrsComposition(DRS([DRSRef('x')], [Rel(self._word, [DRSRef('x')])]), properNoun=self.isproper_noun)
                d.set_lambda_refs(d.drs.universe)
                return d
            elif self._TypeSimplyN.match(self._ccgTypeName):
                if self.isnumber:
                    d = DrsComposition(DRS([DRSRef('x')], [Rel(self._word, [DRSRef('x')]), Rel('is.number', [DRSRef('x')])]))
                else:
                    d = DrsComposition(DRS([DRSRef('x')], [Rel(self._word, [DRSRef('x')])]))
                d.set_lambda_refs(d.drs.universe)
                return d
            elif self.isadverb and _ADV.has_key(self._word):
                adv = _ADV[self._word]
                d = DrsComposition(adv[0], [x for x in adv[1]])
                d.set_lambda_refs(d.drs.universe)
                return d
            else:
                d = DrsComposition(DRS([], [Rel(self._word, [DRSRef('x')])]))
                d.set_lambda_refs(d.drs.universe)
                return d
        else:
            # Functions
            ev = compose[-1]
            if self._ccgTypeName == 'NP/N':
                if self._word in ['a', 'an']:
                    fn = FunctionComposition(ArgRight, DRSRef('x'), DRS([], [Rel('exists.maybe', [DRSRef('x')])]))
                elif self._word in ['the', 'thy']:
                    fn = FunctionComposition(ArgRight, DRSRef('x'), DRS([], [Rel('exists', [DRSRef('x')])]))
                else:
                    fn = FunctionComposition(ArgRight, DRSRef('x'), DRS([], [Rel(self._word, [DRSRef('x')])]))
                fn.set_signature('T/T')
                if ev is not None:
                    fn.set_lambda_refs([ev])
                return fn
            if compose[0][0] == FunctionComposition:
                refs = []
                signatures = []
                s = self._drsTypeName
                refs_without_combinator = None
                for c in compose[:-1]:
                    if refs_without_combinator is None and self.iscombinator_signature(s):
                        refs_without_combinator = refs
                    s = self.split_signature(s)
                    signatures.append(s)
                    s = s[0]
                    if c[1]:
                        # arg right
                        if isinstance(c[2], list):
                            refs.extend(c[2])
                        else:
                            refs.append(c[2])
                    else:   # arg left
                        if isinstance(c[2], list):
                            r = [x for x in c[2]]
                        else:
                            r = [c[2]]
                        r.extend(refs)
                        refs = r

                refs_without_combinator = refs_without_combinator or refs
                if ev is not None and ev in refs:
                    refs = filter(lambda a: a != ev, refs)

                if self.isverb:
                    if ev is None:
                        raise DrsComposeError('Verb signature "%s" does not include event variable' % self._drsTypeName)
                    elif self.iscombinator_signature(self._drsTypeName):
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
                    if ev is None:
                        raise DrsComposeError('Adverb signature "%s" does not include event variable' % self._drsTypeName)
                    if _ADV.has_key(self._word):
                        adv = _ADV[self._word]
                        fn = DrsComposition(adv[0], [x for x in adv[1]])
                    else:
                        fn = DrsComposition(DRS([], self.build_predicates(compose[0][2], refs, ev)))
                    fn.set_lambda_refs([ev])
                else:
                    fn = DrsComposition(DRS([], self.build_predicates(compose[0][2], refs, ev)),
                                        properNoun=self.isproper_noun)
                    if ev is not None:
                        fn.set_lambda_refs([ev])

                for c, s in zip(compose[:-1], signatures):
                    if (c[1] and s[1] != '/') or (not c[1] and s[1] != '\\'):
                        raise DrsComposeError('signature %s%s%s does not match function prototype' % s)
                    fn = c[0](c[1], c[2], fn)
                    fn.set_signature(self.join_signature(s))
                return fn
            else:
                assert compose[0][0] == PropComposition
                fn = compose[0][0](compose[0][1], compose[0][2])
                fn.set_signature(self._drsTypeName)
                if ev is not None:
                    fn.set_lambda_refs([ev])
                return fn


def _process_ccg_node(pt, cl):
    """Internal helper for recursively processing the CCG parse tree.

    See Also:
        process_ccg_pt()
    """
    if pt[-1] == 'T':
        cl2 = CompositionList()
        cl2.set_options(cl.compose_options)
        n = 0
        for nd in pt[1:-1]:
            # FIXME: prefer tail end recursion
            n += _process_ccg_node(nd, cl2)
        if n == 0:
            # n == 0 means we possibly can do a partial application on cl2
            cl3 = cl2.clone()
            try:
                cl2 = cl2.apply()
            except Exception:
                cl2 = cl3
            cl.push_right(cl2, merge=True)
            return 0
        elif n < 0:
            # n <= 0 means we cannot do a partial application on cl2
            cl.push_right(cl2, merge=True)
            return 0
        else:
            # n != 0 means we can do a partial application before adding to main composition list
            cl.push_right(cl2.apply())
            return 0

    # L Node in parse tree
    assert pt[-1] == 'L'
    if pt[0] in [',', '.', ':', ';']:
        return 0    # TODO: handle punctuation
    ccgt = CcgTypeMapper(ccgTypeName=pt[0], word=pt[1], posTags=pt[2:-1])
    cl.push_right(ccgt.get_composer())
    return -10000 if ccgt.isconj else 1


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
    d = cl.apply()
    # Handle verbs with null left arg
    if d.isfunction and d.isarg_left:
        return d.apply_null_left()
    return d


