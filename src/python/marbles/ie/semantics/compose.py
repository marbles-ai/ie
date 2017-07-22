# -*- coding: utf-8 -*-
"""Compositional DRT"""

from __future__ import unicode_literals, print_function

import collections
import weakref

from marbles.ie.ccg import Category, CAT_EMPTY, CAT_NP, CAT_PPNP
from marbles.ie.drt.common import SHOW_LINEAR
from marbles.ie.drt.drs import AbstractDRS, DRS, DRSRef, get_new_drsrefs
from marbles.ie.drt.utils import iterable_type_check, intersect, union, remove_dups
from marbles import safe_utf8_encode, future_string, UNICODE_STRINGS
from marbles.ie.core.constants import *
from marbles.ie.core.sentence import Span


_FCHR = u'p'


class DrsComposeError(Exception):
    """AbstractProduction Error."""
    pass


def unify_vars(f, g, rs):
    pass



def identity_functor(category, refs=None):
    """Return the identity functor `λx.P(x) or λx.P(y)`.

    Args:
        category: A functor category where the result and argument are atoms.
        refs: optional DRSRef's to use as identity referents.

    Returns:
        A FunctorProduction instance.

    Remarks:
        This can be used for atomic unary rules.
    """
    assert category.result_category().isatom
    assert category.argument_category().isatom
    d = DrsProduction([], [], category=category.result_category())
    if refs is None:
        refs = [DRSRef('X1')]
        d.set_lambda_refs(refs)
        return FunctorProduction(category, refs, d)
    elif not isinstance(refs, collections.Iterable):
        d.set_lambda_refs([refs])
        return FunctorProduction(category, [refs], d)
    else:
        d.set_lambda_refs([refs[-1]])
        return FunctorProduction(category, refs[0:-1], d) if len(refs) > 1 else FunctorProduction(category, [refs[0]], d)


def can_unify_refs(d1, r1, d2, r2):
    return not (r1 in d1.universe and r2 in d2.universe)


class AbstractProduction(object):
    """An abstract production."""
    def __init__(self, category=None):
        self._lambda_refs = None
        self._options = 0
        if category is None:
            self._category = CAT_EMPTY
        elif isinstance(category, Category):
            self._category = category
        else:
            raise TypeError('category must be instance of Category')

    def __eq__(self, other):
        return id(self) == id(other)

    def __repr__(self):
        return unicode(self) if UNICODE_STRINGS else str(self)

    def get_raw_variables(self):
        raise NotImplementedError

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
    def ismodifier(self):
        """A modifier expects a functor as the argument and returns a functor of the same type."""
        return False

    @property
    def universe(self):
        """Get the universe of the referents."""
        raise NotImplementedError

    @property
    def referents(self):
        """Get the universe of the referents."""
        return self.universe

    @property
    def variables(self):
        """Get the variables."""
        raise NotImplementedError

    @property
    def freerefs(self):
        """Get the free referents."""
        raise NotImplementedError

    @property
    def islambda_inferred(self):
        """Test if the lambda referents are inferred from the production data."""
        return self.isfunctor or self._lambda_refs is None

    @property
    def lambda_refs(self):
        """Get the lambda function referents"""
        return self._lambda_refs.universe if self._lambda_refs is not None else []

    @property
    def indexes(self):
        raise NotImplementedError

    @property
    def compose_options(self):
        """Get the compose options."""
        return self._options

    @property
    def contains_functor(self):
        """If a list then return true if the list contains 1 or more functors, else returns isfunctor()."""
        return self.isfunctor

    @staticmethod
    def make_new_drsrefs(ors, ers):
        return get_new_drsrefs(ors, ers)

    def size(self):
        """If a list then get the number of elements in the production list else return 1."""
        return 1

    def get_scope_count(self):
        """Get the number of scopes in a functor. Zero for non functor types"""
        return 0

    def set_category(self, cat):
        """Set the CCG category.

        Args:
            cat: A Category instance.
        """
        self._category = cat

    def set_options(self, options):
        """Set the compose options.

        Args:
            options: The compose options.
        """
        self._options = int(options or 0)

    def set_lambda_refs(self, refs):
        """Set the lambda referents for this production.

        Args:
            refs: The lambda referents.
        """
        if refs is None:
            self._lambda_refs = None
        else:
            self._lambda_refs = DRS(refs, [])

    def rename_lambda_refs(self, rs):
        """Perform alpha conversion on the lambda referents.

        Args:
            rs: A list of tuples, (old_name, new_name).
        """
        assert 0 == (self.compose_options & CO_FAST_RENAME)
        if self._lambda_refs is not None:
            self._lambda_refs = self._lambda_refs.alpha_convert(rs)

    def rename_vars(self, rs, other=None):
        """Perform alpha conversion on the production data.

        Args:
            rs: A list of tuples, (old_name, new_name).
            other: Optional production containing new variables.
        """
        raise NotImplementedError

    def fast_rename_vars(self, rs, other=None):
        """Fast version of rename_vars().

        Args:
            rs: A list of tuples, (old_name, new_name).
            other: Optional production containing new variables.
        """
        #assert 0 != (self.compose_options & CO_FAST_RENAME)
        vs = self.get_raw_variables()
        vm = {}
        for x in rs:
            vm.setdefault(x[0].var.to_string(), x[1])
        xrs = None
        if len(vm) != len(rs):
            # duplicate old names
            xrs = map(lambda y: (y[1], vm[x[0].var.to_string()]), filter(lambda x: vm[x[0].var.to_string()] != x[1], rs))
            if len(xrs) != 0:
                if other is not None:
                    assert 0 == len(set(vs).intersection(map(lambda x: x[0], xrs)))
                    ovs = other.get_raw_variables()
                    if 0 == len(set(ovs).intersection(map(lambda x: x[0], xrs))):
                        pass
                    assert 0 != len(set(ovs).intersection(map(lambda x: x[0], xrs)))
            else:
                xrs = None
        for v in vs:
            try:
                n = vm[v.var.to_string()]
            except Exception:
                continue
            v.set_var(n.var)
        if xrs:
            if other is not None:
                other.fast_rename_vars(xrs, None)
            else:
                self.fast_rename_vars(xrs, None)

    def unify(self):
        """Perform a unification.

        Returns:
            A AbstractProduction instance representing unified result.
        """
        return self

    def verify(self):
        """Test helper."""
        return True

    def make_vars_disjoint(self, arg):
        """Make variable names disjoint. This is always done before unification.

        Remarks:
            For functors should only call from outer scope.
        """
        ers = arg.variables
        ers2 = self.variables
        ors = intersect(ers, ers2)
        if len(ors) != 0:
            nrs = self.make_new_drsrefs(ors, union(ers, ers2))
            xrs = zip(ors, nrs)
            self.rename_vars(xrs)

    def union_span(self, other):
        raise NotImplementedError


class DrsProduction(AbstractProduction):
    """A DRS production."""
    def __init__(self, universe, freerefs, category=None, span=None):
        """Constructor.

        Args:
            universe: The universe of bound referents.
            freerefs: The free referents.
            category: The category.
            span: The sentence span.
        """
        super(DrsProduction, self).__init__(category)
        if not isinstance(universe, list) or not iterable_type_check(universe, DRSRef):
            raise TypeError('DrsProduction expects universe of referents')
        if not isinstance(freerefs, list) or not iterable_type_check(freerefs, DRSRef):
            raise TypeError('DrsProduction expects freerefs of referents')
        self._universe = []
        self._freerefs = []
        self._freerefs.extend(universe)
        self._freerefs.extend(freerefs)

        #self._freerefs = freerefs
        #self._universe = universe
        self._span = span

    def __unicode__(self):
        lr = [unicode(r.var) for r in self.lambda_refs]
        if self._span is not None and len(self._span) != 0:
            # Span repr include DRS representation
            fn = unicode(self.span.get_drs().show(SHOW_LINEAR))
        else:
            fn = u'f(' + ','.join([unicode(u.var) for u in self.universe]) + u'| ' + \
                 u','.join([unicode(v.var) for v in self.freerefs]) + u')'
        if len(lr) == 0:
            return fn
        return u'λ' + u'λ'.join(lr) + u'.' + fn

    def __str__(self):
        return safe_utf8_encode(self.__unicode__())

    def get_raw_variables(self):
        """Get the variables. Both free and bound referents are returned.

        Remarks:
            Duplicates are not removed. This is required for fast_rename_vars().
        """
        u = [x for x in self._universe]
        u.extend(self._freerefs)
        u.extend(self.lambda_refs)
        if self.span is not None:
            for x in self.span:
                if x.refs is not None:
                    u.extend(x.refs)
        return [v for v in dict([(id(x), x) for x in u]).itervalues()]

    @property
    def universe(self):
        """Get the universe of the referents."""
        return sorted(set(self._universe))

    @property
    def referents(self):
        """Get the universe of the referents."""
        return sorted(set(self._universe))

    @property
    def variables(self):
        """Get the variables. Both free and bound referents are returned."""
        return sorted(set(self._universe).union(self._freerefs).union(self.lambda_refs))

    @property
    def freerefs(self):
        """Get the free referents."""
        return [x for x in self._freerefs]

    @property
    def indexes(self):
        return [x for x in self._span] if self._span else []

    @property
    def span(self):
        return self._span

    @span.setter
    def span(self, value):
        assert isinstance(value, Span)
        self._span = value

    @property
    def isempty(self):
        """Test if the production is an empty DRS."""
        return len(self._universe) == 0 and len(self._freerefs) == 0

    def verify(self):
        """Test helper."""
        if len(self.lambda_refs) != 1 or not self.category.isatom:
            pass
        return len(self.lambda_refs) == 1 and self.category.isatom

    def rename_vars(self, rs, other=None):
        """Perform alpha conversion on the production data.

        Args:
            rs: A list of tuples, (old_name, new_name).
            other: Optional production containing new variables.
        """
        if len(rs) == 0:
            return
        self.fast_rename_vars(rs, other)
        return

    def union_span(self, other):
        if self._span is None:
            self._span = other
        elif other is not None:
            self._span = self._span.union(other)


class ProductionList(AbstractProduction):
    """A list of productions."""

    def __init__(self, compList=None, category=None):
        super(ProductionList, self).__init__(category)
        if compList is None:
            compList = collections.deque()
        if isinstance(compList, AbstractDRS):
            compList = collections.deque([DrsProduction(compList)])
        elif isinstance(compList, AbstractProduction):
            compList = collections.deque([compList])
        elif not iterable_type_check(compList, AbstractProduction):
            raise TypeError('DrsProduction construction')
        elif not isinstance(compList, collections.deque):
            compList = collections.deque(compList)
        self._compList = compList

    def __unicode__(self):
        lr = [unicode(r.var) for r in self.lambda_refs]
        if len(lr) == 0:
            return u'[' + ';'.join([unicode(x) for x in self._compList]) + u']'
        return u'λ' + u'λ'.join(lr) + u'.[' + u';'.join([unicode(x) for x in self._compList]) + u']'

    def __str__(self):
        return safe_utf8_encode(self.__unicode__())

    def get_raw_variables(self):
        u = self.lambda_refs
        for d in self._compList:
            u.extend(d.get_raw_variables)
        return u

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
        u = set(self.lambda_refs)
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
    def indexes(self):
        """Get the indexes."""
        u = set()
        for d in self._compList:
            u = u.union(d.indexes)
        return sorted(u)

    @property
    def isempty(self):
        """Test if the production results in an empty DRS."""
        return len(self._compList) == 0 or all([x.isempty for x in self._compList])

    @property
    def contains_functor(self):
        for c in self._compList:
            if c.contains_functor:
                return True
        return False

    def size(self):
        """Get the number of elements in this production list."""
        return len(self._compList)

    def flatten(self):
        """Unify subordinate ProductionList's into the current list."""
        compList = collections.deque()
        for d in self._compList:
            if d.isempty and (d.span is None or d.span.isempty):
                continue    # removes punctuation
            if isinstance(d, ProductionList):
                d = d.unify()
                if isinstance(d, ProductionList):
                    compList.extend(d._compList)
                else:
                    compList.append(d)
            else:
                compList.append(d)
        self._compList = compList
        return self

    def rename_vars(self, rs, other=None):
        """Perform alpha conversion on the production data.

        Args:
            rs: A list of tuples, (old_name, new_name).
            other: Optional production containing new variables.
        """
        if len(rs) == 0:
            return
        if 0 == (self.compose_options & CO_FAST_RENAME):
            self.rename_lambda_refs(rs)
            for d in self._compList:
                d.rename_vars(rs)
        else:
            self.fast_rename_vars(rs, other)

    def push_right(self, other, merge=False):
        """Push an argument to the right of the list.

        Args:
            other: The argument to push.
            merge: True if other is a ProductionList instance and you want to
            merge lists (like extend). If False other is added as is (like append).

        Returns:
            The self instance.
        """
        if not isinstance(other, AbstractProduction):
            raise TypeError('production list entries must be productions')
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
        if not isinstance(other, AbstractProduction):
            raise TypeError('production list entries must be productions')
        if merge and isinstance(other, ProductionList):
            self._compList.extendleft(reversed(other._compList))
        else:
            other.set_options(self.compose_options)
            self._compList.appendleft(other)
        return self

    def unify(self):
        """Finalize the production by performing a unification right to left.

        Returns:
            A AbstractProduction instance.
        """
        ml = [x.unify() for x in self._compList]
        self._compList = collections.deque()
        sps = [x.span for x in filter(lambda z: z.span is not None and z.isempty, ml)]
        sp = None if len(sps) == 0 else reduce(lambda x, y: x.union(y), sps)
        empty = filter(lambda x: x.isempty, ml)
        ml = filter(lambda x: not x.isempty, ml)
        if len(ml) == 1:
            # FIXME: Should never infer.
            if not self.islambda_inferred:
                ml[0].set_lambda_refs(self.lambda_refs)
            # Unary type changes require we set here
            ml[0].set_category(self.category)
            ml[0].set_options(self.compose_options)
            ml[0].union_span(sp)
            return ml[0]
        elif any(filter(lambda x: x.contains_functor, ml)):
            self._compList.extend(ml)
            return self

        # Always unify reversed
        universe = set()
        sentence = None
        for i in reversed(range(len(ml))):
            d = ml[i]
            if d.span is not None:
                sentence = d.span.sentence
            rn = universe.intersection(d.universe)
            if len(rn) != 0:
                # FIXME: should this be allowed?
                # Alpha convert bound vars in both self and arg
                xrs = zip(rn, d.make_new_drsrefs(sorted(rn), sorted(universe)))
                # Rename so variable subscripts increase left to right
                for m in ml[i+1:]:
                    m.rename_vars(xrs, m)
            universe = universe.union(d.universe)

        # Merge indexes
        span = Span(sentence) if sentence is not None else None
        freerefs = []
        universe = []
        for d in ml:
            assert d.span is None or d.span.sentence is sentence
            span = span.union(d.span) if span is not None else None
            universe.extend(d._universe)
            freerefs.extend(d._freerefs)

        d = DrsProduction(universe, freerefs, category=self.category, span=span)
        if not self.islambda_inferred:
            d.set_lambda_refs(self.lambda_refs)
        elif len(ml) != 0 and not ml[0].islambda_inferred:
            d.set_lambda_refs(ml[0].lambda_refs)
        elif len(ml) == 0 and len(empty) != 0:
            # Add a lambda just in-case, can choose any
            d.set_lambda_refs(empty[0].lambda_refs)

        d.set_options(self.compose_options)
        return d

    def union_span(self, other):
        pass


class FunctorProduction(AbstractProduction):
    """A functor production. Functors are curried where the inner most functor is the inner scope."""
    def __init__(self, category, referent, production=None):
        """Constructor.

        Args:
            category: A marbles.ie.drt.ccgcat.Category instance.
            referent: Either a list of, or a single, marbles.ie.drt.drs.DRSRef instance.
            production: Optionally an AbstractProduction instance. If production is a functor then the combination
                is a curried functor.
        """
        if production is not None and not isinstance(production, (DrsProduction, FunctorProduction)):
            raise TypeError('production argument must be a AbstractProduction type')
        if category is None :
            raise TypeError('category cannot be None for functors')
        super(FunctorProduction, self).__init__(category)
        self._comp = production
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
        s = u'λ' + unichr(i)
        if self._comp is not None and self._comp.isfunctor:
            s = self._comp._repr_helper1(i+1) + s
        return s

    def _repr_helper2(self, i):
        v = unichr(i)
        r = u','.join([unicode(x.var) for x in self._lambda_refs.referents])
        if self._comp is not None:
            if self._comp.isfunctor:
                s = self._comp._repr_helper2(i+1)
            else:
                s = unicode(self._comp)
            if self._category.isarg_right:
                return u'%s;%s(%s)' % (s, v, r)
            else:
                return u'%s(%s);%s' % (v, r, s)
        else:
            return u'%s(%s)' % (v, r)

    def __unicode__(self):
        global _FCHR
        return self._repr_helper1(ord(_FCHR)) + ''.join([u'λ'+unicode(v.var) for v in self.lambda_refs]) \
               + u'.<' + self._repr_helper2(ord(_FCHR)) + u'>'

    def __str__(self):
        return safe_utf8_encode(self.__unicode__())

    def _get_variables(self, u):
        if self._comp is not None:
            if self._comp.isfunctor:
                u = self._comp._get_variables(u)
            else:
                u.extend(self._comp.get_raw_variables())
        return u

    def _get_freerefs(self, u):
        if self._comp is not None:
            if self._comp.isfunctor:
                u = self._comp._get_freerefs(u)
            else:
                u = u.union(self._comp.freerefs)
        return u

    def _get_universe(self, u):
        if self._comp is not None:
            if self._comp.isfunctor:
                u = self._comp._get_universe(u)
            else:
                u = u.union(self._comp.universe)
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

    def get_raw_variables(self):
        return self._get_variables(self.lambda_refs)

    @property
    def outer_scope(self):
        """Get the outer most functor in this production or self.

        See Also:
            FunctorProduction.inner_scope
            FunctorProduction.outer
        """
        g = self
        while g.outer is not None:
            g = g.outer
        return g

    @property
    def indexes(self):
        inner = self.inner_scope
        return [] if inner._comp is None else inner._comp.indexes

    @property
    def inner_scope(self):
        """Get the inner most functor in this production or self.

        See Also:
            FunctorProduction.outer_scope
            FunctorProduction.inner
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
            FunctorProduction.outer_scope
        """
        return None if self._outer is None else self._outer() # weak deref

    @property
    def inner(self):
        """The immediate inner functor or None.

        See Also:
            FunctorProduction.inner_scope
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
        u = self._get_variables(self.lambda_refs)
        return sorted(set(u))

    @property
    def freerefs(self):
        """Get the free referents."""
        return sorted(self._get_freerefs(set()))

    @property
    def universe(self):
        """Get the universe of the referents."""
        return sorted(self._get_universe(set()))

    @property
    def lambda_refs(self):
        """Get the lambda functor referents. These are the referents that can be bound with during unification.

        See Also:
            get_unify_scopes()
        """
        # Get unique referents, ordered by functor scope
        r = self._get_lambda_refs([])
        # Reverse because we can have args:
        # - [(x,e), (y,e), e] => [x,e,y,e,e] => [x,y,e]
        # - [e, (x, e)] => [e, x, e] => [x,e]
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
        """A combinator expects a functor as the argument and returns a functor of a different category."""
        return self.category.iscombinator

    @property
    def ismodifier(self):
        """A modifier expects a functor as the argument and returns a functor of the same category."""
        return self.category.ismodifier

    @property
    def span(self):
        fn = self.inner_scope
        return None if fn._comp is None else fn._comp.span

    def union_span(self, other):
        fn = self.inner_scope
        if fn._comp is not None:
            fn._comp.union_span(other)

    def unify_atoms(self, a, b):
        """Unify two atoms: a and b.

        Args:
            a: A DrsProduction instance or ProductionList instance.
            b: A DrsProduction instance or ProductionList instance.

        Returns:
            The unified result.
        """
        if isinstance(a, ProductionList):
            a.push_right(b)
            a.flatten()
            return a.unify()
        elif isinstance(b, ProductionList):
            b.push_left(a)
            b.flatten()
            return b.unify()
        else:
            assert isinstance(a, DrsProduction)
            assert isinstance(b, DrsProduction)
            pl = ProductionList()
            pl.set_options(self.compose_options)
            pl.push_right(a)
            pl.push_right(b)
            pl.flatten()
            return pl.unify()

    def get_scope_count(self):
        """Get the number of scopes in a functor. Zero for non functor types"""
        return self.inner_scope._get_position() + 1

    def get_unify_scopes(self, follow=True):
        """Get lambda vars ordered by functor scope.

        Args:
            follow: If True, return refs for argument and result functors recursively. If false just return the refs
                for the functor.

        See Also:
            marbles.ie.drt.ccgcat.Category.extract_unify_atoms()
        """
        # When the inner_scope is applied it removes the argument category, and returns the result category.
        # When outer_scope is applied it returns the final result category.
        # Want same ordering as extract_unify_atoms()
        if follow:
            atoms = []
            atoms.append(self._lambda_refs.referents)
            c = self._comp
            while c is not None and c.isfunctor:
                atoms.append(c._lambda_refs.referents)
                c = c._comp
            atoms.reverse()
            if c is not None:
                assert(len(c.lambda_refs) <= 1)     # final result must be a atom
                atoms.append(c.lambda_refs)
            return atoms
        else:
            atoms = []
            u = self._lambda_refs.universe
            u.reverse()
            atoms.extend(u)
            c = self._comp
            while c is not None and c.isfunctor:
                u = c._lambda_refs.universe
                u.reverse()
                atoms.extend(u)
                c = c._comp
            atoms.reverse()
            if c is not None:
                assert len(c.lambda_refs) <= 1  # final result must be a atom
                atoms.extend(c.lambda_refs)
            return atoms

    def verify(self):
        """Test helper."""
        # functor application
        inscope = self.inner_scope
        if inscope._comp is not None and inscope._comp.contains_functor:
            return False

        atoms = inscope.category.extract_unify_atoms()
        lrefs = self.get_unify_scopes()
        if len(lrefs) != len(atoms):
            return False
        for la, lr in zip(atoms, lrefs):
            if len(la) != len(lr):
                return False
        return inscope._comp.verify()

    def clear(self):
        self._comp = None
        self._lambda_refs = DRS([], [])
        self._set_outer(None)

    def set_lambda_refs(self, refs):
        """Disabled for functors"""
        pass

    def set_category(self, cat):
        """Set the CCG category.

        Args:
            cat: A Category instance.
        """
        prev = self._category
        assert cat.isfunctor
        if self._comp is not None:
            if self._comp.isfunctor:
                cat = self._comp.set_category(cat).result_category()
            else:
                self._comp.set_category(cat.extract_unify_atoms(False)[-1])

        self._category = cat
        # sanity check

        # FIXME: This check can fail for rules FX, FC, BX, BC. At the moment we dont use this method for those rules.
        if (cat.isarg_left and prev.isarg_right) or (cat.isarg_right and prev.isarg_left):
            raise DrsComposeError('Signature %s does not match %s argument position, prev was %s' %
                                 (cat, 'right' if prev.isarg_right else 'left', prev))
        return cat

    def set_options(self, options):
        """Set the compose options.

        Args:
            options: The compose options.
        """
        # Pass down options to nested functor
        super(FunctorProduction, self).set_options(options)
        if self._comp is not None:
            self._comp.set_options(options)

    def rename_vars(self, rs, other=None):
        """Perform alpha conversion on the production data.

        Args:
            rs: A list of tuples, (old_name, new_name).
            other: Optional production containing new variables.
        """
        if len(rs) == 0:
            return
        self.fast_rename_vars(rs, other)
        return
        #if 0 == (self.compose_options & CO_FAST_RENAME):
        #    self.rename_lambda_refs(rs)
        #    if self._comp is not None:
        #        self._comp.rename_vars(rs)
        #else:
        #    self.fast_rename_vars(rs, other)

    def unify(self):
        """Finalize the production by performing a unify right to left.

        Returns:
            self
        """
        if self._comp is not None:
            self._comp = self._comp.unify()
        return self

    def apply_null_left(self):
        """Apply a null left argument `$` to the functor. This is necessary for processing
        the imperative form of a verb.

        Returns:
            A AbstractProduction instance.
        """
        # TODO: Check if we have a proper noun accessible to the right and left
        if self.isarg_right or self._comp is None or self._comp.isfunctor:
            raise DrsComposeError('invalid apply null left to functor')
        if self._comp is not None and isinstance(self._comp, ProductionList):
            self._comp = self._comp.apply()
        d = DrsProduction(universe=self._lambda_refs.universe, freerefs=[], category=CAT_NP)
        d = self.apply(d)
        return d

    def pop(self, level=-1):
        """Remove an inner functor and return the production.

        Args:
            level: Level relative to outer less 1. If -1 then pop the inner scope.

        Returns:
            A AbstractProduction instance.

        Remarks:
            An instance of self is never returned since the true level is always +1.
        """
        if self._comp is None:
            # pop functor
            if self.outer is None:
                return None
            self.outer._comp = None
            self._set_outer(None)
            return self
        elif not self._comp.isfunctor or level == 0:
            c = self._comp
            self._comp = None
            return c

        # tail recursion
        return self._comp.pop(level - 1)

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
        ers = arg.variables
        ers2 = self.variables
        ors = intersect(ers, ers2)
        if len(ors) != 0:
            nrs = self.make_new_drsrefs(ors, union(ers, ers2))
            xrs = zip(ors, nrs)
            self.rename_vars(xrs)

    def type_change_np_snp(self, np):
        """Special type change. See LDC manual section 3.7.2.

        Args:
            np: The noun phrase. Must be a NP category.

        Remarks:
            self is a template. The inner DrsProduction will be discarded.
        """
        self.make_vars_disjoint(np)
        slr = self.inner_scope._comp.lambda_refs
        assert isinstance(np, DrsProduction)
        lr = np.lambda_refs
        if len(lr) == 0:
            lr = np.universe
            np.set_lambda_refs(lr)
        if len(lr) != len(slr):
            if len(slr) != 1:
                raise DrsComposeError('mismatch of lambda vars when doing special type change')
            # Add proposition
            p = PropProduction(category=np.category, referent=slr[0])
            np = p.apply(np)
        else:
            rs = zip(slr, lr)
            self.rename_vars(rs)

        x = self.pop() # discard inner DrsProduction
        np.set_category(x.category)
        self.push(np)
        return self

    def type_raise(self, g):
        """Type raise

        Args:
            np: The argument category.

        Remarks:
            self is a template. The inner DrsProduction will be discarded.
        """
        ## Forward   X:g => T/(T\X): λxf.f(g)
        ## Backward  X:g => T\(T/X): λxf.f(g)
        self.make_vars_disjoint(g)
        # Remove T vars from unify scope but maintain ordering
        fU = self.get_unify_scopes(True)
        fT = set()
        for u in fU[1:]:
            fT = fT.union(u)
        fX = filter(lambda x: x not in fT, fU[0])
        rs = zip(fX, g.lambda_refs)
        self.rename_vars(rs)

        fc = self.pop()
        if g.isfunctor:
            g = g.pop()
        g.set_lambda_refs(fc.lambda_refs)
        self.push(g)
        return self

    def compose(self, g):
        """Function Composition.

        Arg:
            g: The Y|Z functor where self (f) is the X|Y functor.

        Returns:
            An AbstractProduction instance.

        Remarks:
            CALL[X|Y](Y|Z)
            - Backward Composition = `Y\Z:g X\Y:f => X\Z: λx􏰓.f(g(x))`
            - Backward Crossing Composition = `Y/Z:g X\Y:f => X/Z: λx􏰓.f(g(x))`
            - Forward Composition = `X/Y:f Y/Z:g => X/Z: λx􏰓.f(g(x))`
            - Forward Crossing Composition = `X/Y:f Y\Z:g => X\Z: λx􏰓.f(g(x))`
        """
        if not g.isfunctor:
            raise DrsComposeError('composition argument must be a functor')
        assert g.outer is None  # must be outer scope

        # Create a new category
        cat = Category.combine(self.category.result_category(), g.category.slash, g.category.argument_category())

        # Rename so f names are disjoint with g names.
        # Try to keep var subscripts increasing left to right.
        if self.isarg_left:
            self.outer_scope.make_vars_disjoint(g)
        else:
            g.make_vars_disjoint(self.outer_scope)

        # Get scopes before we modify f and g
        fv = self.category.argument_category().extract_unify_atoms(False)
        gv = g.category.result_category().extract_unify_atoms(False)

        fc = self.pop()
        assert fc is not None
        yflr = self.inner_scope.get_unify_scopes(False)

        # Get lambdas
        gc = g.pop()
        zg = g.pop()
        if zg is None:
            # Y is an atom (i.e. Y=gc) and functor scope is exhausted
            assert g.category.result_category().isatom
            zg = g
            glr = gc.lambda_refs
        else:
            # Get Y unification lambdas
            g.push(gc)
            glr = g.get_unify_scopes(False)
            g.pop()
            assert gc is not None
        zg._category = cat
        assert len(yflr) == len(glr)

        # Get Y unification scope
        assert len(fv) == len(gv)
        assert len(fv) == len(yflr)
        uy = map(lambda x: (x[2], x[3]), filter(lambda x: x[0].can_unify_atom(x[1]),
                                                zip(gv, fv, yflr, glr)))
        uy = filter(lambda x: can_unify_refs(fc, x[0], gc, x[1]), uy)
        assert len(uy) != 0

        # Build
        pl = ProductionList()
        pl.set_category(fc.category)
        pl.set_lambda_refs(fc.lambda_refs)
        pl.push_right(fc)
        pl.push_right(gc)
        pl.flatten()
        pl = pl.unify() # merges universes
        assert isinstance(pl, DrsProduction)
        zg.push(pl)
        # Handle atomic X. If X is an atomic type next push() fails because the functor scope
        # is exhausted after this pop()
        fy = self.pop()
        if fy is None:
            # X is atomic
            assert self.category.result_category().isatom
            zg.rename_vars(uy)  # unify
            return zg
        self.push(zg)
        self.rename_vars(uy)    # unify
        return self

    def generalized_compose(self, g):
        """Generalized function Composition.

        Arg:
            g: The (Y|Z)$ functor where self (f) is the X|Y functor.

        Returns:
            An AbstractProduction instance.

        Remarks:
            CALL[X|Y](Y|Z)$
            - Generalized Forward Composition  X/Y:f (Y/Z)/$:...λz.gz... => (X/Z)/$: ...λz.f(g(z...))
            - Generalized Forward Crossing Composition  X/Y:f (Y\Z)$:...λz.gz... => (X\Z)$: ...λz.f(g(z...))
            - Generalized Backward Composition  (Y\Z)$:...λz.gz... X\Y:f => (X\Z)$: ...λz.f(g(z...))
            - Generalized Backward Crossing Composition  (Y/Z)/$:...λz.gz... X\Y:f => (X/Z)/$: ...λz.f(g(z...))
        """
        if not g.isfunctor:
            raise DrsComposeError('generalized composition argument must be a functor')
        assert g.outer is None  # must be outer scope

        # Create a new category
        resultcat = Category.combine(self.category.result_category(), g.category.result_category().slash,
                                     g.category.result_category().argument_category())
        cat = Category.combine(resultcat, g.category.slash, g.category.argument_category())

        # Rename so f names are disjoint with g names.
        # Try to keep var subscripts increasing left to right.
        if self.isarg_left:
            self.outer_scope.make_vars_disjoint(g)
        else:
            g.make_vars_disjoint(self.outer_scope)

        # Get scopes before we modify f and g
        fv = self.category.argument_category().extract_unify_atoms(False)
        gv = g.category.result_category().result_category().extract_unify_atoms(False)

        # Get lambdas
        gc = g.pop()
        assert gc is not None
        dollar = g.pop()
        dollar._category = cat
        zg = g.pop()
        if zg is None:
            # Y is an atom (i.e. Y=gc) and functor scope is exhausted
            assert g.category.result_category().isatom
            zg = g
            glr = gc.lambda_refs
        else:
            # Get Y unification lambdas
            g.push(gc)
            glr = g.get_unify_scopes(False)
            g.pop()
            assert gc is not None
        zg._category = resultcat

        fc = self.pop()
        assert fc is not None
        yflr = self.inner_scope.get_unify_scopes(False)
        assert len(yflr) == len(glr)

        # Get Y unification scope
        assert len(fv) == len(gv)
        assert len(fv) == len(yflr)
        uy = map(lambda x: (x[2], x[3]), filter(lambda x: x[0].can_unify_atom(x[1]),
                                                zip(gv, fv, yflr, glr)))
        uy = filter(lambda x: can_unify_refs(fc, x[0], gc, x[1]), uy)
        assert len(uy) != 0

        # Build
        pl = ProductionList()
        pl.set_category(fc.category)
        pl.set_lambda_refs(fc.lambda_refs)
        pl.push_right(fc)   # first entry sets lambdas
        pl.push_right(gc)
        pl.flatten()
        pl = pl.unify()     # merges universes
        assert isinstance(pl, DrsProduction)
        dollar.push(pl)
        zg.push(dollar)

        # Handle atomic X. If X is an atomic type next push() fails because the functor scope
        # is exhausted after this pop()
        fy = self.pop()
        if fy is None:
            # X is atomic
            assert self.category.result_category().isatom
            zg.rename_vars(uy)  # unify
            return zg
        self.push(zg)
        self.rename_vars(uy)    # unify
        return self

    def substitute(self, g):
        """Functional Substitution.

        Arg:
            g: The Y|Z functor where self (f) is the (X|Y)|Z functor.

        Returns:
            An AbstractProduction instance.

        Remarks:
            CALL[(X|Y)|Z](Y|Z)
            - Forward Substitution (X/Y)/Z:f Y/Z:g => X/Z: λx􏰓.fx􏰨(g􏰨(x􏰩􏰩))
            - Forward Crossing Substitution  (X/Y)\Z:f Y\Z:g => X\Z: λx􏰓.fx􏰨(g􏰨(x􏰩􏰩))
            - Backward Substitution  Y\Z:g (X\Y)\Z:f => X\Z: λx􏰓.fx􏰨(g􏰨(x􏰩􏰩))
            - Backward Crossing Substitution  Y/Z:g (X\Y)/Z:f => X/Z: λx􏰓.fx􏰨(g􏰨(x􏰩􏰩))
        """
        if not g.isfunctor:
            raise DrsComposeError('substitution argument must be a functor')
        assert g.outer is None  # must be outer scope

        # Create a new category
        cat = Category.combine(self.category.result_category().result_category(), self.category.slash,
                               g.category.argument_category())

        # Rename so f names are disjoint with g names.
        # Try to keep var subscripts increasing left to right.
        if self.category.result_category().isarg_right:
            self.outer_scope.make_vars_disjoint(g)
        else:
            g.make_vars_disjoint(self.outer_scope)

        # Get scopes before we modify f and g
        fv = self.category.argument_category().extract_unify_atoms(False)
        gv = g.category.result_category().extract_unify_atoms(False)

        # Get lambdas
        gc = g.pop()
        zg = g.pop()
        if zg is None:
            # Y is an atom (i.e. Y=gc) and functor scope is exhausted
            assert g.category.result_category().isatom
            zg = g
        zg._category = cat

        # Get Y unification lambdas
        g.push(gc)
        glr = g.get_unify_scopes(False)
        g.pop()
        assert gc is not None

        fc = self.pop()
        assert fc is not None
        zf = self.pop()
        assert zf is not None
        self.push(fc)
        yflr = self.inner_scope.get_unify_scopes(False)
        assert len(yflr) == len(glr)

        # Get Y unification scope
        assert len(fv) == len(gv)
        assert len(fv) == len(yflr)
        uy = map(lambda x: (x[2], x[3]), filter(lambda x: x[0].can_unify_atom(x[1]),
                                                zip(gv, fv, yflr, glr)))
        uy = filter(lambda x: can_unify_refs(fc, x[0], gc, x[1]), uy)
        assert len(uy) != 0
        self.pop()

        # Build
        pl = ProductionList()
        pl.set_category(fc.category)
        pl.set_lambda_refs(fc.lambda_refs)
        pl.push_right(fc)   # first in list sets lambdas
        pl.push_right(gc)
        pl.flatten()
        pl = pl.unify()     # merges universes
        assert isinstance(pl, DrsProduction)
        zg.push(pl)
        # Handle atomic X. If X is an atomic type next push() fails because the functor scope
        # is exhausted after this pop()
        yf = self.pop()
        if yf is None:
            # X is atomic
            assert self.category.result_category().isatom
            zg.rename_vars(uy)  # unify
            return zg
        self.push(zg)
        self.rename_vars(uy)    # unify
        return self

    def conjoin(self, g, glambdas):
        """Conjoin Composition.

        Arg:
            g: The X2|Y2 functor where self (f) is the X1|Y1 functor.
            glambdas: If True set lambda from g, else set from self.

        Returns:
            An AbstractProduction instance.

        Remarks:
            CALL[X1|Y1](X2|Y2)
        """
        assert self.outer is None
        if g.category.remove_features() != self.category.remove_features():
            raise DrsComposeError('conjoin argument must be a like type')

        if g.isfunctor:
            assert g.outer is None
            ga = g.category.extract_unify_atoms(False)
            fa = self.category.extract_unify_atoms(False)
            for u, v in zip(ga, fa):
                if not u.can_unify_atom(v):
                    raise DrsComposeError('conjoin argument must be a like functor')

            # Rename f so disjoint with g names
            self.make_vars_disjoint(g)

            gc = g.pop()
            glr = gc.lambda_refs
            gc.set_lambda_refs([])

            fc = self.pop()
            flr = fc.lambda_refs
            fc.set_lambda_refs([])

            c = ProductionList(fc)
            c.push_right(gc)
            c.set_lambda_refs(glr if glambdas else flr)
            c.set_category(gc.category if glambdas else fc.category)
            c.flatten()
            self.push(c.unify())
        else:
            # Rename f so disjoint with g names
            self.make_vars_disjoint(g)
            glr = g.lambda_refs
            g.set_lambda_refs([])
            fc = self.pop()
            flr = fc.lambda_refs
            c = ProductionList(fc)
            c.push_right(g)
            if glambdas and len(glr) != len(flr):
                # FIXME: A AbstractProduction should always have lambda_refs set.
                c.set_lambda_refs(flr)
                c.set_category(fc.category)
            else:
                c.set_lambda_refs(glr if glambdas else flr)
            c.set_category(fc.category)
            c.flatten()
            self.push(c.unify())

        return self

    def apply(self, g):
        """Function application.

        Arg:
            g: The application argument.

        Returns:
            An AbstractProduction instance.
        """
        global _FCHR
        if self._comp is not None and self._comp.isfunctor:
            self._comp = self._comp.apply(g)
            if self._comp.isfunctor:
                self._comp._set_outer(self)
            return self

        assert self._comp is not None

        if 0 != (self.compose_options & CO_PRINT_DERIVATION):
            print('DERIVATION:= %s {%s=%s}' % (future_string(self.outer_scope), chr(ord(_FCHR)+self._get_position()), future_string(g)))

        # Ensure names do not conflict. Need to execute at outer scope so all variables are covered.
        # Try to keep var subscripts increasing left to right.
        if self.isarg_left or not g.isfunctor:
            self.outer_scope.make_vars_disjoint(g)
        else:
            g.make_vars_disjoint(self.outer_scope)

        # Add a proposition if too many variables to bind
        glr = g.lambda_refs if not g.isfunctor else g.get_unify_scopes(False)
        if len(glr) == 0:
            # FIXME: lambda_refs should always be set
            assert not g.isfunctor
            glr = g.universe

        if not g.isfunctor and len(self._lambda_refs.referents) == 1 and len(glr) != 1:
            # Add proposition
            p = PropProduction(CAT_PPNP, self._lambda_refs.referents[0])
            g = p.apply(g)
        else:
            # Use Category.extract_unify_atoms to get binding region
            # Bind with inner scope
            flr = self.get_unify_scopes(False)
            fs = self.category.argument_category().extract_unify_atoms(False)
            gs = g.category.extract_unify_atoms(False)
            assert fs is not None
            assert gs is not None and len(gs) == len(fs)

            rs = map(lambda x: (x[2], x[3]), filter(lambda x: x[0].can_unify_atom(x[1]),
                                                    zip(fs, gs, glr, flr)))
            rs = filter(lambda x: can_unify_refs(g, x[0], self._comp, x[1]), rs)
            # Unify
            g.rename_vars(rs, self)

        ors = intersect(g.universe, self.universe)
        if len(ors) != 0:
            # FIXME: Partial unification requires at least one variable
            #if len(rs) == len(ors):
            #    raise DrsComposeError('unification not possible')
            ers = union(g.variables, self.outer_scope.variables)
            nrs = g.make_new_drsrefs(ors, ers)
            g.rename_vars(zip(ors, nrs), self)

        if g.isfunctor:
            assert g.inner_scope._comp is not None
            # functor production
            cl = ProductionList()
            cl.set_options(self.compose_options)

            # Apply the combinator
            gcomp = g.pop()
            fcomp = self.pop()
            cl.set_category(fcomp.category)
            cl.set_lambda_refs(fcomp.lambda_refs)
            if self.isarg_left:
                cl.push_right(gcomp)
                cl.push_right(fcomp)
            else:
                cl.push_right(fcomp)
                cl.push_right(gcomp)

            self.clear()
            #cl.flatten()
            return cl.unify()

        # Remove resolved referents from lambda refs list
        assert len(self._lambda_refs.referents) != 0
        if isinstance(self._comp, ProductionList):
            c = self._comp
        else:
            c = ProductionList(self._comp)

        if self.isarg_right:
            c.push_right(g)
        else:
            c.push_left(g)

        lr = self._comp.lambda_refs
        cat = self._comp.category
        c.set_options(self.compose_options)
        #c.flatten()
        c = c.unify()
        c.set_lambda_refs(lr)
        c.set_category(cat)
        self.clear()

        if 0 != (self.compose_options & CO_PRINT_DERIVATION):
            print('          := %s' % future_string(c))

        return c


class PropProduction(FunctorProduction):
    """A proposition functor."""
    def __init__(self, category, referent, production=None):
        super(PropProduction, self).__init__(category, referent, production)

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
            A AbstractProduction instance.
        """
        global _FCHR
        if self._comp is not None and self._comp.isfunctor:
            self._comp = self._comp.apply(d)
            if self._comp.isfunctor:
                self._comp._set_outer(self)
            return self

        if 0 != (self.compose_options & CO_PRINT_DERIVATION):
            print('DERIVATION:= %s {%s=%s}' % (future_string(self.outer_scope), chr(ord(_FCHR)+self._get_position()), future_string(d)))
        if isinstance(d, ProductionList):
            d = d.unify()
        assert isinstance(d, DrsProduction)
        if (self.compose_options & CO_REMOVE_UNARY_PROPS) != 0 and len(d.referents) == 1:
            rs = zip(d.referents, self._lambda_refs.referents)
            d.rename_vars(rs)
            d.set_options(self.compose_options)
            lr = self._lambda_refs.referents
            self.clear()
            d.set_lambda_refs(lr)
            if 0 != (self.compose_options & CO_PRINT_DERIVATION):
                print('          := %s' % future_string(d))
            return d
        lr = self._lambda_refs.referents
        lr.extend(d._universe)
        dd = DrsProduction(universe=lr, freerefs=d._freerefs,
                           category=self.category.result_category(), span=d.span)
        dd.set_options(self.compose_options)
        self.clear()
        dd.set_lambda_refs(lr)
        if 0 != (self.compose_options & CO_PRINT_DERIVATION):
            print('          := %s' % future_string(dd))
        return dd

