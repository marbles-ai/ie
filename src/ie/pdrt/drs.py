from utils import iterable_type_check, union, union_inplace, intersect, rename_var
from common import DRSVar, LambdaDRSVar


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
        return self._var != other._var or self._pos != other._pos

    def __eq__(self, other):
        return self._var == other._var and self._pos == other._pos

    def __repr__(self):
        return 'LambdaTuple(%s,%i)' % (self._var, self._pos)

    def __hash__(self):
        return hash(self._var) ^ hash(self._set)

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


# Original haskell code in DRS/Input/Properties.hs:isPureDRS:pureRefs
def _pure_refs(ld, gd, rs, srs):
    return all(filter(lambda r: r.has_bound(ld, gd) or r not in srs, rs))


class AbstractDRS(object):
    """Abstract Discourse Representation Structure (DRS)"""

    def _isproper_subdrsof(self, d):
        """Helper for isproper"""
        return False

    def _ispure_helper(self, rs, gd):
        """Helper for ispure"""
        return False

    ## @remarks original haskell code in `DRS/Input/Structure.hs:isResolvedDRS`
    @property
    def isresolved(self):
        """Test whether this DRS is resolved (containing no unresolved merges or lambdas)"""
        return False

    ## @remarks original haskell code in `DRS/Input/Structure.hs:isLambdaDRS`
    @property
    def islambda(self):
        """Test whether this DRS is entirely a 'LambdaDRS' (at its top-level)."""
        return False

    ## @remarks original haskell code in `DRS/Input/Structure.hs:isMergeDRS`
    @property
    def ismerge(self):
        """Test whether this DRS is entirely a 'Merge' (at its top-level)."""
        return False

    ## @remarks original haskell code in `DRS/Input/Structure.hs:drsUniverse`
    @property
    def universe(self):
        """Returns the universe of a DRS.

        Returns:
            A list of DRSRef instances.
        """
        return []

    ## @remarks original haskell code in `DRS/Input/Properties.hs:isPureDRS`
    @property
    def ispure(self):
        """Test whether this DRS is pure, where:
        A DRS is pure iff it does not contain any otiose declarations of discourse referents
        (i.e. it does not contain any unbound, duplicate uses of referents).
        """
        return self._ispure_helper([], self)

    ## @remarks original haskell code in `DRS/Input/Properties.hs:isProperDRS`
    @property
    def isproper(self):
        """Test whether this DRS is proper, where:
        A DRS is proper iff it does not contain any free variables.
        """
        return self._isproper_subdrsof(self)

    ## @remarks original haskell code in `DRS/Input/Properties.hs:isFOLDRS`
    @property
    def isfol(self):
        """Test whether this DRS can be translated into a FOLForm instance."""
        return self.isresolved and self.ispure and self.isproper

    ## @remarks original haskell code in `DRS/Input/Structure.hs:isSubDRS`
    def has_subdrs(self, d1):
        """Returns whether d1 is a direct or indirect sub-DRS of this DRS"""
        return False

    ## @remarks original haskell code in `DRS/Input/Binding.hs:drsFreeRefs`
    def get_freerefs(self, gd):
        """Returns the list of all free DRSRef's in a DRS."""
        return []

    ## @remarks original haskell code in `DRS/Input/Merge.hs:drsResolveMerges`
    def resolve_merges(self):
        """ Resolves all unresolved merges in a 'DRS'."""
        raise NotImplementedError

    ## @remarks original haskell code in `DRS/Input/Variables.hs:drsVariables`
    def get_variables(self, u=None):
        """Returns the list of all DRSRef's in this DRS (equals getUniverses getFreeRefs)"""
        if u is None: return []
        return u

    ## @remarks original haskell code in `DRS/Input/Variables.hs:drsUniverses`
    def get_universes(self, u=None):
        """Returns the list of DRSRef's from all universes in this DRS."""
        if u is None: return []
        return u

    ## @remarks original haskell code in `DRS/Input/Variables.hs:drsLambdas`
    def get_lambdas(self):
        """Returns the ordered list of all lambda variables in this DRS."""
        s = self.get_lambda_tuples()
        lts = sorted(s)
        return [x.var for x in lts]

    ## @remarks original haskell code in `DRS/Input/Variables.hs:lambdas`
    def get_lambda_tuples(self, u=None):
        """Returns the list of all lambda tuples in this DRS."""
        raise NotImplementedError

    ## @remarks Original haskell code in `DRS/Input/LambdaCalculus.hs:purifyRefs`
    def purify_refs(self, gd, refs):
        """Replaces duplicate uses of DRSRef's by new DRSRef's.

        This function implements the following algorithm:
        (1) start with the global DRS @gd@ and add all free 'PVar's in @gd@ to
        the list of seen referents @rs@ (see 'drsPurify');

        (2) check the universe @u@ of the first atomic DRS @ld@ against @rs@
        and, if necessary, alpha-convert @ld@ replacing duplicates for new
        DRSRef's in @u@;

        (3) add the universe of @ld@ to the list of seen DRSRef's @rs@;

        (4) go through all conditions of @ld@, while continually updating @rs@.
        """
        raise NotImplementedError

    ## @remarks original haskell code in `DRS/Input/LambdaCalculus.hs:drsPurify`
    def purify(self):
        """Converts a DRS into a pure DRS by purifying its DRSRef's,

        where a DRS is pure iff there are no occurrences of duplicate, unbound uses
        of the same DRSRef.
        """
        refs = self.get_freerefs(self)
        drs,_ = self.purify_refs(self, refs)
        return drs


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
        self._var = lambdaVar
        self._pos = pos

    def __ne__(self, other):
        return self._var != other._var or self._pos != other._pos

    def __eq__(self, other):
        return self._var == other._var and self._pos == other._pos

    def __repr__(self):
        return 'LambdaDRS(%s,%i)' % (self._var, self._pos)

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
        """Returns the set of all lambda tuples in this DRS."""
        lt = LambdaTuple(self._var, self._pos)
        if u is None: return set([lt])
        u.add(lt)
        return u

    ## @remarks Original haskell code in `DRS/Input/LambdaCalculus.hs:purifyRefs`
    def purify_refs(self, gd, ers):
        return (self, ers)


class DRS(AbstractDRS):
    """Default DRS"""
    def __init__(self, drsRefs, drsConds):
        self._refs = drsRefs
        self._conds = drsConds

    def __ne__(self, other):
        return self._refs != other._refs or self._conds != other._conds

    def __eq__(self, other):
        return self._refs == other._refs and self._conds == other._conds

    def __repr__(self):
        return 'DRS(%s,%s)' % (self._refs, self._conds)

    def _isproper_subdrsof(self, gd):
        """Help for isproper"""
        return all(filter(lambda x: x._isproper_subdrsof(self, gd), self._conds))

    def _ispure_helper(self, rs, gd):
        if any(filter(lambda x: x in rs, self._refs)): return False
        if len(self._conds) == 0: return True
        rss = []
        rss.extend(rs)
        rss.extend(self._refs)
        for c in self._conds:
            (r,rss) = c._ispure(self, gd, rss)
            if not r: return False
        return False

    @property
    def referents(self):
        return [x for x in self._refs] # deep copy

    @property
    def conditions(self):
        return [x for x in self._conds] # deep copy

    @property
    def isresolved(self):
        """Test whether this DRS is resolved (containing no unresolved merges or lambdas)"""
        return all(filter(lambda x: x.isresolved, self._refs)) and all(filter(lambda x: x.isresolved, self._conds))

    @property
    def universe(self):
        """Returns the universe of a DRS.

        Returns:
            A list of DRSRef instances.
        """
        return [x for x in self._refs] # deep copy

    def has_subdrs(self, d1):
        """Test whether d1 is a direct or indirect sub-DRS of this DRS."""
        return self == d1 or any(filter(lambda x: x.has_subdrs(self), self._conds))

    def get_freerefs(self, gd):
        """Returns the list of all free DRSRef's in a DRS."""
        y = []
        for c in self.conds:
            y = union_inplace(y, c.get_freerefs(self, gd))
        return sorted(set(y))

    def resolve_merges(self):
        """Resolves all unresolved merges in this DRS."""
        return DRS(self._refs, [x.resolve_merges() for x in self._conds])

    ## @remarks original haskell code in `DRS/Input/Variables.hs:drsVariables`
    def get_variables(self, u=None):
        """Returns the list of all DRSRef's in this DRS (equals getUniverses getFreeRefs)"""
        if u is None:
            u = [x for x in self._refs] # deep copy
        else:
            u = union_inplace(u, self._refs) # union to avoid duplicates
        for c in self._conds:
            u = c._variables(u)
        return u

    ## @remarks original haskell code in `DRS/Input/Variables.hs:drsUniverses`
    def get_universes(self, u=None):
        """Returns the list of DRSRef's from all universes in this DRS."""
        if u is None:
            u = [x for x in self._refs] # deep copy
        else:
            u.extend(self._refs)
        for c in self._conds:
            u = c._universes(u)
        return u

    def get_lambda_tuples(self, u=None):
        """Returns the set of all lambda tuples in this DRS."""
        if u is None:
            u = set()
        for r in self._refs:
            u = r._lambda_tuple(u)
        for c in self._conds:
            u = c._lambda_tuple(u)

    ## @remarks Original haskell code in `DRS/Input/LambdaCalculus.hs:drsAlphaConvert`
    def alpha_convert(self, rs):
        return rename_subdrs(self, self, rs)

    ## @remarks Original haskell code in `DRS/Input/LambdaCalculus.hs:purifyRefs`
    def purify_refs(self, gd, ers):
        # In case we do not want to rename ambiguous bindings:
        # purifyRefs (ld@(DRS u _),ers) gd = (DRS u1 c2,u1 ++ ers1)
        ors = intersect(self._refs, ers)
        d = self.alpha_convert(zip(ors, get_new_drsrefs(ors, union_inplace(gd.get_variables(),ers))))
        r = d.referents
        r.extend(ers)
        conds = []
        for c in self._conds:
            x,r = c._purify(gd, r)
            conds.append(x)
        return (DRS(d.referents,conds), r)


class Merge(AbstractDRS):
    """A merge between two DRSs"""
    def __init__(self, drsA, drsB):
        if not isinstance(drsA, AbstractDRS) or not isinstance(drsB, AbstractDRS):
            raise TypeError
        self._drsA = drsA
        self._drsB = drsB

    def __ne__(self, other):
        return self._drsA != other._drsA or self._drsB != other._drsB

    def __eq__(self, other):
        return self._drsA == other._drsA and self._drsB == other._drsB

    def __repr__(self):
        return 'MergeDRS(%s,%s)' % (self._drsA, self._drsB)

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
    def drs_a(self):
        return self._drsA

    @property
    def drs_b(self):
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
        """Returns the universe of a DRS.

        Returns:
            A list of DRSRef instances.
        """
        return union(self._drsA.universe, self._drsB.universe)

    def has_subdrs(self, d1):
        """Test whether d1 is a direct or indirect sub-DRS of this DRS"""
        return self._drsA.has_subdrs(d1) or self._drsB.has_subdrs(d1)

    def get_freerefs(self, gd):
        """Returns the list of all free DRSRef's in a DRS."""
        return union(self._drsA.get_freerefs(gd), self._drsB.get_freerefs(gd))

    def resolve_merges(self):
        """Resolves all unresolved merges in a DRS."""
        merge(self._drsA.resolve_merges(), self._drsB.resolve_merges())

    ## @remarks original haskell code in `DRS/Input/Variables.hs:drsVariables`
    def get_variables(self, u=None):
        u = self._drsA.get_variables(u)
        u = self._drsB.get_variables(u)
        return u

    ## @remarks original haskell code in `DRS/Input/Variables.hs:drsUniverses`
    def get_universes(self, u=None):
        """Returns the list of DRSRef's from all universes in this DRS."""
        u = self._drsA.get_universes(u)
        u = self._drsB.get_universes(u)
        return u

    def get_lambda_tuples(self, u=None):
        """Returns the set of all lambda tuples in this DRS."""
        u = self._drsA.get_lambda_tuples(u)
        u = self._drsB.get_lambda_tuples(u)
        return u

    ## @remarks Original haskell code in `DRS/Input/LambdaCalculus.hs:purifyRefs`
    def purify_refs(self, gd, ers):
        cd1, ers1 = self._drsA.purify_refs(gd, ers)
        cd2, ers2 = self._drsB.purify_refs(gd, ers1)
        return (Merge(cd1, cd2), ers2)


# Original haskell code in DSI/Input/Merge.hs:drsMerge
def merge(d1, d2):
    """Applies merge to 'DRS' d1 and 'DRS' d2"""
    if isinstance(d2, LambdaDRS) or isinstance(d1, LambdaDRS):
        return Merge(d1, d2)
    elif isinstance(d2, Merge):
        if d2.drs_a.islambda:
            return Merge(d2.drs_a, merge(d1, d2.drs_b))
        elif d2.drs_b.islambda:
            return Merge(merge(d1, d2.drs_a), d2.drs_b)
        else:
            return merge(d1, d2.resolve_merges())
    elif isinstance(d1, Merge):
        if d1.drs_a.islambda:
            return Merge(d1.drs_a, merge(d1.drs_b, d2))
        elif d1.drs_b.islambda:
            return Merge(d1.drs_b, merge(d1.drs_a, d2))
        else:
            return merge(d2, d1.resolve_merges())
    else:
        # orig haskell code Merge.hs and Variable.hs
        p1 = d1.resolve_merges().purify()
        p2 = d2.resolve_merges().purify()
        ors = intersect(p2.get_variables(), p1.get_variables())
        nrs = get_new_drsrefs(ors, union(p2.get_variables(), p1.get_variables()))
        da = p2.alpha_convert(zip(ors,nrs))
        return DRS(union(p1.referents, da.referents), union(p1.conditions, da.conditions))


## @remarks Original haskell code in `DRS/Input/Variables.hs:newDRSRefs`
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
        ors[i] = rd
        if r in union(ors[i:], ers):
            ors[i] = r
            return get_new_drsrefs(ors[i:], ers)
        else:
            ors[i] = r
            y = [rd]
            y.extend(ers)
            result.append(rd)
            result.extend(get_new_drsrefs(ors[i+1:], y))
            return result


## @remarks Original haskell code in `DRS/Input/Variables.hs::drsCombine`
def combine(func, d):
    """Combines an unresolved 'DRS' and a 'DRS' into a resolved 'DRS'."""
    return func(d).resolve_merges()


## @remarks Original haskell code in `DRS/Input/LambdaCalculus.hs::renameSubDRS`
def rename_subdrs(ld, gd, rs):
    """Applies alpha conversion to a DRS ld, which is a sub-DRS of the
    global DRS gd, on the basis of a conversion list for DRSRef's rs.
    """
    if isinstance(ld, LambdaDRS):
        return ld
    elif isinstance(ld, Merge):
        return Merge(rename_subdrs(ld._drs_a, gd, rs),rename_subdrs(ld._drs_b, gd, rs))
    elif isinstance(ld, DRS):
        return DRS([rename_var(r, rs) for r in ld.referents], \
                   [c._convert(ld, gd, rs) for c in ld.conditions])
    else:
        raise TypeError


class AbstractDRSRef(object):
    """Abstract DRS referent"""
    def _has_antecedent(self, drs, conds):
        return any(filter(lambda x: x._antecedent(self, drs), conds))

    # Helper for DRS.get_lambda_tuples()
    def _lambda_tuple(self, u):
        raise NotImplementedError

    def has_bound(self, drsLD, drsGD):
        """Returns whether this DRSRef in local 'DRS' drsLD is bound in the global 'DRS' drsGD."""
        if isinstance(drsLD, LambdaDRS):
            return False
        elif isinstance(drsLD, Merge):
            return self.has_bound(drsLD.drs_a, drsGD) or self.has_bound(drsLD.drs_b, drsGD)
        elif isinstance(drsGD, LambdaDRS):
            return False
        elif isinstance(drsGD, Merge):
            return self.has_bound(drsLD, drsGD.drs_a) or self.has_bound(drsLD, drsGD.drs_b)
        elif isinstance(drsLD, DRS) and isinstance(drsGD, DRS):
            return self in drsLD.referents or self in drsGD.referents or \
                   self._has_antecedent(drsLD, drsGD.conditions)
        else:
            raise TypeError

    @property
    def isresolved(self):
        """Returns whether a 'DRS' is resolved (containing no unresolved merges or lambdas)"""
        return False

    def to_var(self):
        """Converts a DRSRef into a DRSVar."""
        raise NotImplementedError


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
        return self._var != other._var or self._pos != other._pos

    def __eq__(self, other):
        return self._var == other._var and self._pos == other._pos

    def __repr__(self):
        return 'LambdaDRSRef(%s,%i)' % (self._var, self._pos)

    # Helper for DRS.get_lambda_tuples()
    def _lambda_tuple(self, u):
        u.add(LambdaTuple(self._var, self._pos))
        return u

    def to_var(self):
        """Converts a DRSRef into a DRSVar."""
        return self._var.var


class DRSRef(AbstractDRSRef):
    """DRS referent"""
    def __init__(self, drsVar):
        if not isinstance(drsVar, DRSVar):
            raise TypeError
        self._var = drsVar

    def __ne__(self, other):
        return self._var != other._var

    def __eq__(self, other):
        return self._var == other._var

    def __repr__(self):
        return 'DRSRef(%s)' % self._var

    # Helper for DRS.get_lambda_tuples()
    def _lambda_tuple(self, u):
        return u

    @property
    def isresolved(self):
        return True

    def to_var(self):
        """Converts a DRSRef into a DRSVar."""
        return self._var


class AbstractDRSRelation(object):
    """Abstract DRS Relation"""

    # Helper for DRS.get_lambda_tuples()
    def _lambda_tuple(self, u):
        raise NotImplementedError

    def to_string(self):
        """Converts this instance into a string."""
        raise NotImplementedError


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
        return self._var != other._var or self._idx != other._idx

    def __eq__(self, other):
        return self._var == other._var and self._idx == other._idx

    def __repr__(self):
        return 'LambdaDRSRelation(%s,%i)' % (self._var, self._idx)

    # Helper for DRS.get_lambda_tuples()
    def _lambda_tuple(self, u):
        u.add(LambdaTuple(self._var, self._pos))
        return u

    def to_string(self):
        """Converts this instance into a string."""
        return self._var.var


class DRSRelation(AbstractDRSRelation):
    """DRS Relation"""
    def __init__(self, drsVar):
        self._var = drsVar

    def __ne__(self, other):
        return self._var != other._var

    def __eq__(self, other):
        return self._var == other._var

    def __repr__(self):
        return 'DRSRelation(%s)' % self._var

    # Helper for DRS.get_lambda_tuples()
    def _lambda_tuple(self, u):
        return u

    def to_string(self):
        """Converts this instance into a string."""
        return self._var


class AbstractDRSCond(object):
    """Abstract DRS Condition"""

    def _antecedent(self, ref, drs):
        #  always True == isinstance(drs, DRS)
        return False

    def _isproper_subdrsof(self, sd, gd):
        """Helper for DRS.isproper"""
        return False

    def _get_freerefs(self, ld, gd):
        #  always True == isinstance(ld, DRS) and True == isinstance(gd, DRS)
        return []

    # Original haskell code in DRS/Input/Properties.hs:isPureDRS:pureCons
    def _ispure(self, ld, gd, rs):
        return (False, None)

    # Original haskell code in DRS/Input/Variables.hs:drsUniverses:universes
    def _universes(self, u):
        return u

    # Original haskell code in DRS/Input/Variables.hs:drsVariables:variables
    def _variables(self, u):
        return u

    # Helper for DRS.get_lambda_tuples()
    def _lambda_tuple(self, u):
        raise NotImplementedError

    # Original haskell code in DRS/Input/LambdaCalculus.hs:renameCons:convertCon
    def _convert(self, ld, gd, rs):
        raise NotImplementedError

    # Original haskell code in DRS/Input/LambdaCalculus.hs:purifyRefs:purify
    def _purify(self, gd, rs):
        raise NotImplementedError

    @property
    def isresolved(self):
        return False

    def has_subdrs(self, d1):
        return False

    def resolve_merges(self):
        raise NotImplementedError


class Rel(AbstractDRSCond):
    """A relation defined on a set of referents"""
    def __init__(self, drsRel, drsRefs):
        if not isinstance(drsRel, AbstractDRSRelation) or iterable_type_check(drsRefs, AbstractDRSRef):
            raise TypeError
        self._rel = drsRel
        self._refs = drsRefs

    def _get_freerefs(self, ld, gd):
        """Helper for DRS.get_freerefs()"""
        # orig haskell code (Rel _ d:cs) = snd (partition (flip (`drsBoundRef` ld) gd) d) `union` free cs
        return filter(lambda x: not x.has_bound(x, ld, gd), self._refs)

    def _isproper_subdrsof(self, sd, gd):
        """Helper for DRS.isproper"""
        return all(filter(lambda x: not x.has_bound(sd, gd), self._refs))

    def _ispure(self, ld, gd, rs):
        if not _pure_refs(ld, gd, self._refs, rs): return (False, None)
        rs.extend(self._refs)
        return (True, rs)

    # Original haskell code in DRS/Input/Variables.hs:drsVariables:variables
    def _variables(self, u):
        return union_inplace(u, self._refs)

    # Helper for DRS.get_lambda_tuples()
    def _lambda_tuple(self, u):
        u = self._rel._lambda_tuple(u)
        for x in self._refs:
            u = x._lambda_tuple(u)

    # Original haskell code in DRS/Input/LambdaCalculus.hs:renameCons:convertCon
    def _convert(self, ld, gd, rs):
        return Rel(self._rel, [rename_var(r,rs) if r.has_bound(ld, gd) else r for r in self._refs])

    # Original haskell code in DRS/Input/LambdaCalculus.hs:purifyRefs:purify
    def _purify(self, gd, rs):
        rs.extend(self._refs)
        return (self, rs)

    @property
    def isresolved(self):
        return all(filter(lambda x: x.isresolved, self._refs))

    def resolve_merges(self):
        return self


class Neg(AbstractDRSCond):
    """A negated DRS"""
    def __init__(self, drs):
        if not isinstance(drs, AbstractDRS):
            raise TypeError
        self._drs = drs

    def __ne__(self, other):
        return self._drs != other._drs

    def __eq__(self, other):
        return self._drs == other._drs

    def __repr__(self):
        return 'Neg(%s)' % self._drs

    def _antecedent(self, ref, drs):
        return self._drs.has_subdrs(drs) and ref.has_bound(drs, self._drs)

    def _ispure(self, ld, gd, rs):
        if not self._drs._ispure_helper(rs, gd): return (False, None)
        # Can modify rs because it will be replaced by caller by the one we pass back
        rs = self._drs.get_variables(rs)
        return True, rs

    def _get_freerefs(self, ld, gd):
        # free (Neg d1:cs) = drsFreeRefs d1 gd `union` free cs
        return self._drs.get_freerefs(gd)

    def _isproper_subdrsof(self, sd, gd):
        """Helper for DRS.isproper"""
        return self._drs._isproper_subdrsof(gd)

    # Original haskell code in DRS/Input/Variables.hs:drsUniverses:universes
    def _universes(self, u):
        return self._drs.get_universes(u)

    # Original haskell code in DRS/Input/Variables.hs:drsVariables:variables
    def _variables(self, u):
        return self._drs.get_variables(u)

    # Helper for DRS.get_lambda_tuples()
    def _lambda_tuple(self, u):
        return self._drs.get_lambda_tuples(u)

    # Helper for DRS.get_lambda_tuples()
    def _lambda_tuple(self, u):
        return self._drs.get_lambda_tuples(u)

    # Original haskell code in DRS/Input/LambdaCalculus.hs:renameCons:convertCon
    def _convert(self, ld, gd, rs):
        return Neg(rename_subdrs(self._drs, gd, rs))

    # Original haskell code in DRS/Input/LambdaCalculus.hs:purifyRefs:purify
    def _purify(self, gd, rs):
        cd1, rs1 = self._drs.purify_refs(gd, rs)
        return Neg(cd1), rs1

    @property
    def isresolved(self):
        return self._drs.isresolved

    def has_subdrs(self, d1):
        return self._drs.has_subdrs(d1)

    def resolve_merges(self):
        return Neg(self._drs.resolve_merges())


class Imp(AbstractDRSCond):
    """An implication between two DRSs"""
    def __init__(self, drsA, drsB):
        if not isinstance(drsA, AbstractDRS) or not isinstance(drsB, AbstractDRS):
            raise TypeError
        self._drsA = drsA
        self._drsB = drsB

    def __ne__(self, other):
        return self._drsA != other._drsA or self._drsB != other._drsB

    def __eq__(self, other):
        return self._drsA == other._drsA and self._drsB == other._drsB

    def __repr__(self):
        return 'Imp(%s,%s)' % (self._drsA, self._drsB)

    def _antecedent(self, ref, drs):
        return (ref in self._drsA.universe and self._drsB.has_subdrs(drs)) or \
               (self._drsA.has_subdrs(drs) and ref.has_bound(drs, self._drsA)) or \
               (self._drsB.has_subdrs(drs) and ref.has_bound(drs, self._drsB))

    def _get_freerefs(self, ld, gd):
        # free (Imp d1 d2:cs) = drsFreeRefs d1 gd `union` drsFreeRefs d2 gd `union` free cs
        return union(self._drsA.get_freerefs(gd), self._drsB.get_freerefs(gd))

    def _isproper_subdrsof(self, sd, gd):
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
        u = self._drsB.get_universes(u)
        return u

    def _variables(self, u):
        u = self._drsA.get_variables(u)
        u = self._drsB.get_variables(u)
        return u

    # Helper for DRS.get_lambda_tuples()
    def _lambda_tuple(self, u):
        u = self._drsA.get_lambda_tuples(u)
        return self._drsB.get_lambda_tuples(u)

    # Original haskell code in DRS/Input/LambdaCalculus.hs:renameCons:convertCon
    def _convert(self, ld, gd, rs):
        return Imp(rename_subdrs(self._drsA, gd, rs), rename_subdrs(self._drsB, gd, rs))

    # Original haskell code in DRS/Input/LambdaCalculus.hs:purifyRefs:purify
    def _purify(self, gd, rs):
        orsd = intersect(self._drsA.universe, rs)
        nrs = zip(orsd, union_inplace(get_new_drsrefs(orsd, gd.get_variables()), rs))
        # In case we do not want to rename ambiguous bindings:
        # ors = drsUniverses d2 \\ drsUniverse d1 `intersect` rs
        cd1, rs1 = rename_subdrs(self._drsA, gd, nrs).purify_refs(gd, rs)
        cd2, rs2 = rename_subdrs(self._drsB, gd, nrs).purify_refs(gd, rs1)
        return Imp(cd1,cd2), rs2

    @property
    def isresolved(self):
        return self._drsA.isresolved and self._drsB.isresolved

    def has_subdrs(self, d1):
        return self._drsA.has_subdrs(d1) and self._drsB.has_subdrs(d1)

    def resolve_merges(self):
        return Imp(self._drsA.resolve_merges(), self._drsB.resolve_merges())


class Or(AbstractDRSCond):
    """A disjunction between two DRSs"""
    def __init__(self, drsA, drsB):
        if not isinstance(drsA, AbstractDRS) or not isinstance(drsB, AbstractDRS):
            raise TypeError
        self._drsA = drsA
        self._drsB = drsB

    def __ne__(self, other):
        return self._drsA != other._drsA or self._drsB != other._drsB

    def __eq__(self, other):
        return self._drsA == other._drsA and self._drsB == other._drsB

    def __repr__(self):
        return 'Or(%s,%s)' % (self._drsA, self._drsB)

    def _antecedent(self, ref, drs):
        return (self._drsA.has_subdrs(drs) and ref.has_bound(drs, self._drsA)) or \
               (self._drsB.has_subdrs(drs) and ref.has_bound(drs, self._drsB))

    def _get_freerefs(self, ld, gd):
        # free (Imp d1 d2:cs) = drsFreeRefs d1 gd `union` drsFreeRefs d2 gd `union` free cs
        return union(self._drsA.get_freerefs(gd), self._drsB.get_freerefs(gd))

    def _isproper_subdrsof(self, sd, gd):
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
        u = self._drsB.get_universes(u)
        return u

    def _variables(self, u):
        u = self._drsA.get_variables(u)
        u = self._drsB.get_variables(u)
        return u

    # Helper for DRS.get_lambda_tuples()
    def _lambda_tuple(self, u):
        u = self._drsA.get_lambda_tuples(u)
        return self._drsB.get_lambda_tuples(u)

    # Original haskell code in DRS/Input/LambdaCalculus.hs:renameCons:convertCon
    def _convert(self, ld, gd, rs):
        return Or(rename_subdrs(self._drsA, gd, rs), rename_subdrs(self._drsB, gd, rs))

    # Original haskell code in DRS/Input/LambdaCalculus.hs:purifyRefs:purify
    def _purify(self, gd, rs):
        orsd = intersect(self._drsA.universe, rs)
        nrs = zip(orsd, union_inplace(get_new_drsrefs(orsd, gd.get_variables()), rs))
        # In case we do not want to rename ambiguous bindings:
        # ors = drsUniverses d2 \\ drsUniverse d1 `intersect` rs
        cd1, rs1 = rename_subdrs(self._drsA, gd, nrs).purify_refs(gd, rs)
        cd2, rs2 = rename_subdrs(self._drsB, gd, nrs).purify_refs(gd, rs1)
        return Or(cd1,cd2), rs2

    @property
    def isresolved(self):
        return self._drsA.isresolved and self._drsB.isresolved

    def has_subdrs(self, d1):
        return self._drsA.has_subdrs(d1) and self._drsB.has_subdrs(d1)

    def resolve_merges(self):
        return Or(self._drsA.resolve_merges(), self._drsB.resolve_merges())


class Prop(AbstractDRSCond):
    """A proposition DRS"""
    def __init__(self, drsRef, drs):
        if not isinstance(drs, AbstractDRS) or not isinstance(drsRef, AbstractDRSRef):
            raise TypeError
        self._drs = drs
        self._ref = drsRef

    def __ne__(self, other):
        return self._ref != other._ref or self._drs != other._drs

    def __eq__(self, other):
        return self._ref == other._ref and self._drs == other._drs

    def __repr__(self):
        return 'Prop(%s,%s)' % (self._ref, self._drs)

    def _antecedent(self, ref, drs):
        return self._drs.has_subdrs(drs) and ref.has_bound(drs, self._drs)

    def _get_freerefs(self, ld, gd):
        # free (Prop r d1:cs) = snd (partition (flip (`drsBoundRef` ld) gd) [r]) `union` drsFreeRefs d1 gd `union` free cs
        return union(filter(lambda x: not x.has_bound(x, ld, gd), [self._ref]), self._drs.get_freerefs(gd))

    def _isproper_subdrsof(self, sd, gd):
        """Helper for DRS.isproper"""
        return self._ref.has_bound(sd, gd) and self._drs._isproper_subdrsof(gd)

    def _ispure(self, ld, gd, rs):
        if not _pure_refs(ld, gd, [self._ref], rs) or not self._drs._ispure_helper(rs, gd):
            return (False, None)
        rs = self._drs.get_variables(rs)
        return True, rs

    def _universes(self, u):
        return self._drs.get_universes(u)

    def _variables(self, u):
        if self._ref in u:
            return self._drs.get_variables(u)
        u.append(self._ref)
        return self._drs.get_variables(u)

    # Helper for DRS.get_lambda_tuples()
    def _lambda_tuple(self, u):
        u = self._ref._lambda_tuple(u)
        return self._drs.get_lambda_tuples(u)

    # Original haskell code in DRS/Input/LambdaCalculus.hs:renameCons:convertCon
    def _convert(self, ld, gd, rs):
        return Prop(rename_var(self._ref,rs) if self._ref.has_bound(ld, gd) else self._ref, rename_subdrs(self._drs, gd, rs))

    # Original haskell code in DRS/Input/LambdaCalculus.hs:purifyRefs:purify
    def _purify(self, gd, rs):
        # FIXME: does this really need to be added to front of list
        rsx = [self._ref]
        rsx.extend(rs)
        cd1, rs1 = self._drs.purify_refs(gd, rsx)
        return Prop(self._ref, cd1), rs1

    @property
    def isresolved(self):
        return self._ref.isresolved and self._drs.isresolved

    def has_subdrs(self, d1):
        return self._drs.has_subdrs(d1)

    def resolve_merges(self):
        return Prop(self._ref, self._drs.resolve_merges())


class Diamond(AbstractDRSCond):
    """A possible DRS"""
    def __init__(self, drs):
        if not isinstance(drs, AbstractDRS):
            raise TypeError
        self._drs = drs

    def __ne__(self, other):
        return self._drs != other._drs

    def __eq__(self, other):
        return self._drs == other._drs

    def __repr__(self):
        return 'Diamond(%s)' % self._drs

    def _get_freerefs(self, ld, gd):
        # free (Neg d1:cs) = drsFreeRefs d1 gd `union` free cs
        return self._drs.get_freerefs(gd)

    def _isproper_subdrsof(self, sd, gd):
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

    def _variables(self, u):
        return self._drs.get_variables(u)

    # Helper for DRS.get_lambda_tuples()
    def _lambda_tuple(self, u):
        return self._drs.get_lambda_tuples(u)

    # Original haskell code in DRS/Input/LambdaCalculus.hs:renameCons:convertCon
    def _convert(self, ld, gd, rs):
        return Diamond(rename_subdrs(self._drs, gd, rs))

    # Original haskell code in DRS/Input/LambdaCalculus.hs:purifyRefs:purify
    def _purify(self, gd, rs):
        cd1, rs1 = self._drs.purify_refs(gd, rs)
        return Diamond(cd1), rs1

    @property
    def isresolved(self):
        return self._drs.isresolved

    def has_subdrs(self, d1):
        return self._drs.has_subdrs(d1)

    def resolve_merges(self):
        return Diamond(self._drs.resolve_merges())


class Box(AbstractDRSCond):
    """A necessary DRS"""
    def __init__(self, drs):
        if not isinstance(drs, AbstractDRS):
            raise TypeError
        self._drs = drs

    def __ne__(self, other):
        return self._drs != other._drs

    def __eq__(self, other):
        return self._drs == other._drs

    def __repr__(self):
        return 'Box(%s)' % self._drs

    def _get_freerefs(self, ld, gd):
        # free (Neg d1:cs) = drsFreeRefs d1 gd `union` free cs
        return self._drs.get_freerefs(gd)

    def _isproper_subdrsof(self, sd, gd):
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

    def _variables(self, u):
        return self._drs.get_variables(u)

    # Helper for DRS.get_lambda_tuples()
    def _lambda_tuple(self, u):
        return self._drs.get_lambda_tuples(u)

    # Original haskell code in DRS/Input/LambdaCalculus.hs:renameCons:convertCon
    def _convert(self, ld, gd, rs):
        return Box(rename_subdrs(self._drs, gd, rs))

    # Original haskell code in DRS/Input/LambdaCalculus.hs:purifyRefs:purify
    def _purify(self, gd, rs):
        cd1, rs1 = self._drs.purify_refs(gd, rs)
        return Box(cd1), rs1

    @property
    def isresolved(self):
        return self._drs.isresolved

    def has_subdrs(self, d1):
        return self._drs.has_subdrs(d1)

    def resolve_merges(self):
        return Box(self._drs.resolve_merges())
