# -*- coding: utf-8 -*-

from drs import DRS, DRSRef, Merge, Prop, Imp, Rel, Neg, Box, Diamond, Or
from drs import get_new_drsrefs
from utils import iterable_type_check, intersect, union, union_inplace, complement, compare_lists_eq, rename_var, \
    remove_dups
from common import SHOW_LINEAR
import collections, re
from parse import parse_drs, parse_ccgtype
import weakref

## @{
## @ingroup gconst
## @defgroup CCG to DRS Constants

## Compose option
CO_REMOVE_UNARY_PROPS = 0x1

## Function argument position
ArgRight = True

## Function argument position
ArgLeft  = False
## @}


class DrsComposeError(Exception):
    pass


class Composition(object):
    def __init__(self):
        self._lambda_refs = None
        self._options = 0

    def __eq__(self, other):
        return id(self) == id(other)

    @property
    def isfunction(self):
        return False

    @property
    def universe(self):
        raise NotImplementedError

    @property
    def freerefs(self):
        raise NotImplementedError

    @property
    def lambda_refs(self):
        return self._lambda_refs.universe if self._lambda_refs is not None else []

    @property
    def conditions(self):
        return []

    @property
    def compose_options(self):
        return self._options

    @property
    def isproper_noun(self):
        return False

    def set_options(self, options):
        self._options = int(options)

    def set_lambda_refs(self, refs):
        if refs is None:
            self._lambda_refs = None
        else:
            self._lambda_refs = DRS(refs,[])

    def rename_lambda_refs(self, rs):
        if self._lambda_refs is not None:
            self._lambda_refs.alpha_convert(rs)

    def rename_vars(self, rs):
        raise NotImplementedError


class DrsComposition(Composition):
    def __init__(self, drs, properNoun=False):
        super(DrsComposition, self).__init__()
        if not isinstance(drs, DRS):
            raise TypeError
        self._drs = drs
        self._nnp = properNoun

    def __repr__(self):
        refs = self.lambda_refs
        if len(refs) != 0:
            return ''.join(['λ'+v.var.to_string() for v in self.lambda_refs]) + '.' + self.drs.show(SHOW_LINEAR).encode('utf-8')
        return self.drs.show(SHOW_LINEAR).encode('utf-8')

    def __str__(self):
        return self.__repr__()

    @property
    def lambda_refs(self):
        # For DRS we treat None as a special case meaning infer from DRS. This may not be always the best
        # policy so in the code we prefer to explicitly set which refs can be resolved during a merge
        if self._lambda_refs is None:
            r = self._drs.freerefs
            r.extend(self._drs.universe)
            return r
        return self._lambda_refs.universe

    @property
    def isproper_noun(self):
        return self._nnp

    @property
    def universe(self):
        return self._drs.universe

    @property
    def freerefs(self):
        return self._drs.freerefs

    @property
    def isempty(self):
        return self._drs.isempty

    @property
    def conditions(self):
        return self._drs.conditions

    @property
    def drs(self):
        return self._drs

    def rename_vars(self, rs):
        self._drs = self._drs.alpha_convert(rs)
        self._drs = self._drs.substitute(rs)
        self.rename_lambda_refs(rs)


class CompositionList(Composition):

    def __init__(self, compList=None):
        super(CompositionList, self).__init__()
        if compList is None:
            compList = []
        if isinstance(compList, (DRS, Merge)):
            compList = [DrsComposition(compList)]
        elif isinstance(compList, Composition):
            compList = [compList]
        elif iterable_type_check(compList, (DRS, Merge)):
            compList = [DrsComposition(x) for x in compList]
        elif not iterable_type_check(compList, Composition):
            raise TypeError('DrsComposition construction')
        self._compList = compList

    def __repr__(self):
        lr = self.lambda_refs
        if len(lr) == 0:
            return '<' + '#'.join([repr(x) for x in self._compList]) + '>'
        return  ''.join(['λ'+v.var.to_string() for v in lr]) + '.<' + '#'.join([repr(x) for x in self._compList]) + '>'

    @property
    def isproper_noun(self):
        return all([x.isproper_noun for x in self._compList])

    @property
    def universe(self):
        u = set()
        for d in self._compList:
            u = u.union(d.universe)
        return sorted(u)

    @property
    def freerefs(self):
        u = set()
        for d in self._compList:
            u = u.union(d.freerefs)
        return sorted(u.difference(self.universe))

    @property
    def isempty(self):
        return len(self._compList) == 0

    def flatten(self):
        compList = []
        for i in range(len(self._compList)):
            d = self._compList[i]
            if d.isempty:
                continue
            if isinstance(d, CompositionList):
                if len(d.freerefs) != 0 or len(d.universe) == 0:
                    raise DrsComposeError('flatten failed')
                compList.append(d.apply())
            compList.append(d)
        self._compList = compList

    def rename_vars(self, rs):
        self.rename_lambda_refs(rs)
        for d in self._compList:
            d.rename_vars(rs)

    def push_right(self, other, merge=False):
        if isinstance(other, DRS):
            other = DrsComposition(other)
        if merge and isinstance(other, CompositionList):
            self._compList.extend(other._compList)
        else:
            other.set_options(self.compose_options)
            self._compList.append(other)
        return self

    def push_left(self, other, merge=False):
        if isinstance(other, DRS):
            other = DrsComposition(other)
        if merge and isinstance(other, CompositionList):
            compList = [x for x in other._compList]
            compList.extend(self._compList)
            self._compList = compList
        else:
            other.set_options(self.compose_options)
            compList = [other]
            compList.extend(self._compList)
            self._compList = compList
        return self

    def apply(self):
        """Merge, returns a DrsComposition"""
        if len(self._compList) == 0:
            return None

        # alpha convert variables
        self.flatten()
        rstk = []
        lstk = self._compList
        self._compList = []
        while len(lstk) != 0:
            d = lstk[-1]
            lstk.pop()
            if isinstance(d, FunctionComposition):
                if d.isarg_right:
                    if len(rstk) == 0:
                        if len(lstk) != 0:
                            raise DrsComposeError('Function missing right argument')
                        else:
                            return d
                    d = d.apply(rstk[-1])
                    rstk.pop()
                    lstk.append(d)
                else:
                    if len(lstk) == 0:
                        if len(rstk) != 0:
                            raise DrsComposeError('Function missing left argument')
                        else:
                            return d
                    else:
                        d = d.apply(lstk[-1])
                        lstk.pop()
                        lstk.append(d)
            elif isinstance(d, CompositionList):
                d = d.apply()
                if not isinstance(d, DrsComposition):
                    raise DrsComposeError('apply failed')
                rstk.append(d)
            else:
                rstk.append(d)

        universe = []
        for i in range(len(rstk)):
            d = rstk[i]
            rn = intersect(d.universe, universe)
            if len(rn) != 0:
                # FIXME: should this be allowed?
                # Alpha convert bound vars in both self and arg
                xrs = zip(rn, get_new_drsrefs(rn, universe))
                d.rename_vars(xrs)
                for j in range(i+1,len(rstk)):
                    rstk[j].rename_vars(xrs)
            universe = union(universe, d.universe)

        universe = set(universe)
        lambda_refs = filter(lambda x: x in universe, self.lambda_refs)

        refs = []
        conds = []
        proper = len(rstk) != 0
        for d in reversed(rstk):
            proper = proper and d.isproper_noun
            refs.extend(d.drs.referents)
            conds.extend(d.drs.conditions)
        if proper:
            # Hyphenate name
            if len(refs) != 1 or any(filter(lambda x: not isinstance(x, Rel) or len(x.referents) != 1, conds)):
                raise DrsComposeError('bad proper noun in DRS condition')
            name = '-'.join([c.relation.to_string() for c in conds])
            conds = [Rel(name,refs)]
        lambda_refs = rstk[0].lambda_refs if len(rstk) != 0 else []
        drs = DRS(refs, conds).purify()
        assert drs.ispure
        d = DrsComposition(drs, proper)
        if len(lambda_refs) != 0:
            d.set_lambda_refs(lambda_refs)
        return d


class FunctionComposition(Composition):

    def __init__(self, position, referent, composition=None):
        super(FunctionComposition, self).__init__()
        if composition is not None:
            if isinstance(composition, (DRS, Merge)):
                composition = DrsComposition(composition)
            elif not isinstance(composition, Composition):
                raise TypeError('Function argument must be a Composition type')
        if not isinstance(referent, DRSRef):
            raise TypeError('Function referent must be DRSRef type')
        self._comp = composition
        self._pos  = position or False
        self._drsref = DRS([referent],[])
        self._outer = None
        if self._comp is not None:
            if isinstance(self._comp, FunctionComposition):
                self._comp._set_outer(self)
            else:   # Only set once we apply()
                self._comp.set_lambda_refs([])

    def _set_outer(self, outer):
        if outer is not None:
            self._outer = weakref.ref(outer)
        else:
            self._outer = None

    def _repr_helper1(self, i):
        s = 'λ' + chr(i)
        if self._comp is not None and self._comp.isfunction:
            s = self._comp._repr_helper1(i+1) + s
        return s

    def _repr_helper2(self, i):
        v = chr(i)
        r = self._drsref.referents[0].var.to_string()
        if self._comp is not None:
            if self._comp.isfunction:
                s = self._comp._repr_helper2(i+1)
            else:
                s = str(self._comp)
            if self._pos:
                return '%s;%s(%s)' % (s, v, r)
            else:
                return '%s(%s);%s' % (v, r, s)
        else:
            return '%s(%s)' % (v, r)

    def __repr__(self):
        return self._repr_helper1(ord('Z')) + ''.join(['λ'+v.var.to_string() for v in self.lambda_refs]) + \
               '.' + self._repr_helper2(ord('Z'))

    def __str__(self):
        return self.__repr__()

    def _get_freerefs(self, u):
        if self._comp is not None:
            if self._comp.isfunction:
                u = self._comp._get_freerefs(u)
            else:
                u = union_inplace(u, self._comp.freerefs)
        return u

    def _get_universe(self, u):
        if self._comp is not None:
            if self._comp.isfunction:
                u = self._comp._get_universe(u)
            else:
                u = union_inplace(u, self._comp.universe)
        return u

    def _get_lambda_refs(self, u):
        # Get lambda vars orderd by function scope
        u.extend(self._drsref.referents)
        if self._comp is not None:
            if self._comp.isfunction:
                u.extend(self._comp._get_lambda_refs(u))
            else:
                u.extend(self._comp.lambda_refs)
        return u

    def _get_position(self):
        # Get position in function scope
        g = self
        i = 0
        while g.outer is not None:
            g = g.outer
            i += 1
        return i

    @property
    def global_scope(self):
        g = self
        while g.outer is not None:
            g = g.outer
        return g

    @property
    def outer(self):
        return None if self._outer is None else self._outer() # weak deref

    @property
    def isempty(self):
        return self._drsref.isempty and (self._comp is None or self._comp.isempty)

    @property
    def freerefs(self):
        return self._get_freerefs([])

    @property
    def universe(self):
        return self._get_universe([])

    @property
    def lambda_refs(self):
        # Get unique referents, ordered by function scope
        return remove_dups(self._get_lambda_refs([]))

    @property
    def isarg_right(self):
        if self._comp is not None and self._comp.isfunction:
            return self._comp.isarg_right
        return self._pos

    @property
    def isarg_left(self):
        return not self.isarg_right

    @property
    def isfunction(self):
        return True

    def set_options(self, options):
        # Pass down options to nested function
        super(FunctionComposition, self).set_options(options)
        if self._comp is not None:
            self._comp.set_options(options)

    def rename_vars(self, rs):
        self._drsref = self._drsref.alpha_convert(rs)
        if self._comp is not None:
            self._comp.rename_vars(rs)

    def apply_null_left(self):
        # TODO: Check if we have a proper noun accessible to the right and left
        if self.isarg_right or self._comp is None or self._comp.isfunction:
            raise DrsComposeError('invalid apply null left to function')
        if self._comp is not None and isinstance(self._comp, CompositionList):
            self._comp = self._comp.apply()
        d = DrsComposition(DRS(self._drsref.universe,[]))
        d = self.apply(d)
        return d

    def apply(self, arg):
        if self._comp is not None and self._comp.isfunction:
            self._comp = self._comp.apply(arg)
            if self._comp.isfunction:
                self._comp._set_outer(self)
            return self

        # Alpha convert (old,new)
        alr = arg.lambda_refs
        slr = self.lambda_refs
        rs = zip(alr, slr)
        # Make sure names don't conflict with global scope
        ors = intersect(alr[len(rs):], complement(self.global_scope.lambda_refs, slr))
        if len(ors) != 0:
            xrs = zip(ors, get_new_drsrefs(ors, union(alr, slr)))
            arg.rename_vars(xrs)
        arg.rename_vars(rs)

        rn = intersect(arg.universe, self.universe)
        if len(rn) != 0:
            # Alpha convert bound vars in both self and arg
            xrs = zip(rn, get_new_drsrefs(rn, union(arg.lambda_refs, slr)))
            arg.rename_vars(xrs)

        if arg.isfunction:
            arg.set_options(self.compose_options)
            if self._comp is not None:
                if arg._comp is None:
                    arg._comp = self._comp
                elif self.isarg_left and arg.isarg_left:
                    if isinstance(arg._comp, CompositionList):
                        arg._comp.push_right(self._comp, merge=True)
                    elif isinstance(self._comp, CompositionList):
                        self._comp.push_left(arg._comp, merge=True)
                    else:
                        cl = CompositionList(arg._comp)
                        cl.set_options(self.compose_options)
                        cl.push_right(self._comp)
                        arg._comp = cl
                elif self.isarg_right and arg.isarg_right:
                    if isinstance(arg._comp, CompositionList):
                        arg._comp.push_left(self._comp, merge=True)
                    elif isinstance(self._comp, CompositionList):
                        self._comp.push_right(arg._comp, merge=True)
                    else:
                        cl = CompositionList(self._comp)
                        cl.set_options(self.compose_options)
                        cl.push_right(arg._comp)
                        arg._comp = cl
                else:
                    raise DrsComposeError('Function application of functions requires same argument ordering')
            self._comp = None
            self._drsref = DRS([], [])
            self._set_outer(None)
            return arg

        # Remove resolved referent from lambda refs list
        gscope = self.global_scope
        i = gscope._get_position()
        cr = gscope._get_lambda_refs([])
        nr = cr[0:i]
        nr.extend(cr[i+1:])
        cr = remove_dups(nr)

        if self._comp is None:
            arg.set_lambda_refs(cr)
            return arg
        elif isinstance(self._comp, CompositionList):
            c = self._comp
        else:
            c = CompositionList(self._comp)
        if self.isarg_right:
            c.push_right(arg)
        else:
            c.push_left(arg)
        c.set_options(self.compose_options)
        c = c.apply()
        c.set_lambda_refs(cr)
        self._comp = None
        self._drsref = DRS([],[])
        self._set_outer(None)
        return c


class PropComposition(FunctionComposition):
    def __init__(self, position, referent, composition=None):
        super(PropComposition, self).__init__(position, referent)

    def _repr_helper2(self, i):
        v = chr(i)
        r = self._drsref.referents[0].var.to_string()
        return '[%s| %s: %s(*)]' % (r, r, v)

    @property
    def freerefs(self):
        return []

    @property
    def universe(self):
        return self._drsref.universe

    def apply_null_left(self):
        raise DrsComposeError('cannot apply null left to a proposition function')

    def apply(self, arg):
        if not isinstance(arg, CompositionList):
            arg = CompositionList([arg])
        d = arg.apply()
        assert isinstance(d, DrsComposition)
        # FIXME: removing proposition from a proper noun causes an exception during CompositionList.apply()
        if (self.compose_options & CO_REMOVE_UNARY_PROPS) != 0 and len(d.drs.referents) == 1 and not d.isproper_noun:
            rs = d.drs.referents[0], self._drsref.referents[0]
            d.rename_vars(rs)
            return d
        return DrsComposition(DRS(self._drsref.referents, [Prop(self._drsref.referents[0], d.drs)]))


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
         function, or a combinator.
       - Combinators: Rules which take a function as the argument and return a function of the same type. Combinators
         can take a variable number of referents, indicated by *. When applying combinators the resultant must
         produce a function, or combinator, where the DRS merges are adjacent
         - For λP.P(*);R[...] {P=λQ.Q(*);U[...] } is OK<br>
         - For λP.P(*);R[...] {P=λQ.U[...];Q(*) } is an invalid combinator application because it produces a function
           λQ.U[...];Q(*);R[...] and U and R are not adjacent.
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
    _AllTypes = {
        # DRS base types
        'Z':            None,
        'T':            None,
        'conj':         None,
        # Simple DRS functions
        r'Z/T':         [(PropComposition, ArgRight, DRSRef('p'))],
        r'T/Z':         [(FunctionComposition, ArgRight, DRSRef('p'))],
        r'T/T':         [(FunctionComposition, ArgRight, DRSRef('x'))],
        r'T\T':         [(FunctionComposition, ArgLeft, DRSRef('x'),)],
        # DRS Verb functions
        r'S/T':         [(FunctionComposition, ArgRight, DRSRef('x'))],
        r'S\T':         [(FunctionComposition, ArgLeft, DRSRef('x'))],
        r'(S/T)/T':     [(FunctionComposition, ArgRight, DRSRef('y')), (FunctionComposition, ArgRight, DRSRef('x'))],
        r'(S/T)\T':     [(FunctionComposition, ArgLeft, DRSRef('x')), (FunctionComposition, ArgRight, DRSRef('y'))],
        r'(S\T)/T':     [(FunctionComposition, ArgRight, DRSRef('y')), (FunctionComposition, ArgLeft, DRSRef('x'))],
        r'(S\T)/Z':     [(FunctionComposition, ArgRight, DRSRef('y')), (FunctionComposition, ArgLeft, DRSRef('x'))],
        r'(S/T)/Z':     [(FunctionComposition, ArgRight, DRSRef('y')), (FunctionComposition, ArgRight, DRSRef('x'))],
        r'S\S':         [(FunctionComposition, ArgLeft, DRSRef('x'))],
        r'S/S':         [(FunctionComposition, ArgRight, DRSRef('x'))],
        # Combinators
        r'(S\T)\(S\T)': [(FunctionComposition, ArgLeft, DRSRef('x'))],

    }
    _EventPredicates = ['agent', 'theme', 'extra']
    _TypeChangerAll = re.compile(r'NP(?:\[[a-z]+\])?|N(?:\[[a-z]+\])?|PP')
    _TypeChangerNoPP = re.compile(r'NP(?:\[[a-z]+\])?|N(?:\[[a-z]+\])?')
    _TypeSimplyS = re.compile(r'S(?:\[[a-z]+\])?')

    def __init__(self, ccgTypeName, word, posTags=None):
        self._ccgTypeName = ccgTypeName
        self._word = word.lower().rstrip('?.,:;')
        self._pos  = posTags or []
        self._drsTypeName = self.get_drs_typename(ccgTypeName)

        if not self._AllTypes.has_key(self._drsTypeName):
            raise DrsComposeError('CCG type %s maps to unknown DRS composition type %s' %
                                  (ccgTypeName, self._drsTypeName))

    def __repr__(self):
        return '<' + self._word + ' ' + self.partofspeech + ' ' + self._ccgTypeName + '->' + self._drsTypeName + '>'

    @classmethod
    def get_base_type(cls, pt):
        """Get a base type and return the remainder of the rule to be process. Combinators are extracted.

        Args:
            pt: A parse tree of DRS type.

        Returns:
            A tuple of the base DRS type and the remainder of the parse tree.
        """
        if len(pt) == 3 and isinstance(pt[0], list) and isinstance(pt[2], list) and repr(pt[0]) == repr(pt[2]):
            # Combinator with DRS T[...], * means any number of referents

            # Determine the number of arguments

            if pt[1] == '/':
                # λP.T[...];P(*)
                cls._AllTypes[d] = [(FunctionComposition, ArgRight, DRSRef('x'))]
            else:
                # λP.P(*);T[...]
                cls._AllTypes[d] = [(FunctionComposition, ArgLeft, DRSRef('x'))]
        elif len(pt) == 3 and isinstance(pt[0], list) and len(pt[0]) == 3 and \
                ((isinstance(pt[2], str) and repr(pt[0][0]) == repr(pt[0][2])) or \
                         (repr(pt[0][0]) == repr(pt[0][2]) and repr(pt[2]) == repr(pt[0][2]))):
            if pt[1] == '/':
                if pt[0][1] == '/':
                    cls._AllTypes[d] = [(FunctionComposition, ArgRight, DRSRef('y')),
                                        (FunctionComposition, ArgRight, DRSRef('x'))]
                else:
                    cls._AllTypes[d] = [(FunctionComposition, ArgLeft, DRSRef('y')),
                                        (FunctionComposition, ArgRight, DRSRef('x'))]
            elif pt[0][1] == '/':
                cls._AllTypes[d] = [(FunctionComposition, ArgRight, DRSRef('y')),
                                    (FunctionComposition, ArgLeft, DRSRef('x'))]
            else:
                cls._AllTypes[d] = [(FunctionComposition, ArgLeft, DRSRef('y')),
                                    (FunctionComposition, ArgLeft, DRSRef('x'))]
        elif len(pt) == 3 and isinstance(pt[2], list) and len(pt[2]) == 3 and \
                ((isinstance(pt[0], str) and repr(pt[2][0]) == repr(pt[2][2])) or \
                         (repr(pt[0]) == repr(pt[2][0]) and repr(pt[2][0]) == repr(pt[2][2]))):
            if pt[1] == '/':
                if pt[2][1] == '/':
                    cls._AllTypes[d] = [(FunctionComposition, ArgRight, DRSRef('y')),
                                        (FunctionComposition, ArgRight, DRSRef('x'))]
                else:
                    cls._AllTypes[d] = [(FunctionComposition, ArgLeft, DRSRef('y')),
                                        (FunctionComposition, ArgRight, DRSRef('x'))]
            elif pt[2][1] == '/':
                cls._AllTypes[d] = [(FunctionComposition, ArgRight, DRSRef('y')),
                                    (FunctionComposition, ArgLeft, DRSRef('x'))]
            else:
                cls._AllTypes[d] = [(FunctionComposition, ArgLeft, DRSRef('y')),
                                    (FunctionComposition, ArgLeft, DRSRef('x'))]
        elif d in result:
            result[d].append(c)
        else:
            result[d] = [c]


    @classmethod
    def get_drs_typename(cls, ccgTypeName):
        return cls._TypeChangerAll.sub('Z', cls._TypeChangerNoPP.sub('T', cls._TypeSimplyS.sub('S', ccgTypeName)))

    @classmethod
    def convert_model_categories(cls, lines):
        results = set()
        for ln in lines:
            c = ln.strip()
            if len(c) == 0 or c[0] == '#':
                continue
            # TODO: handle punctuation
            if c in ['.', '.', ':', ';']:
                continue
            d = cls.get_drs_typename(c)
            if d in cls._AllTypes:
                continue
            results.add(d)
        return sorted(results)

    @classmethod
    def add_model_categories(cls, filename):
        """Add the CCG categories file and update the DRS types.

        Args:
            filename: The categories file from the model folder.

        Returns:
            A list of DRS categories that could not be added to_AllTypes dictionary or None.
        """
        result = {}
        with open(filename, 'r') as fd:
            lines = fd.readlines()
            for ln in lines:
                c = ln.strip()
                # TODO: handle punctuation
                if c in ['.', '.', ':', ';']:
                    continue
                d = cls.get_drs_typename(c)
                if d in cls._AllTypes:
                    continue
                # Use DRS categories since this results in less types
                pt = parse_ccgtype(d)
                if len(pt) == 3 and isinstance(pt[0], list) and isinstance(pt[2], list) and repr(pt[0]) == repr(pt[2]):
                    # Combinator with DRS T[...], * means any number of referents

                    # Determine the number of arguments

                    if pt[1] == '/':
                        # λP.T[...];P(*)
                        cls._AllTypes[d] = [(FunctionComposition, ArgRight, DRSRef('x'))]
                    else:
                        # λP.P(*);T[...]
                        cls._AllTypes[d] = [(FunctionComposition, ArgLeft, DRSRef('x'))]
                elif len(pt) == 3 and isinstance(pt[0], list) and len(pt[0]) == 3 and \
                        ((isinstance(pt[2], str) and repr(pt[0][0]) == repr(pt[0][2])) or \
                             (repr(pt[0][0]) == repr(pt[0][2]) and repr(pt[2]) == repr(pt[0][2]))):
                    if pt[1] == '/':
                        if pt[0][1] == '/':
                            cls._AllTypes[d] = [(FunctionComposition, ArgRight, DRSRef('y')),
                                                (FunctionComposition, ArgRight, DRSRef('x'))]
                        else:
                            cls._AllTypes[d] = [(FunctionComposition, ArgLeft, DRSRef('y')),
                                                (FunctionComposition, ArgRight, DRSRef('x'))]
                    elif pt[0][1] == '/':
                        cls._AllTypes[d] = [(FunctionComposition, ArgRight, DRSRef('y')),
                                            (FunctionComposition, ArgLeft, DRSRef('x'))]
                    else:
                        cls._AllTypes[d] = [(FunctionComposition, ArgLeft, DRSRef('y')),
                                            (FunctionComposition, ArgLeft, DRSRef('x'))]
                elif len(pt) == 3 and isinstance(pt[2], list) and len(pt[2]) == 3 and \
                        ((isinstance(pt[0], str) and repr(pt[2][0]) == repr(pt[2][2])) or \
                             (repr(pt[0]) == repr(pt[2][0]) and repr(pt[2][0]) == repr(pt[2][2]))):
                    if pt[1] == '/':
                        if pt[2][1] == '/':
                            cls._AllTypes[d] = [(FunctionComposition, ArgRight, DRSRef('y')),
                                                (FunctionComposition, ArgRight, DRSRef('x'))]
                        else:
                            cls._AllTypes[d] = [(FunctionComposition, ArgLeft, DRSRef('y')),
                                                (FunctionComposition, ArgRight, DRSRef('x'))]
                    elif pt[2][1] == '/':
                        cls._AllTypes[d] = [(FunctionComposition, ArgRight, DRSRef('y')),
                                            (FunctionComposition, ArgLeft, DRSRef('x'))]
                    else:
                        cls._AllTypes[d] = [(FunctionComposition, ArgLeft, DRSRef('y')),
                                            (FunctionComposition, ArgLeft, DRSRef('x'))]
                elif d in result:
                    result[d].append(c)
                else:
                    result[d] = [c]
        return None if len(result) == 0 else result

    @property
    def ispronoun(self):
        return (self._pos is not None and self._pos and self._pos[0] in ['PRP', 'PRP$', 'WP', 'WP$']) or \
                    _PRON.has_key(self._word)
    @property
    def ispreposition(self):
        return self.partofspeech == 'IN'

    @property
    def isadverb(self):
        return self.partofspeech in ['RB', 'RBR', 'RBS']

    @property
    def isverb(self):
        # FIXME: use dictionary to get type
        return self.partofspeech in ['VB', 'VBD', 'VBN', 'VBP', 'VBZ']

    @property
    def isconj(self):
        return self._ccgTypeName == 'conj'

    @property
    def isgerund(self):
        return self.partofspeech == 'VBG'

    @property
    def isproper_noun(self):
        return self.partofspeech == 'NNP'

    @property
    def partofspeech(self):
        return self._pos[0] if self._pos is not None else 'UNKNOWN'

    @property
    def ccgtype(self):
        return self._ccgTypeName

    def get_composer(self):
        compose = self._AllTypes[self._drsTypeName]
        if compose is None:
            # Simple type
            # Handle prepositions 'Z'
            if self.isconj:
                if self._word in ['or', 'nor']:
                    raise NotImplementedError
                return CompositionList()
            elif self.ispronoun:
                return DrsComposition(_PRON[self._word])
            elif self._ccgTypeName == 'N':
                return DrsComposition(DRS([DRSRef('x')], [Rel(self._word, [DRSRef('x')])]),properNoun=self.isproper_noun)
            elif self.isadverb and _ADV.has_key(self._word):
                adv = _ADV[self._word]
                return DrsComposition(adv[0], [x for x in adv[1]])
            else:
                return DrsComposition(DRS([], [Rel(self._word, [DRSRef('x')])]))
        else:
            # Functions
            if self._ccgTypeName == 'NP/N':
                if self._word in ['a', 'an']:
                    return FunctionComposition(ArgRight, DRSRef('x'), DRS([], [Rel('exists.maybe', [DRSRef('x')])]))
                elif self._word in ['the', 'thy']:
                    return FunctionComposition(ArgRight, DRSRef('x'), DRS([], [Rel('exists', [DRSRef('x')])]))
                else:
                    return FunctionComposition(ArgRight, DRSRef('x'), DRS([], [Rel(self._word, [DRSRef('x')])]))
            if compose[0][0] == FunctionComposition:
                order  = []
                refs = []
                # FIXME: Assumes x,y,z ordering of variables. Should use right/left arg flag.
                for c in compose:
                    order.append(ord(c[2].var.to_string()) - ord('x') )
                for i in order:
                    refs.append(compose[i][2])

                if self.isverb:
                    # TODO: use verbnet to get semantics
                    conds = [Rel('event', [DRSRef('e')]), Rel(self._word,[DRSRef('e')])]
                    for v,e in zip(refs, self._EventPredicates):
                        conds.append(Rel('event.'+ e, [DRSRef('e'), v]))
                    if len(refs) > len(self._EventPredicates):
                        for i in range(len(self._EventPredicates),len(refs)):
                            conds.append(Rel('event.extra.%d' % i, [DRSRef('e'), refs[i]]))
                    lambda_refs = []
                    lambda_refs.extend(refs)
                    lambda_refs.append(DRSRef('e'))
                    fn = DrsComposition(DRS([DRSRef('e')], conds))
                    fn.set_lambda_refs(lambda_refs)
                elif self.isadverb and _ADV.has_key(self._word):
                    adv = _ADV[self._word]
                    fn =  DrsComposition(adv[0], [x for x in adv[1]])
                else:
                    fn = DrsComposition(DRS([],[Rel(self._word, refs)]), properNoun=self.isproper_noun)

                for c in compose:
                    fn = c[0](c[1], c[2], fn)
                return fn
            else:
                assert compose[0][0] == PropComposition
                return compose[0][0](compose[0][1], compose[0][2])


def build_composer(ccgTypespec, word):
    ccgt = CcgTypeMapper(ccgTypespec, word)
    return ccgt.get_composer()


def process_easysrl_node(pt, cl):
    """Recursively process the parse tree"""
    if pt[-1] == 'T':
        cl2 = CompositionList()
        cl2.set_options(cl.compose_options)
        for nd in pt[1:-1]:
            # FIXME: prefer tail end recurrsion
            process_easysrl_node(nd, cl2)
        cl.push_right(cl2.apply())
        return

    # L Node in parse tree
    assert pt[-1] == 'L'
    ccgt = CcgTypeMapper(ccgTypeName=pt[0], word=pt[1], posTags=pt[2:-1])
    cl.push_right(ccgt.get_composer())


def process_easysrl(pt, options=None):
    """Process the EasySRL parse tree"""
    if pt is None or len(pt) == 0:
        return None
    cl = CompositionList()
    if options is not None:
        cl.set_options(options)
    process_easysrl_node(pt, cl)
    d = cl.apply()
    # Handle verbs with null left arg
    if d.isfunction and d.isarg_left:
        return d.apply_null_left()
    return d


