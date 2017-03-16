# -*- coding: utf-8 -*-
"""Compositional DRT"""

from drs import DRS, DRSRef, Merge, Prop, Imp, Rel, Neg, Box, Diamond, Or
from drs import get_new_drsrefs, ConditionRef
from utils import iterable_type_check, intersect, union, union_inplace, complement, compare_lists_eq, rename_var, \
    remove_dups
from common import SHOW_LINEAR
from ccgcat import Category, CAT_EMPTY, RL_RPASS, RL_LPASS, RL_FA, RL_BA, RL_BC, RL_FC, RL_BX, RL_FX, \
    RL_FORWARD_TYPE_RAISE, RL_BACKWARD_TYPE_RAISE, RL_RNUM, RL_TYPE_CHANGE_VPMOD, RL_RCONJ, RL_LCONJ, \
    RL_TYPE_CHANGE_NP_NP
import weakref
import collections

## @{
## @ingroup gconst
## @defgroup CCG to DRS Constants

## Compose option: remove propositions containing single referent in the subordinate DRS.
CO_REMOVE_UNARY_PROPS = 0x1
## Compose option: print derivations to stdout during production
CO_PRINT_DERIVATION = 0x2
## Compose option: verify signature during production
CO_VERIFY_SIGNATURES = 0x4

## @}


class DrsComposeError(Exception):
    """Production Error."""
    pass


class Production(object):
    """An abstract production."""
    def __init__(self, category=None):
        self._lambda_refs = DRS([], [])
        self._options = 0
        if category is None:
            self._category = CAT_EMPTY
        elif isinstance(category, Category):
            self._category = category
        else:
            raise TypeError('category must be instance of Category')

    def __eq__(self, other):
        return id(self) == id(other)

    @staticmethod
    def nodups(rs):
        return filter(lambda x: x[0] != x[1], rs)

    @property
    def signature(self):
        """The drs type signature."""
        return 'T'

    @property
    def category(self):
        """The CCG category"""
        return self._category

    @property
    def isempty(self):
        """Test if the production is an empty."""
        return False

    @property
    def isfunctor(self):
        """Test if this class is a functor production."""
        return False

    @property
    def iscombinator(self):
        """Test if this class is a combinator. A combinator expects a functors as the argument."""
        return False

    @property
    def universe(self):
        """Get the universe of the referents."""
        raise NotImplementedError

    @property
    def variables(self):
        """Get the variables."""
        raise NotImplementedError

    @property
    def freerefs(self):
        """Get the free referents."""
        raise NotImplementedError

    @property
    def lambda_refs(self):
        """Get the lambda function referents"""
        return self._lambda_refs.universe if self._lambda_refs is not None else []

    @property
    def conditions(self):
        """Get the DRS conditions for this production."""
        return []

    @property
    def compose_options(self):
        """Get the compose options."""
        return self._options

    @property
    def isproper_noun(self):
        """Test if the production resolved to a proper noun"""
        return False

    @property
    def iterator(self):
        """If a list then iterate the productions in the list else return self."""
        yield self

    @property
    def size(self):
        """If a list then get the number of elements in the production list else return 1."""
        return 1

    @property
    def contains_functor(self):
        """If a list then return true if the list contains 1 or more functors, else returns isfunctor()."""
        return self.isfunctor

    @property
    def ispure(self):
        """Test if the underlying DRS instance is a pure DRS.

        Returns:
            True if a pure DRS.
        """
        return False

    def remove_proper_noun(self):
        pass

    def find_anaphora(self, r):
        """Find anaphora for referent r.

        Args:
            r: A marbles.ie.drt.drs.DRSRef instance.
        """
        return None

    def set_category(self, cat):
        """Set the CCG category.

        Args:
            cat: A Category instance.
        """
        self._category = cat

    def set_options(self, options):
        """Set the compose opions.

        Args:
            options: The compose options.
        """
        self._options = int(options)

    def set_lambda_refs(self, refs):
        """Set the lambda referents for this production.

        Args:
            refs: The lambda referents.
        """
        if refs is None:
            self._lambda_refs = None
        else:
            self._lambda_refs = DRS(refs,[])

    def rename_lambda_refs(self, rs):
        """Perform alpha conversion on the lambda referents.

        Args:
            rs: A list of tuples, (old_name, new_name).
        """
        if self._lambda_refs is not None:
            self._lambda_refs = self._lambda_refs.alpha_convert(rs)
            self._lambda_refs = self._lambda_refs.substitute(rs)

    def rename_vars(self, rs):
        """Perform alpha conversion on the production data.

        Args:
            rs: A list of tuples, (old_name, new_name).
        """
        raise NotImplementedError

    def unify(self):
        """Perform a DRS unification.

        Returns:
            A Production instance representing unified result.
        """
        return self

    def resolve_anaphora(self):
        """Purify the underlying DRS instance.

        Returns:
            A Production instance representing purified result.
        """
        return self


class DrsProduction(Production):
    """A DRS production."""
    def __init__(self, drs, properNoun=False, category=None):
        """Constructor.

        Args:
            drs: A marbles.ie.drt.DRS instance.
            properNoun: True is a proper noun.
        """
        super(DrsProduction, self).__init__(category)
        if not isinstance(drs, DRS):
            raise TypeError
        self._drs = drs
        self._nnp = properNoun

    def __repr__(self):
        lr = [r.var.to_string() for r in self.lambda_refs]
        if len(lr) == 0:
            return self.drs.show(SHOW_LINEAR).encode('utf-8')
        return 'λ' + 'λ'.join(lr) + '.' + self.drs.show(SHOW_LINEAR).encode('utf-8')

    @property
    def signature(self):
        """The drs type signature."""
        if self._category == CAT_EMPTY:
            if len(self._drs.referents) == 1 and len(self._drs.conditions) == 1 and \
                    isinstance(self._drs.conditions[0], Prop):
                return 'Z'
            return 'T'
        return self._category.drs_signature

    @property
    def lambda_refs(self):
        """Get the lambda function referents"""
        # For DRS we treat None as a special case meaning infer from DRS. This may not be always the best
        # policy so in the code we prefer to explicitly set which refs can be resolved during a unify
        if self._lambda_refs is None:
            r = self._drs.freerefs
            r.extend(self._drs.universe)
            return r
        return self._lambda_refs.universe

    @property
    def isproper_noun(self):
        """Test if the production resolved to a proper noun"""
        return self._nnp

    @property
    def universe(self):
        """Get the universe of the referents."""
        return self._drs.universe

    @property
    def variables(self):
        """Get the variables. Both free and bound referents are returned."""
        return union(self._drs.universes, self._drs.freerefs)

    @property
    def freerefs(self):
        """Get the free referents."""
        return self._drs.freerefs

    @property
    def isempty(self):
        """Test if the production is an empty DRS."""
        return self._drs.isempty

    @property
    def conditions(self):
        """Get the DRS conditions for this production."""
        return self._drs.conditions

    @property
    def drs(self):
        """Get the DRS data attached to this production."""
        return self._drs

    @property
    def ispure(self):
        """Test if the underlying DRS instance is a pure DRS.

        Returns:
            True if a pure DRS.
        """
        return self._drs.ispure

    def remove_proper_noun(self):
        self._nnp = False

    def find_anaphora(self, r):
        """Find anphora for referent r.

        Args:
            r: A marbles.ie.drt.drs.DRSRef instance.
        """
        return self._drs.find_condition(Rel('is.anaphora',[r]))

    def rename_vars(self, rs):
        """Perform alpha conversion on the production data.

        Args:
            rs: A list of tuples, (old_name, new_name).
        """
        if len(rs) == 0:
            return
        self._drs = self._drs.alpha_convert(rs)
        self._drs = self._drs.substitute(rs)
        self.rename_lambda_refs(rs)

    def resolve_anaphora(self):
        """Purify the underlying DRS instance.

        Returns:
            A Production instance representing purified result.
        """
        # Find proper nouns
        pn = []
        u = self._drs.universes
        for r in u:
            rc = self._drs.find_condition(Rel('is.propernoun', [r]))
            if rc is not None:
                pn.append(rc)

        # Find anaphora
        fr = self._drs.freerefs
        anaphora = []
        for r in fr:
            rc = self._drs.find_condition(Rel('is.anaphora', [r]))
            if rc is not None:
                anaphora.append(rc)
        # If we have more freerefs than those marked as anphora we need to add markers
        needMarker = len(fr) != len(anaphora)

        # Create resolve list
        rs = []
        for a in anaphora:
            nn = None
            for n in pn:
                if n.gdlevel >= a.ldlevel and n.ldlevel >= a.ldlevel and n.gd.find_subdrs(a.ld) is not None:
                    if nn is None:
                        nn = n
                    elif nn.gdlevel > n.gdlevel:
                        nn = n
                    elif nn.gdlevel == n.gdlevel and nn.ldlevel < n.ldlevel:
                        nn = n
            if nn is not None:
                rs.append((a.cond.referents[0], nn.cond.referents[0]))

        # Resolve anaphora
        self.rename_vars(rs)
        fr = self._drs.freerefs
        if len(fr) != 0:
            if needMarker:
                # FIXME: resolve anaphora later so add marker
                pass
            self._drs = DRS(union(self._drs.universe, fr), self._drs.conditions)
        self._drs = self._drs.purify()
        return self


class ProductionList(Production):
    """A list of productions."""
    def __init__(self, compList=None):
        super(ProductionList, self).__init__()
        if compList is None:
            compList = []
        if isinstance(compList, (DRS, Merge)):
            compList = [DrsProduction(compList)]
        elif isinstance(compList, Production):
            compList = [compList]
        elif iterable_type_check(compList, (DRS, Merge)):
            compList = [DrsProduction(x) for x in compList]
        elif not iterable_type_check(compList, Production):
            raise TypeError('DrsProduction construction')
        self._compList = compList

    def __repr__(self):
        lr = [r.var.to_string() for r in self.lambda_refs]
        if len(lr) == 0:
            return '<' + '##'.join([repr(x) for x in self._compList]) + '>'
        return 'λ' + 'λ'.join(lr) + '.<' + '##'.join([repr(x) for x in self._compList]) + '>'

    @property
    def isproper_noun(self):
        """Test if the production resolved to a proper noun"""
        return all([x.isproper_noun for x in self._compList])

    @property
    def universe(self):
        """Get the universe of the referents."""
        u = set()
        for d in self._compList:
            u = u.union(d.universe)
        return sorted(u)

    @property
    def variables(self):
        """Get the variables."""
        u = set()
        for d in self._compList:
            u = u.union(d.variables)
        return sorted(u)

    @property
    def freerefs(self):
        """Get the free referents."""
        u = set()
        for d in self._compList:
            u = u.union(d.freerefs)
        return sorted(u.difference(self.universe))

    @property
    def isempty(self):
        """Test if the production results in an empty DRS."""
        return len(self._compList) == 0

    @property
    def size(self):
        """Get the number of elements in this production list."""
        return len(self._compList)

    @property
    def contains_functor(self):
        for c in self._compList:
            if c.contains_functor:
                return True
        return False

    @property
    def signature(self):
        """The production type signature."""
        return ';'.join([x.signature for x in self._compList])

    def find_anaphora(self, r):
        """Find anphora for referent r.

        Args:
            r: A marbles.ie.drt.drs.DRSRef instance.
        """
        for d in self._compList:
            rc = d.find_anaphora(r)
            if rc is not None:
                return rc
        return None

    def iterator(self):
        """Iterate the productions in this list."""
        for c in self._compList:
            yield c

    def reversed_iterator(self):
        """Iterate the productions in this list."""
        for c in reversed(self._compList):
            yield c

    def clone(self):
        cl = ProductionList([x for x in self._compList])
        cl.set_options(self.compose_options)
        cl.set_lambda_refs(self.lambda_refs)
        return cl

    def flatten(self):
        """Unify subordinate ProductionList's into the current list."""
        compList = []
        for d in self._compList:
            if d.isempty:
                continue
            if isinstance(d, ProductionList):
                d = d.unify()
                if isinstance(d, ProductionList):
                    compList.extend(d._compList)
                else:
                    compList.append(d)
            else:
                compList.append(d)
        self._compList = compList

    def rename_vars(self, rs):
        """Perform alpha conversion on the production data.

        Args:
            rs: A list of tuples, (old_name, new_name).
        """
        if len(rs) == 0:
            return
        self.rename_lambda_refs(rs)
        for d in self._compList:
            d.rename_vars(rs)

    def push_right(self, other, merge=False):
        """Push an argument to the right of the list.

        Args:
            other: The argument to push.
            merge: True if other is a ProductionList instance and you want to
            merge lists (like extend). If False other is added as is (like append).

        Returns:
            The self instance.
        """
        if isinstance(other, DRS):
            other = DrsProduction(other)
        if merge and isinstance(other, ProductionList):
            self._compList.extend(other._compList)
        else:
            other.set_options(self.compose_options)
            self._compList.append(other)
        return self

    def push_left(self, other, merge=False):
        """Push an argument to the left of the list.

        Args:
            other: The argument to push.
            merge: True if other is a ProductionList instance and you want to
            merge lists (like extend). If False other is added as is (like append).

        Returns:
            The self instance.
        """
        if isinstance(other, DRS):
            other = DrsProduction(other)
        if merge and isinstance(other, ProductionList):
            compList = [x for x in other._compList]
            compList.extend(self._compList)
            self._compList = compList
        else:
            other.set_options(self.compose_options)
            compList = [other]
            compList.extend(self._compList)
            self._compList = compList
        return self

    '''
    def apply_functor(self, fn, arg):
        """Need this because the parse tree is not always clear regarding the order of operations.

        Args:
            fn: A functor production instance.
            arg: The functor argument.

        Returns:
            A production.
        """
        if not fn.iscombinator and arg.iscombinator and ((fn.isarg_left and arg.isarg_right) or (fn.isarg_right and arg.isarg_left)):
            d = arg.apply(fn)
        d = fn.apply(arg)
        return d
    '''

    def apply_forward(self):
        """Forward application.

        Remarks:
            Executes a single production rule.
        """
        if len(self._compList) < 2:
            return self
        fn = self._compList[0]
        arg = self._compList[1]
        c = self._compList[1:]
        d = fn.apply(arg)
        c[0] = d
        self._compList = c
        self.set_lambda_refs(d.lambda_refs)
        self.set_category(d.category)
        return self
        '''
        rstk = self._compList
        rstk.reverse()
        lstk = []
        self._compList = []

        while len(rstk) != 0:
            d = rstk[-1]
            rstk.pop()
            if d.isfunctor:
                if d.isarg_right:
                    if len(rstk) == 0:
                        if len(lstk) != 0:
                            if lstk[-1].iscombinator and lstk[-1].isarg_right:
                                d = self.apply_functor(lstk[-1], d)
                                lstk.pop()
                                rstk.append(d)
                                continue
                            if enableException:
                                raise DrsComposeError('Function "%s" missing right argument' % repr(d))
                            else:
                                lstk.append(d)
                                self._compList = lstk
                                return self
                        self._compList = [d]
                        return self
                    d = self.apply_functor(d, rstk[-1])
                    rstk.pop()
                    rstk.append(d)
                else:
                    if len(lstk) == 0:
                        if len(rstk) != 0:
                            if rstk[-1].iscombinator and rstk[-1].isarg_left:
                                d = self.apply_functor(rstk[-1], d)
                                rstk.pop()
                                rstk.append(d)
                                continue
                            if enableException:
                                raise DrsComposeError('Function "%s" missing left argument' % repr(d))
                            else:
                                rstk.append(d)
                                rstk.reverse()
                                self._compList = rstk
                                return self
                        self._compList = [d]
                        return self
                    d = self.apply_functor(d, lstk[-1])
                    lstk.pop()
                    rstk.append(d)
            elif isinstance(d, ProductionList):
                # Merge lists
                for x in d.reversed_iterator():
                    rstk.append(x)
            else:
                lstk.append(d)

        self._compList = lstk
        return self
        '''

    def apply_backward(self, enableException=False):
        """Backward application.

        Remarks:
            Executes a single production rule.
        """
        if len(self._compList) < 2:
            return self
        fn = self._compList[-1]
        arg = self._compList[-2]
        c = self._compList[0:-1]
        d = fn.apply(arg)
        c[-1] = d
        self._compList = c
        self.set_lambda_refs(d.lambda_refs)
        self.set_category(d.category)
        return self

        '''
        rstk = []
        lstk = self._compList
        self._compList = []

        # Now process functor application right to left
        while len(lstk) != 0:
            d = lstk[-1]
            lstk.pop()
            if d.isfunctor:
                if d.isarg_right:
                    if len(rstk) == 0:
                        if len(lstk) != 0:
                            if lstk[-1].iscombinator and lstk[-1].isarg_right:
                                d = self.apply_functor(lstk[-1], d)
                                lstk.pop()
                                lstk.append(d)
                                continue
                            if enableException:
                                raise DrsComposeError('Function "%s" missing right argument' % repr(d))
                            else:
                                lstk.append(d)
                                self._compList = lstk
                                return self
                        self._compList = [d]
                        return self
                    d = self.apply_functor(d, rstk[-1])
                    rstk.pop()
                    lstk.append(d)
                else:
                    if len(lstk) == 0:
                        if len(rstk) != 0:
                            if rstk[-1].iscombinator and rstk[-1].isarg_left:
                                d = self.apply_functor(rstk[-1], d)
                                rstk.pop()
                                lstk.append(d)
                                continue
                            if enableException:
                                raise DrsComposeError('Function "%s" missing left argument' % repr(d))
                            else:
                                rstk.append(d)
                                rstk.reverse()
                                self._compList = rstk
                                return self
                        self._compList = [d]
                        return self
                    d = self.apply_functor(d, lstk[-1])
                    lstk.pop()
                    lstk.append(d)
            elif isinstance(d, ProductionList):
                # Merge lists
                for x in d.iterator():
                    lstk.append(x)
            else:
                rstk.append(d)

        rstk.reverse()
        self._compList = rstk
        return self
        '''

    def unify(self):
        """Finalize the production by performing a unification right to left.

        Returns:
            A Production instance.
        """
        ml = [x.unify() for x in self._compList]
        self._compList = []
        if len(ml) == 1:
            if not ml[0].isfunctor:
                ml[0].set_lambda_refs(self.lambda_refs)
            return ml[0]
        elif any(filter(lambda x: x.contains_functor, ml)):
            self._compList = ml
            return self

        # Always unify reversed
        universe = []
        for i in reversed(range(len(ml))):
            d = ml[i]
            rn = intersect(d.universe, universe)
            if len(rn) != 0:
                # FIXME: should this be allowed?
                # Alpha convert bound vars in both self and arg
                xrs = self.nodups(zip(rn, get_new_drsrefs(rn, universe)))
                # Rename so variable subscripts increase left to right
                for m in ml[i+1:]:
                    m.rename_vars(xrs)
            universe = union(universe, d.universe)

        refs = []
        conds = []
        pconds = [] # proper nouns
        oconds = [] # other predicates, for example is.propernoun()
        lastr = DRSRef('$$$$')
        proper = 0
        for d in ml:
            if d.isproper_noun:
                nextr = d.drs.referents[0] if len(d.drs.referents) != 0 else d.drs.freerefs[0]
                if nextr != lastr:
                    # Hyphenate name
                    lastr = nextr
                    proper += 1
                    if len(pconds) != 0:
                        conds.append(Rel('-'.join([c.relation.to_string() for c in pconds]), [lastr]))
                        conds.extend(oconds)
                    ctmp = d.drs.conditions
                    if isinstance(ctmp[0], Prop):
                        pass
                    pconds = [ ctmp[0] ]
                    oconds = ctmp[1:]
                else:
                    ctmp = d.drs.conditions
                    if isinstance(ctmp[0], Prop):
                        pass
                    pconds.append(ctmp[0])
                    oconds.extend(ctmp[1:])
            else:
                # FIXME: proper-noun followed by noun, for example Time magazine, should we colate?
                if len(pconds) != 0:
                    conds.append(Rel('-'.join([c.relation.to_string() for c in pconds]), [lastr]))
                    conds.extend(oconds)
                lastr = DRSRef('$$$$')
                pconds = []
                oconds = []
                conds.extend(d.drs.conditions)
                proper += 1
            refs.extend(d.drs.referents)
        # FIXME: Boc Raton and Hot Spring => Boca(x) Raton(x) Hot(x1) Springs(x1)
        # Hyphenate name
        if len(pconds) != 0:
            conds.append(Rel('-'.join([c.relation.to_string() for c in pconds]), [lastr]))
            conds.extend(oconds)

        drs = DRS(refs, conds).purify()
        d = DrsProduction(drs, proper == 1)
        d.set_lambda_refs(self.lambda_refs)
        d.set_category(self.category)
        return d
    
    def compose_forward(self):
        """Forward composition and forward crossing composition.

        Remarks:
            Executes a single production rule.
        """
        assert len(self._compList) >= 2
        fn = self._compList[0]
        arg = self._compList[1]
        c = self._compList[1:]
        # CALL[X/Y](Y|Z)
        # Forward Composition           X/Y:f Y/Z:g => X/Z: λx􏰓.f(g(x))
        # Forward Crossing Composition  X/Y:f Y\Z:g => X\Z: λx􏰓.f(g(x))
        d = fn.compose(arg)
        c[0] = d
        self._compList = c
        self.set_lambda_refs(d.lambda_refs)
        self.set_category(d.category)
        return self

    def compose_backward(self):
        """Backward composition and forward crossing composition.

        Remarks:
            Executes a single production rule.
        """
        assert len(self._compList) >= 2
        fn = self._compList[-1]
        arg = self._compList[-2]
        c = self._compList[0:-1]
        # CALL[X\Y](Y|Z)
        # Backward Composition          Y\Z:g X\Y:f => X\Z: λx􏰓.f(g(x))
        # Backward Crossing Composition Y/Z:g X\Y:f => X/Z: λx􏰓.f(g(x))
        d = fn.compose(arg)
        c[-1] = d
        self._compList = c
        self.set_lambda_refs(d.lambda_refs)
        self.set_category(d.category)
        return self

    def conjoin_forward(self):
        """Forward conjoin of like types."""
        assert len(self._compList) >= 2
        f = self._compList[0]
        g = self._compList[1]
        c = self._compList[1:]
        if f.isfunctor:
            d = f.conjoin(g)
            c[0] = d
            self._compList = c
            self.set_lambda_refs(d.lambda_refs)
            self.set_category(d.category)
        elif g.isfunctor:
            d = g.conjoin(f)
            c[0] = d
            self._compList = c
            self.set_lambda_refs(d.lambda_refs)
            self.set_category(d.category)
        else:
            d = ProductionList(f)
            d.push_right(g)
            d = d.unify()
            c[0] = d
            self.set_category(f.category)
        return self

    def conjoin_backward(self):
        """Backward conjoin of like types."""
        assert len(self._compList) >= 2
        f = self._compList.pop()
        g = self._compList.pop()
        c = self._compList
        if f.isfunctor:
            d = f.conjoin(g)
            c.append(d)
            self._compList = c
            self.set_lambda_refs(d.lambda_refs)
            self.set_category(d.category)
        elif g.isfunctor:
            d = g.conjoin(f)
            c.append(d)
            self._compList = c
            self.set_lambda_refs(d.lambda_refs)
            self.set_category(d.category)
        else:
            d = ProductionList(f)
            d.push_right(g)
            c.append(d.unify())
            self.set_category(f.category)
        return self

    def type_change_forward(self, isvp):
        """Special type change rules. See section 3.8 of LDC 2005T13 manual.

        Args:
            isvp: True if a verb phrase.

        Remarks:
            Executes a single production rule.
        """
        assert len(self._compList) >= 2
        template = self._compList[0]
        vp = self._compList[1]
        c = self._compList[1:]
        d = template.special_type_change(vp, isvp)
        c[0] = d
        self._compList = c
        self.set_lambda_refs(d.lambda_refs)
        self.set_category(d.category)
        return self

    def apply(self, rule):
        """Applications based on rule.

        Args:
            rule: A marbles.ie.drt.ccgcat.Rule instance.

        Returns:
            A Production instance.
        """

        # alpha convert variables
        self.flatten()

        if rule in [RL_RPASS, RL_LPASS, RL_RNUM]:
            # TODO; add extra RL_RNUM predicate number.value(37), number.units(million)
            d = self.unify()
            if id(d) != id(self):
                self._compList = [d]
        elif rule == RL_BA:
            self.apply_backward()
        elif rule == RL_FA:
            self.apply_forward()
        elif rule in [RL_FC, RL_FX]:
            self.compose_forward()
        elif rule in [RL_BC, RL_BX]:
            self.compose_backward()
        elif rule == RL_LCONJ:
            self.conjoin_backward()
        elif rule == RL_RCONJ:
            self.conjoin_forward()
        elif rule == RL_TYPE_CHANGE_VPMOD:
            self.type_change_forward(True)
        elif rule == RL_TYPE_CHANGE_NP_NP:
            self.type_change_forward(False)
        elif rule in [RL_FORWARD_TYPE_RAISE, RL_BACKWARD_TYPE_RAISE]:
            # TODO: handle type raising
            raise NotImplementedError
        else:
            # TODO: handle all rules
            raise NotImplementedError

        if len(self._compList) == 0:
            return self

        if len(self._compList) == 1:
            d = self._compList[0]
            self._compList = []
            if d.isfunctor:
                d.inner_scope.set_category(self.category)
            else:
                d.set_category(self.category)
            return d
        return self


class FunctorProduction(Production):
    """A functor production. Functors are curried where the inner most functor is the inner scope."""
    def __init__(self, category, referent, production=None):
        """Constructor.

        Args:
            category: A marbles.ie.drt.ccgcat.Category instance.
            referent: Either a list of, or a single, marbles.ie.drt.drs.DRSRef instance.
            production: Optionally a marbles.ie.drt.drs.DRS instance or a Production instance. The DRS will be converted
                to a DrsProduction. If production is a functor then the combination is a curried functor.
        """
        super(FunctorProduction, self).__init__(category)
        if production is not None:
            if isinstance(production, (DRS, Merge)):
                production = DrsProduction(production)
            elif not isinstance(production, Production):
                raise TypeError('production argument must be a Production type')
        if category is None :
            raise TypeError('category cannot be None for functors')
        self._comp = production
        self._category = category
        # Store lambda vars as a DRS with no conditions so we inherit alpha conversion methods.
        if isinstance(referent, list):
            self._lambda_refs = DRS(referent, [])
        elif isinstance(referent, tuple):
            self._lambda_refs = DRS(list(referent), [])
        else:
            self._lambda_refs = DRS([referent], [])
        self._outer = None
        if self._comp is not None:
            if isinstance(self._comp, FunctorProduction):
                self._comp._set_outer(self)

    def _set_outer(self, outer):
        if outer is not None:
            self._outer = weakref.ref(outer)
        else:
            self._outer = None

    def _repr_helper1(self, i):
        if self.iscombinator:
            dash = "'";
        else:
            dash = ""
        s = 'λ' + chr(i) + dash
        if self._comp is not None and self._comp.isfunctor:
            s = self._comp._repr_helper1(i+1) + s
        return s

    def _repr_helper2(self, i):
        if self.iscombinator:
            dash = "'";
        else:
            dash = ""
        v = chr(i) + dash
        r = ','.join([x.var.to_string() for x in self._lambda_refs.referents])
        if self._comp is not None:
            if self._comp.isfunctor:
                s = self._comp._repr_helper2(i+1)
            else:
                s = str(self._comp)
            if self._category.isarg_right:
                return '%s;%s(%s)' % (s, v, r)
            else:
                return '%s(%s);%s' % (v, r, s)
        else:
            return '%s(%s)' % (v, r)

    def __repr__(self):
        return self._repr_helper1(ord('P')) + ''.join(['λ'+v.var.to_string() for v in self.lambda_refs]) \
               + '.' + self._repr_helper2(ord('P'))

    def _get_variables(self, u):
        if self._comp is not None:
            if self._comp.isfunctor:
                u = self._comp._get_variables(u)
            else:
                u = union_inplace(u, self._comp.variables)
        return u

    def _get_freerefs(self, u):
        if self._comp is not None:
            if self._comp.isfunctor:
                u = self._comp._get_freerefs(u)
            else:
                u = union_inplace(u, self._comp.freerefs)
        return u

    def _get_universe(self, u):
        if self._comp is not None:
            if self._comp.isfunctor:
                u = self._comp._get_universe(u)
            else:
                u = union_inplace(u, self._comp.universe)
        return u

    def _get_lambda_refs(self, u):
        # Get lambda vars ordered by functor scope
        u.extend(self._lambda_refs.referents)
        if self._comp is not None:
            if self._comp.isfunctor:
                u.extend(self._comp._get_lambda_refs(u))
            else:
                u.extend(self._comp.lambda_refs)
        return u

    def _get_position(self):
        # Get position in functor scope
        g = self
        i = 0
        while g.outer is not None:
            g = g.outer
            i += 1
        return i

    @property
    def signature(self):
        """Get the functor signature. For functors the signature returned is the signature at the global scope.

        Remarks:
            Properties outer_scope.signature, self.signature both map to inner_scope.signature. There is no public
            method to access the signature of outer curried functors.
        """
        return self.inner_scope._category.drs_signature

    @property
    def outer_scope(self):
        """Get the outer most functor in this production or self.

        See Also:
            marbles.ie.drt.compose.FunctorProduction.inner_scope
            marbles.ie.drt.compose.FunctorProduction.outer
        """
        g = self
        while g.outer is not None:
            g = g.outer
        return g

    @property
    def inner_scope(self):
        """Get the inner most functor in this production or self.

        See Also:
            marbles.ie.drt.compose.FunctorProduction.outer_scope
            marbles.ie.drt.compose.FunctorProduction.inner
        """
        c = self._comp
        cprev = self
        while c is not None and c.isfunctor:
            cprev = c
            c = c._comp
        return cprev

    @property
    def category(self):
        """The CCG category of the inner scope."""
        return self.inner_scope._category

    @property
    def outer(self):
        """The immediate outer functor or None.

        See Also:
            marbles.ie.drt.compose.FunctorProduction.outer_scope
        """
        return None if self._outer is None else self._outer() # weak deref

    @property
    def inner(self):
        """The immediate inner functor or None.

        See Also:
            marbles.ie.drt.compose.FunctorProduction.inner_scope
        """
        return None if self._comp is None or not self._comp.isfunctor else self._comp

    @property
    def iscurried(self):
        """Test if the functor is curried.

        Remarks:
            Test is same as `self.inner_scope.outer is not None`
        """
        return self._outer is not None or (self._comp is not None and self._comp.isfunctor)

    @property
    def isempty(self):
        """Test if the production produces an empty DRS."""
        return self._lambda_refs.isempty and (self._comp is None or self._comp.isempty)

    @property
    def variables(self):
        """Get the variables."""
        return self._get_variables([])

    @property
    def freerefs(self):
        """Get the free referents."""
        return self._get_freerefs([])

    @property
    def universe(self):
        """Get the universe of the referents."""
        return self._get_universe([])

    @property
    def lambda_refs(self):
        """Get the lambda functor referents ordered by functor scope. These are the referents that can be bound with
        during unification.
        """
        # Get unique referents, ordered by functor scope
        r = self._get_lambda_refs([])
        # Reverse because we can have args:
        # - [(x,e), (y,e), e] => [x,e,y,e,e] => [x,y,e] (REDUCTIONS AND PASS THRU)
        # - [e, (x, e)] => [e, x, e] => [x,e]           (EXPANDERS)
        r.reverse()
        r = remove_dups(r)
        r.reverse()
        return r

    @property
    def isarg_right(self):
        """Test if the functor takes a right argument."""
        if self._comp is not None and self._comp.isfunctor:
            return self._comp.isarg_right
        return self._category.isarg_right

    @property
    def isarg_left(self):
        """Test if the functor takes a left argument."""
        return not self.isarg_right

    @property
    def isfunctor(self):
        """Test if this class is a functor production. Always True for FunctorProduction instances."""
        return True

    @property
    def iscombinator(self):
        """A combinator expects a functor as the argument and returns a functor."""
        s = self._category.iscombinator

    def find_anaphora(self, r):
        """Find anaphora for referent r.

        Args:
            r: A marbles.ie.drt.drs.DRSRef instance.
        """
        return self._comp.find_anaphora(r) if self._comp is not None else None

    def clear(self):
        self._comp = None
        self._lambda_refs = DRS([], [])
        self._set_outer(None)

    def set_lambda_refs(self, refs):
        """Disabled for functors"""
            
    def set_category(self, cat):
        """Set the CCG category.

        Args:
            cat: A Category instance.
        """
        prev = self._category
        self._category = cat
        # sanity check
        if (cat.isarg_left and prev.isarg_right) or (cat.isarg_right and prev.isarg_left):
            raise DrsComposeError('Signature %s does not match %s argument position' %
                                 (cat.ccg_signature, 'right' if prev.isarg_right else 'left'))

    def set_options(self, options):
        """Set the compose options.

        Args:
            options: The compose options.
        """
        # Pass down options to nested functor
        super(FunctorProduction, self).set_options(options)
        if self._comp is not None:
            self._comp.set_options(options)

    def rename_vars(self, rs):
        """Perform alpha conversion on the production data.

        Args:
            rs: A list of tuples, (old_name, new_name).
        """
        if len(rs) == 0:
            return
        self._lambda_refs = self._lambda_refs.alpha_convert(rs)
        if self._comp is not None:
            self._comp.rename_vars(rs)

    def unify(self):
        """Finalize the production by performing a unify right to left.

        Returns:
            A Production instance.
        """
        if self._comp is not None:
            if self._comp.isfunctor:
                self._comp = self._comp.unify()
            else:
                lr = self._comp.lambda_refs
                cat = self.category.result_category
                d = self._comp.unify()
                # Make sure we don't change scoping after unifying combinators.
                if d.isfunctor:
                    fr = d.freerefs
                    fr = complement(fr, self.universe)
                    if len(fr) == 0:
                        # Remove functor since unification is complete
                        self._comp = d.inner_scope._comp
                        assert not self._comp.isfunctor
                        if not compare_lists_eq(lr, self._comp.lambda_refs):
                            pass
                        if 0 != (self.compose_options & CO_VERIFY_SIGNATURES):
                            assert compare_lists_eq(lr, self._comp.lambda_refs)
                    else:
                        self._comp = ProductionList(d)
                else:
                    self._comp = d
                self._comp.set_lambda_refs(lr)
                self._comp.set_category(cat)
        return self

    def apply_null_left(self):
        """Apply a null left argument `$` to the functor. This is necessary for processing
        the imperative form of a verb.

        Returns:
            A Production instance.
        """
        # TODO: Check if we have a proper noun accessible to the right and left
        if self.isarg_right or self._comp is None or self._comp.isfunctor:
            raise DrsComposeError('invalid apply null left to functor')
        if self._comp is not None and isinstance(self._comp, ProductionList):
            self._comp = self._comp.apply()
        d = DrsProduction(DRS(self._lambda_refs.universe, []))
        d = self.apply(d)
        return d

    def pop(self):
        """Remove inner scope and return the production."""
        if self._comp is None:
            # pop functor
            if self.outer is None:
                return None
            self.outer._comp = None
            self._set_outer(None)
            return self
        elif not self._comp.isfunctor:
            c = self._comp
            self._comp = None
            return c

        # tail recursion
        return self._comp.pop()

    def push(self, fn):
        """Push a production to the inner scope."""
        if self._comp is None:
            self._comp = fn
            if fn.isfunctor:
                fn._set_outer(self)
            return self
        elif not self._comp.isfunctor:
            raise DrsComposeError('cannot push functor to non-functor inner scope')

        # tail recursion
        return self._comp.push(fn)

    def make_vars_disjoint(self, arg):
        """Make variable names disjoint. This is always done before unification.

        Remarks:
            Should only call from outer scope.
        """
        ers = union(arg.lambda_refs, arg.variables)
        ers2 = union(self.lambda_refs, self.variables)
        ors = intersect(ers, ers2)
        if len(ors) != 0:
            nrs = get_new_drsrefs(ors, union(ers, ers2))
            xrs = self.nodups(zip(ors, nrs))
            self.rename_vars(xrs)

    def special_type_change(self, vp, hasevent):
        """Special type change. See LDC manual section 3.8.

        Args:
            vp: The verb phrase. Must be a S\NP category.
            hasevent: Should be True for verb phrases, false for adjectival phrases.

        Remarks:
            self is a template. The inner DrsProduction will be discarded.
        """
        slr = self.lambda_refs
        lr = vp.lambda_refs
        if len(lr) != len(slr):
            raise DrsComposeError('mismatch of lambda vars when doing special type change')
        if not hasevent:
            rs = zip(slr, lr)
        else:
            rs = zip(slr[0:-1], lr[0:-1])
            # event is always lr[-1] for verb phrases - don't merge these
            if slr[-1] == lr[-1]:
                ors = [slr[-1]]
                nrs = get_new_drsrefs(ors, union(slr, lr))
                xrs = self.nodups(zip(ors, nrs))
                self.rename_vars(xrs)
        self.rename_vars(rs)
        self.pop() # discard inner DrsProduction
        g = vp.pop()
        self.push(g)
        return self

    def compose(self, g):
        """Function Composition.

        Arg:
            g: The Y|Z functor where self (f) is the X|Y functor.

        Returns:
            A Production instance.

        Remarks:
            CALL[X|Y](Y|Z)
            - Backward Composition = `Y\Z:g X\Y:f => X\Z: λx􏰓.f(g(x))`
            - Backward Crossing Composition = `Y/Z:g X\Y:f => X/Z: λx􏰓.f(g(x))`
            - Forward Composition = `X/Y:f Y/Z:g => X/Z: λx􏰓.f(g(x))`
            - Forward Crossing Composition = `X/Y:f Y\Z:g => X\Z: λx􏰓.f(g(x))`
        """
        if not g.isfunctor:
            raise DrsComposeError('compose argument must be a functor')
        assert g.outer is None  # must be outer scope

        # Create a new category
        cat = Category.combine(self.category.result_category, g.category.slash, g.category.argument_category)

        # Rename so f names are disjoint with g names.
        # Try to keep var subscripts increasing left to right.
        if self.isarg_left:
            self.outer_scope.make_vars_disjoint(g)
        else:
            g.make_vars_disjoint(self.outer_scope)

        # Get lambdas
        glr = g.lambda_refs
        yg = g.pop()
        xf = self.pop()
        assert yg is not None
        assert xf is not None
        yflr = self.lambda_refs

        # Get Y unification region
        fv = self.category.argument_category.extract_atoms()
        gv = g.result_category.extract_atoms()
        rs = map(lambda x: (x[2], x[3]), filter(lambda x: x[0].can_unify(x[1]),
                                                zip(gv, fv, yflr, glr)))
        if len(zip(yflr, glr)) != len(rs):
            pass

        # Unify
        rs = self.nodups(zip(yflr, glr))
        assert len(rs) != 0
        xf.rename_vars(rs)

        # Build
        pl = ProductionList()
        pl.push_right(xf)
        pl.push_right(yg)
        pl = pl.unify()
        assert isinstance(pl, DrsProduction)
        g.push(pl)
        g.set_category(cat)
        return g

    def conjoin(self, g):
        """Conjoin Composition.

        Arg:
            g: The X2|Y2 functor where self (f) is the X1|Y1 functor.

        Returns:
            A Production instance.

        Remarks:
            CALL[X1|Y1](X2|Y2)
        """
        assert self.outer is None
        if g.isfunctor:
            assert g.outer is None
            ga = g.extract_atoms()
            fa = self.extract_atoms()
            for u, v in zip(ga, fa):
                if not u.can_unify(v):
                    raise DrsComposeError('conjoin argument must be a like functor')

            if len(g.lambda_refs) != len(self.lambda_refs) or self.inner_scope._get_position() != g.inner_scope._get_position():
                raise DrsComposeError('cannot cojoin functors with different structure')

            # Rename f so disjoint with g names
            self.make_vars_disjoint(g)

            # Remove resolved vars, for example events - these cannot be unified
            u = []
            gc = g.pop()
            u.extend(gc.lambda_refs)
            gc.set_lambda_refs([])
            g.push(gc)

            fc = self.pop()
            fclr = fc.lambda_refs
            u.extend(fclr)
            fc.set_lambda_refs([])
            self.push(fc)

            rs = zip(complement(g.lambda_refs, u), complement(self.lambda_refs, u))
            g.rename_vars(rs)
            gc = g.pop()
            fc = self.pop()
            c = ProductionList(fc)
            c.push_right(gc)
            c = c.unify()
            c.set_lambda_refs(fclr)
            self.push(c)
        else:
            if g.category.simplify() != self.category.simplify():
                raise DrsComposeError('conjoin argument must be a like type of functor result')

            # Rename f so disjoint with g names
            self.make_vars_disjoint(g)
            g.set_lambda_refs([])
            fc = self.pop()
            c = ProductionList(fc)
            c.push_right(g)
            c.set_lambda_refs(fc.lambda_refs)
            c.set_category(fc.category)
            self.push(c.unify())

        return self

    def apply(self, arg):
        """Function application.

        Arg:
            The substitution argument.

        Returns:
            A Production instance.
        """
        if self._comp is not None and self._comp.isfunctor:
            self._comp = self._comp.apply(arg)
            if self._comp.isfunctor:
                self._comp._set_outer(self)
            return self

        assert self._comp is not None

        if 0 != (self.compose_options & CO_PRINT_DERIVATION):
            print('DERIVATION:= %s {%s=%s}' % (repr(self.outer_scope), chr(ord('P')+self._get_position()), repr(arg)))

        # Ensure names do not conflict. Need to execute at outer scope so all variables are covered.
        # Try to keep var subscripts increasing left to right.
        if self.isarg_left or not arg.isfunctor:
            self.outer_scope.make_vars_disjoint(arg)
        else:
            arg.make_vars_disjoint(self.outer_scope)

        # Add a proposition if too many variables to bind
        alr = arg.lambda_refs
        if len(alr) == 0:
            # FIXME: lambda_refs should always be set
            alr = arg.universe
        slr = self.lambda_refs

        # Use Category.extract_atoms to get binding region
        # Bind with inner scope
        vs = self.category.argument_category.extract_atoms()
        us = arg.category.extract_atoms()

        if len(self._lambda_refs.referents) == 1 and len(us) != 1 and len(alr) != 1 and not arg.isfunctor:
            # Add proposition
            p = PropProduction(Category('PP/NP'), slr[0])
            arg = p.apply(arg)
            alr = arg.lambda_refs

        rs = map(lambda x: (x[2], x[3]), filter(lambda x: x[0].can_unify(x[1]),
                    zip(us, vs, alr, self._lambda_refs.referents)))
        if 0 != (self.compose_options & CO_VERIFY_SIGNATURES):
            xxx = zip(alr, self._lambda_refs.referents)
            if len(xxx) != len(rs):
                pass
            assert len(xxx) != 0
        arg.rename_vars(self.nodups(rs))
        '''
        # Make sure names don't conflict with global scope
        ors = intersect(alr[len(rs):], complement(self.outer_scope.lambda_refs, slr))
        if len(ors) != 0:
            xrs = zip(ors, get_new_drsrefs(ors, union(alr, slr)))
            arg.rename_vars(self.nodups(xrs))
        arg.rename_vars(self.nodups(rs))

        ers = union(alr, arg.universe, arg.freerefs)
        ors = intersect(ers, union(self.lambda_refs, self.universe, self.freerefs))
        if len(ors) != 0:
            nrs = get_new_drsrefs(ors, union(ers, ors))
            xrs = self.nodups(zip(ors, nrs))
            self.rename_vars(xrs)
        flr = self.lambda_refs
        '''

        rn = intersect(arg.universe, self.universe)
        if len(rn) != 0:
            pass
        assert len(rn) == 0
        '''
        if len(rn) != 0:
            # FIXME: should we allow this or hide behind propositions
            # Alpha convert bound vars in both self and arg
            xrs = zip(rn, get_new_drsrefs(rn, union(arg.lambda_refs, slr)))
            arg.rename_vars(self.nodups(xrs))
        '''
        if arg.isfunctor:
            assert arg.inner_scope._comp is not None
            # functor production
            if arg.iscombinator:
                # Can't handle at the moment
                raise DrsComposeError('Combinators arguments %s for combinators %s not supported' %
                                      (arg.signature, self.signature))
            cl = ProductionList()
            cl.set_options(self.compose_options)
            cl.set_category(self.category.result_category)

            # Apply the combinator
            acomp = arg.pop()
            scomp = self.pop()
            cl.set_lambda_refs(union_inplace(acomp.lambda_refs, scomp.lambda_refs))
            if self.isarg_left:
                cl.push_right(acomp)
                cl.push_right(scomp)
            else:
                cl.push_right(scomp)
                cl.push_right(acomp)

            if self.category.ismodifier:
                arg.push(cl.unify())
                return arg
            else:
                self.clear()
                return cl.unify()

            '''
            if self._comp is not None:

                # Carry forward lambda refs to combinator scope
                lr = self._comp.lambda_refs
                uv = self._comp.universe
                uv = filter(lambda x: x in uv, lr) # keep lambda ordering
                if self._category.isarg_right:
                    lr = union_inplace(lr, arg.outer_scope.lambda_refs)
                else:
                    lr = union_inplace(arg.outer_scope.lambda_refs, lr)
                lr = complement(lr, uv)
                lr.extend(uv)
                cl.set_lambda_refs(lr)

                # Set arg lambdas, the ordering will be different to above
                uv = [] if arg_comp is None else complement(lr, arg.lambda_refs)
                lr = [] if arg_comp is None else arg_comp.lambda_refs
                lr = union_inplace(lr, uv)

                if arg_comp is None:
                    arg.inner_scope._comp = self._comp
                elif self.isarg_left:
                    cl2 = ProductionList()
                    cl2.push_right(arg_comp, merge=True)
                    cl2.push_right(self._comp, merge=True)
                    cl2.set_lambda_refs(lr)
                    arg.inner_scope._comp = cl2
                else:
                    cl2 = ProductionList()
                    cl2.push_right(self._comp, merge=True)
                    cl2.push_right(arg_comp, merge=True)
                    cl2.set_lambda_refs(lr)
                    arg.inner_scope._comp = cl2

            cl.set_category(self.category.result_category)
            cl.push_right(arg, merge=True)
            outer = self.outer
            self.clear()
            if 0 != (self.compose_options & CO_PRINT_DERIVATION):
                print('          := %s' % repr(cl if outer is None else outer.outer_scope))

            if outer is None and cl.contains_functor:
                cl = cl.unify()

            return cl
            '''

        # functor application
        if self._comp is not None and arg.contains_functor:
            raise DrsComposeError('Invalid functor placement during functor application')

        # Remove resolved referents from lambda refs list
        assert len(self._lambda_refs.referents) != 0
        lr = filter(lambda x: x != self._lambda_refs.referents[0], self.lambda_refs)
        if self._comp is None:
            arg.set_options(self.compose_options)
            self.clear()
            arg.set_lambda_refs(lr)
            return arg
        elif isinstance(self._comp, ProductionList):
            c = self._comp
        else:
            c = ProductionList(self._comp)

        if self.isarg_right:
            c.push_right(arg)
        else:
            c.push_left(arg)

        c.set_options(self.compose_options)
        c = c.unify()
        c.set_lambda_refs(lr)
        c.set_category(self.category.result_category)
        self.clear()

        if 0 != (self.compose_options & CO_PRINT_DERIVATION):
            print('          := %s' % repr(c))

        return c


class PropProduction(FunctorProduction):
    """A proposition functor."""
    def __init__(self, category, referent, production=None):
        super(PropProduction, self).__init__(category, referent)

    def _repr_helper2(self, i):
        v = chr(i)
        if len(self._lambda_refs.referents) != 0:
            r = self._lambda_refs.referents[0].var.to_string()
            return '[%s| %s: %s(*)]' % (r, r, v)
        return '[| ]'

    @property
    def variables(self):
        """Get the variables."""
        return []

    @property
    def freerefs(self):
        """Get the free referents. Always empty for a proposition."""
        return []

    @property
    def universe(self):
        """Get the universe of the referents."""
        return self._lambda_refs.universe

    def apply_null_left(self):
        """It is an error to call this method for propositions"""
        raise DrsComposeError('cannot apply null left to a proposition functor')

    def apply(self, d):
        """Function application.

        Arg:
            d: The substitution argument.

        Returns:
            A Production instance.
        """
        if self._comp is not None and self._comp.isfunctor:
            self._comp = self._comp.apply(d)
            if self._comp.isfunctor:
                self._comp._set_outer(self)
            return self

        if 0 != (self.compose_options & CO_PRINT_DERIVATION):
            print('DERIVATION:= %s {%s=%s}' % (repr(self.outer_scope), chr(ord('P')+self._get_position()), repr(d)))
        if isinstance(d, ProductionList):
            d = d.unify()
        assert isinstance(d, DrsProduction)
        # FIXME: removing proposition from a proper noun causes an exception during ProductionList.apply()
        if (self.compose_options & CO_REMOVE_UNARY_PROPS) != 0 and len(d.drs.referents) == 1 and not d.isproper_noun:
            rs = zip(d.drs.referents, self._lambda_refs.referents)
            d.rename_vars(self.nodups(rs))
            d.set_options(self.compose_options)
            lr = self._lambda_refs.referents
            self.clear()
            d.set_lambda_refs(lr)
            if 0 != (self.compose_options & CO_PRINT_DERIVATION):
                print('          := %s' % repr(d))
            return d
        lr = self._lambda_refs.referents
        dd = DrsProduction(DRS(lr, [Prop(self._lambda_refs.referents[0], d.drs)]))
        dd.set_options(self.compose_options)
        self.clear()
        dd.set_lambda_refs(lr)
        dd.set_category(self.category.result_category)
        if 0 != (self.compose_options & CO_PRINT_DERIVATION):
            print('          := %s' % repr(dd))
        return dd


class OrProduction(FunctorProduction):
    """An Or functor."""
    def __init__(self, category, negate=False):
        super(OrProduction, self).__init__(category, [])
        self._negate = negate

    ## @cond
    def __repr__(self):
        if self._comp is None:
            return '||'
        elif self.isarg_left:
            return '||' + super(OrProduction, self).__repr__()
        else:
            return super(OrProduction, self).__repr__() + '||'
    ## @endcond

    @property
    def variables(self):
        """Get the variables."""
        inner = self.inner_scope
        return [] if inner._comp is None else inner._comp.variables

    @property
    def freerefs(self):
        """Get the free referents. Always empty for a proposition."""
        inner = self.inner_scope
        return [] if inner._comp is None else inner._comp.freerefs

    @property
    def universe(self):
        """Get the universe of the referents."""
        inner = self.inner_scope
        return [] if inner._comp is None else inner._comp.universe

    def set_lambda_refs(self, refs):
        """Disabled for Or functors."""
        pass

    def apply_null_left(self):
        """It is an error to call this method for Or functors"""
        raise DrsComposeError('cannot apply null left to a Or functor')

    def apply(self, arg):
        """Function application.

        Arg:
            The substitution argument.

        Returns:
            A Production instance.
        """
        if self._comp is not None and self._comp.isfunctor:
            self._comp = self._comp.apply(arg)
            if self._comp.isfunctor:
                self._comp._set_outer(self)
            return self

        # We are at the inner scope
        if arg.isfunctor:
            if arg.outer is not None:
                raise DrsComposeError('cannot apply Or functor to inner scope functors')
            if self._comp is not None and len(arg.lamba_refs) != (self._comp.lambda_refs):
                raise DrsComposeError('Or functor requires lamba refs to be same size')

        if self._comp is None:
            c = ProductionList(arg)
            c.set_lambda_refs(arg.lambda_refs)
            self._comp = c
            return self

        if isinstance(arg, OrProduction):
            raise DrsComposeError('cannot apply Or production to another Or production.')

        if 0 != (self.compose_options & CO_PRINT_DERIVATION):
            print('DERIVATION:= %s {%s=%s}' % (repr(self.outer_scope), chr(ord('P')+self._get_position()), repr(arg)))

        # Extract inner production
        p = [x for x in self._comp.iterator()]
        assert len(p) == 1
        p = p[0]
        cl = ProductionList()
        if p.isfunctor:
            # unify inner production
            assert arg.isfunctor
            arg_inner = arg.inner_scope
            p_inner = p.inner_scope
            if self.isarg_left:
                rs = zip(p.lambda_refs, arg.lambda_refs)
                p.rename_vars(self.nodups(rs))
                lr = arg_inner._comp.lambda_refs
                cl.push_right(arg_inner._comp)
                cl.push_right(p_inner._comp)
            else:
                rs = zip(arg.lambda_refs, p.lambda_refs)
                arg.rename_vars(self.nodups(rs))
                lr = p_inner._comp.lambda_refs
                cl.push_right(p_inner._comp)
                cl.push_right(arg_inner._comp)
            cl.set_lambda_refs(lr)
            d = cl.unify()
            assert isinstance(d, DrsProduction)
            p_inner.clear()
            arg_inner._comp = d
            d = arg
        else:
            assert not arg.isfunctor
            if self.isarg_left:
                rs = zip(p.lambda_refs, arg.lambda_refs)
                p.rename_vars(self.nodups(rs))
                cl.push_right(arg)
                cl.push_right(p)
            else:
                rs = zip(arg.lambda_refs, p.lambda_refs)
                arg.rename_vars(self.nodups(rs))
                cl.push_right(p)
                cl.push_right(arg)
            cl.set_lambda_refs(arg.lambda_refs)
            d = cl.unify()
            assert isinstance(d, DrsProduction)

        self.clear()
        if 0 != (self.compose_options & CO_PRINT_DERIVATION):
            print('          := %s' % repr(d))
        return d
