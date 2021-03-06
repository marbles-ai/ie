from __future__ import unicode_literals, print_function
from marbles import safe_utf8_decode, safe_utf8_encode, UNICODE_STRINGS
from utils import iterable_type_check, union, union_inplace, intersect, rename_var, compare_lists_eq
from common import SHOW_BOX, SHOW_LINEAR, SHOW_SET, SHOW_DEBUG
from common import DRSVar, DRSConst, Showable
import fol
import weakref


WORLD_VAR = 'w'


# Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Properties.hs#isPureDRS:pureRefs
def _pure_refs(ld, gd, rs, srs):
    return all([(r.has_bound(ld, gd) or r not in srs) for r in rs])


class ConditionRef(object):
    """References a condition in a DRS."""

    def __init__(self, ld, gd, cond):
        """Constructor.

        Args:
            ld: The local DRS containing the condition, where ls is a subordinate DRS of gd.
            gd: The global DRS such that gd.universes included of all referents in cond.
            cond: The condition.
        """
        self.ld = ld
        self.gd = gd
        self.cond = cond
        self.gdlevel = 0
        self.ldlevel = 0
        while ld != gd:
            ld = ld.accessible_drs
            assert ld is not None
            self.ldlevel += 1
        while gd is not None:
            self.ldlevel += 1
            self.gdlevel += 1
            gd = gd.accessible_drs

    def __eq__(self, other):
        return type(self) == type(other) and self.cond == other.cond and self.ld == other.ld and self.gd == other.gd

    def remove(self):
        self.ld.remove_condition(self)


class AbstractDRS(Showable):
    """Abstract Core Discourse Representation Structure for DRS and PDRS"""
    def __init__(self):
        self._accessible_drs = None

    def __str__(self):
        return safe_utf8_encode(self.show(SHOW_LINEAR))

    def __unicode__(self):
        return safe_utf8_decode(self.show(SHOW_LINEAR))

    def __repr__(self):
        return unicode(self) if UNICODE_STRINGS else str(self)

    def _isproper_subdrsof(self, d):
        """Helper for isproper"""
        return False

    def _ispure_helper(self, rs, gd):
        """Helper for ispure"""
        return False

    def _set_accessible(self, d):
        self._accessible_drs = None
        return True

    @property
    def isempty(self):
        return False

    @property
    def accessible_drs(self):
        """Returns the next accessible DRS or None."""
        return None if self._accessible_drs is None else self._accessible_drs() # weak de-ref

    @property
    def global_drs(self):
        """Returns the outer-most DRS accessible from this DRS. If this DRS is the outer-most DRS then self is returned."""
        g = self
        while g.accessible_drs is not None:
            g = g.accessible_drs
        return g

    @property
    def accessible_universe(self):
        """Returns the universe of referents accessible to this DRS."""
        u = set()
        g = self
        while g is not None:
            u = u.union(g.referents)
            g = g.accessible_drs
        return sorted(u)

    @property
    def freerefs(self):
        """Returns the list of all free DRSRef's in this DRS.

        Remarks:
            Same as sorted(set(get_freerefs(self)))
        """
        return sorted(set(self.get_freerefs(self)))

    @property
    def variables(self):
        """Returns the list of all bound DRSRef's in this DRS.

        Remarks:
            Same as sorted(set(get_variables(None)))
        """
        return sorted(set(self.get_variables(None)))

    @property
    def constants(self):
        """Returns the list of all constant DRSRef's in this DRS.

        Remarks:
            Same as sorted(set(get_constants(None)))
        """
        return sorted(set(self.get_constants(None)))

    @property
    def universes(self):
        """Returns the list of DRSRef's from all universes in this DRS.

        Remarks:
            Same as sorted(set(get_universes(None)))

        See Also:
            AbstractDRS.universe property.
        """
        return sorted(set(self.get_universes(None)))

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Structure.hs">/Data/DRS/Structure.hs:isResolvedDRS</a>
    ## and <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Structure.hs">/Data/PDRS/Structure.hs:isResolvedPDRS</a>.
    ##
    @property
    def isresolved(self):
        """Test whether this DRS is resolved (containing no unresolved merges)."""
        return False

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Structure.hs">/Data/DRS/Structure.hs:isMergeDRS</a>
    ## and <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Structure.hs">/Data/PDRS/Structure.hs:isMergePDRS</a>.
    ##
    @property
    def ismerge(self):
        """Test whether this DRS is entirely a 'Merge' (at its top-level)."""
        return False

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Structure.hs">/Data/DRS/Structure.hs:drsUniverse</a>
    ## and <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Structure.hs">/Data/PDRS/Structure.hs:pdrsUniverse</a>.
    ##
    @property
    def universe(self):
        """Returns the universe of referents in this DRS. A shallow copy is always returned."""
        return []

    @property
    def referents(self):
        """Similar to universe but will only returns referents for a DRS. Also no copy is performed whereas universe
        will do  a shallow copy.
        """
        return []

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Properties.hs">/Data/DRS/Properties.hs:isPureDRS</a>
    ## and <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Properties.hs">/Data/DRS/Properties.hs:isPurePDRS</a>.
    ##
    @property
    def ispure(self):
        """Test whether this DRS is pure, where a DRS is pure iff it does not contain any otiose declarations of
        discourse referents (i.e. it does not contain any unbound, duplicate uses of referents).
        """
        return self._ispure_helper([], self)

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Properties.hs">/Data/DRS/Properties.hs:isProperDRS</a>
    ## <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Properties.hs">/Data/PDRS/Properties.hs:isProperPDRS</a>
    ##
    @property
    def isproper(self):
        """Test whether this DRS is proper, where a DRS is proper iff it does not contain any free variables."""
        return self._isproper_subdrsof(self)

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Properties.hs">/Data/DRS/Properties.hs:isFOLDRS</a>.
    ##
    @property
    def isfol(self):
        """Test whether this DRS can be translated into a FOLForm instance."""
        return self.isresolved and self.ispure and self.isproper

    def simplify_props(self):
        """Simplify propositions"""
        return self

    def find_subdrs(self, d):
        """Test whether d is a direct or indirect subordinate DRS of this DRS and return the found subordinate DRS."""
        return None

    def find_condition(self, c):
        """Search for a condition matching `c`.

        Args:
            c: A condition.

        Returns:
            A tuple of the global DRS, and the condition or (self,None).
        """
        return None

    def test_is_accessible_to(self, d):
        """Test whether this DRS is accessible to d."""
        if d.accessible_drs is not None and self.accessible_drs is None:
            gd = d.global_drs
            if gd != self:
                s = gd.find_subdrs(self)
                if s is not None:
                    return s.test_is_accessible_to(d)
                return False
            return True
        elif self.accessible_drs is None:
            # d.accessible_drs is None and self.accessible_drs is None
            return d == self or self.find_subdrs(d) is not None
        elif d.accessible_drs is None:
            # d.accessible_drs is None and self.accessible_drs is not None
            d = self.global_drs.find_subdrs(d)
        # else d.accessible_drs is not None and self.accessible_drs is not None
        while d is not None:
            if d == self:
                return True
            d = d.accessible_drs
        return False

    def clone(self):
        return self

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Structure.hs">/Data/DRS/Structure.hs:isSubDRS</a>
    ## and <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Structure.hs">/Data/PDRS/Structure.hs:isSubPDRS</a>.
    ##
    def has_subdrs(self, d):
        """Returns whether d is a direct or indirect subordinate DRS of this DRS"""
        return self.find_subdrs(d) is not None

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Binding.hs">/Data/DRS/Binding.hs:drsFreeRefs</a>.
    ##
    def get_freerefs(self, gd=None):
        """Returns the list of all free DRSRef's in a DRS.

        Args:
            gd: A global DRS where `self` is a subordinate DRS of `gd`.

        Returns:
            A list of DRSRef instances.
        """
        return []

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Merge.hs">/Data/DRS/Merge.hs:drsResolveMerges</a>
    ## and <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Merge.hs">/Data/PDRS/Merge.hs:pdrsResolveMerges</a>.
    ##
    def resolve_merges(self):
        """ Resolves all unresolved merges in a 'DRS'."""
        raise NotImplementedError

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Variables.hs">/Data/DRS/Variables.hs:drsVariables</a>
    ## and <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Variables.hs">/Data/PDRS/Variables.hs:pdrsVariables</a>.
    ##
    def get_variables(self, u=None):
        """Returns the list of all bound DRSRef's in this DRS.

        Args:
            u: An initial list. If None `u` is set to [].

        Returns:
            A list of DRSRef's unioned with `u`.
        """
        return u if u is not None else []

    def get_constants(self, u=None):
        """Returns the list of all constant DRSRef's in this DRS. Constants were introduced by Muskens, 1996. A constant
        can only appear in conditions, i.e. it is never bound.

        Args:
            u: An initial list. If None `u` is set to [].

        Returns:
            A list of constant DRSRef's unioned with `u`.
        """
        return u if u is not None else []

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Variables.hs">/Data/PDRS/Variables.hs:drsUniverses</a>
    ## and <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Structure.hs">/Data/PDRS/Structure.hs:pdrsUniverses</a>.
    ##
    def get_universes(self, u=None):
        """Returns the list of DRSRef's from all universes in this DRS.

        Args:
            u: An initial list. If None `u` is set to [].

        Returns:
            A list of DRSRef's unioned with `u`.
        """
        return u if u is not None else []

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/LambdaCalculus.hs">/Data/DRS/LambdaCalculus.hs:purifyRefs</a>
    ## and <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/RDRS/LambdaCalculus.hs">/Data/RDRS/LambdaCalculus.hs:purifyPRefs</a>.
    ##
    def purify_refs(self, gd, rs):
        """Replaces duplicate uses of DRSRef's by new DRSRef's.

        Args:
            gd: A global DRS, where `self` is a subordinate DRS of global.
            rs: A list of referents

        Returns:
            A tuple of a new DRS instance and a list of referents seen.
        """
        raise NotImplementedError

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/LambdaCalculus.hs">/Data/DRS/LambdaCalculus.hs:drsAlphaConvert</a>
    ## and <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/LambdaCalculus.hs">/Data/PDRS/LambdaCalculus.hs:pdrsAlphaConvert</a>.
    ##
    def alpha_convert(self, rs, ps=None):
        """Applies alpha conversion to the bound variables in this DRS on the basis of the conversion list `rs` for
        DRSRef's and the conversion list `ps` for PVar's.

        Args:
            rs: A list of DRSRef|LambaDRSRef conversion tuples formated as (old, new).
            ps: A list of integer tuples formated as (old, new). Cannot be None in PDRS implementation but we have to
                reproduce the type declaration of AbstractDRS.

        Returns:
            A DRS instance.
        """
        if isinstance(rs, tuple) and len(rs) == 2 and iterable_type_check(rs, AbstractDRSRef):
            rs = [rs]
        elif iterable_type_check([rs, ps], AbstractDRSRef):
            rs = [(rs, ps)]
            ps = None
        elif not iterable_type_check(rs, tuple):
            raise TypeError
        return self.rename_subdrs(self, rs, ps)

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/LambdaCalculus.hs">/Data/DRS/LambdaCalculus.hs::renameSubDRS</a>
    ## and <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/LambdaCalculus.hs">/Data/PDRS/LambdaCalculus.hs::renameSubPDRS</a>.
    ##
    def rename_subdrs(self, gd, rs, ps=None):
        """Applies alpha conversion to this DRS, which is a subordinate DRS of the global DRS `gd`, on the basis of the
        conversion list `rs` for DRSRef's and the conversion list `ps` for PVar's.

        Args:
            gd: An DRS|Merge instance.
            rs: A list of DRSRef tuples.
            ps: A list of integer tuples. Cannot be None in PDRS implementation but we
                have to reproduce the type declaration of AbstractDRS.

        Returns:
            A DRS instance.
        """
        raise NotImplementedError

    def substitute(self, rs, ps=None):
        """Applies substitution to the free variables in this DRS on the basis of the conversion list `rs` for
        DRSRef's.

        Args:
            rs: A list of DRSRef|LambaDRSRef conversion tuples formatted as (old, new).

        Returns:
            A DRS instance.
        """
        if self.isproper:
            return self
        elif isinstance(rs, tuple) and len(rs) == 2 and iterable_type_check(rs, AbstractDRSRef):
            rs = [rs]
        elif iterable_type_check([rs, ps], AbstractDRSRef):
            rs = [(rs, ps)]
            ps = None
        elif not iterable_type_check(rs, tuple):
            raise TypeError
        return self.subst_subdrs(self, rs)

    def subst_subdrs(self, gd, rs):
        """Applies substitution to this DRS, which is a subordinate DRS of the global DRS `gd`, on the basis of the
        conversion list `rs` for DRSRef's .

        Args:
            gd: An DRS|Merge instance.
            rs: A list of DRSRef tuples.

        Returns:
            A DRS instance.
        """
        raise NotImplementedError

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/LambdaCalculus.hs">/Data/DRS/LambdaCalculus.hs:drsPurify</a>
    ##
    def purify(self):
        """Converts a DRS into a pure DRS by purifying its DRSRef's, where a DRS is pure iff there are no occurrences of
        duplicate, unbound uses of the same DRSRef.
        """
        refs = self.get_freerefs(self)
        drs,_ = self.purify_refs(self, refs)
        return drs

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Translate.hs">/Data/DRS/Translate.hs:drsToFOL</a>
    ##
    def to_fol(self):
        """Convert to FOLForm

        Returns:
            A tuple of an ie.fol.FOLForm instance and a list of possible worlds.

        Raises:
            ie.fol.FOLConversionError
        """
        global WORLD_VAR
        worlds = [DRSVar(WORLD_VAR)]
        mfol = self.to_mfol(worlds[0], worlds)
        return mfol, worlds

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Translate.hs">/Data/DRS/Translate.hs:drsToMFOL</a>
    ##
    def to_mfol(self, world, worlds):
        """Converts a DRS to a modal FOL formula with world

        Args:
            world: A ie.fol.FOLVar instance
            worlds: A list of all worlds.

        Returns:
            A tuple of an ie.fol.FOLForm instance and a list of possible worlds.

        Raises:
            ie.fol.FOLConversionError
        """
        raise fol.FOLConversionError('infelicitous FOL formula')


def conds_to_mfol(conds, world, worlds):
    """Converts a list of DRS conditions to a modal FOL formula with world"""
    if len(conds) == 0:
        return fol.Top()
    if len(conds) == 1:
        return conds[0].to_mfol(world, worlds)
    else:
        f = fol.And(conds[-2].to_mfol(world, worlds), conds[-1].to_mfol(world, worlds))
        for i in reversed(range(len(conds) - 2)):
            f = fol.And(conds[i].to_mfol(world, worlds), f)
        return f


class DRS(AbstractDRS):
    """Default DRS"""
    def __init__(self, drsRefs, drsConds):
        if not iterable_type_check(drsRefs, AbstractDRSRef) or not iterable_type_check(drsConds, AbstractDRSCond):
            raise TypeError
        #if any([x.isconst for x in drsRefs]):
        #    raise TypeError('DRSConst cannot be bound')
        super(DRS, self).__init__()
        self._refs = drsRefs
        self._conds = drsConds
        ok = True
        for c in drsConds:
            if not c._set_accessible(self):
                ok = False
                break
        if not ok:
            self._conds = [c.clone() for c in drsConds]
            for c in self._conds:
                assert c._set_accessible(self)

    def __ne__(self, other):
        return type(self) != type(other) or not compare_lists_eq(self._refs, other._refs) \
               or not compare_lists_eq(self._conds, other._conds)

    def __eq__(self, other):
        return type(self) == type(other) and compare_lists_eq(self._refs, other._refs) \
               and compare_lists_eq(self._conds, other._conds)

    def __hash__(self):
        refs = set(self.universe)
        refs.union(self.freerefs)
        conds = set(self._conds)
        return hash(conds) ^ hash(refs)

    def _set_accessible(self, d):
        if self._accessible_drs is None:
            self._accessible_drs = weakref.ref(d)
            return True
        return False

    def _isproper_subdrsof(self, gd):
        """Help for isproper"""
        return all([x._isproper_subdrsof(self, gd) for x in self._conds])

    def _ispure_helper(self, rs, gd):
        if any([(x in rs) for x in self._refs]): return False
        if len(self._conds) == 0: return True
        rss = []
        rss.extend(rs)
        rss.extend(self._refs)
        r = True
        for c in self._conds:
            r,rss = c._ispure(self, gd, rss)
            if not r: return False
        return r

    @property
    def isempty(self):
        return len(self._refs) == 0 and len(self._conds) == 0

    @property
    def referents(self):
        """Similar to universe but will only returns referents for a DRS. No shallow copy."""
        return self._refs

    @property
    def universe(self):
        """Returns the universe of referents in this DRS."""
        return [x for x in self._refs] # shallow copy

    @property
    def conditions(self):
        """Get the list of conditions."""
        return [x for x in self._conds] # shallow copy

    @property
    def isresolved(self):
        """Test whether this DRS is resolved (containing no unresolved merges)"""
        return all([x.isresolved for x in self._refs]) and all([x.isresolved for x in self._conds])

    def simplify_props(self):
        """Simplify propositions"""
        if not self.ispure:
            return self
        conds = []
        for c in self._conds:
            conds.extend(c.simplify_props())
        return DRS(self.universe, conds)

    def clone(self):
        return DRS(self._refs, [c.clone() for c in self._conds])

    def remove_condition(self, rc):
        """Remove a condition from the DRS.

        Args:
            rc: A ConditionRef returned from find_condition().
        """
        if rc is None:
            return
        if not isinstance(rc, ConditionRef):
            raise TypeError('DRS.remove_condition expects a ConditionRef.')
        if id(rc.ld) == id(self):
            conds = filter(lambda c: c != rc.cond, self._conds)
            self._conds = conds
        elif self.find_subdrs(self.ld) is not None:
            rc.ld.remove_condition(rc)

    def find_condition(self, c):
        """Search for a condition matching `c`.

        Args:
            c: A condition.

        Returns:
            A tuple of the global DRS, and the found condition or (self,None).
        """
        for ctest in self._conds:
            rc = ctest.find_condition(c, self)
            if rc is not None:
                return rc
        return None

    def find_subdrs(self, d):
        """Test whether d is a direct or indirect subordinate DRS of this DRS and return the found subordinate DRS."""
        if self == d:
            return self
        for c in self._conds:
            x = c.find_subdrs(d)
            if x is not None:
                return x
        return None

    def get_freerefs(self, gd=None):
        """Returns the list of all free DRSRef's in a DRS. If `gd` is set then self must be a subordinate DRS of `gd` and the
        function only returns free referents in the accessible domain of DRS between `self` and `gd`.

        Args:
            gd: A global DRS where `self` is a subordinate DRS of `gd`. Default is self.global_drs

        Returns:
            A list of DRSRef instances.
        """
        if gd is None:
            gd = self.global_drs
        u = []
        for c in self._conds:
            u.extend(c._get_freerefs(self, gd))
        return u

    def resolve_merges(self):
        """Resolves all unresolved merges in this DRS."""
        return DRS(self._refs, [x.resolve_merges() for x in self._conds])

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Variables.hs">/Data/DRS/Variables.hs:drsVariables</a>
    ##
    def get_variables(self, u=None):
        """Returns the list of all bound DRSRef's in this DRS.

        Args:
            u: An initial list. If None `u` is set to [].

        Returns:
            A set of bound DRSRef's unioned with `u`.
        """
        if u is None:
            u = filter(lambda x: not x.isconst, self.universe)
        else:
            u.extend(filter(lambda x: not x.isconst, self.universe))
        for c in self._conds:
            u = c.get_variables(u)
        return u

    def get_constants(self, u=None):
        """Returns the list of all constant DRSRef's in this DRS.

        Args:
            u: An initial list. If None `u` is set to [].

        Returns:
            A set of constant DRSRef's unioned with `u`.
        """
        if u is None:
            u = filter(lambda x: x.isconst, self.universe)
        else:
            u.extend(filter(lambda x: x.isconst, self.universe))
        for c in self._conds:
            u = c.get_constants(u)
        return u

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Variables.hs">/Data/DRS/Variables.hs:drsUniverses</a>
    ##
    def get_universes(self, u=None):
        """Returns the list of DRSRef's from all universes in this DRS.

        Args:
            u: An initial list. If None `u` is set to [].

        Returns:
            A list of DRSRef's unioned with `u`.
        """
        if u is None:
            u = [x for x in self._refs] # shallow copy
        else:
            u.extend(self._refs)
        for c in self._conds:
            u = c._universes(u)
        return u

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/LambdaCalculus.hs">/Data/DRS/LambdaCalculus.hs:purifyRefs</a>
    ##
    def purify_refs(self, gd, ers):
        """Replaces duplicate uses of DRSRef's by new DRSRef's.

         This function implements the following algorithm:
         - start with the global DRS `gd` and add all free DRSRefs's in `gd` to the list of seen referents `rs`;
         - check the universe `u` of the first atomic DRS `self` against `rs` and, if necessary, alpha-convert
           `self` replacing duplicates for new DRSRef's in `u`;
         - add the universe of self to the list of seen DRSRef's `rs`;
         - go through all conditions of `self`, while continually updating `rs`.

         Args:
             gd: A global DRS, where `self` is a subordinate DRS of global.
             ers: A list of referents

         Returns:
             A tuple of a new DRS instance and the list of seen referents

         See Also:
             purify()
         """

        # In case we do not want to rename ambiguous bindings:
        # purifyRefs (ld@(DRS u _),ers) gd = (DRS u1 c2,u1 ++ ers1)
        ors = intersect(self._refs, ers)
        d = self.alpha_convert(zip(ors, get_new_drsrefs(ors, union_inplace(gd.variables,ers))))
        r = union(d.universe, ers)
        conds = []
        for c in d._conds:
            x,r = c._purify_refs(gd, r)
            conds.append(x)
        return DRS(d.universe,conds), r

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/LambdaCalculus.hs">/Data/DRS/LambdaCalculus.hs::renameSubDRS</a>
    ##
    def rename_subdrs(self, gd, rs, ps=None):
        """Applies alpha conversion to this DRS, which is a subordinate DRS of the
        global DRS gd, on the basis of a conversion list for DRSRef's rs.

        Args:
            gd: An DRS|Merge instance.
            rs: A list of DRSRef tuples.
            ps: A list of integer tuples. Only used in PDRS implementation.

        Returns:
            A DRS instance.
        """
        # FIXME: rename_vars searches list each iter - needs to change
        return DRS([rename_var(r, rs) for r in self._refs], \
                   [c._convert(self, gd, rs) for c in self._conds])

    def subst_subdrs(self, gd, rs):
        """Applies substitution to this DRS, which is a subordinate DRS of the global DRS `gd`, on the basis of the
        conversion list `rs` for DRSRef's .

        Args:
            gd: An DRS|Merge instance.
            rs: A list of DRSRef tuples.

        Returns:
            A DRS instance.
        """
        return DRS(self.universe, [c._substitute(self, gd, rs) for c in self._conds])

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Translate.hs">/Data/DRS/Translate.hs:drsToMFOL</a>
    ##
    def to_mfol(self, world, worlds):
        """Converts a DRS to a modal FOL formula with world

        Args:
            world: A ie.fol.FOLVar instance

        Returns:
            An ie.fol.FOLForm instance.

        Raises:
            ie.fol.FOLConversionError
        """
        if len(self._refs) == 0:
            return conds_to_mfol(self._conds, world, worlds)
        # FIXME: remove recursion
        #return fol.Exists(fol.FOLVar(self._refs[0].var), DRS(self._refs[1:], self._conds).to_mfol(world, worlds))
        return fol.Exists(self._refs[0].var, DRS(self._refs[1:], self._conds).to_mfol(world, worlds))

    # Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Show.hs">/Data/DRS/Show.hs::showUniverse</a>
    def _show_universe(self, d, notation):
        return d.join([x.var.show(notation) for x in self._refs])

    def _show_conditions(self, notation):
        if len(self._conds) == 0 and notation == SHOW_BOX:
            return u' '
        if notation == SHOW_BOX:
            return u''.join([x.show(notation) for x in self._conds])
        return u','.join([x.show(notation) for x in self._conds])

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Show.hs">/Data/DRS/Show.hs::showDRSBox</a>
    ##
    def show(self, notation):
        """For pretty printing.

        Args:
            notation: An integer notation.

        Returns:
             A unicode string.
        """
        if notation == SHOW_BOX:
            if len(self._refs) == 0:
                ul = u' '
            else:
                ul = self._show_universe(u'  ', notation)
            cl = self._show_conditions(notation).rstrip()
            l = 4 + max(union(map(len, ul.split(u'\n')), map(len, cl.split(u'\n'))))
            top = self.show_horz_line(l, self.boxTopLeft, self.boxTopRight)
            mid = self.show_content(l, ul) + u'\n' + self.show_horz_line(l, self.boxMiddleLeft, self.boxMiddleRight)
            bottom = self.show_content(l, cl) + u'\n' + self.show_horz_line(l, self.boxBottomLeft, self.boxBottomRight)
            return top + mid + bottom
        elif notation == SHOW_LINEAR:
            ul = self._show_universe(',', notation)
            cl = self._show_conditions(notation)
            return u'[' + ul + u'| ' + cl + u']'
        elif notation == SHOW_SET:
            ul = self._show_universe(',', notation)
            cl = self._show_conditions(notation)
            return u'<{' + ul + u'},{' + cl + u'}>'
        cl = self._show_conditions(notation)
        return u'DRS ' + unicode(self._refs) + u' [' + cl + u']'


class Merge(AbstractDRS):
    """A merge between two DRSs"""
    def __init__(self, drsA, drsB):
        if not isinstance(drsA, AbstractDRS) or not isinstance(drsB, AbstractDRS):
            raise TypeError('Merge expects DRS arguments')
        super(Merge, self).__init__()
        if drsA._set_accessible(self) and drsB._set_accessible(self):
            self._drsA = drsA
            self._drsB = drsB
        else:
            self._drsA = drsA.clone()
            self._drsB = drsB.clone()
            assert self._drsA._set_accessible(self)
            assert self._drsB._set_accessible(self)

    def __ne__(self, other):
        return type(self) != type(other) or self._drsA != other._drsA or self._drsB != other._drsB

    def __eq__(self, other):
        return type(self) == type(other) and self._drsA == other._drsA and self._drsB == other._drsB

    def __unicode__(self):
        return '%s %s %s' % (safe_utf8_decode(self._drsA), Showable.opMerge, safe_utf8_decode(self._drsB))

    def __str__(self):
        return b'%s %s %s' % (safe_utf8_encode(self._drsA),
                             safe_utf8_encode(Showable.opMerge), safe_utf8_encode(self._drsB))

    def _set_accessible(self, d):
        if self._accessible_drs is None:
            self._accessible_drs = weakref.ref(d)
            return True
        return False

    def _isproper_subdrsof(self, gd):
        """Help for isproper"""
        return self._drsA._isproper_subdrsof(gd) and self._drsB._isproper_subdrsof(gd)

    def _ispure_helper(self, rs, gd):
        if not self._drsA._ispure_helper(rs, gd): return False
        y = []
        y.extend(rs)
        # TODO: get_variables() no longer uses sets, do we need set()
        y = sorted(set(self._drsA.get_variables(y)))
        return self._drsB._ispure_helper(y, gd)

    @property
    def isempty(self):
        return self._drsA.isempty and self._drsB.isempty

    @property
    def ldrs(self):
        return self._drsA

    @property
    def rdrs(self):
        return self._drsB

    @property
    def ismerge(self):
        """Test whether this DRS is entirely a Merge (at its top-level)."""
        return True

    @property
    def universe(self):
        """Returns the universe of a DRS."""
        return union(self._drsA.universe, self._drsB.universe)

    @property
    def referents(self):
        """Returns the universe of a DRS. Alias for universe property."""
        return union(self._drsA.referents, self._drsB.referents)

    def find_condition(self, c):
        """Search for a condition matching `c`.

        Args:
            c: A condition.

        Returns:
            A tuple of the global DRS, and the found condition or (self,None).
        """
        rc = self._drsA.find_condition(c)
        if rc is None:
            return self._drsB.find_condition(c)
        return rc

    def simplify_props(self):
        """Simplify propositions"""
        Merge(self._drsA.referents.simplify_props(), self._drsB.referents.simplify_props())

    def clone(self):
        return Merge(self._drsA.clone(), self._drsB.clone())

    def find_subdrs(self, d):
        """Test whether d is a direct or indirect subordinate DRS of this DRS and return the found subordinate DRS."""
        return self._drsA.find_subdrs(d) or self._drsB.find_subdrs(d)

    def get_freerefs(self, gd=None):
        """Returns the list of all free DRSRef's in a DRS. If `gd` is set then self must be a subordinate DRS of `gd` and the
        function only returns free referents in domain of DRS between `self` and `gd`.

        Args:
            gd: A global DRS where `self` is a subordinate DRS of `gd`.

        Returns:
            A list of DRSRef instances.
        """
        if gd is None:
            gd = self.global_drs
        u = self._drsA.get_freerefs(gd)
        u.extend(self._drsB.get_freerefs(gd))
        return u

    def resolve_merges(self):
        """Resolves all unresolved merges in a DRS."""
        return merge(self._drsA.resolve_merges(), self._drsB.resolve_merges())

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Variables.hs">/Data/DRS/Variables.hs:drsVariables</a>
    ##
    def get_variables(self, u=None):
        """Returns the list of all bound DRSRef's in this DRS.

        Args:
            u: An initial list. If None `u` is set to [].

        Returns:
            A list of bound DRSRef's unioned with `u`.
        """
        u = self._drsA.get_variables(u)
        return self._drsB.get_variables(u)

    def get_constants(self, u=None):
        """Returns the list of all constant DRSRef's in this DRS.

        Args:
            u: An initial list. If None `u` is set to [].

        Returns:
            A list of constant DRSRef's unioned with `u`.
        """
        u = self._drsA.get_constants(u)
        return self._drsB.get_constants(u)

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Variables.hs">/Data/DRS/Variables.hs:drsUniverses</a>
    ##
    def get_universes(self, u=None):
        """Returns the list of DRSRef's from all universes in this DRS.

        Args:
            u: An initial list. If None `u` is set to [].

        Returns:
            A list of DRSRef's unioned with `u`.
        """
        u = self._drsA.get_universes(u)
        return self._drsB.get_universes(u)

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/LambdaCalculus.hs">/Data/DRS/LambdaCalculus.hs:purifyRefs</a>
    ##
    def purify_refs(self, gd, ers):
        """Replaces duplicate uses of DRSRef's by new DRSRef's.

         Args:
             gd: A global DRS, where `self` is a subordinate DRS of global.
             ers: A list of referents

         Returns:
             A tuple of a new Merge instance and the list of seen referents
         """
        cd1, ers1 = self._drsA.purify_refs(gd, ers)
        cd2, ers2 = self._drsB.purify_refs(gd, ers1)
        return (Merge(cd1, cd2), ers2)

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/LambdaCalculus.hs">/Data/DRS/LambdaCalculus.hs::renameSubDRS</a>
    ##
    def rename_subdrs(self, gd, rs, ps=None):
        """Applies alpha conversion to this DRS, which is a subordinate DRS of the
        global DRS gd, on the basis of a conversion list for DRSRef's rs.

        Args:
            gd: An DRS|Merge instance.
            rs: A list of DRSRef|LambaDRSRef tuples.
            ps: A list of integer tuples. Only used in PDRS implementation.

        Returns:
            A DRS instance.
        """
        return Merge(self._drsA.rename_subdrs(gd, rs), self._drsB.rename_subdrs(gd, rs))

    def subst_subdrs(self, gd, rs):
        """Applies substitution to this DRS, which is a subordinate DRS of the global DRS `gd`, on the basis of the
        conversion list `rs` for DRSRef's .

        Args:
            gd: An DRS|Merge instance.
            rs: A list of DRSRef tuples.

        Returns:
            A DRS instance.
        """
        return Merge(self._drsA.subst_subdrs(gd, rs), self._drsB.subst_subdrs(gd, rs))

    def _show_brackets(self, s):
        # show() helper
        return self.show_modifier(u'(', 2, self.show_concat(s, self.show_padding(u')\n')))

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Show.hs">/Data/DRS/Show.hs::showDRSBox</a>
    ##
    def show(self, notation):
        """For pretty printing.

        Args:
            notation: An integer notation.

        Returns:
             A unicode string.
        """
        if notation == SHOW_BOX:
            return self._show_brackets(self.show_concat(self._drsA.show(notation),
                                            self.show_modifier(self.opMerge, 2, self._drsB.show(notation))))
        elif notation in [SHOW_LINEAR, SHOW_SET]:
            return merge(self._drsA, self._drsB).show(notation)
        return u'Merge (' + self._drsA.show(notation) + ') (' + self._drsB.show(notation) + u')'


## @ingroup gfn
## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Merge.hs">/Data/PDRS/Merge.hs:drsMerge</a>
##
def merge(d1, d2):
    """Applies merge to 'DRS' d1 and 'DRS' d2"""
    if isinstance(d2, Merge):
        return merge(d1, d2.resolve_merges())
    elif isinstance(d1, Merge):
        return merge(d2, d1.resolve_merges())
    else:
        # orig haskell code Merge.hs and Variable.hs
        p1 = d1.resolve_merges().purify()
        p2 = d2.resolve_merges().purify()
        ors = sorted(set(p2.get_variables()).intersection(p1.variables))
        nrs = get_new_drsrefs(ors, sorted(set(p2.get_variables()).union(p1.get_variables())))
        da = p2.alpha_convert(zip(ors,nrs))
        return DRS(union(p1.universe, da.universe), union(p1.conditions, da.conditions))


## @ingroup gfn
## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Variables.hs">/Data/DRS/Variables.hs:newDRSRefs</a>
##
def get_new_drsrefs(ors, ers):
    """Returns a list of new DRSRef's, based on a list of old DRSRef's and a list of existing DRSRef's"""
    if len(ors) == 0:
        return []
    result = []
    for i in range(len(ors)):
        r = ors[i]
        if not isinstance(r, AbstractDRSRef):
            raise TypeError('get_new_drsrefs expects a DRS argument')
        rd = r.increase_new()
        if rd in union(ors[i+1:], ers):
            ors = [x for x in ors[i:]]  # shallow partial copy
            ors[0] = rd
            # FIXME: remove recursion
            result.extend(get_new_drsrefs(ors, ers))
            return result
        else:
            # FIXME: check if we can ue append rather then push front
            y = [rd]
            y.extend(ers)
            ers = y
            result.append(rd)
    return result


class AbstractDRSRef(Showable):
    """Abstract DRS referent"""

    def __init__(self, drsVar):
        self._var = drsVar

    def __hash__(self):
        return hash(self.var.to_string())

    def __str__(self):
        return safe_utf8_encode(self.var.to_string())

    def __repr__(self):
        return unicode(self) if UNICODE_STRINGS else str(self)

    def __unicode__(self):
        return safe_utf8_decode(self.var.to_string())

    @property
    def var(self):
        raise NotImplementedError

    ## @remarks Original code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Binding.hs">/Data/DRS/Binding.hs:drsBoundRef</a>
    ##
    def has_bound(self, ld, gd):
        """Test if this DRSRef is bound in the accessible universes between local DRS `ld` and global DRS `gd`. A
        necessary condition is that `gd` be accessible from `ld`. If any implication exists in the bound between `ld`
        and `gd` then the accessible constraint of the consequent is extended to the antecedent.

        Args:
            ld: A Merge|DRS instance.
            gd: A Merge|DRS instance.

        Returns:
            True if this referent is bound.
        """
        rd = gd.global_drs
        ld = rd.find_subdrs(ld)
        if ld is None or not gd.test_is_accessible_to(ld):
            return False
        u = set(ld.referents)
        while ld != gd:
            ld = ld.accessible_drs
            u = u.union(ld.referents)
        return self in u

    @property
    def isconst(self):
        return False

    @property
    def isresolved(self):
        """Test if this DRS is resolved (containing no unresolved merges)"""
        return False

    # Make public to support fast renaming
    #@property
    #def var(self):
    #    """Converts a DRSRef into a DRSVar."""
    #    raise NotImplementedError

    ## @remarks Original code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Variables.hs">/Data/DRS/Variables.hs:increase</a>
    ##
    def increase_new(self):
        """Adds a trailing integer to the referent to make it unique."""
        raise NotImplementedError

    ## @remarks Required by PDRSRef's
    def to_drsref(self):
        """Convert to a DRSRef. This implementation returns self."""
        return self

    def set_var(self, var):
        assert not self.isconst
        self._var = var


class DRSRef(AbstractDRSRef):
    """DRS referent"""
    def __init__(self, drsVar):
        if isinstance(drsVar, (str, unicode)):
            drsVar = DRSVar(drsVar)
        elif not isinstance(drsVar, (DRSVar, DRSConst)):
            raise TypeError('DRSRef expect string or DRSVar')
        super(DRSRef, self).__init__(drsVar)

    def __ne__(self, other):
        return type(self) != type(other) or self._var != other.var

    def __eq__(self, other):
        return type(self) == type(other) and self._var == other.var

    @property
    def isconst(self):
        return isinstance(self._var, DRSConst)

    @property
    def isresolved(self):
        return True

    @property
    def var(self):
        """Converts a DRSRef into a DRSVar."""
        return self._var

    ## @remarks Original code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Variables.hs">/Data/DRS/Variables.hs:increase</a>
    ##
    def increase_new(self):
        """Adds a trailing integer to the referent to make it unique."""
        if self.isconst:
            pass
        assert not self.isconst
        return DRSRef(self._var.increase_new())


class AbstractDRSRelation(object):
    """Abstract DRS Relation"""

    def __hash__(self):
        return hash(self.to_string())

    ## @remarks Original code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Variables.hs">/Data/DRS/Variables.hs:drsRelToString</a>
    ##
    def to_string(self):
        """Converts this instance into a string."""
        raise NotImplementedError

    def __str__(self):
        return safe_utf8_encode(self.to_string())

    def __unicode__(self):
        return safe_utf8_decode(self.to_string())

    def __repr__(self):
        return unicode(self) if UNICODE_STRINGS else str(self)



class DRSRelation(AbstractDRSRelation):
    """DRS Relation"""
    def __init__(self, name):
        if isinstance(name, (str, unicode)):
            self._name = name
        else:
            raise TypeError('DRSRelation expects a string')

    def __ne__(self, other):
        return type(self) != type(other) or self._name != other._name

    def __eq__(self, other):
        return type(self) == type(other) and self._name == other._name

    ## @remarks Original code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Variables.hs">/Data/DRS/Variables.hs:drsRelToString</a>
    ##
    def to_string(self):
        """Converts this instance into a string."""
        return self._name

    def rename(self, name):
        if isinstance(name, (str, unicode)):
            self._name = name
        else:
            raise TypeError('DRSRelation expects a string')


class AbstractDRSCond(Showable):
    """Abstract DRS Condition"""

    def __hash__(self):
        return hash(unicode(self))

    def __repr__(self):
        return unicode(self) if UNICODE_STRINGS else str(self)

    def _set_accessible(self, d):
        raise NotImplementedError

    def _antecedent(self, ref, drs):
        #  always True == isinstance(drs, DRS)
        return False

    def _isproper_subdrsof(self, sd, gd, pvar=None):
        """Helper for DRS.isproper"""
        return False

    def _get_freerefs(self, ld, gd, pvar=None):
        #  always True == isinstance(ld, DRS) and True == isinstance(gd, DRS)
        return []

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Properties.hs#isPureDRS:pureCons
    def _ispure(self, ld, gd, rs):
        return (False, None)

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Variables.hs#drsUniverses:universes
    def _universes(self, u):
        return u

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/LambdaCalculus.hs#renameCons:convertCon
    def _convert(self, ld, gd, rs, pv=None, ps=None):
        raise NotImplementedError

    def _substitute(self, ld, gd, rs):
        raise NotImplementedError

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/LambdaCalculus.hs#purifyRefs:purify
    def _purify_refs(self, gd, rs, pv=None):
        raise NotImplementedError

    @property
    def isresolved(self):
        """Helper for DRS function of same name."""
        return False

    def simplify_props(self):
        """Simply propositions.

        Returns:
            The referents that were removed.
        """
        raise NotImplementedError

    def find_condition(self, c, gd):
        """Search for a condition matching `c` within global DRS gd."""
        raise NotImplementedError

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Variables.hs">/Data/DRS/Variables.hs:drsVariables:variables</a>
    def get_variables(self, u):
        """Returns the list of all DRSRef's in this condition. This serves as a helper to DRS.get_variables()

        Args:
            u: An initial list. Cannot be None.

        Returns:
            A list of DRSRef's unioned with `u`.
        """
        return u

    def get_constants(self, u):
        """Returns the list of all constant DRSRef's in this condition. This serves as a helper to DRS.get_constants()

        Args:
            u: An initial list. Cannot be None.

        Returns:
            A list of constant DRSRef's unioned with `u`.
        """
        return u

    def clone(self):
        raise NotImplementedError

    def find_subdrs(self, d):
        """Test whether d is a direct or indirect subordinate DRS of this condition and return the found subordinate DRS."""
        return None

    def resolve_merges(self):
        """Helper for DRS function of same name."""
        raise NotImplementedError

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Translate.hs">/Data/DRS/Translate.hs:drsToMFOL:drsConsToMFOL</a>
    ##
    def to_mfol(self, world, worlds):
        """Helper for DRS function of same name."""
        raise NotImplementedError


class Rel(AbstractDRSCond):
    """A relation defined on a set of referents."""
    def __init__(self, drsRel, drsRefs):
        """Constructor.

        Args:
            drsRel: A DRSRelation instance or string. The string will be converted to a DRSRelation.
            drsRefs: Either a list of DRSRefs or a DRSRef.
        """
        if isinstance(drsRefs, AbstractDRSRef):
            drsRefs = [drsRefs]
        elif not iterable_type_check(drsRefs, AbstractDRSRef):
            raise TypeError('Rel expects DRS')
        if isinstance(drsRel, (str, unicode)):
            drsRel = DRSRelation(drsRel)
        if not isinstance(drsRel, AbstractDRSRelation):
            raise TypeError('Rel expects DRSRelation')
        self._rel = drsRel
        self._refs = drsRefs

    def __str__(self):
        return b'%s(%s)' % (str(self._rel), ','.join([str(x) for x in self._refs]))

    def __unicode__(self):
        return u'%s(%s)' % (unicode(self._rel), ','.join([unicode(x) for x in self._refs]))

    def __ne__(self, other):
        return type(self) != type(other) or self._rel != other._rel or not compare_lists_eq(self._refs, other._refs)

    def __eq__(self, other):
        return type(self) == type(other) and self._rel == other._rel and compare_lists_eq(self._refs, other._refs)

    def _set_accessible(self, d):
        return True

    def _get_freerefs(self, ld, gd, pvar=None):
        """Helper for DRS.get_freerefs()"""
        # orig haskell code (Rel _ d:cs) = snd (partition (flip (`drsBoundRef` ld) gd) d) `union` free cs
        return filter(lambda x: not x.has_bound(ld, gd), self._refs)

    def _isproper_subdrsof(self, sd, gd, pvar=None):
        """Helper for DRS.isproper"""
        return all([(x.has_bound(sd, gd)) for x in self._refs])

    def _ispure(self, ld, gd, rs):
        if not _pure_refs(ld, gd, self._refs, rs): return (False, None)
        rs.extend(self._refs)
        return (True, rs)

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/LambdaCalculus.hs#renameCons:convertCon
    def _convert(self, ld, gd, rs, pv=None, ps=None):
        return Rel(self._rel, [rename_var(r,rs) if r.has_bound(ld, gd) else r for r in self._refs])

    def _substitute(self, ld, gd, rs):
        return Rel(self._rel, [rename_var(r,rs) if not r.has_bound(ld, gd) else r for r in self._refs])

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/LambdaCalculus.hs#purifyRefs:purify
    def _purify_refs(self, gd, rs, pv=None):
        rs = union(rs, self._refs)
        return (self, rs)

    @property
    def relation(self):
        """Get the predicate"""
        return self._rel

    @property
    def referents(self):
        """Get the referents in this relation"""
        return [x for x in self._refs]

    @property
    def isresolved(self):
        """Helper for DRS function of same name."""
        return all([x.isresolved for x in self._refs])

    def find_condition(self, c, ld):
        """Search for a condition matching `c` within global DRS gd."""
        if c == self:
            u = set()
            rf = set(self._refs)
            dlast = DRS([],[])
            gd = ld
            while gd is not None and gd != dlast:
                u = u.union(gd.universe)
                rf = rf.difference(u)
                if len(rf) == 0:
                    return ConditionRef(ld, gd, self)
                dlast = gd
                gd = gd.accessible_drs
            return ConditionRef(ld, ld.global_drs, self)
        return None

    def simplify_props(self):
        """Simply propositions.

        Returns:
            The referents that were removed.
        """
        return [self]

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Variables.hs">/Data/DRS/Variables.hs:drsVariables:variables</a>
    def get_variables(self, u):
        """Returns the list of all bound DRSRef's in this condition. This serves as a helper to DRS.get_variables()

        Args:
            u: An initial list. Cannot be None.

        Returns:
            A list of bound DRSRef's unioned with `u`.
        """
        u.extend(filter(lambda x: not x.isconst, self._refs))
        return u

    def get_constants(self, u):
        """Returns the list of all constant DRSRef's in this condition. This serves as a helper to DRS.get_constants()

        Args:
            u: An initial list. Cannot be None.

        Returns:
            A list of constant DRSRef's unioned with `u`.
        """
        u.extend(filter(lambda x: x.isconst, self._refs))
        return u

    def clone(self):
        return self

    def resolve_merges(self):
        """Helper for DRS function of same name."""
        return self

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Translate.hs">/Data/DRS/Translate.hs:drsToMFOL:drsConsToMFOL</a>
    ##
    def to_mfol(self, world, worlds):
        """Helper for DRS function of same name."""
        v = [world]
        v.extend([x.var for x in self._refs])
        return fol.Rel(self._rel.to_string(), v)

    def show(self, notation):
        """Helper for DRS function of same name."""
        if notation == SHOW_BOX:
            return unicode(self._rel) + u'(' + ','.join([x.var.show(notation) for x in self._refs]) + u')\n'
        elif notation in [SHOW_LINEAR, SHOW_SET]:
            return unicode(self._rel) + u'(' + ','.join([x.var.show(notation) for x in self._refs]) + u')'
        return u'Rel (' + unicode(self._rel) + u') (' + ','.join([x.var.show(notation) for x in self._refs]) + u')'


class Neg(AbstractDRSCond):
    """A negated DRS"""
    def __init__(self, drs):
        if not isinstance(drs, AbstractDRS):
            raise TypeError('Neg constructor')
        self._drs = drs

    def __ne__(self, other):
        return type(self) != type(other) or self._drs != other._drs

    def __eq__(self, other):
        return type(self) == type(other) and self._drs == other._drs

    def __str__(self):
        return safe_utf8_encode(Showable.opNeg) + str(self._drs)

    def __unicode__(self):
        return u'%s%s' % (Showable.opNeg, unicode(self._drs))

    def _set_accessible(self, d):
        return self._drs._set_accessible(d)

    def _antecedent(self, ref, drs):
        return self._drs.has_subdrs(drs) and ref.has_bound(drs, self._drs)

    def _ispure(self, ld, gd, rs):
        if not self._drs._ispure_helper(rs, gd): return (False, None)
        # Can modify rs because it will be replaced by caller by the one we pass back
        # TODO: get_variables() no longer uses sets so should we use set()?
        rs = sorted(set(self._drs.get_variables(rs)))
        return True, rs

    def _get_freerefs(self, ld, gd, pvar=None):
        # free (Neg d1:cs) = drsFreeRefs d1 gd `union` free cs
        return self._drs.get_freerefs(gd)

    def _isproper_subdrsof(self, sd, gd, pvar=None):
        """Helper for DRS.isproper"""
        return self._drs._isproper_subdrsof(gd)

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Variables.hs#drsUniverses:universes
    def _universes(self, u):
        return self._drs.get_universes(u)

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/LambdaCalculus.hs#renameCons:convertCon
    def _convert(self, ld, gd, rs, pv=None, ps=None):
        return type(self)(self._drs.rename_subdrs(gd, rs, ps))

    def _substitute(self, ld, gd, rs):
        return type(self)(self._drs.subst_subdrs(gd, rs))

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/LambdaCalculus.hs#purifyRefs:purify
    def _purify_refs(self, gd, rs, pv=None):
        cd1, rs1 = self._drs.purify_refs(gd, rs)
        return type(self)(cd1), rs1

    @property
    def isresolved(self):
        """Helper for DRS function of same name."""
        return self._drs.isresolved

    @property
    def drs(self):
        return self._drs

    def find_condition(self, c, gd):
        """Search for a condition matching `c` within global DRS gd."""
        if c == self:
            u = set()
            rf = set(self._drs.freerefs)
            if len(rf) == 0:
                return ConditionRef(gd, gd, self)
            dlast = DRS([],[])
            d = gd
            while d != dlast:
                u = u.union(d.universe)
                rf = rf.difference(u)
                if len(rf) == 0:
                    return ConditionRef(d, gd, self)
                dlast = d
                d = d.accessible_drs
        return self._drs.find_condition(c)

    def simplify_props(self):
        """Simply propositions.

        Returns:
            The new condition.
        """
        return [type(self)(self._drs.simplify_props())]

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Variables.hs">/Data/DRS/Variables.hs:drsVariables:variables</a>
    def get_variables(self, u):
        """Returns the list of all bound DRSRef's in this condition. This serves as a helper to DRS.get_variables()

        Args:
            u: An initial list. Cannot be None.

        Returns:
            A list of bound DRSRef's unioned with `u`.
        """
        return self._drs.get_variables(u)

    def get_constants(self, u):
        """Returns the list of all constant DRSRef's in this condition. This serves as a helper to DRS.get_constants()

        Args:
            u: An initial list. Cannot be None.

        Returns:
            A list of constant DRSRef's unioned with `u`.
        """
        return self._drs.get_constants(u)

    def clone(self):
        return Neg(self._drs.clone())

    def find_subdrs(self, d):
        """Test whether d is a direct or indirect subordinate DRS of this condition and return the found subordinate DRS."""
        return self._drs.find_subdrs(d)

    def resolve_merges(self):
        """Helper for DRS function of same name."""
        return type(self)(self._drs.resolve_merges())

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Translate.hs">/Data/DRS/Translate.hs:drsToMFOL:drsConsToMFOL</a>
    ##
    def to_mfol(self, world, worlds):
        """Helper for DRS function of same name."""
        return fol.Neg(self._drs.to_mfol(world, worlds))

    def show(self, notation):
        """Helper for DRS function of same name."""
        if notation == SHOW_BOX:
            return self.show_modifier(self.opNeg, 2, self._drs.show(notation))
        elif notation in [SHOW_LINEAR, SHOW_SET]:
            return self.opNeg + self._drs.show(notation)
        return u'Neg (' + self._drs.show(notation) + u')'


class Imp(AbstractDRSCond):
    """An implication between two DRSs"""
    def __init__(self, antecedent, consequent):
        if not isinstance(antecedent, AbstractDRS) or not isinstance(consequent, AbstractDRS):
            raise TypeError('Imp constructor')
        self._drsA = antecedent
        self._drsB = consequent

    def __ne__(self, other):
        return type(self) != type(other) or self._drsA != other._drsA or self._drsB != other._drsB

    def __eq__(self, other):
        return type(self) == type(other) and self._drsA == other._drsA and self._drsB == other._drsB

    def __str__(self):
        return b'%s %s %s' % (str(self._drsA), safe_utf8_encode(Showable.opImp), str(self._drsB))

    def __unicode__(self):
        return u'%s %s %s' % (unicode(self._drsA), Showable.opImp, unicode(self._drsB))

    def _set_accessible(self, d):
        return self._drsA._set_accessible(d) and self._drsB._set_accessible(self._drsA)

    def _antecedent(self, ref, drs):
        return (ref in self._drsA.universe and self._drsB.has_subdrs(drs)) or \
               (self._drsA.has_subdrs(drs) and ref.has_bound(drs, self._drsA)) or \
               (self._drsB.has_subdrs(drs) and ref.has_bound(drs, self._drsB))

    def _get_freerefs(self, ld, gd, pvar=None):
        # free (Imp d1 d2:cs) = drsFreeRefs d1 gd `union` drsFreeRefs d2 gd `union` free cs
        u = self._drsA.get_freerefs(gd)
        u.extend(self._drsB.get_freerefs(gd))
        return u

    def _isproper_subdrsof(self, sd, gd, pvar=None):
        """Helper for DRS.isproper"""
        return self._drsA._isproper_subdrsof(gd) and self._drsB._isproper_subdrsof(gd)

    def _ispure(self, ld, gd, rs):
        if not self._drsA._ispure_helper(rs, gd): return (False, None)
        # TODO: get_variables() no longer uses sets so should we use set()?
        rs = sorted(set(self._drsA.get_variables(rs)))
        if not self._drsB._ispure_helper(rs, gd): return (False, None)
        rs = sorted(set(self._drsB.get_variables(rs)))
        return True, rs

    def _universes(self, u):
        u = self._drsA.get_universes(u)
        return self._drsB.get_universes(u)

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/LambdaCalculus.hs#renameCons:convertCon
    def _convert(self, ld, gd, rs, pv=None, ps=None):
        return type(self)(self._drsA.rename_subdrs(gd, rs, ps), self._drsB.rename_subdrs(gd, rs, ps))

    def _substitute(self, ld, gd, rs):
        return type(self)(self._drsA.subst_subdrs(gd, rs), self._drsB.subst_subdrs(gd, rs))

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/LambdaCalculus.hs#purifyRefs:purify
    def _purify_refs(self, gd, rs, pv=None):
        orsd = intersect(self._drsA.universe, rs)
        nrs = zip(orsd, union_inplace(get_new_drsrefs(orsd, gd.get_variables()), rs))
        # In case we do not want to rename ambiguous bindings:
        # ors = drsUniverses d2 \\ drsUniverse d1 `intersect` rs
        cd1, rs1 = self._drsA.rename_subdrs(gd, nrs).purify_refs(gd, rs)
        cd2, rs2 = self._drsB.rename_subdrs(gd, nrs).purify_refs(gd, rs1)
        return type(self)(cd1,cd2), rs2

    @property
    def isresolved(self):
        """Helper for DRS function of same name."""
        return self._drsA.isresolved and self._drsB.isresolved

    @property
    def antecedent(self):
        """Get the antecedent DRS"""
        return self._drsA

    @property
    def consequent(self):
        """Get the consequent DRS"""
        return self._drsB

    def find_condition(self, c, gd):
        """Search for a condition matching `c` within global DRS gd."""
        if c == self:
            u = set()
            rf = set(self._drsA.freerefs).union(self._drsB.freerefs)
            if len(rf) == 0:
                return ConditionRef(gd, gd, self)
            dlast = DRS([],[])
            d = self._drsB
            while d != dlast:
                u = u.union(d.universe)
                rf = rf.difference(u)
                if len(rf) == 0:
                    return ConditionRef(d, gd, self)
                dlast = d
                d = d.accessible_drs
        x = self._drsA.find_condition(c)
        if x is None:
            return self._drsB.find_condition(c)
        return x

    def simplify_props(self):
        """Simply propositions.

        Returns:
            The new condition.
        """
        return [type(self)(self._drsA.simplify_props(), self._drsB.simplify_props())]

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Variables.hs">/Data/DRS/Variables.hs:drsVariables:variables</a>
    def get_variables(self, u):
        """Returns the list of all bound DRSRef's in this condition. This serves as a helper to DRS.get_variables()

        Args:
            u: An initial list. Cannot be None.

        Returns:
            A list of bound DRSRef's unioned with `u`.
        """
        u = self._drsA.get_variables(u)
        return self._drsB.get_variables(u)

    def get_constants(self, u):
        """Returns the list of all constant DRSRef's in this condition. This serves as a helper to DRS.get_constants()

        Args:
            u: An initial list. Cannot be None.

        Returns:
            A list of constants DRSRef's unioned with `u`.
        """
        u = self._drsA.get_constants(u)
        return self._drsB.get_constants(u)

    def clone(self):
        return Imp(self._drsA.clone(), self._drsB.clone())

    def find_subdrs(self, d):
        """Test whether d is a direct or indirect subordinate DRS of this condition and return the found subordinate DRS."""
        return self._drsA.find_subdrs(d) or self._drsB.find_subdrs(d)

    def resolve_merges(self):
        """Helper for DRS function of same name."""
        return type(self)(self._drsA.resolve_merges(), self._drsB.resolve_merges())

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Translate.hs">/Data/DRS/Translate.hs:drsToMFOL:drsConsToMFOL</a>
    ##
    def to_mfol(self, world, worlds):
        """Helper for DRS function of same name."""
        if not isinstance(self._drsA, DRS):
            raise fol.FOLConversionError
        refs = self._drsA.universe # causes a shallow copy of referents
        f = fol.Imp(conds_to_mfol(self._drsA._conds, world, worlds), self._drsB.to_mfol(world, worlds))
        refs.reverse()
        for r in refs:
            f = fol.ForAll(r.var, f)
        return f

    def show(self, notation):
        """Helper for DRS function of same name."""
        if notation == SHOW_BOX:
            return self.show_concat(self._drsA.show(notation), \
                                    self.show_modifier(self.opImp, 2, self._drsB.show(notation)))
        elif notation in [SHOW_LINEAR, SHOW_SET]:
            return self._drsA.show(notation) + u' ' + self.opImp + u' ' + self._drsB.show(notation)
        return u'Imp (' + self._drsA.show(notation) + u') (' + self._drsB.show(notation) + u')'


class Or(AbstractDRSCond):
    """A disjunction between two DRSs"""
    def __init__(self, drsA, drsB):
        if not isinstance(drsA, AbstractDRS) or not isinstance(drsB, AbstractDRS):
            raise TypeError('Or constructor')
        self._drsA = drsA
        self._drsB = drsB

    def __ne__(self, other):
        return type(self) != type(other) or self._drsA != other._drsA or self._drsB != other._drsB

    def __eq__(self, other):
        return type(self) == type(other) and self._drsA == other._drsA and self._drsB == other._drsB

    def __str__(self):
        return b'%s %s %s' % (str(self._drsA), safe_utf8_encode(Showable.opOr), str(self._drsB))

    def __unicode__(self):
        return u'%s %s %s' % (unicode(self._drsA), Showable.opOr, unicode(self._drsB))

    def _set_accessible(self, d):
        return self._drsA._set_accessible(d) and self._drsB._set_accessible(d)

    def _antecedent(self, ref, drs):
        return (self._drsA.has_subdrs(drs) and ref.has_bound(drs, self._drsA)) or \
               (self._drsB.has_subdrs(drs) and ref.has_bound(drs, self._drsB))

    def _get_freerefs(self, ld, gd, pvar=None):
        # free (Imp d1 d2:cs) = drsFreeRefs d1 gd `union` drsFreeRefs d2 gd `union` free cs
        u = self._drsA.get_freerefs(gd)
        u.extend(self._drsB.get_freerefs(gd))
        return u

    def _isproper_subdrsof(self, sd, gd, pvar=None):
        """Helper for DRS.isproper"""
        return self._drsA._isproper_subdrsof(gd) and self._drsB._isproper_subdrsof(gd)

    def _ispure(self, ld, gd, rs):
        if not self._drsA._ispure_helper(rs, gd): return (False, None)
        # TODO: get_variables() no longer uses sets so should we use set()?
        rs = sorted(set(self._drsA.get_variables(rs)))
        if not self._drsB._ispure_helper(rs, gd): return (False, None)
        rs = sorted(set(self._drsB.get_variables(rs)))
        return True, rs

    def _universes(self, u):
        u = self._drsA.get_universes(u)
        return self._drsB.get_universes(u)

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/LambdaCalculus.hs#renameCons:convertCon
    def _convert(self, ld, gd, rs, pv=None, ps=None):
        return type(self)(self._drsA.rename_subdrs(gd, rs, ps), self._drsB.rename_subdrs(gd, rs, ps))

    def _substitute(self, ld, gd, rs):
        return type(self)(self._drsA.subst_subdrs(gd, rs), self._drsB.subst_subdrs(gd, rs))

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/LambdaCalculus.hs#purifyRefs:purify
    def _purify_refs(self, gd, rs, pv=None):
        orsd = intersect(self._drsA.universe, rs)
        nrs = zip(orsd, union_inplace(get_new_drsrefs(orsd, gd.get_variables()), rs))
        # In case we do not want to rename ambiguous bindings:
        # ors = drsUniverses d2 \\ drsUniverse d1 `intersect` rs
        cd1, rs1 = self._drsA.rename_subdrs(gd, nrs).purify_refs(gd, rs)
        cd2, rs2 = self._drsB.rename_subdrs(gd, nrs).purify_refs(gd, rs1)
        return type(self)(cd1,cd2), rs2

    @property
    def isresolved(self):
        """Helper for DRS function of same name."""
        return self._drsA.isresolved and self._drsB.isresolved

    @property
    def ldrs(self):
        """Get the left DRS operand"""
        return self._drsA

    @property
    def rdrs(self):
        """Get the right DRS operand"""
        return self._drsB

    def find_condition(self, c, gd):
        """Search for a condition matching `c` within global DRS gd."""
        if c == self:
            u = set()
            rf = set(self._drsA.freerefs).union(self._drsB.freerefs)
            if len(rf) == 0:
                return ConditionRef(gd, gd, self)
            dlast = DRS([],[])
            d = gd
            while d != dlast:
                u = u.union(d.universe)
                rf = rf.difference(u)
                if len(rf) == 0:
                    return ConditionRef(d, gd, self)
                dlast = d
                d = d.accessible_drs
        x = self._drsA.find_condition(c)
        if x is None:
            return self._drsB.find_condition(c)
        return x

    def simplify_props(self):
        """Simply propositions.

        Returns:
            The new condition.
        """
        return [type(self)(self._drsA.simplify_props(), self._drsB.simplify_props())]

    def clone(self):
        return Or(self._drsA.clone(), self._drsB.clone())

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Variables.hs">/Data/DRS/Variables.hs:drsVariables:variables</a>
    def get_variables(self, u):
        """Returns the list of all bound DRSRef's in this condition. This serves as a helper to DRS.get_variables()

        Args:
            u: An initial list. Cannot be None.

        Returns:
            A list of bound DRSRef's unioned with `u`.
        """
        u = self._drsA.get_variables(u)
        return self._drsB.get_variables(u)

    def get_constants(self, u):
        """Returns the list of all constant DRSRef's in this condition. This serves as a helper to DRS.get_constants()

        Args:
            u: An initial list. Cannot be None.

        Returns:
            A list of constant DRSRef's unioned with `u`.
        """
        u = self._drsA.get_constants(u)
        return self._drsB.get_constants(u)

    def find_subdrs(self, d):
        """Test whether d is a direct or indirect subordinate DRS of this condition and return the found subordinate DRS."""
        return self._drsA.find_subdrs(d) or self._drsB.find_subdrs(d)

    def resolve_merges(self):
        """Helper for DRS function of same name."""
        return type(self)(self._drsA.resolve_merges(), self._drsB.resolve_merges())

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Translate.hs">/Data/DRS/Translate.hs:drsToMFOL:drsConsToMFOL</a>
    ##
    def to_mfol(self, world, worlds):
        """Helper for DRS function of same name."""
        return fol.Or(self._drsA.to_mfol(world, worlds), self._drsB.to_mfol(world, worlds))

    def show(self, notation):
        """Helper for DRS function of same name."""
        if notation == SHOW_BOX:
            return self.show_concat(self._drsA.show(notation), \
                                    self.show_modifier(self.opOr, 2, self._drsB.show(notation)))
        elif notation in [SHOW_LINEAR, SHOW_SET]:
            return self._drsA.show(notation) + u' ' + self.opOr + u' ' + self._drsB.show(notation)
        return u'Or (' + self._drsA.show(notation) + u') (' + self._drsB.show(notation) + u')'


class Prop(AbstractDRSCond):
    """A proposition DRS"""
    def __init__(self, drsRef, drs):
        if not isinstance(drs, AbstractDRS) or not isinstance(drsRef, AbstractDRSRef):
            raise TypeError('Prop constructor')
        self._drs = drs
        self._ref = drsRef

    def __ne__(self, other):
        return type(self) != type(other) or self._ref != other._ref or self._drs != other._drs

    def __eq__(self, other):
        return type(self) == type(other) and self._ref == other._ref and self._drs == other._drs

    def __unicode__(self):
        return '%s: %s' % (unicode(self._ref), unicode(self._drs))

    def __str__(self):
        return b'%s: %s' % (str(self._ref), str(self._drs))

    def _set_accessible(self, d):
        return self._drs._set_accessible(d)

    def _antecedent(self, ref, drs):
        return self._drs.has_subdrs(drs) and ref.has_bound(drs, self._drs)

    def _get_freerefs(self, ld, gd, pvar=None):
        # free (Prop r d1:cs) = snd (partition (flip (`drsBoundRef` ld) gd) [r]) `union` drsFreeRefs d1 gd `union` free cs
        u = filter(lambda x: not x.has_bound(ld, gd), [self._ref])
        u.extend(self._drs.get_freerefs(gd))
        return u

    def _isproper_subdrsof(self, sd, gd, pvar=None):
        """Helper for DRS.isproper"""
        return self._ref.has_bound(sd, gd) and self._drs._isproper_subdrsof(gd)

    def _ispure(self, ld, gd, rs):
        if not _pure_refs(ld, gd, [self._ref], rs) or not self._drs._ispure_helper(rs, gd):
            return (False, None)
        # TODO: get_variables() no longer uses sets so should we use set()?
        rs = sorted(set(self._drs.get_variables(rs)))
        return True, rs

    def _universes(self, u):
        return self._drs.get_universes(u)

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/LambdaCalculus.hs#renameCons:convertCon
    def _convert(self, ld, gd, rs, pv=None, ps=None):
        return type(self)(rename_var(self._ref,rs) if self._ref.has_bound(ld, gd) else self._ref, self._drs.rename_subdrs(gd, rs, ps))

    def _substitute(self, ld, gd, rs):
        return type(self)(rename_var(self._ref,rs) if not self._ref.has_bound(ld, gd) else self._ref, self._drs.subst_subdrs(gd, rs))

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/LambdaCalculus.hs#purifyRefs:purify
    def _purify_refs(self, gd, rs, pv=None):
        # FIXME: does this really need to be added to front of list
        rs = union([self._ref], rs)
        cd1, rs = self._drs.purify_refs(gd, rs)
        return type(self)(self._ref, cd1), rs

    @property
    def isresolved(self):
        """Helper for DRS function of same name."""
        return self._ref.isresolved and self._drs.isresolved

    @property
    def referent(self):
        """Get the variable (a referent) of this proposition."""
        return self._ref

    @property
    def drs(self):
        """Get the DRS hypothesis in this proposition"""
        return self._drs

    def find_condition(self, c, gd):
        """Search for a condition matching `c` within global DRS gd."""
        if c == self:
            u = set()
            rf = set(self._drs.freerefs)
            rf = rf.union([self._ref])
            dlast = DRS([],[])
            d = gd
            while d != dlast:
                u = u.union(d.universe)
                rf = rf.difference(u)
                if len(rf) == 0:
                    return ConditionRef(d, gd, self)
                dlast = d
                d = d.accessible_drs
        return self._drs.find_condition(c)

    def simplify_props(self):
        """Simply propositions.

        Returns:
            The simplified conditions.
        """
        d = self._drs.simplify_props()
        if len(d.referents) == 1:
            rs = [(d.referents[0], self._ref)]
            d = d.alpha_convert(rs)
            return d.conditions
        else:
            return [type(self)(self._ref, d)]

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Variables.hs">/Data/DRS/Variables.hs:drsVariables:variables</a>
    def get_variables(self, u):
        """Returns the list of all bound DRSRef's in this condition. This serves as a helper to DRS.get_variables()

        Args:
            u: An initial list. Cannot be None.

        Returns:
            A list of bound DRSRef's unioned with `u`.
        """
        if not self._ref.isconst:
            u.append(self._ref)
        return self._drs.get_variables(u)

    def get_constants(self, u):
        """Returns the list of all constant DRSRef's in this condition. This serves as a helper to DRS.get_constants()

        Args:
            u: An initial list. Cannot be None.

        Returns:
            A list of constant DRSRef's unioned with `u`.
        """
        if self._ref.isconst:
            u.append(self._ref)
        return self._drs.get_constants(u)

    def clone(self):
        return Prop(self._ref, self._drs.clone())

    def find_subdrs(self, d):
        """Test whether d is a direct or indirect subordinate DRS of this condition and return the found subordinate DRS."""
        return self._drs.find_subdrs(d)

    def resolve_merges(self):
        """Helper for DRS function of same name."""
        return type(self)(self._ref, self._drs.resolve_merges())

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Translate.hs">/Data/DRS/Translate.hs:drsToMFOL:drsConsToMFOL</a>
    ##
    def to_mfol(self, world, worlds):
        """Helper for DRS function of same name."""
        return fol.And(fol.Acc([world, self._ref.var]), self._drs.to_mfol(world, worlds))

    def show(self, notation):
        """Helper for DRS function of same name."""
        if notation == SHOW_BOX:
            return self.show_modifier(self._ref.var.show(notation) + u':', 2, self._drs.show(notation))
        elif notation in [SHOW_LINEAR, SHOW_SET]:
            return self._ref.var.show(notation) + u': ' + self._drs.show(notation)
        return u'Prop (' + self._ref.var.show(notation) + u') (' + self._drs.show(notation) + u')'


class Diamond(AbstractDRSCond):
    """A possible DRS - possibly among other things."""
    def __init__(self, drs):
        if not isinstance(drs, AbstractDRS):
            raise TypeError('Diamond constructor')
        self._drs = drs

    def __ne__(self, other):
        return type(self) != type(other) or self._drs != other._drs

    def __eq__(self, other):
        return type(self) == type(other) and self._drs == other._drs

    def __unicode__(self):
        return u'%s%s' % (Showable.opDiamond, unicode(self._drs))

    def __str__(self):
        return b'%s%s' % (safe_utf8_encode(Showable.opDiamond), str(self._drs))

    def _set_accessible(self, d):
        return self._drs._set_accessible(d)

    def _get_freerefs(self, ld, gd, pvar=None):
        # free (Neg d1:cs) = drsFreeRefs d1 gd `union` free cs
        return self._drs.get_freerefs(gd)

    def _isproper_subdrsof(self, sd, gd, pvar=None):
        """Helper for DRS.isproper"""
        return self._drs._isproper_subdrsof(gd)

    def _antecedent(self, ref, drs):
        return self._drs.find_subdrs(drs) and ref.find_bound(drs, self._drs)

    def _ispure(self, ld, gd, rs):
        if not self._drs._ispure_helper(rs, gd): return (False, None)
        # Can modify rs because it will be replaced by caller by the one we pass back
        # TODO: get_variables() no longer uses sets so should we use set()?
        rs = sorted(set(self._drs.get_variables(rs)))
        return True, rs

    def _universes(self, u):
        return self._drs.get_universes(u)

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/LambdaCalculus.hs#renameCons:convertCon
    def _convert(self, ld, gd, rs, pv=None, ps=None):
        return type(self)(self._drs.rename_subdrs(gd, rs, ps))

    def _substitute(self, ld, gd, rs):
        return type(self)(self._drs.subst_subdrs(gd, rs))

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/LambdaCalculus.hs#purifyRefs:purify
    def _purify_refs(self, gd, rs, pv=None):
        cd1, rs1 = self._drs.purify_refs(gd, rs)
        return type(self)(cd1), rs1

    @property
    def isresolved(self):
        """Helper for DRS function of same name."""
        return self._drs.isresolved

    @property
    def drs(self):
        return self._drs

    def find_condition(self, c, gd):
        """Search for a condition matching `c` within global DRS gd."""
        if c == self:
            u = set()
            rf = set(self._drs.freerefs)
            if len(rf) == 0:
                return ConditionRef(gd, gd, self)
            dlast = DRS([],[])
            d = gd
            while d != dlast:
                u = u.union(d.universe)
                rf = rf.difference(u)
                if len(rf) == 0:
                    return ConditionRef(d, gd, self)
                dlast = d
                d = d.accessible_drs
        return self._drs.find_condition(c)

    def simplify_props(self):
        """Simply propositions.

        Returns:
            The new condition.
        """
        return type(self)(self._ref, self._drs.simplify_props())

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Variables.hs">/Data/DRS/Variables.hs:drsVariables:variables</a>
    def get_variables(self, u):
        """Returns the list of all bound DRSRef's in this condition. This serves as a helper to DRS.get_variables()

        Args:
            u: An initial list. Cannot be None.

        Returns:
            A list of bound DRSRef's unioned with `u`.
        """
        return self._drs.get_variables(u)

    def get_constants(self, u):
        """Returns the list of all constant DRSRef's in this condition. This serves as a helper to DRS.get_constants()

        Args:
            u: An initial list. Cannot be None.

        Returns:
            A list of constant DRSRef's unioned with `u`.
        """
        return self._drs.get_constants(u)

    def clone(self):
        return Diamond(self._drs.clone())

    def find_subdrs(self, d):
        """Test whether d is a direct or indirect subordinate DRS of this condition and return the found subordinate DRS."""
        return self._drs.find_subdrs(d)

    def resolve_merges(self):
        """Helper for DRS function of same name."""
        return type(self)(self._drs.resolve_merges())

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Translate.hs">/Data/DRS/Translate.hs:drsToMFOL:drsConsToMFOL</a>
    ##
    def to_mfol(self, world, worlds):
        """Helper for DRS function of same name."""
        v = world.increase_new()
        worlds.append(v)
        return fol.Exists(v, fol.And(fol.Acc([world,v]),self._drs.to_mfol(v, worlds)))

    def show(self, notation):
        """Helper for DRS function of same name."""
        if notation == SHOW_BOX:
            return self.show_modifier(self.opDiamond, 2, self._drs.show(notation))
        elif notation in [SHOW_LINEAR, SHOW_SET]:
            return self.opDiamond + self._drs.show(notation)
        return u'Diamond (' + self._drs.show(notation) + u')'


class Box(AbstractDRSCond):
    """A necessary DRS"""
    def __init__(self, drs):
        if not isinstance(drs, AbstractDRS):
            raise TypeError('Box constructor')
        self._drs = drs

    def __ne__(self, other):
        return type(self) != type(other) or self._drs != other._drs

    def __eq__(self, other):
        return type(self) == type(other) and self._drs == other._drs

    def __unicode__(self):
        return u'%s%s' % (Showable.opBox, unicode(self._drs))

    def __str__(self):
        return b'%s%s' % (safe_utf8_encode(Showable.opBox), str(self._drs))

    def _set_accessible(self, d):
        return self._drs._set_accessible(d)

    def _get_freerefs(self, ld, gd, pvar=None):
        # free (Neg d1:cs) = drsFreeRefs d1 gd `union` free cs
        return self._drs.get_freerefs(gd)

    def _isproper_subdrsof(self, sd, gd, pvar=None):
        """Helper for DRS.isproper"""
        return self._drs._isproper_subdrsof(gd)

    def _antecedent(self, ref, drs):
        return self._drs.has_subdrs(drs) and ref.has_bound(drs, self._drs)

    def _ispure(self, ld, gd, rs):
        if not self._drs._ispure_helper(rs, gd): return (False, None)
        # Can modify rs because it will be replaced by caller by the one we pass back
        # TODO: get_variables() no longer uses sets so should we use set()?
        rs = sorted(set(self._drs.get_variables(rs)))
        return True, rs

    def _universes(self, u):
        return self._drs.get_universes(u)

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/LambdaCalculus.hs#renameCons:convertCon
    def _convert(self, ld, gd, rs, pv=None, ps=None):
        return type(self)(self._drs.rename_subdrs(gd, rs, ps))

    def _substitute(self, ld, gd, rs):
        return type(self)(self._drs.subst_subdrs(gd, rs))

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/LambdaCalculus.hs#purifyRefs:purify
    def _purify_refs(self, gd, rs, pv=None):
        cd1, rs1 = self._drs.purify_refs(gd, rs)
        return type(self)(cd1), rs1

    @property
    def isresolved(self):
        """Helper for DRS function of same name."""
        return self._drs.isresolved

    @property
    def drs(self):
        return self._drs

    def find_condition(self, c, gd):
        """Search for a condition matching `c` within global DRS gd."""
        if c == self:
            u = set()
            rf = set(self._drs.freerefs)
            if len(rf) == 0:
                return ConditionRef(gd, gd, self)
            dlast = DRS([],[])
            d = gd
            while d != dlast:
                u = u.union(d.universe)
                rf = rf.difference(u)
                if len(rf) == 0:
                    return ConditionRef(d, gd, self)
                dlast = d
                d = d.accessible_drs
        return self._drs.find_condition(c)

    def simplify_props(self):
        """Simply propositions.

        Returns:
            The simplfied condition.
        """
        return type(self)(self._ref, self._drs.simplify_props())

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Variables.hs">/Data/DRS/Variables.hs:drsVariables:variables</a>
    def get_variables(self, u):
        """Returns the list of all bound DRSRef's in this condition. This serves as a helper to DRS.get_variables()

        Args:
            u: An initial list. Cannot be None.

        Returns:
            A list of bound DRSRef's unioned with `u`.
        """
        return self._drs.get_variables(u)

    def get_constants(self, u):
        """Returns the list of all constant DRSRef's in this condition. This serves as a helper to DRS.get_constants()

        Args:
            u: An initial list. Cannot be None.

        Returns:
            A list of constant DRSRef's unioned with `u`.
        """
        return self._drs.get_constants(u)

    def clone(self):
        return Box(self._drs.clone())

    def find_subdrs(self, d):
        """Test whether d is a direct or indirect subordinate DRS of this condition and return the found subordinate DRS."""
        return self._drs.find_subdrs(d)

    def resolve_merges(self):
        """Helper for DRS function of same name."""
        return type(self)(self._drs.resolve_merges())

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Translate.hs">/Data/DRS/Translate.hs:drsToMFOL:drsConsToMFOL</a>
    ##
    def to_mfol(self, world, worlds):
        """Helper for DRS function of same name."""
        v = world.increase_new()
        worlds.append(v)
        return fol.ForAll(v, fol.Imp(fol.Acc([world,v]),self._drs.to_mfol(v, worlds)))

    def show(self, notation):
        """Helper for DRS function of same name."""
        if notation == SHOW_BOX:
            return self.show_modifier(self.opBox, 2, self._drs.show(notation))
        elif notation in [SHOW_LINEAR, SHOW_SET]:
            return self.opBox + self._drs.show(notation)
        return u'Box (' + self._drs.show(notation) + u')'
