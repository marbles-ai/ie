from utils import iterable_type_check, union, union_inplace, intersect, rename_var, compare_lists_eq
from common import SHOW_BOX, SHOW_LINEAR, SHOW_SET, SHOW_DEBUG
from common import DRSVar, LambdaDRSVar, Showable
import fol
import weakref


WORLD_VAR = 'w'
WORLD_REL = 'Acc'


class LambdaTuple(object):
    """Lambda DRS tuple"""
    def __init__(self, lambdaVar, pos):
        """A lambda tuple.

        Args:
            lambdaVar: A LambdaDRSVar instance.
            pos: Argument position.
        """
        if not isinstance(lambdaVar, LambdaDRSVar):
            raise TypeError
        self._var = lambdaVar
        self._pos = pos

    def __ne__(self, other):
        return type(self) != type(other) or self._var != other._var or self._pos != other._pos

    def __eq__(self, other):
        return type(self) == type(other) and self._var == other._var and self._pos == other._pos

    def __repr__(self):
        return 'LambdaTuple(%s,%i)' % (repr(self._var), self._pos)

    def __hash__(self):
        return hash(self.__repr__())

    def __lt__(self, other):
        return self._pos < other._pos or (self._pos == other._pos and self._var < other._var)

    def __le__(self, other):
        return self._pos < other._pos or (self._pos == other._pos and self._var <= other._var)

    def __gt__(self, other):
        return not self.__le__(other)

    def __ge__(self, other):
        return not self.__lt__(other)

    @property
    def var(self):
        return self._var


# Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Properties.hs#isPureDRS:pureRefs
def _pure_refs(ld, gd, rs, srs):
    return all([(r.has_bound(ld, gd) or r not in srs) for r in rs])


class AbstractDRS(Showable):
    """Abstract Core Discourse Representation Structure for DRS and PDRS"""
    def __init__(self):
        self._accessible_drs = None

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
        """Returns the universe of referents accessible from this DRS."""
        u = set()
        g = self
        while g is not None:
            u = u.union(g.referents)
            g = g.accessible_drs
        return sorted(u)

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Structure.hs">/Data/DRS/Structure.hs:isResolvedDRS</a>
    ## and <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Structure.hs">/Data/PDRS/Structure.hs:isResolvedPDRS</a>.
    ##
    @property
    def isresolved(self):
        """Test whether this DRS is resolved (containing no unresolved merges or lambdas)."""
        return False

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Structure.hs">/Data/DRS/Structure.hs:isLambdaDRS</a>
    ## and <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Structure.hs">/Data/PDRS/Structure.hs:isLambdaPDRS</a>.
    ##
    @property
    def islambda(self):
        """Test whether this DRS is entirely a 'LambdaDRS' (at its top-level)."""
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

    def find_subdrs(self, d):
        """Test whether d is a direct or indirect sub-DRS of this DRS and return the found sub-DRS."""
        return None

    def test_is_accessible_to(self, d):
        """Test whether this DRS is accessible to d."""
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
        """Returns whether d is a direct or indirect sub-DRS of this DRS"""
        return self.find_subdrs(d) is not None

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Binding.hs">/Data/DRS/Binding.hs:drsFreeRefs</a>.
    ##
    def get_freerefs(self, gd=None):
        """Returns the list of all free DRSRef's in a DRS.

        Args:
            gd: A global DRS where `self` is a sub-DRS of `gd`.

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
        """Returns the list of all DRSRef's in this DRS (equals getUniverses getFreeRefs).

        Args:
            u: An initial list. If None `u` is set to [].

        Returns:
            A list of DRSRef's unioned with `u`.
        """
        if u is None: return []
        return u

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
        if u is None: return []
        return u

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Variables.hs">/Data/DRS/Variables.hs:drsLambdas</a>
    ## and <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Variables.hs">/Data/PDRS/Variables.hs:pdrsLambdaVars</a>.
    ##
    def get_lambdas(self):
        """Get the ordered list of all lambda variables in this DRS.

        Returns:
            A list of LambdaVar instances.
        """
        s = self.get_lambda_tuples()
        lts = sorted(s)
        return [x.var for x in lts]

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Variables.hs">/Data/DRS/Variables.hs:lambdas</a>
    ## and <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Variables.hs">/Data/PDRS/Variables.hs:pdrsLambdas</a>.
    ## @remarks Helper for get_lambdas().
    ##
    def get_lambda_tuples(self, u=None):
        """Returns the set of all lambda tuples in this DRS.

        Args:
            u: An initial set of tuples. If not present `u` is set to `set()`.

        Returns:
            A set of LambdaTuple instances union'ed with `u`.
        """
        raise NotImplementedError

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/LambdaCalculus.hs">/Data/DRS/LambdaCalculus.hs:purifyRefs</a>
    ## and <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/RDRS/LambdaCalculus.hs">/Data/RDRS/LambdaCalculus.hs:purifyPRefs</a>.
    ##
    def purify_refs(self, gd, rs):
        """Replaces duplicate uses of DRSRef's by new DRSRef's.

        Args:
            gd: A global DRS, where `self` is a sub-DRS of global.
            rs: A list of referents

        Returns:
            A tuple of a new DRS instance and a list of referents seen.
        """
        raise NotImplementedError

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/LambdaCalculus.hs">/Data/DRS/LambdaCalculus.hs:drsAlphaConvert</a>
    ## and <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/LambdaCalculus.hs">/Data/PDRS/LambdaCalculus.hs:pdrsAlphaConvert</a>.
    ##
    def alpha_convert(self, rs, ps=None):
        """Applies alpha conversion to this DRS on the basis of the conversion list `rs` for DRSRef's and the conversion
        list `ps` for PVar's.

        Args:
            gd: An DRS|LambdaDRS|Merge instance.
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
        """Applies alpha conversion to this DRS, which is a sub-DRS of the global DRS `gd`, on the basis of the
        conversion list `rs` for DRSRef's and the conversion list `ps` for PVar's.

        Args:
            gd: An DRS|LambdaDRS|Merge instance.
            rs: A list of DRSRef|LambaDRSRef tuples.
            ps: A list of integer tuples. Cannot be None in PDRS implementation but we
                have to reproduce the type declaration of AbstractDRS.

        Returns:
            A DRS instance.
        """
        raise NotImplementedError

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Properties.hs">/Data/DRS/Properties.hs:isFOLDRS</a>.
    ##
    @property
    def isfol(self):
        """Test whether this DRS can be translated into a FOLForm instance."""
        return self.isresolved and self.ispure and self.isproper

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
            An ie.fol.FOLForm instance.

        Raises:
            ie.fol.FOLConversionError
        """
        return self.to_mfol(WORLD_VAR)

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Translate.hs">/Data/DRS/Translate.hs:drsToMFOL</a>
    ##
    def to_mfol(self, world):
        """Converts a DRS to a modal FOL formula with world

        Args:
            world: A ie.fol.FOLVar instance

        Returns:
            An ie.fol.FOLForm instance.

        Raises:
            ie.fol.FOLConversionError
        """
        raise fol.FOLConversionError('infelicitous FOL formula')


class LambdaDRS(AbstractDRS):
    """A lambda DRS."""

    def __init__(self, lambdaVar, pos):
        """A lambda DRS.

        Args:
            lambdaVar: A LambdaDRSVar instance.
            pos: Argument position.
        """
        if not isinstance(lambdaVar, LambdaDRSVar):
            raise TypeError
        super(LambdaDRS, self).__init__()
        self._var = lambdaVar
        self._pos = pos

    def __ne__(self, other):
        return type(self) != type(other) or self._var != other._var or self._pos != other._pos

    def __eq__(self, other):
        return type(self) == type(other) and self._var == other._var and self._pos == other._pos

    def __repr__(self):
        return 'LambdaDRS(%s,%i)' % (repr(self._var), self._pos)

    def _isproper_subdrsof(self, d):
        """Help for isproper"""
        return True

    def _ispure_helper(self, rs, gd):
        """Help for isproper"""
        return True

    @property
    def isresolved(self):
        """Test whether this DRS is resolved (containing no unresolved merges or lambdas)"""
        return False

    @property
    def islambda(self):
        """Test whether this DRS is entirely a LambdaDRS (at its top-level)."""
        return True

    def resolve_merges(self):
        """Resolves all unresolved merges in this DRS."""
        return self

    def get_lambda_tuples(self, u=None):
        """Returns the set of all lambda tuples in this DRS.

        Args:
            u: An initial set of tuples. If not present `u` is set to `set()`.

        Returns:
            The set of LambdaTuple instances union'ed with `u`.
        """
        lt = LambdaTuple(self._var, self._pos)
        if u is None: return set([lt])
        u.add(lt)
        return u

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/LambdaCalculus.hs">/Data/DRS/LambdaCalculus.hs:purifyRefs</a>
    ##
    def purify_refs(self, gd, rs):
        """Replaces duplicate uses of DRSRef's by new DRSRef's. For a Lambda DRS
        this function does nothing.

        Args:
            gd: A global DRS, where `self` is a sub-DRS of global.
            rs: A list of referents.

        Returns:
             A tuple of (`self`, `ers`).
         """
        return (self, rs)

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/LambdaCalculus.hs">/Data/DRS/LambdaCalculus.hs::renameSubDRS</a>
    ##
    def rename_subdrs(self, gd, rs, ps=None):
        """Applies alpha conversion to this DRS, which is a sub-DRS of the
        global DRS gd, on the basis of a conversion list for DRSRef's rs.

        Args:
            gd: An DRS|LambdaDRS|Merge instance.
            rs: A list of DRSRef|LambaDRSRef tuples.
            ps: A list of integer tuples. Only used in PDRS implementation.

        Returns:
            This instance.
        """
        return self

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
            return self._var.show(notation) + u'\n'
        elif notation in [SHOW_LINEAR, SHOW_SET]:
            return self._var.show(notation)
        return u'LambdaDRS ' + self._var.to_string().decode('utf-8')


def conds_to_mfol(conds, world):
    """Converts a list of DRS conditions to a modal FOL formula with world"""
    if len(conds) == 0:
        return fol.Top()
    if len(conds) == 1:
        return conds[0].to_mfol(world)
    else:
        f = fol.And(conds[-1].to_mfol(world), conds[-2].to_mfol(world))
        for i in reversed(range(len(conds) - 2)):
            f = fol.And(conds[i].to_mfol(world), f)
        return f


class DRS(AbstractDRS):
    """Default DRS"""
    def __init__(self, drsRefs, drsConds):
        if not iterable_type_check(drsRefs, AbstractDRSRef) or not iterable_type_check(drsConds, AbstractDRSCond):
            raise TypeError
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
                c._set_accessible(self)

    def __ne__(self, other):
        return type(self) != type(other) or not compare_lists_eq(self._refs, other._refs) \
               or not compare_lists_eq(self._conds, other._conds)

    def __eq__(self, other):
        return type(self) == type(other) and compare_lists_eq(self._refs, other._refs) \
               and compare_lists_eq(self._conds, other._conds)

    def __repr__(self):
        return 'DRS(%s,%s)' % (repr(self._refs), repr(self._conds))

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
    def referents(self):
        """Similar to universe but will only returns referents for a DRS."""
        return [x for x in self._refs] # shallow copy

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
        """Test whether this DRS is resolved (containing no unresolved merges or lambdas)"""
        return all([x.isresolved for x in self._refs]) and all([x.isresolved for x in self._conds])

    def clone(self):
        return DRS(self._refs, [c.clone() for c in self._conds])

    def find_subdrs(self, d):
        """Test whether d is a direct or indirect sub-DRS of this DRS and return the found sub-DRS."""
        if self == d:
            return self
        for c in self._conds:
            x = c.find_subdrs(d)
            if x is not None:
                return x
        return None

    def get_freerefs(self, gd=None):
        """Returns the list of all free DRSRef's in a DRS. If `gd` is set then self must be a sub-DRS of `gd` and the
        function only returns free referents in the accessible domain of DRS between `self` and `gd`.

        Args:
            gd: A global DRS where `self` is a sub-DRS of `gd`. Default is self.global_drs

        Returns:
            A list of DRSRef instances.
        """
        if gd is None:
            gd = self.global_drs
        y = set()
        for c in self._conds:
            y = y.union(c._get_freerefs(self, gd))
        return sorted(y)

    def resolve_merges(self):
        """Resolves all unresolved merges in this DRS."""
        return DRS(self._refs, [x.resolve_merges() for x in self._conds])

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Variables.hs">/Data/DRS/Variables.hs:drsVariables</a>
    ##
    def get_variables(self, u=None):
        """Returns the list of all DRSRef's in this DRS. Equivalent to get_freevars() union get_universes()

        Args:
            u: An initial list. If None `u` is set to [].

        Returns:
            A list of DRSRef's unioned with `u`.
        """
        if u is None:
            u = set(self._refs) # shallow copy
        else:
            u = set(self._refs).union(u)
        for c in self._conds:
            u = c.get_variables(u)
        return sorted(u)

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

    def get_lambda_tuples(self, u=None):
        """Returns the set of all lambda tuples in this DRS.

        Args:
            u: An initial set of tuples. If not present `u` is set to `set()`.

        Returns:
            The set of LambdaTuple instances union'ed with `u`.
        """
        if u is None:
            u = set()
        for r in self._refs:
            u = r._lambda_tuple(u)
        for c in self._conds:
            u = c._lambda_tuple(u)
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
             gd: A global DRS, where `self` is a sub-DRS of global.
             ers: A list of referents

         Returns:
             A tuple of a new DRS instance and the list of seen referents

         See Also:
             purify()
         """

        # In case we do not want to rename ambiguous bindings:
        # purifyRefs (ld@(DRS u _),ers) gd = (DRS u1 c2,u1 ++ ers1)
        ors = intersect(self._refs, ers)
        d = self.alpha_convert(zip(ors, get_new_drsrefs(ors, union_inplace(gd.get_variables(),ers))))
        r = union(d.universe, ers)
        conds = []
        for c in d._conds:
            x,r = c._purify_refs(gd, r)
            conds.append(x)
        return DRS(d.universe,conds), r

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/LambdaCalculus.hs">/Data/DRS/LambdaCalculus.hs::renameSubDRS</a>
    ##
    def rename_subdrs(self, gd, rs, ps=None):
        """Applies alpha conversion to this DRS, which is a sub-DRS of the
        global DRS gd, on the basis of a conversion list for DRSRef's rs.

        Args:
            gd: An DRS|LambdaDRS|Merge instance.
            rs: A list of DRSRef|LambaDRSRef tuples.
            ps: A list of integer tuples. Only used in PDRS implementation.

        Returns:
            A DRS instance.
        """
        return DRS([rename_var(r, rs) for r in self._refs], \
                   [c._convert(self, gd, rs) for c in self._conds])

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Translate.hs">/Data/DRS/Translate.hs:drsToMFOL</a>
    ##
    def to_mfol(self, world):
        """Converts a DRS to a modal FOL formula with world

        Args:
            world: A ie.fol.FOLVar instance

        Returns:
            An ie.fol.FOLForm instance.

        Raises:
            ie.fol.FOLConversionError
        """
        if len(self._refs) == 0:
            return conds_to_mfol(self._conds, world)
        # FIXME: remove recursion
        return fol.Exists(fol.FOLVar(self._refs[0].var), DRS(self._refs[1:], self._conds).to_mfol(world))

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
            cl = self._show_conditions(notation) + u'\n'
            l = 4 + max(union(map(len, ul.split(u'\n')), map(len, cl.split(u'\n'))))
            return self.show_horz_line(l, self.boxTopLeft, self.boxTopRight) + \
                   self.show_content(l, ul) + u'\n' + self.show_horz_line(l, self.boxMiddleLeft, self.boxMiddleRight) + \
                   self.show_content(l, cl) + u'\n' + self.show_horz_line(l, self.boxBottomLeft, self.boxBottomRight)
        elif notation == SHOW_LINEAR:
            ul = self._show_universe(',', notation)
            cl = self._show_conditions(notation)
            return u'[' + ul + u': ' + cl + u']'
        elif notation == SHOW_SET:
            ul = self._show_universe(',', notation)
            cl = self._show_conditions(notation)
            return u'<{' + ul + u'},{' + cl + u'}>'
        cl = self._show_conditions(notation)
        return u'DRS ' + str(self._refs).decode('utf-8') + u' [' + cl + u']'


class Merge(AbstractDRS):
    """A merge between two DRSs"""
    def __init__(self, drsA, drsB):
        if not isinstance(drsA, AbstractDRS) or not isinstance(drsB, AbstractDRS):
            raise TypeError
        super(Merge, self).__init__()
        if drsA._set_accessible(self) and drsB._set_accessible(self):
            self._drsA = drsA
            self._drsB = drsB
        else:
            self._drsA = drsA.clone()
            self._drsB = drsB.clone()
            self._drsA._set_accessible(self)
            self._drsB._set_accessible(self)

    def __ne__(self, other):
        return type(self) != type(other) or self._drsA != other._drsA or self._drsB != other._drsB

    def __eq__(self, other):
        return type(self) == type(other) and self._drsA == other._drsA and self._drsB == other._drsB

    def __repr__(self):
        return 'Merge(%s,%s)' % (repr(self._drsA), repr(self._drsB))

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
        y = self._drsA.get_variables(y)
        return self._drsB._ispure_helper(y, gd)

    @property
    def ldrs(self):
        return self._drsA

    @property
    def rdrs(self):
        return self._drsB

    @property
    def islambda(self):
        """test whether this DRS is entirely a LambdaDRS (at its top-level)."""
        return self._drsA.islambda and self._drsB.islambda

    @property
    def ismerge(self):
        """Test whether this DRS is entirely a Merge (at its top-level)."""
        return True

    @property
    def universe(self):
        """Returns the universe of a DRS."""
        return union(self._drsA.universe, self._drsB.universe)

    def clone(self):
        return Merge(self._drsA.clone(), self._drsB.clone())

    def find_subdrs(self, d):
        """Test whether d is a direct or indirect sub-DRS of this DRS"""
        return self._drsA.find_subdrs(d) or self._drsB.find_subdrs(d)

    def get_freerefs(self, gd=None):
        """Returns the list of all free DRSRef's in a DRS. If `gd` is set then self must be a sub-DRS of `gd` and the
        function only returns free referents in domain of DRS between `self` and `gd`.

        Args:
            gd: A global DRS where `self` is a sub-DRS of `gd`.

        Returns:
            A list of DRSRef instances.
        """
        if gd is None:
            gd = self.global_drs
        return union(self._drsA.get_freerefs(gd), self._drsB.get_freerefs(gd))

    def resolve_merges(self):
        """Resolves all unresolved merges in a DRS."""
        return merge(self._drsA.resolve_merges(), self._drsB.resolve_merges())

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Variables.hs">/Data/DRS/Variables.hs:drsVariables</a>
    ##
    def get_variables(self, u=None):
        """Returns the list of all DRSRef's in this DRS (equals getUniverses getFreeRefs).

        Args:
            u: An initial list. If None `u` is set to [].

        Returns:
            A list of DRSRef's unioned with `u`.
        """
        u = self._drsA.get_variables(u)
        return self._drsB.get_variables(u)

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

    def get_lambda_tuples(self, u=None):
        """Returns the set of all lambda tuples in this DRS.

        Args:
            u: An initial set of tuples. If not present `u` is set to `set()`.

        Returns:
            The set of LambdaTuple instances union'ed with `u`.
        """
        u = self._drsA.get_lambda_tuples(u)
        return self._drsB.get_lambda_tuples(u)

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/LambdaCalculus.hs">/Data/DRS/LambdaCalculus.hs:purifyRefs</a>
    ##
    def purify_refs(self, gd, ers):
        """Replaces duplicate uses of DRSRef's by new DRSRef's.

         Args:
             gd: A global DRS, where `self` is a sub-DRS of global.
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
        """Applies alpha conversion to this DRS, which is a sub-DRS of the
        global DRS gd, on the basis of a conversion list for DRSRef's rs.

        Args:
            gd: An DRS|LambdaDRS|Merge instance.
            rs: A list of DRSRef|LambaDRSRef tuples.
            ps: A list of integer tuples. Only used in PDRS implementation.

        Returns:
            A DRS instance.
        """
        return Merge(self._drsA.rename_subdrs(gd, rs), self._drsA.rename_subdrs(gd, rs))

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
            if self._drsA.islambda and self._drsB.islambda:
                self.show_modifier(u'(', 0, self.show_concat(self.show_concat(self._drsA.show(notation), \
                                            self.show_modifier(self.opMerge, 0, self._drsB.show(notation))), u')'))
            elif not self._drsA.islambda and self._drsB.islambda:
                return self._show_brackets(self.show_concat(self._drsA.show(notation),
                                            self.show_modifier(self.opMerge, 2, self._drsA.show(notation))))
            elif self._drsA.islambda and not self._drsB.islambda:
                self._show_brackets(self.show_concat(self.show_padding(self._drsA.show(notation)),
                                            self.show_modifier(self.opMerge, 2, self._drsB.show(notation))))
            return self._show_brackets(self.show_concat(self._drsA.show(notation),
                                            self.show_modifier(self.opMerge, 2, self._drsB.show(notation))))
        elif notation in [SHOW_LINEAR, SHOW_SET]:
            if not self._drsA.islambda and not self._drsB.islambda:
                return merge(self._drsA, self._drsB).show(notation)
            return self._drsA.show(notation) + u' ' + self.opMerge + u' ' + self._drsB.show(notation)
        return u'Merge (' + self._drsA.show(notation) + ') (' + self._drsB.show(notation) + u')'


## @ingroup gfn
## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Merge.hs">/Data/PDRS/Merge.hs:drsMerge</a>
##
def merge(d1, d2):
    """Applies merge to 'DRS' d1 and 'DRS' d2"""
    if isinstance(d2, LambdaDRS) or isinstance(d1, LambdaDRS):
        return Merge(d1, d2)
    elif isinstance(d2, Merge):
        if d2.ldrs.islambda:
            return Merge(d2.ldrs, merge(d1, d2.rdrs))
        elif d2.rdrs.islambda:
            return Merge(merge(d1, d2.ldrs), d2.rdrs)
        else:
            return merge(d1, d2.resolve_merges())
    elif isinstance(d1, Merge):
        if d1.ldrs.islambda:
            return Merge(d1.ldrs, merge(d1.rdrs, d2))
        elif d1.rdrs.islambda:
            return Merge(d1.rdrs, merge(d1.ldrs, d2))
        else:
            return merge(d2, d1.resolve_merges())
    else:
        # orig haskell code Merge.hs and Variable.hs
        p1 = d1.resolve_merges().purify()
        p2 = d2.resolve_merges().purify()
        ors = intersect(p2.get_variables(), p1.get_variables())
        nrs = get_new_drsrefs(ors, union(p2.get_variables(), p1.get_variables()))
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
            raise TypeError
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

    # Helper for DRS.get_lambda_tuples()
    def _lambda_tuple(self, u):
        raise NotImplementedError

    def __hash__(self):
        return hash(self.__repr__())

    ## @remarks Original code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Binding.hs">/Data/DRS/Binding.hs:drsBoundRef</a>
    ##
    def has_bound(self, ld, gd):
        """Test if this DRSRef is bound in the accessible universes between local DRS `ld` and global DRS `gd`. A
        necessary condition is that `gd` be accessible from `ld`. If any implication exists in the bound between `ld`
        and `gd` then the accessible constraint of the consequent is extended to the antecedent.

        Args:
            ld: A LambdaDRS|Merge|DRS instance.
            gd: A LambdaDRS|Merge|DRS instance.

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
        '''
        if isinstance(ld, LambdaDRS):
            return False
        elif isinstance(ld, Merge):
            return self.has_bound(ld.ldrs, gd) or self.has_bound(ld.rdrs, gd)
        elif isinstance(gd, LambdaDRS):
            return False
        elif isinstance(gd, Merge):
            return self.has_bound(ld, gd.ldrs) or self.has_bound(ld, gd.rdrs)
        elif isinstance(ld, DRS) and isinstance(gd, DRS):
            # PWG: Original haskell code did not check accessibility which is incorrect.
            if self in ld.universe or self in gd.universe:
                return gd.test_is_accessible_to(ld)
            return any([x._antecedent(self, ld) for x in gd.conditions])
        else:
            raise TypeError
        '''

    @property
    def isresolved(self):
        """Test if this DRS is resolved (containing no unresolved merges or lambdas)"""
        return False

    ## @remarks Original code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Variables.hs">/Data/DRS/Variables.hs:drsRefToDRSVar</a>
    ##
    @property
    def var(self):
        """Converts a DRSRef into a DRSVar."""
        raise NotImplementedError

    ## @remarks Original code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Variables.hs">/Data/DRS/Variables.hs:increase</a>
    ##
    def increase_new(self):
        """Adds a trailing integer to the referent to make it unique."""
        raise NotImplementedError

    ## @remarks Required by PDRSRef's
    def to_drsref(self):
        """Convert to a DRSRef. This implementation returns self."""
        return self


class LambdaDRSRef(AbstractDRSRef):
    """Lambda DRS referent"""
    def __init__(self, lambdaVar, pos):
        """A lambda DRSRef.

        Args:
            lambdaVar: A LambdaDRSVar instance.
            pos: Argument position.
        """
        if not isinstance(lambdaVar, LambdaDRSVar):
            raise TypeError
        self._var = lambdaVar
        self._pos = pos

    def __ne__(self, other):
        return type(self) != type(other) or self._var != other._var or self._pos != other._pos

    def __eq__(self, other):
        return type(self) == type(other) and self._var == other._var and self._pos == other._pos

    def __repr__(self):
        return 'LambdaDRSRef(%s,%i)' % (self._var.var, self._pos)

    # Helper for DRS.get_lambda_tuples()
    def _lambda_tuple(self, u):
        """Adds a trailing integer to the referent to make it unique."""
        u.add(LambdaTuple(self._var, self._pos))
        return u

    ## @remarks Original code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Variables.hs">/Data/DRS/Variables.hs:drsRefToDRSVar</a>
    ##
    @property
    def var(self):
        """Converts a DRSRef into a DRSVar."""
        return self._var.var


class DRSRef(AbstractDRSRef):
    """DRS referent"""
    def __init__(self, drsVar):
        if isinstance(drsVar, str):
            drsVar = DRSVar(drsVar)
        elif not isinstance(drsVar, DRSVar):
            raise TypeError
        self._var = drsVar

    def __ne__(self, other):
        return type(self) != type(other) or self._var != other._var

    def __eq__(self, other):
        return type(self) == type(other) and self._var == other._var

    def __repr__(self):
        return 'DRSRef(%s)' % self._var

    # Helper for DRS.get_lambda_tuples()
    def _lambda_tuple(self, u):
        return u

    @property
    def isresolved(self):
        return True

    ## @remarks Original code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Variables.hs">/Data/DRS/Variables.hs:drsRefToDRSVar</a>
    ##
    @property
    def var(self):
        """Converts a DRSRef into a DRSVar."""
        return self._var

    ## @remarks Original code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Variables.hs">/Data/DRS/Variables.hs:increase</a>
    ##
    def increase_new(self):
        """Adds a trailing integer to the referent to make it unique."""
        return DRSRef(self._var.increase_new())


class AbstractDRSRelation(object):
    """Abstract DRS Relation"""

    # Helper for DRS.get_lambda_tuples()
    def _lambda_tuple(self, u):
        raise NotImplementedError

    def __hash__(self):
        return hash(self.__repr__())

    ## @remarks Original code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Variables.hs">/Data/DRS/Variables.hs:drsRelToString</a>
    ##
    def to_string(self):
        """Converts this instance into a string."""
        raise NotImplementedError

    ## @remarks Original code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Variables.hs">/Data/DRS/Variables.hs:drsRelToString</a>
    ##
    def to_unicode(self):
        """Converts this instance into a string."""
        raise NotImplementedError

    def __str__(self):
        return self.to_string()


class LambdaDRSRelation(AbstractDRSRelation):
    """Lambda DRS Relation"""
    def __init__(self, lambdaVar, idx):
        """A lambda DRSRef.

        Args:
            lambdaVar: A LambdaDRSVar instance.
            idx: Argument position.
        """
        if not isinstance(lambdaVar, LambdaDRSVar):
            raise TypeError
        self._var = lambdaVar
        self._idx = idx

    def __ne__(self, other):
        return type(self) != type(other) or self._var != other._var or self._idx != other._idx

    def __eq__(self, other):
        return type(self) == type(other) and self._var == other._var and self._idx == other._idx

    def __repr__(self):
        return 'LambdaDRSRelation(%s,%i)' % (self._var, self._idx)

    # Helper for DRS.get_lambda_tuples()
    def _lambda_tuple(self, u):
        u.add(LambdaTuple(self._var, self._pos))
        return u

    ## @remarks Original code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Variables.hs">/Data/DRS/Variables.hs:drsRelToString</a>
    ##
    def to_string(self):
        """Converts this instance into a string."""
        return self._var.var.to_string()

    ## @remarks Original code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Variables.hs">/Data/DRS/Variables.hs:drsRelToString</a>
    ##
    def to_unicode(self):
        """Converts this instance into a string."""
        return self._var.var.to_string().decode('utf-8')


class DRSRelation(AbstractDRSRelation):
    """DRS Relation"""
    def __init__(self, drsVar):
        if isinstance(drsVar, str):
            drsVar = DRSVar(drsVar)
        elif not isinstance(drsVar, DRSVar):
            raise TypeError
        self._var = drsVar

    def __ne__(self, other):
        return type(self) != type(other) or self._var != other._var

    def __eq__(self, other):
        return type(self) == type(other) and self._var == other._var

    def __repr__(self):
        return 'DRSRelation(%s)' % self._var

    # Helper for DRS.get_lambda_tuples()
    def _lambda_tuple(self, u):
        return u

    ## @remarks Original code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Variables.hs">/Data/DRS/Variables.hs:drsRelToString</a>
    ##
    def to_string(self):
        """Converts this instance into a string."""
        return self._var.to_string()

    ## @remarks Original code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Variables.hs">/Data/DRS/Variables.hs:drsRelToString</a>
    ##
    def to_unicode(self):
        """Converts this instance into a string."""
        return self._var.to_string().decode('utf-8')


class AbstractDRSCond(Showable):
    """Abstract DRS Condition"""

    def __hash__(self):
        return hash(self.__repr__())

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

    # Helper for DRS.get_lambda_tuples()
    def _lambda_tuple(self, u):
        return u

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/LambdaCalculus.hs#renameCons:convertCon
    def _convert(self, ld, gd, rs, pv=None, ps=None):
        raise NotImplementedError

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/LambdaCalculus.hs#purifyRefs:purify
    def _purify_refs(self, gd, rs, pv=None):
        raise NotImplementedError

    @property
    def isresolved(self):
        """Helper for DRS function of same name."""
        return False

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Variables.hs">/Data/DRS/Variables.hs:drsVariables:variables</a>
    def get_variables(self, u):
        """Returns the list of all DRSRef's in this condition. This serves as a helper to DRS.get_variables()

        Args:
            u: An initial set(). Cannot be None.

        Returns:
            A list of DRSRef's unioned with `u`.
        """
        return u

    def clone(self):
        raise NotImplementedError

    def find_subdrs(self, d):
        """Test whether d is a direct or indirect sub-DRS of this condition and return the found sub-DRS."""
        return None

    def resolve_merges(self):
        """Helper for DRS function of same name."""
        raise NotImplementedError

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Translate.hs">/Data/DRS/Translate.hs:drsToMFOL:drsConsToMFOL</a>
    ##
    def to_mfol(self, world):
        """Helper for DRS function of same name."""
        raise NotImplementedError


class Rel(AbstractDRSCond):
    """A relation defined on a set of referents"""
    def __init__(self, drsRel, drsRefs):
        if not iterable_type_check(drsRefs, AbstractDRSRef):
            raise TypeError
        if isinstance(drsRel, str):
            drsRel = DRSRelation(drsRel)
        if not isinstance(drsRel, AbstractDRSRelation):
            raise TypeError
        self._rel = drsRel
        self._refs = drsRefs

    def __repr__(self):
        return 'Rel(%s,%s)' % (repr(self._rel), ','.join([repr(x) for x in self._refs]))

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

    # Helper for DRS.get_lambda_tuples()
    def _lambda_tuple(self, u):
        u = self._rel._lambda_tuple(u)
        for x in self._refs:
            u = x._lambda_tuple(u)

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/LambdaCalculus.hs#renameCons:convertCon
    def _convert(self, ld, gd, rs, pv=None, ps=None):
        return Rel(self._rel, [rename_var(r,rs) if r.has_bound(ld, gd) else r for r in self._refs])

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

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Variables.hs">/Data/DRS/Variables.hs:drsVariables:variables</a>
    def get_variables(self, u):
        """Returns the list of all DRSRef's in this condition. This serves as a helper to DRS.get_variables()

        Args:
            u: An initial set(). Cannot be None.

        Returns:
            A list of DRSRef's unioned with `u`.
        """
        return u.union(self._refs)

    def clone(self):
        return self

    def resolve_merges(self):
        """Helper for DRS function of same name."""
        return self

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Translate.hs">/Data/DRS/Translate.hs:drsToMFOL:drsConsToMFOL</a>
    ##
    def to_mfol(self, world):
        """Helper for DRS function of same name."""
        v = [world]
        v.extend([x.var.to_string() for x in self._refs])
        return fol.Rel(self._rel.to_string(), v)

    def show(self, notation):
        """Helper for DRS function of same name."""
        if notation == SHOW_BOX:
            return self._rel.to_unicode() + u'(' + ','.join([x.var.show(notation) for x in self._refs]) + u')\n'
        elif notation in [SHOW_LINEAR, SHOW_SET]:
            return self._rel.to_unicode() + u'(' + ','.join([x.var.show(notation) for x in self._refs]) + u')'
        return u'Rel (' + self._rel.to_unicode() + u') (' + ','.join([x.var.show(notation) for x in self._refs]) + u')'


class Neg(AbstractDRSCond):
    """A negated DRS"""
    def __init__(self, drs):
        if not isinstance(drs, AbstractDRS):
            raise TypeError
        self._drs = drs

    def __ne__(self, other):
        return type(self) != type(other) or self._drs != other._drs

    def __eq__(self, other):
        return type(self) == type(other) and self._drs == other._drs

    def __repr__(self):
        return 'Neg(%s)' % repr(self._drs)

    def _set_accessible(self, d):
        return self._drs._set_accessible(d)

    def _antecedent(self, ref, drs):
        return self._drs.has_subdrs(drs) and ref.has_bound(drs, self._drs)

    def _ispure(self, ld, gd, rs):
        if not self._drs._ispure_helper(rs, gd): return (False, None)
        # Can modify rs because it will be replaced by caller by the one we pass back
        rs = self._drs.get_variables(rs)
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

    # Helper for DRS.get_lambda_tuples()
    def _lambda_tuple(self, u):
        return self._drs.get_lambda_tuples(u)

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/LambdaCalculus.hs#renameCons:convertCon
    def _convert(self, ld, gd, rs, pv=None, ps=None):
        return type(self)(self._drs.rename_subdrs(gd, rs, ps))

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

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Variables.hs">/Data/DRS/Variables.hs:drsVariables:variables</a>
    def get_variables(self, u):
        """Returns the list of all DRSRef's in this condition. This serves as a helper to DRS.get_variables()

        Args:
            u: An initial set(). Cannot be None.

        Returns:
            A list of DRSRef's unioned with `u`.
        """
        return self._drs.get_variables(u)

    def clone(self):
        return Neg(self._drs.clone())

    def find_subdrs(self, d):
        """Test whether d is a direct or indirect sub-DRS of this condition and return the found sub-DRS."""
        return self._drs.find_subdrs(d)

    def resolve_merges(self):
        """Helper for DRS function of same name."""
        return type(self)(self._drs.resolve_merges())

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Translate.hs">/Data/DRS/Translate.hs:drsToMFOL:drsConsToMFOL</a>
    ##
    def to_mfol(self, world):
        """Helper for DRS function of same name."""
        return fol.Neg(self._drs.to_mfol(world))

    def show(self, notation):
        """Helper for DRS function of same name."""
        if notation == SHOW_BOX:
            if self._drs.islambda:
                return self.show_modifier(self.opNeg, 0, self._drs.show(notation))
            return self.show_modifier(self.opNeg, 2, self._drs.show(notation))
        elif notation in [SHOW_LINEAR, SHOW_SET]:
            return self.opNeg + self._drs.show(notation)
        return u'Neg (' + self._drs.show(notation) + u')'


class Imp(AbstractDRSCond):
    """An implication between two DRSs"""
    def __init__(self, antecedent, consequent):
        if not isinstance(antecedent, AbstractDRS) or not isinstance(consequent, AbstractDRS):
            raise TypeError
        self._drsA = antecedent
        self._drsB = consequent

    def __ne__(self, other):
        return type(self) != type(other) or self._drsA != other._drsA or self._drsB != other._drsB

    def __eq__(self, other):
        return type(self) == type(other) and self._drsA == other._drsA and self._drsB == other._drsB

    def __repr__(self):
        return 'Imp(%s,%s)' % (repr(self._drsA), repr(self._drsB))

    def _set_accessible(self, d):
        return self._drsA._set_accessible(d) and self._drsB._set_accessible(self._drsA)

    def _antecedent(self, ref, drs):
        return (ref in self._drsA.universe and self._drsB.has_subdrs(drs)) or \
               (self._drsA.has_subdrs(drs) and ref.has_bound(drs, self._drsA)) or \
               (self._drsB.has_subdrs(drs) and ref.has_bound(drs, self._drsB))

    def _get_freerefs(self, ld, gd, pvar=None):
        # free (Imp d1 d2:cs) = drsFreeRefs d1 gd `union` drsFreeRefs d2 gd `union` free cs
        return union(self._drsA.get_freerefs(gd), self._drsB.get_freerefs(gd))

    def _isproper_subdrsof(self, sd, gd, pvar=None):
        """Helper for DRS.isproper"""
        return self._drsA._isproper_subdrsof(gd) and self._drsB._isproper_subdrsof(gd)

    def _ispure(self, ld, gd, rs):
        if not self._drsA._ispure_helper(rs, gd): return (False, None)
        rs = self._drsA.get_variables(rs)
        if not self._drsB._ispure_helper(rs, gd): return (False, None)
        rs = self._drsB.get_variables(rs)
        return True, rs

    def _universes(self, u):
        u = self._drsA.get_universes(u)
        return self._drsB.get_universes(u)

    # Helper for DRS.get_lambda_tuples()
    def _lambda_tuple(self, u):
        u = self._drsA.get_lambda_tuples(u)
        return self._drsB.get_lambda_tuples(u)

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/LambdaCalculus.hs#renameCons:convertCon
    def _convert(self, ld, gd, rs, pv=None, ps=None):
        return type(self)(self._drsA.rename_subdrs(gd, rs, ps), self._drsB.rename_subdrs(gd, rs, ps))

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

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Variables.hs">/Data/DRS/Variables.hs:drsVariables:variables</a>
    def get_variables(self, u):
        """Returns the list of all DRSRef's in this condition. This serves as a helper to DRS.get_variables()

        Args:
            u: An initial set(). Cannot be None.

        Returns:
            A list of DRSRef's unioned with `u`.
        """
        u = self._drsA.get_variables(u)
        return self._drsB.get_variables(u)

    def clone(self):
        return Imp(self._drsA.clone(), self._drsB.clone())

    def find_subdrs(self, d):
        """Test whether d is a direct or indirect sub-DRS of this condition and return the found sub-DRS."""
        return self._drsA.find_subdrs(d) or self._drsB.find_subdrs(d)

    def resolve_merges(self):
        """Helper for DRS function of same name."""
        return type(self)(self._drsA.resolve_merges(), self._drsB.resolve_merges())

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Translate.hs">/Data/DRS/Translate.hs:drsToMFOL:drsConsToMFOL</a>
    ##
    def to_mfol(self, world):
        """Helper for DRS function of same name."""
        if not isinstance(self._drsA, DRS):
            raise fol.FOLConversionError
        refs = self._drsA.universe # causes a shallow copy of referents
        f = fol.Imp(conds_to_mfol(self._drsA._conds, world), self._drsB.to_mfol(world))
        refs.reverse()
        for r in refs:
            f = fol.ForAll(r.var.to_string(), f)
        return f

    def show(self, notation):
        """Helper for DRS function of same name."""
        if notation == SHOW_BOX:
            if self._drsA.islambda and self._drsB.islambda:
                return self.show_concat(self._drsA.show(notation), \
                                        self.show_modifier(self.opImp, 0, self._drsB.show(notation)))
            elif not self._drsA.islambda and self._drsB.islambda:
                return self.show_concat(self._drsA.show(notation), \
                                        self.show_modifier(self.opImp, 2, self.show_padding(self._drsB.show(notation))))
            elif self._drsA.islambda and not self._drsB.islambda:
                return self.show_concat(self.show_padding(self._drsA.show(notation)), \
                                        self.show_modifier(self.opImp, 0, self._drsB.show(notation)))
            return self.show_concat(self._drsA.show(notation), \
                                    self.show_modifier(self.opImp, 2, self._drsB.show(notation)))
        elif notation in [SHOW_LINEAR, SHOW_SET]:
            return self._drsA.show(notation) + u' ' + self.opImp + u' ' + self._drsB.show(notation)
        return u'Imp (' + self._drsA.show(notation) + u') (' + self._drsB.show(notation) + u')'


class Or(AbstractDRSCond):
    """A disjunction between two DRSs"""
    def __init__(self, drsA, drsB):
        if not isinstance(drsA, AbstractDRS) or not isinstance(drsB, AbstractDRS):
            raise TypeError
        self._drsA = drsA
        self._drsB = drsB

    def __ne__(self, other):
        return type(self) != type(other) or self._drsA != other._drsA or self._drsB != other._drsB

    def __eq__(self, other):
        return type(self) == type(other) and self._drsA == other._drsA and self._drsB == other._drsB

    def __repr__(self):
        return 'Or(%s,%s)' % (repr(self._drsA), repr(self._drsB))

    def _set_accessible(self, d):
        return self._drsA._set_accessible(d) and self._drsB._set_accessible(d)

    def _antecedent(self, ref, drs):
        return (self._drsA.has_subdrs(drs) and ref.has_bound(drs, self._drsA)) or \
               (self._drsB.has_subdrs(drs) and ref.has_bound(drs, self._drsB))

    def _get_freerefs(self, ld, gd, pvar=None):
        # free (Imp d1 d2:cs) = drsFreeRefs d1 gd `union` drsFreeRefs d2 gd `union` free cs
        return union(self._drsA.get_freerefs(gd), self._drsB.get_freerefs(gd))

    def _isproper_subdrsof(self, sd, gd, pvar=None):
        """Helper for DRS.isproper"""
        return self._drsA._isproper_subdrsof(gd) and self._drsB._isproper_subdrsof(gd)

    def _ispure(self, ld, gd, rs):
        if not self._drsA._ispure_helper(rs, gd): return (False, None)
        rs = self._drsA.get_variables(rs)
        if not self._drsB._ispure_helper(rs, gd): return (False, None)
        rs = self._drsB.get_variables(rs)
        return True, rs

    def _universes(self, u):
        u = self._drsA.get_universes()
        return self._drsB.get_universes(u)

    # Helper for DRS.get_lambda_tuples()
    def _lambda_tuple(self, u):
        u = self._drsA.get_lambda_tuples(u)
        return self._drsB.get_lambda_tuples(u)

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/LambdaCalculus.hs#renameCons:convertCon
    def _convert(self, ld, gd, rs, pv=None, ps=None):
        return type(self)(self._drsA.rename_subdrs(gd, rs, ps), self._drsB.rename_subdrs(gd, rs, ps))

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

    def clone(self):
        return Or(self._drsA.clone(), self._drsB.clone())

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Variables.hs">/Data/DRS/Variables.hs:drsVariables:variables</a>
    def get_variables(self, u):
        """Returns the list of all DRSRef's in this condition. This serves as a helper to DRS.get_variables()

        Args:
            u: An initial set(). Cannot be None.

        Returns:
            A list of DRSRef's unioned with `u`.
        """
        u = self._drsA.get_variables(u)
        return self._drsB.get_variables(u)

    def find_subdrs(self, d):
        """Test whether d is a direct or indirect sub-DRS of this condition and return the found sub-DRS."""
        return self._drsA.find_subdrs(d) or self._drsB.find_subdrs(d)

    def resolve_merges(self):
        """Helper for DRS function of same name."""
        return type(self)(self._drsA.resolve_merges(), self._drsB.resolve_merges())

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Translate.hs">/Data/DRS/Translate.hs:drsToMFOL:drsConsToMFOL</a>
    ##
    def to_mfol(self, world):
        """Helper for DRS function of same name."""
        return fol.Or(self._drsA.to_mfol(world), self._drsB.to_mfol(world))

    def show(self, notation):
        """Helper for DRS function of same name."""
        if notation == SHOW_BOX:
            if self._drsA.islambda and self._drsB.islambda:
                return self.show_concat(self._drsA.show(notation), \
                                        self.show_modifier(self.opOr, 0, self._drsB.show(notation)))
            elif not self._drsA.islambda and self._drsB.islambda:
                return self.show_concat(self._drsA.show(notation), \
                                        self.show_modifier(self.opOr, 2, self.show_padding(self._drsB.show(notation))))
            elif self._drsA.islambda and not self._drsB.islambda:
                return self.show_concat(self.show_padding(self._drsA.show(notation)), \
                                        self.show_modifier(self.opOr, 0, self._drsB.show(notation)))
            return self.show_concat(self._drsA.show(notation), \
                                    self.show_modifier(self.opOr, 2, self._drsB.show(notation)))
        elif notation in [SHOW_LINEAR, SHOW_SET]:
            return self._drsA.show(notation) + u' ' + self.opOr + u' ' + self._drsB.show(notation)
        return u'Or (' + self._drsA.show(notation) + u') (' + self._drsB.show(notation) + u')'


class Prop(AbstractDRSCond):
    """A proposition DRS"""
    def __init__(self, drsRef, drs):
        if not isinstance(drs, AbstractDRS) or not isinstance(drsRef, AbstractDRSRef):
            raise TypeError
        self._drs = drs
        self._ref = drsRef

    def __ne__(self, other):
        return type(self) != type(other) or self._ref != other._ref or self._drs != other._drs

    def __eq__(self, other):
        return type(self) == type(other) and self._ref == other._ref and self._drs == other._drs

    def __repr__(self):
        return 'Prop(%s,%s)' % (repr(self._ref), repr(self._drs))

    def _set_accessible(self, d):
        return self._drs._set_accessible(d)

    def _antecedent(self, ref, drs):
        return self._drs.has_subdrs(drs) and ref.has_bound(drs, self._drs)

    def _get_freerefs(self, ld, gd, pvar=None):
        # free (Prop r d1:cs) = snd (partition (flip (`drsBoundRef` ld) gd) [r]) `union` drsFreeRefs d1 gd `union` free cs
        return union(filter(lambda x: not x.has_bound(ld, gd), [self._ref]), self._drs.get_freerefs(gd))

    def _isproper_subdrsof(self, sd, gd, pvar=None):
        """Helper for DRS.isproper"""
        return self._ref.has_bound(sd, gd) and self._drs._isproper_subdrsof(gd)

    def _ispure(self, ld, gd, rs):
        if not _pure_refs(ld, gd, [self._ref], rs) or not self._drs._ispure_helper(rs, gd):
            return (False, None)
        rs = self._drs.get_variables(rs)
        return True, rs

    def _universes(self, u):
        return self._drs.get_universes(u)

    # Helper for DRS.get_lambda_tuples()
    def _lambda_tuple(self, u):
        u = self._ref._lambda_tuple(u)
        return self._drs.get_lambda_tuples(u)

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/LambdaCalculus.hs#renameCons:convertCon
    def _convert(self, ld, gd, rs, pv=None, ps=None):
        return type(self)(rename_var(self._ref,rs) if self._ref.has_bound(ld, gd) else self._ref, self._drs.rename_subdrs(gd, rs, ps))

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

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Variables.hs">/Data/DRS/Variables.hs:drsVariables:variables</a>
    def get_variables(self, u):
        """Returns the list of all DRSRef's in this condition. This serves as a helper to DRS.get_variables()

        Args:
            u: An initial set(). Cannot be None.

        Returns:
            A list of DRSRef's unioned with `u`.
        """
        u.add(self._ref)
        return self._drs.get_variables(u)

    def clone(self):
        return Prop(self._ref, self._drs.clone())

    def find_subdrs(self, d):
        """Test whether d is a direct or indirect sub-DRS of this condition and return the found sub-DRS."""
        return self._drs.find_subdrs(d)

    def resolve_merges(self):
        """Helper for DRS function of same name."""
        return type(self)(self._ref, self._drs.resolve_merges())

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Translate.hs">/Data/DRS/Translate.hs:drsToMFOL:drsConsToMFOL</a>
    ##
    def to_mfol(self, world):
        """Helper for DRS function of same name."""
        return fol.And(fol.Rel(WORLD_REL, [world, self._ref.var.to_string()]), self._drs.to_mfol(world))

    def show(self, notation):
        """Helper for DRS function of same name."""
        if notation == SHOW_BOX:
            if self._drs.islambda:
                return self.show_modifier(self._ref.var.show(notation) + u':', 0, self._drs.show(notation))
            return self.show_modifier(self._ref.var.show(notation) + u':', 2, self._drs.show(notation))
        elif notation in [SHOW_LINEAR, SHOW_SET]:
            return self._ref.var.show(notation) + u': ' + self._drs.show(notation)
        return u'Prop (' + self._ref.var.show(notation) + u') (' + self._drs.show(notation) + u')'


class Diamond(AbstractDRSCond):
    """A possible DRS"""
    def __init__(self, drs):
        if not isinstance(drs, AbstractDRS):
            raise TypeError
        self._drs = drs

    def __ne__(self, other):
        return type(self) != type(other) or self._drs != other._drs

    def __eq__(self, other):
        return type(self) == type(other) and self._drs == other._drs

    def __repr__(self):
        return 'Diamond(%s)' % repr(self._drs)

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
        rs = self._drs.get_variables(rs)
        return True, rs

    def _universes(self, u):
        return self._drs.get_universes(u)

    # Helper for DRS.get_lambda_tuples()
    def _lambda_tuple(self, u):
        return self._drs.get_lambda_tuples(u)

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/LambdaCalculus.hs#renameCons:convertCon
    def _convert(self, ld, gd, rs, pv=None, ps=None):
        return type(self)(self._drs.rename_subdrs(gd, rs, ps))

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

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Variables.hs">/Data/DRS/Variables.hs:drsVariables:variables</a>
    def get_variables(self, u):
        """Returns the list of all DRSRef's in this condition. This serves as a helper to DRS.get_variables()

        Args:
            u: An initial set(). Cannot be None.

        Returns:
            A list of DRSRef's unioned with `u`.
        """
        return self._drs.get_variables(u)

    def clone(self):
        return Diamond(self._drs.clone())

    def find_subdrs(self, d):
        """Test whether d is a direct or indirect sub-DRS of this condition and return the found sub-DRS."""
        return self._drs.find_subdrs(d)

    def resolve_merges(self):
        """Helper for DRS function of same name."""
        return type(self)(self._drs.resolve_merges())

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Translate.hs">/Data/DRS/Translate.hs:drsToMFOL:drsConsToMFOL</a>
    ##
    def to_mfol(self, world):
        """Helper for DRS function of same name."""
        v = world + "'"
        return fol.Exists(v, fol.And(fol.Rel(WORLD_REL,[world,v]),self._drs.to_mfol(v)))

    def show(self, notation):
        """Helper for DRS function of same name."""
        if notation == SHOW_BOX:
            if self._drs.islambda:
                return self.show_modifier(self.opDiamond, 0, self._drs.show(notation))
            return self.show_modifier(self.opDiamond, 2, self._drs.show(notation))
        elif notation in [SHOW_LINEAR, SHOW_SET]:
            return self.opDiamond + self._drs.show(notation)
        return u'Diamond (' + self._drs.show(notation) + u')'


class Box(AbstractDRSCond):
    """A necessary DRS"""
    def __init__(self, drs):
        if not isinstance(drs, AbstractDRS):
            raise TypeError
        self._drs = drs

    def __ne__(self, other):
        return type(self) != type(other) or self._drs != other._drs

    def __eq__(self, other):
        return type(self) == type(other) and self._drs == other._drs

    def __repr__(self):
        return 'Box(%s)' % repr(self._drs)

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
        rs = self._drs.get_variables(rs)
        return True, rs

    def _universes(self, u):
        return self._drs.get_universes(u)

    # Helper for DRS.get_lambda_tuples()
    def _lambda_tuple(self, u):
        return self._drs.get_lambda_tuples(u)

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/LambdaCalculus.hs#renameCons:convertCon
    def _convert(self, ld, gd, rs, pv=None, ps=None):
        return type(self)(self._drs.rename_subdrs(gd, rs, ps))

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

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Variables.hs">/Data/DRS/Variables.hs:drsVariables:variables</a>
    def get_variables(self, u):
        """Returns the list of all DRSRef's in this condition. This serves as a helper to DRS.get_variables()

        Args:
            u: An initial set(). Cannot be None.

        Returns:
            A list of DRSRef's unioned with `u`.
        """
        return self._drs.get_variables(u)

    def clone(self):
        return Box(self._drs.clone())

    def find_subdrs(self, d):
        """Test whether d is a direct or indirect sub-DRS of this condition and return the found sub-DRS."""
        return self._drs.find_subdrs(d)

    def resolve_merges(self):
        """Helper for DRS function of same name."""
        return type(self)(self._drs.resolve_merges())

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Translate.hs">/Data/DRS/Translate.hs:drsToMFOL:drsConsToMFOL</a>
    ##
    def to_mfol(self, world):
        """Helper for DRS function of same name."""
        v = world + "'"
        return fol.ForAll(v, fol.Imp(fol.Rel(WORLD_REL,[world,v]),self._drs.to_mfol(v)))

    def show(self, notation):
        """Helper for DRS function of same name."""
        if notation == SHOW_BOX:
            if self._drs.islambda:
                return self.show_modifier(self.opBox, 0, self._drs.show(notation))
            return self.show_modifier(self.opBox, 2, self._drs.show(notation))
        elif notation in [SHOW_LINEAR, SHOW_SET]:
            return self.opBox + self._drs.show(notation)
        return u'Box (' + self._drs.show(notation) + u')'
