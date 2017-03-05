# -*- coding: utf-8 -*-

from drs import DRS, DRSRef, Merge, Prop, Imp, Rel, Neg, Box, Diamond, Or
from drs import get_new_drsrefs
from utils import iterable_type_check, intersect, union, union_inplace, complement, compare_lists_eq, rename_var, \
    remove_dups
from common import SHOW_LINEAR
from ccgcat import Category, CAT_EMPTY, RL_RPASS, RL_LPASS, RL_FA, RL_BA, RL_BC, RL_FC, RL_BX, RL_FX
import weakref

## @{
## @ingroup gconst
## @defgroup CCG to DRS Constants

## Compose option: remove propositions containing single referent in the subordinate DRS.
CO_REMOVE_UNARY_PROPS = 0x1
## Compose option: print derivations to stdout during production
CO_PRINT_DERIVATION = 0x2
## Compose option: verify signature during production
CO_VERIFY_SIGNATURES = 0x4

## Function right argument position
ArgRight = True

## Function left argument position
ArgLeft  = False
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
            self._lambda_refs.alpha_convert(rs)

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

    def purify(self):
        """Purify the underlying DRS instance.

        Returns:
            A Production instance representing purified result.
        """
        return self


class DrsProduction(Production):
    """A DRS production."""
    def __init__(self, drs, properNoun=False):
        """Constructor.

        Args:
            drs: A marbles.ie.drt.DRS instance.
            properNoun: True is a proper noun.
        """
        super(DrsProduction, self).__init__()
        if not isinstance(drs, DRS):
            raise TypeError
        self._drs = drs
        self._nnp = properNoun

    def __repr__(self):
        return self.drs.show(SHOW_LINEAR).encode('utf-8')

    def __str__(self):
        return self.__repr__()

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

    def rename_vars(self, rs):
        """Perform alpha conversion on the production data.

        Args:
            rs: A list of tuples, (old_name, new_name).
        """
        self._drs = self._drs.alpha_convert(rs)
        self._drs = self._drs.substitute(rs)
        self.rename_lambda_refs(rs)

    def purify(self):
        """Purify the underlying DRS instance.

        Returns:
            A Production instance representing purified result.
        """
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
        return '<' + '##'.join([repr(x) for x in self._compList]) + '>'

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
        """Merge subordinate ProductionList's into the current list."""
        compList = []
        for d in self._compList:
            if d.isempty:
                continue
            if isinstance(d, ProductionList):
                d = d.apply()
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

    def apply_forward(self, enableException=False):
        """Applies all functors. The list size should reduce."""
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

    def apply_reverse(self, enableException=False):
        """Applies all functors. The list size should reduce."""
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
                xrs = zip(rn, get_new_drsrefs(rn, universe))
                d.rename_vars(xrs)
                for j in range(0, i):
                    ml[j].rename_vars(xrs)
            universe = union(universe, d.universe)

        refs = []
        conds = []
        proper = len(ml) != 0
        for d in ml:
            proper = proper and d.isproper_noun
            refs.extend(d.drs.referents)
            conds.extend(d.drs.conditions)
        if proper:
            # Hyphenate name
            if len(refs) != 1 or any(filter(lambda x: not isinstance(x, Rel) or len(x.referents) != 1, conds)):
                raise DrsComposeError('bad proper noun in DRS condition')
            name = '-'.join([c.relation.to_string() for c in conds])
            conds = [Rel(name,refs)]

        drs = DRS(refs, conds).purify()
        d = DrsProduction(drs, proper)
        d.set_lambda_refs(self.lambda_refs)
        d.set_category(self.category)
        return d

    def apply(self, rule=None):
        """Applications based on rule.

        Args:
            rule: A marbles.ie.drt.ccgcat.Rule instance.

        Returns:
            A Production instance.
        """
        if rule is None:
            reverse = True
        elif rule in [RL_RPASS, RL_BA]:
            reverse = True
        elif rule in [RL_LPASS, RL_FA]:
            reverse = False
        else:
            # TODO: handle all rules
            raise NotImplementedError
        if len(self._compList) == 0:
            return None

        # alpha convert variables
        self.flatten()
        if reverse:
            self.apply_reverse()
        else:
            self.apply_forward()

        if len(self._compList) == 1:
            d = self._compList[0]
            self._compList = []
            if d.isfunctor:
                d.local_scope.set_category(self.category)
            else:
                d.set_category(self.category)
            return d
        return self


class FunctorProduction(Production):
    """A functor production. All functors are curried."""
    def __init__(self, category, referent, production=None):
        super(FunctorProduction, self).__init__(category)
        if production is not None:
            if isinstance(production, (DRS, Merge)):
                production = DrsProduction(production)
            elif not isinstance(production, Production):
                raise TypeError('Function argument must be a Production type')
        if category is None :
            raise TypeError('category cannot be None for functors')
        self._comp = production
        self._category = category
        if isinstance(referent, list):
            self._drsref = DRS(referent, [])
        else:
            self._drsref = DRS([referent], [])
        self._outer = None
        if self._comp is not None:
            if isinstance(self._comp, FunctorProduction):
                self._comp.set_outer(self)

    def set_outer(self, outer):
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
        r = ','.join([x.var.to_string() for x in self._drsref.referents])
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

    def __str__(self):
        return self.__repr__()

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
        u.extend(self._drsref.referents)
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
    def local_lambda_refs(self):
        """Get the referents that will be resolved after a call to apply(). """
        return self.local_scope._drsref.universe

    @property
    def signature(self):
        """Get the functor signature."""
        return self.local_scope._category.drs_signature

    @property
    def global_scope(self):
        """Get the outer most functor in this production or self.

        See Also:
            local_scope()
        """
        g = self
        while g.outer is not None:
            g = g.outer
        return g

    @property
    def local_scope(self):
        """Get the inner most functor in this production or self.

        See Also:
            global_scope()
        """
        c = self._comp
        cprev = self
        while c is not None and c.isfunctor:
            cprev = c
            c = c._comp
        return cprev

    @property
    def category(self):
        """The CCG category"""
        return self.local_scope._category

    @property
    def outer(self):
        """The outer functor or None."""
        return None if self._outer is None else self._outer() # weak deref

    @property
    def isempty(self):
        """Test if the production prduces an empty DRS."""
        return self._drsref.isempty and (self._comp is None or self._comp.isempty)

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
        """Get the lambda function referents"""
        # Get unique referents, ordered by functor scope
        # Reverse because we can have args [(x,e), (y,e), e] =>[x,e,y,e,e] => [x,y,e]
        r = self._get_lambda_refs([])
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
        self._drsref = self._drsref.alpha_convert(rs)
        if self._comp is not None:
            self._comp.rename_vars(rs)

    def unify(self):
        """Finalize the production by performing a unify right to left.

        Returns:
            A Production instance.
        """
        if self._comp is not None:
            lr = self._comp.lambda_refs
            if self._comp.isfunctor:
                self._comp = self._comp.unify()
            else:
                # Make sure we don't change scoping after unifying combinators.
                cat = self.category.result_category
                d = self._comp.unify()
                if d.isfunctor:
                    fr = d.freerefs
                    fr = complement(fr, self.universe)
                    if len(fr) == 0:
                        # Remove functor since unification is complete
                        self._comp = d.local_scope._comp
                        assert not self._comp.isfunctor
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
        d = DrsProduction(DRS(self._drsref.universe, []))
        d = self.apply(d)
        return d

    def clear(self):
        self._comp = None
        self._drsref = DRS([], [])
        self.set_outer(None)

    def apply(self, arg):
        """Function application if arg is a DrsProduction or ProductionList. Otherwise functor production.

        Arg:
            The substitution argument.

        Returns:
            A Production instance.
        """
        if self._comp is not None and self._comp.isfunctor:
            self._comp = self._comp.apply(arg)
            if self._comp.isfunctor:
                self._comp.set_outer(self)
            return self

        if 0 != (self.compose_options & CO_PRINT_DERIVATION):
            print('DERIVATION:= %s {%s=%s}' % (repr(self.global_scope), chr(ord('P')+self._get_position()), repr(arg)))

        # Alpha convert (old,new)
        alr = arg.lambda_refs
        if len(alr) == 0:
            alr = arg.universe
        slr = self.lambda_refs
        sllr = self.local_lambda_refs
        if len(sllr) == 1 and len(alr) != 1 and not arg.isfunctor:
            # Add proposition
            p = PropProduction(Category('PP/NP'), slr[0])
            arg = p.apply(arg)
            alr = arg.lambda_refs

        rs = zip(alr, slr)
        # Make sure names don't conflict with global scope
        ors = intersect(alr[len(rs):], complement(self.global_scope.lambda_refs, slr))
        if len(ors) != 0:
            xrs = zip(ors, get_new_drsrefs(ors, union(alr, slr)))
            arg.rename_vars(xrs)
        arg.rename_vars(rs)

        rn = intersect(arg.universe, self.universe)
        if len(rn) != 0:
            # FIXME: should we allow this or hide behind propositions
            # Alpha convert bound vars in both self and arg
            xrs = zip(rn, get_new_drsrefs(rn, union(arg.lambda_refs, slr)))
            arg.rename_vars(xrs)

        if arg.isfunctor:
            # functor production
            if arg.iscombinator:
                # Can't handle at the moment
                raise DrsComposeError('Combinators arguments %s for combinators %s not supported' %
                                      (arg.signature, self.signature))
            cl = ProductionList()
            cl.set_options(self.compose_options)

            # Apply the combinator
            if self._comp is not None:
                arg_comp = arg.local_scope._comp
                # Carry forward lambda refs to combinator scope
                lr = self._comp.lambda_refs
                uv = self._comp.universe
                uv = filter(lambda x: x in uv, lr) # keep lambda ordering
                if self._category.isarg_right:
                    lr = union_inplace(lr, arg.global_scope.lambda_refs)
                else:
                    lr = union_inplace(arg.global_scope.lambda_refs, lr)
                lr = complement(lr, uv)
                lr.extend(uv)
                cl.set_lambda_refs(lr)

                # Set arg lambdas, the ordering will be different to above
                uv = [] if arg_comp is None else complement(lr, arg.lambda_refs)
                lr = [] if arg_comp is None else arg_comp.lambda_refs
                lr = union_inplace(lr, uv)

                if arg_comp is None:
                    arg.local_scope._comp = self._comp
                elif self.isarg_left:
                    cl2 = ProductionList()
                    cl2.push_right(arg_comp, merge=True)
                    cl2.push_right(self._comp, merge=True)
                    cl2.set_lambda_refs(lr)
                    arg.local_scope._comp = cl2
                else:
                    cl2 = ProductionList()
                    cl2.push_right(self._comp, merge=True)
                    cl2.push_right(arg_comp, merge=True)
                    cl2.set_lambda_refs(lr)
                    arg.local_scope._comp = cl2

            cl.set_category(self.category.result_category)
            cl.push_right(arg, merge=True)
            outer = self.outer
            self.clear()
            if 0 != (self.compose_options & CO_PRINT_DERIVATION):
                print('          := %s' % repr(cl if outer is None else outer.global_scope))

            if outer is None and cl.contains_functor:
                cl = cl.unify()

            return cl

        # functor application
        if self._comp is not None and arg.contains_functor:
            raise DrsComposeError('Invalid functor placement during functor application')

        # Remove resolved referents from lambda refs list
        lr = complement(self.lambda_refs, self.local_lambda_refs)
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
        #c = c.apply()
        c.set_lambda_refs(lr)
        c.set_category(self.category.result_category)
        self.clear()

        if 0 != (self.compose_options & CO_PRINT_DERIVATION):
            print('          := %s' % repr(c))

        return c


class PropProduction(FunctorProduction):
    """A proposition functor."""
    def __init__(self, position, referent, production=None):
        super(PropProduction, self).__init__(position, referent)

    def _repr_helper2(self, i):
        v = chr(i)
        r = self._drsref.referents[0].var.to_string()
        return '[%s| %s: %s(*)]' % (r, r, v)

    @property
    def freerefs(self):
        """Get the free referents. Always empty for a proposition."""
        return []

    @property
    def universe(self):
        """Get the universe of the referents."""
        return self._drsref.universe

    def apply_null_left(self):
        """It is an error to call this method for propositions"""
        raise DrsComposeError('cannot apply null left to a proposition functor')

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
                self._comp.set_outer(self)
            return self

        if 0 != (self.compose_options & CO_PRINT_DERIVATION):
            print('DERIVATION:= %s {%s=%s}' % (repr(self.global_scope), chr(ord('P')+self._get_position()), repr(arg)))
        if not isinstance(arg, ProductionList):
            arg = ProductionList([arg])
        d = arg.apply()
        assert isinstance(d, DrsProduction)
        # FIXME: removing proposition from a proper noun causes an exception during ProductionList.apply()
        if (self.compose_options & CO_REMOVE_UNARY_PROPS) != 0 and len(d.drs.referents) == 1 and not d.isproper_noun:
            rs = zip(d.drs.referents, self._drsref.referents)
            d.rename_vars(rs)
            d.set_options(self.compose_options)
            g = self.global_scope
            self.clear()
            d.set_lambda_refs(g.lambda_refs)
            if 0 != (self.compose_options & CO_PRINT_DERIVATION):
                print('          := %s' % repr(d))
            return d
        dd = DrsProduction(DRS(self._drsref.referents, [Prop(self._drsref.referents[0], d.drs)]))
        dd.set_options(self.compose_options)
        g = self.global_scope
        self.clear()
        dd.set_lambda_refs(g.lambda_refs)
        if 0 != (self.compose_options & CO_PRINT_DERIVATION):
            print('          := %s' % repr(dd))
        return dd
