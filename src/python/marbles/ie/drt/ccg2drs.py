# -*- coding: utf-8 -*-

from drs import DRS, DRSRef, Merge, Prop, Imp, Rel, Neg, Box, Diamond, Or
from drs import get_new_drsrefs
from utils import iterable_type_check, intersect, union, union_inplace, complement, compare_lists_eq, rename_var
from common import SHOW_LINEAR
import collections, re
from parse import parse_drs
import weakref


class DrsComposeError(Exception):
    pass


ArgRight = True
ArgLeft  = False


class Composition(object):

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
        raise NotImplementedError

    @property
    def conditions(self):
        return []

    @property
    def isproper_noun(self):
        return False

    def rename_vars(self, rs):
        raise NotImplementedError


class DrsComposition(Composition):
    def __init__(self, drs, lambdaRefs=None, properNoun=False):
        if not isinstance(drs, DRS):
            raise TypeError
        self._drs = drs
        self._nnp = properNoun
        if lambdaRefs is None:
            self._lambda_refs = DRS(union_inplace(drs.universe, drs.freerefs),[])
        else:
            self._lambda_refs = DRS(lambdaRefs,[])

    def __repr__(self):
        return ''.join(['λ'+v.var.to_string() for v in self.lambda_refs]) + '.' + self.drs.show(SHOW_LINEAR).encode('utf-8')

    def __str__(self):
        return self.drs.show(SHOW_LINEAR).encode('utf-8')

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
    def lambda_refs(self):
        return self._lambda_refs.universe

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
        self._lambda_refs = self._lambda_refs.alpha_convert(rs)


class CompositionList(Composition):

    def __init__(self, compList=None):
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
        return '#'.join([repr(x) for x in self._compList])

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
    def lambda_refs(self):
        # must preserve ordering
        u = []
        for d in self._compList:
            u = union_inplace(d.lambda_refs)
        return u

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
        for d in self._compList:
            d.rename_vars(rs)

    def push_right(self, other, merge=False):
        if isinstance(other, DRS):
            other = DrsComposition(other)
        if merge and isinstance(other, CompositionList):
            self._compList.extend(other._compList)
        else:
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

        dprev = rstk[-1] if len(rstk) != 0 else None
        ers = []
        for d in rstk[:-1]:
            # Alpha convert (old,new)
            dlr = d.lambda_refs
            plr = dprev.lambda_refs
            rs = zip(dlr, plr)
            # If d has more refs than dprev, make sure names don't conflict
            ors = intersect(dlr[len(rs):], plr)
            if len(ors) != 0:
                nrs = get_new_drsrefs(ors, union(dlr, plr, ers))
                ers = union(ers, nrs)
                xrs = zip(ors, nrs)
                d.rename_vars(xrs)
            d.rename_vars(rs)
            # Ensure these names are never resolved as we progress
            ers = union(ers, plr[len(rs):])

            rn = intersect(d.universe, dprev.universe)
            if len(rn) != 0:
                # FIXME: should this be allowed?
                # Alpha convert bound vars in both self and arg
                xrs = zip(rn, get_new_drsrefs(rn, union(d.lambda_refs, plr)))
                d.rename_vars(xrs)

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
                raise DrsComposeError('bad proper noun DRS condition')
            name = '-'.join([c.relation.to_string() for c in conds])
            conds = [Rel(name,refs)]
        lambda_refs = rstk[0].lambda_refs if len(rstk) != 0 else []
        drs = DRS(refs, conds).purify()
        assert drs.ispure
        return DrsComposition(drs, lambda_refs, proper)


class FunctionComposition(Composition):

    def __init__(self, position, referent, composition=None):
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
        if self._comp is not None and isinstance(self._comp, FunctionComposition):
            self._comp._set_outer(self)

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
        return self._repr_helper1(ord('P')) + ''.join(['λ'+v.var.to_string() for v in self.lambda_refs]) + \
               '.' + self._repr_helper2(ord('P'))

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
        u = union_inplace(u, self._drsref.referents)
        if self._comp is not None:
            if self._comp.isfunction:
                u = self._comp._get_lambda_refs(u)
            else:
                u = union_inplace(u, self._comp.lambda_refs)
        return u

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
        # Get global scope
        g = self
        while g.outer is not None:
            g = g.outer
        return g._get_lambda_refs([])

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
        return d.apply()

    def apply(self, arg):
        if self._comp is not None and self._comp.isfunction:
            self._comp = self._comp.apply(arg)
            if self._comp.isfunction:
                self._comp._set_outer(self)
            return self

        # Alpha convert (old,new)
        alr = arg.lambda_refs
        # remove outer scope referents
        slr = self.lambda_refs
        i = slr.index(self._drsref.referents[0])
        slr = slr[i:]
        rs = zip(alr, slr)
        # If arg has more refs than self, make sure names don't conflict
        ors = intersect(alr[len(rs):], slr)
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
                        cl.push_right(self._comp)
                        arg._comp = cl
                elif self.isarg_right and arg.isarg_right:
                    if isinstance(arg._comp, CompositionList):
                        arg._comp.push_left(self._comp, merge=True)
                    elif isinstance(self._comp, CompositionList):
                        self._comp.push_right(arg._comp, merge=True)
                    else:
                        cl = CompositionList(self._comp)
                        cl.push_right(arg._comp)
                        arg._comp = cl
                else:
                    raise DrsComposeError('Function application of functions requires same argument ordering')
            self._comp = None
            self._drsref = DRS([], [])
            self._outer = None
            return arg

        if self._comp is None:
            return arg
        elif isinstance(self._comp, CompositionList):
            c = self._comp
        else:
            c = CompositionList(self._comp)
        if self.isarg_right:
            c.push_right(arg)
        else:
            c.push_left(arg)
        self._comp = None
        self._drsref = DRS([],[])
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


class CcgType(object):
    _AllTypes = {
        # DRS
        'P':            None,
        'T':            None,
        'conj':         None,
        # Functions
        r'P/T':         [(PropComposition, ArgRight, DRSRef('p'))],
        r'T/T':         [(FunctionComposition, ArgRight, DRSRef('x'))],
        r'T\T':         [(FunctionComposition, ArgLeft, DRSRef('x'),)],
        # Verbs
        r'S/T':         [(FunctionComposition, ArgRight, DRSRef('x'))],
        r'S\T':         [(FunctionComposition, ArgLeft, DRSRef('x'))],
        r'(S\T)\(S\T)': [(FunctionComposition, ArgLeft, DRSRef('x'))],
        r'(S/T)/T':     [(FunctionComposition, ArgRight, DRSRef('y')), (FunctionComposition, ArgRight, DRSRef('x'))],
        r'(S/T)\T':     [(FunctionComposition, ArgLeft, DRSRef('x')), (FunctionComposition, ArgRight, DRSRef('y'))],
        r'(S\T)/T':     [(FunctionComposition, ArgRight, DRSRef('y')), (FunctionComposition, ArgLeft, DRSRef('x'))],
        r'S\S':         [(FunctionComposition, ArgLeft, DRSRef('x'))],
        r'S/S':         [(FunctionComposition, ArgRight, DRSRef('x'))],

        r'(S\T)/P':     [(FunctionComposition, ArgRight, DRSRef('y')), (FunctionComposition, ArgLeft, DRSRef('x'))],
        r'(S/T)/P':     [(FunctionComposition, ArgRight, DRSRef('y')), (FunctionComposition, ArgRight, DRSRef('x'))],

        r'T/P':         [(FunctionComposition, ArgRight, DRSRef('p'))],
    }
    _EventPredicates = ['agent', 'theme', 'extra']
    _TypeChangerAll = re.compile(r'NP|N|PP')
    _TypeChangerNoPP = re.compile(r'NP|N')
    _TypeSimplyS = re.compile(r'S(?:\[[a-z]+\])?')

    def __init__(self, ccgTypeName, word, posTags=None):
        self._ccgTypeName = ccgTypeName
        self._word = word.lower().rstrip('?.,:;')
        self._pos  = posTags or []
        self._drsTypeName = self._TypeChangerAll.sub('P',
                            self._TypeChangerNoPP.sub('T', self._TypeSimplyS.sub('S', ccgTypeName)))

        if not self._AllTypes.has_key(self._drsTypeName):
            raise DrsComposeError('CCG type %s maps to unknown DRS composition type %s' %
                                  (ccgTypeName, self._drsTypeName))

    def __repr__(self):
        return '<' + self._word + ' ' + self.partofspeech + ' ' + self._ccgTypeName + '->' + self._drsTypeName + '>'

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
            # Handle prepositions 'P'
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
                    fn = DrsComposition(DRS([DRSRef('e')], conds), lambda_refs)
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
    ccgt = CcgType(ccgTypespec, word)
    return ccgt.get_composer()


def process_easysrl_node(pt, cl):
    """Recursively process the parse tree"""
    if pt[-1] == 'T':
        cl2 = CompositionList()
        for nd in pt[1:-1]:
            # FIXME: prefer tail end recurrsion
            process_easysrl_node(nd, cl2)
        cl.push_right(cl2.apply())
        return

    # L Node in parse tree
    assert pt[-1] == 'L'
    ccgt = CcgType(ccgTypeName=pt[0], word=pt[1], posTags=pt[2:-1])
    cl.push_right(ccgt.get_composer())


def process_easysrl(pt):
    """Process the EasySRL parse tree"""
    if pt is None or len(pt) == 0:
        return None
    cl = CompositionList()
    process_easysrl_node(pt, cl)
    d = cl.apply()
    # Handle verbs with null left arg
    if d.isfunction and d.isarg_left:
        return d.apply_null_left()
    return d


