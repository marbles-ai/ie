# -*- coding: utf-8 -*-

from drs import DRS, DRSRef, Merge, Prop, Imp, Rel, Neg, Box, Diamond, Or
from drs import get_new_drsrefs
from utils import iterable_type_check, intersect, union, compare_lists_eq
from common import SHOW_LINEAR


class DrsComposeError(Exception):
    pass


ArgRight = True
ArgLeft  = False


class Composition(object):

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
    def conditions(self):
        raise NotImplementedError

    def rename_vars(self, rs):
        raise NotImplementedError


class DrsComposition(Composition):
    def __init__(self, drs):
        if not isinstance(drs, DRS):
            raise TypeError
        self._drs = drs

    def __repr__(self):
        return self.drs.show(SHOW_LINEAR)

    def __str__(self):
        return self.drs.show(SHOW_LINEAR)

    @property
    def universe(self):
        return self._drs.universe

    @property
    def freerefs(self):
        return self._drs.freerefs

    @property
    def conditions(self):
        return self._drs.conditions

    @property
    def drs(self):
        return self._drs

    def rename_vars(self, rs):
        self._drs = self._drs.alpha_convert(rs)
        self._drs = self._drs.substitute(rs)


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
        return ';'.join([repr(x) for x in self._compList])

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

    def flatten(self):
        for i in range(len(self._compList)):
            d = self._compList[i]
            if isinstance(d, CompositionList):
                if len(d.freerefs) != 0 or len(d.universe) == 0:
                    raise DrsComposeError('flatten failed')
                self._compList[i] = d.apply()

    def rename_vars(self, rs):
        for d in self._compList:
            d.rename_vars(rs)
    
    def push_right(self, other):
        if isinstance(other, DRS):
            other = DrsComposition(other)
        self._compList.append(other)
        return self

    def push_left(self, other):
        if isinstance(other, DRS):
            other = DrsComposition(other)
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
                        raise DrsComposeError('Function missing right argument')
                    d = d.apply(rstk[-1])
                    rstk.pop()
                    lstk.append(d)
                else:
                    if len(lstk) == 0:
                        raise DrsComposeError('Function missing left argument')
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

        refs = []
        conds = []
        for d in reversed(rstk):
            refs.extend(d.drs.referents)
            conds.extend(d.drs.conditions)
        drs = DRS(refs, conds).purify()
        assert drs.ispure
        return DrsComposition(drs)


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
                s = repr(self._comp)
            if self._pos:
                return '%s;%s(%s)' % (s, v, r)
            else:
                return '%s(%s);%s' % (v, r, s)
        else:
            return '%s(%s)' % (v, r)

    def __repr__(self):
        return self._repr_helper1(ord('P')) + '.' + self._repr_helper2(ord('P'))

    def __str__(self):
        return self._repr_helper1(ord('P')) + '.' + self._repr_helper2(ord('P'))

    def _get_freerefs(self, u):
        if self._comp is not None:
            if self._comp.isfunction:
                u = self._comp._get_freerefs(u)
            else:
                u = u.union(self._comp.freerefs)
        return u

    def _get_universe(self, u):
        if self._comp is not None:
            if self._comp.isfunction:
                u = self._comp._get_universe(u)
            else:
                u = u.union(self._comp.universe)
        return u

    def _get_refs(self, u):
        u = u.union(self._drsref.referents)
        if self._comp is not None:
            if self._comp.isfunction:
                u = self._comp._get_refs(u)
        return u

    @property
    def freerefs(self):
        fr = self._get_freerefs(set())
        r  = self._get_refs(set())
        fr = fr.intersect(r)
        return sorted(fr)

    @property
    def universe(self):
        u = self._get_universe(set())
        r = self._get_refs(set())
        u = u.intersect(r)
        return sorted(u)

    @property
    def isarg_right(self):
        if self._comp is not None and self._comp.isfunction:
            return self._comp.isarg_right
        return self._pos

    @property
    def isarg_left(self):
        return not self.isarg_right()

    @property
    def isfunction(self):
        return True

    def rename_vars(self, rs):
        self._drsref = self._drsref.alpha_convert(rs)
        if self._comp is not None:
            self._comp.rename_vars(rs)

    def apply(self, arg):
        if self._comp is not None and self._comp.isfunction:
            self._comp = self._comp.apply(arg)
            return self
        au = arg.universe
        af = arg.freerefs
        if len(au) == 0 or len(af) != 0:
            raise DrsComposeError('Function application requires arguments with boundrefs')
        if self._drsref.referents[0] not in au:
            if len(au) == 1:
                # (old,new)
                rs = [(au[0], self._drsref.referents[0])]
                arg.rename_vars(rs)
                assert self._drsref.referents[0] in arg.universe
            else:
                # Add proposition
                p = PropComposition(ArgRight, self._drsref.referents[0])
                arg = p.apply(arg)
        elif len(au) > 1:
            # Add proposition
            p = PropComposition(ArgRight, self._drsref.referents[0])
            arg = p.apply(arg)
        if self._comp is None:
            return arg
        if isinstance(self._comp, CompositionList):
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
    def __init__(self, position, referent):
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

    def apply(self, arg):
        if not isinstance(arg, CompositionList):
            arg = CompositionList([arg])
        d = arg.apply()
        assert isinstance(d, DrsComposition)
        return DrsComposition(DRS(self._drsref.referents, [Prop(self._drsref.referents[0], d.drs)]))
