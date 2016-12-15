from utils import iterable_type_check, union, union_inplace, intersect, rename_var, compare_lists_eq
from common import SHOW_BOX, SHOW_LINEAR, SHOW_SET, SHOW_DEBUG
from common import LambdaDRSVar
from drs import AbstractDRSRef, DRSRef, LambdaDRSRef, AbstractDRSCond, AbstractDRS, LambdaTuple
from drs import LambdaDRS, Merge, DRS
from drs import Rel, Neg, Imp, Or, Diamond, Box, Prop
# Note: get_new_drsrefs() works on any AbstractPDRSRef.
from drs import get_new_drsrefs
import networkx as nx


PVar = int


## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Variables.hs">/Data/PDRS/Variables.hs:newPVars</a>
def get_new_pvars(opvs, epvs):
    """Returns a list of new projection variables from a list of old
    PVar's opvs, based on a list of existing PVar's epvs.

    Args:
        opvs: Old projection variables.
        evps: Existing projection variables.

    Returns:
        A list of projection variables.
    """
    if len(epvs) == 0: return opvs
    n = max(epvs) + 1
    return [x+n for x in range(len(opvs))]


## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/LambdaCalculus.hs">/Data/PDRS/LambdaCalculus.hs:renamePVar</a>
def rename_pvar(pv, lp, gp, ps):
    """Converts a PVar into a new PVar in case it occurs bound in
    local PDRS lp in global PDRS gp.

    Args:
        pv: The projection variable to rename.
        lp: The local PDRS.
        gp: The global PDRS.
        ps: A list project variable tuples for renaming.

    Returns:
        A projection variable.
    """
    if not gp.test_bound_pvar(abs(pv), lp):
        return pv
    if pv < 0:
        return rename_var(abs(pv), ps)
    return rename_var(pv, ps)


## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/LambdaCalculus.hs">/Data/PDRS/LambdaCalculus.hs:renamePDRSRef</a>
def rename_pdrsref(pv, r, lp, gp, rs):
    """Applies alpha conversion to a projected referent PRef(pv,r), in
    local PDRS lp which is in global PDRS gp, on the basis of two conversion lists
    for projection variables ps and PDRS referents rs
    """
    u = gp.get_universes()
    prtest = PRef(pv, r)
    if any([prtest.has_projected_bound(lp, pr, gp) and gp.test_free_pvar(pr.plabel) for pr in u]) or \
            not prtest.has_bound(lp, gp):
        return r
    return rename_var(r, rs)


## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/LambdaCalculus.hs">/Data/PDRS/LambdaCalculus.hs:renameMAPs</a>
def rename_mapper(m, lp, gp, ps):
    """Applies alpha conversion to a list of MAP's m, on the basis of a
    conversion list for projection variables ps.
    """
    return map(lambda x: MAP(rename_pvar(x[0], lp, gp, ps), rename_pvar(x[1], lp, gp, ps)), m)


## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/LambdaCalculus.hs">/Data/PDRS/LambdaCalculus.hs:renameUniverse</a>
def rename_universe(u, lp, gp, ps, rs):
    """Applies alpha conversion to a list of PRef's u, on the basis of
    a conversion list for PVar's ps and PDRSRef's rs.
    """
    return map(lambda r: PRef(rename_pvar(r.plabel, lp, gp, ps), rename_pdrsref(r.plabel, r.ref, lp, gp, rs)), u)


## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Merge.hs">/Data/PDRS/Merge.hs:pdrsDisjoin</a>
def disjoin(d1, d2):
    """Disjoins PDRS d1 from PDRS d2, where d1 is disjoined from d2 iff all duplicate
    occurrences of PVar's and PDRSRef's from PDRS d2 in PDRS d1 are replaced by new
    variables.
    """
    ops = intersect(d2.get_pvars(), d1.get_pvars())
    nps = get_new_pvars(ops, union(d2.get_pvars(), d1.get_pvars()))
    ors = intersect(d2.get_variables(), d1.get_variables())
    nrs = get_new_drsrefs(ors, union(d2.get_variables(), d1.get_variables()))
    return d2.alpha_convert(zip(ors, nrs), zip(ops, nps))


## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Merge.hs">/Data/PDRS/Merge.hs:pdrsAMerge</a>
def amerge(d1, d2):
    """Applies assertive merge to PDRS d1 and PDRS d2,"""
    if isinstance(d2, LambdaPDRS) or isinstance(d1, LambdaPDRS):
        return AMerge(d1, d2)
    elif isinstance(d2, AMerge):
        if d2.drs_a.islambda:
            return AMerge(d2.drs_a, amerge(d1, d2.drs_b))
        elif d2.drs_b.islambda:
            return AMerge(amerge(d1, d2.drs_a), d2.drs_b)
        else:
            return amerge(d1, d2.resolve_merges())
    elif isinstance(d1, AMerge):
        if d1.drs_a.islambda:
            return AMerge(d1.drs_a, amerge(d1.drs_b, d2))
        elif d1.drs_b.islambda:
            return AMerge(d1.drs_b, amerge(d1.drs_a, d2))
        else:
            return amerge(d2, d1.resolve_merges())
    elif isinstance(d2, PMerge):
        if d2.drs_a.islambda:
            return PMerge(d2.drs_a, amerge(d1, d2.drs_b))
        elif d2.drs_b.islambda:
            return AMerge(pmerge(d1, d2.drs_a), d2.drs_b)
        else:
            return amerge(d1, d2.resolve_merges())
    elif isinstance(d1, PMerge):
        if d1.drs_a.islambda:
            return PMerge(d1.drs_a, amerge(d1.drs_b, d2))
        elif d1.drs_b.islambda:
            return AMerge(d1.drs_b, pmerge(d1.drs_a, d2))
        else:
            return amerge(d2, d1.resolve_merges())
    else:
        p1 = d1.resolve_merges().purify()
        p2 = disjoin(d2.resolve_merges().purify(), p1)
        if not iterable_type_check([p1, p2], PDRS):
            return AMerge(p1, p2)
        p3 = p1.alpha_convert([(p1.label, p2.label)], [])
        p4 = PDRS(p1.label, p2.mapper, p2.referents, p2.conditions).alpha_convert([(p1.label, p2.label)], [])
        return PDRS(p2.label, union_inplace(p3.mapper, p4.mapper), union_inplace(p3.rererents, p4.rererents), \
                    union_inplace(p3.conditions, p4.conditions)).purify()


## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Merge.hs">/Data/PDRS/Merge.hs:pdrsPMerge</a>
def pmerge(d1, d2):
    """Applies projective merge to PDRS d1 and PDRS d2,"""
    if isinstance(d2, LambdaPDRS) or isinstance(d1, LambdaPDRS):
        return PMerge(d1, d2)
    elif isinstance(d2, PMerge):
        if d2.drs_a.islambda:
            return AMerge(d2.drs_a, pmerge(d1, d2.drs_b))
        elif d2.drs_b.islambda:
            return AMerge(pmerge(d1, d2.drs_a), d2.drs_b)
        else:
            return pmerge(d1, d2.resolve_merges())
    elif isinstance(d1, AMerge):
        if d1.drs_a.islambda:
            return PMerge(amerge(d1.drs_a, d1.drs_a.get_empty()), pmerge(d1.drs_b, d2))
        elif d1.drs_b.islambda:
            return PMerge(d1.drs_b, amerge(d1.drs_a, pmerge(d1.drs_a, d2)))
        else:
            return pmerge(d2, d1.resolve_merges())
    elif isinstance(d2, PMerge):
        if d2.drs_a.islambda:
            return PMerge(d2.drs_a, pmerge(d1, d2.drs_b))
        elif d2.drs_b.islambda:
            return PMerge(pmerge(d1, d2.drs_a), d2.drs_b)
        else:
            return pmerge(d1, d2.resolve_merges())
    elif isinstance(d1, PMerge):
        if d1.drs_a.islambda:
            return PMerge(d1.drs_a, pmerge(d1.drs_b, d2))
        elif d1.drs_b.islambda:
            return PMerge(d1.drs_b, pmerge(d1.drs_a, d2))
        else:
            return pmerge(d2, d1.resolve_merges())
    else:
        p1 = d1.resolve_merges().purify()
        p2 = disjoin(d2.resolve_merges().purify(), p1)
        if not iterable_type_check([p1, p2], PDRS):
            return PMerge(p1, p2)
        return PDRS(p2.label, union_inplace(union_inplace([p2.label, p1.label], p1.mapper), p2.mapper), \
                    union_inplace(p1.rererents, p2.rererents), \
                    union_inplace(p1.conditions, p1.conditions)).purify()


# Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/LambdaCalculus.hs">/Data/PDRS/LambdaCalculus.hs:unboundDupPRefs:dup</a>
def _dup(pr, eps, lp, gp):
    if not gp.test_bound_pvar(pr.plabel, lp):
        return False
    for prd in eps:
        if pr.ref == prd.ref and pr.test_independent(lp, gp, [prd]):
            return True
    return False


class MAP(object):
    def __init__(self, v1, v2):
        self._v1 = v1
        self._v2 = v2

    def __ne__(self, other):
        return type(self) != type(other) or self._v1 != other._v1 or self._v2 != other._v2

    def __eq__(self, other):
        return type(self) == type(other) and self._v1 == other._v1 and self._v2 == other._v2

    def __len__(self):
        return 2

    def __getitem__(self, idx):
        if idx < 0 or idx > 2:
            raise IndexError
        return self._v1 if idx == 0 else self._v2

    def __str__(self):
        return '(%i, %i)' % (self._v1, self._v2)

    def __repr__(self):
        return 'MAP(%i, %i)' % (self._v1, self._v2)

    def __unicode__(self):
        return u'(%i, %i)' % (self._v1, self._v2)

    def __hash__(self):
        return hash(self.__repr__())

    def swap(self):
        return MAP(self._v2, self._v1)

    def to_tuple(self):
        return (self._v1, self._v2)

    def to_list(self):
        return [self._v1, self._v2]

    def show(self, notation):
        """Display for screen.

        Args:
            notation: An integer notation. Ignored for this class.

        Returns:
            A unicode string.
        """
        return u'(%s,%s)' % self.to_tuple()


class PDRSRef(DRSRef):
    """A PDRS referent"""
    def __init__(self, drsVar):
        super(PDRSRef,self).__init__(drsVar)

    def __repr__(self):
        return 'PDRSRef(%s)' % self._var

    def _has_antecedent(self, drs, conds):
        return False

    def has_bound(self, drsLD, drsGD):
        """Disabled for PDRS. Always returns False."""
        return False

    def increase_new(self):
        r = super(PDRSRef, self).increase_new()
        return PDRSRef(r._var)

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Variables.hs">/Data/PDRS/Variables.hs:pdrsRefToDRSRef</a>
    def to_drsref(self):
        """Converts a PDRSRef into a DRSRef"""
        return DRSRef(self._var)


class LambdaPDRSRef(LambdaDRSRef):
    """A lambda PDRS referent"""
    def __init__(self, lambdaVar, pos):
        super(LambdaPDRSRef,self).__init__(lambdaVar, pos)

    def __repr__(self):
        return 'LambdaPDRSRef(%s,%i)' % (self._var.var, self._pos)

    def _has_antecedent(self, drs, conds):
        return False

    def has_bound(self, drsLD, drsGD):
        """Disabled for PDRS. Always returns False."""
        return False

    def increase_new(self):
        r = super(LambdaPDRSRef, self).increase_new()
        return LambdaPDRSRef(r._var, r._pos)

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Variables.hs">/Data/PDRS/Variables.hs:pdrsRefToDRSRef</a>
    def to_drsref(self):
        """Converts a PDRSRef into a DRSRef"""
        return LambdaDRSRef(self._var, self._pos)


class PRef(AbstractDRSRef):
    """A projected referent, consisting of a PVar and a AbstractPDRSRef"""
    def __init__(self, label, drsRef):
        if not isinstance(label, PVar) or not isinstance(drsRef, (PDRSRef, LambdaPDRSRef)):
            raise TypeError
        self._plabel = label
        self._ref = drsRef

    def __ne__(self, other):
        return type(self) != type(other) or self._plabel != other._plabel or self._ref != other._ref

    def __eq__(self, other):
        return type(self) == type(other) and self._plabel == other._plabel and self._ref == other._ref

    def __repr__(self):
        return 'PRef(%i,%s)' % (self._plabel, repr(self._ref))

    @property
    def isresolved(self):
        return self._ref.isresolved

    def _has_antecedent(self, drs, conds):
        # Not required for PRef's
        return False

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Binding.hs">/Data/PDRS/Binding.hs:pdrsBoundPRef</a>
    def has_bound(self, drsLP, drsGP):
        """Test whether this PRef in context drsLP is bound in the PDRS drsGP."""

        # Where this PRef is bound iff there exists a context pv, such that:
        #  - pv is accessible from the introduction site of @pr@ drsLP; and
        #  - pv is accessible from the interpretation site of @pr@ (@this@); and
        # - together with the PDRSRef of @pr@ (@r@), @pv@ forms a 'PRef'
        #   that is introduced in some universe in drsGP.
        if not isinstance(drsLP, AbstractPDRS) or not isinstance(drsGP, AbstractPDRS):
            raise TypeError
        pg = drsGP.get_pgraph()
        vs = pg.nodes()
        if drsLP.label in vs and self._plabel in vs:
            for pv in vs:
                if pv in nx.dfs_postorder_nodes(pg, source=drsLP.label) and \
                    pv in nx.dfs_postorder_nodes(pg, source=self.plabel) and \
                    PRef(pv,self._ref) in drsGP.get_universes():
                    return True
        return False

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Binding.hs">/Data/PDRS/Binding.hs:pdrsPRefBoundByPRef</a>
    def has_projected_bound(self, pdrs1, pr2, pdrs2):
        """Test whether this PRef introduced in local PDRS pdrs1 is bound by
        projected referent pr2 in PDRS pdrs2.
        """
        # where boundByPRef self=pr1 pdrs1 pr2 pdrs2 iff
        # 1. @pr1@ and @pr2@ share the same referent; and
        # 2. @pr2@ is part of some universe in @pdrs2@ (i.e., can bind referents); and
        # 3. The interpretation site of @pr2@ is accessible from both the
        #    introduction and interpretation site of @pr1@.
        if not isinstance(pr2, PRef) or not isinstance(pdrs1, AbstractPDRS) or not isinstance(pdrs2, AbstractPDRS):
            raise TypeError
        return self.ref == pr2.ref and pr2 in pdrs2.get_universes() and \
               pdrs2.has_accessible_context(self.plabel, pr2.plabel) and \
               pdrs2.has_accessible_context(pdrs1.label, pr2.plabel)

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Binding.hs">/Data/PDRS/Binding.hs:pdrsPBoundPRef</a>
    def has_other_bound(self, drsLP, drsGP):
        """Test whether a referent is bound by some other referent than itself."""
        u = drsGP.get_universes()
        u.remove(self)
        return any([self.has_projected_bound(drsLP, x, drsGP) for x in u])

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/LambdaCalculus.hs">/Data/PDRS/LambdaCalculus.hs:independentPRefs</a>
    def test_independent(self, lp, gp, prs):
        """Test whether this PRef is independent based on a list of PRef's prs,
        where: This PRef=pr is not independent w.r.t. prs iff

        (1) pr is bound by any 'PRef' in prs; and
        (2) pr occurs free and there is some element of prs that is accessible
            from this. (NB. this only holds if both pr and @pr'@ occur free in
            accessible contexts, in which case they are not independent).
        (3) pr occurs free and there is some element of @prs@ that may become
            accessible from @pr@ at some later point, because its projection site
            is undetermined with respect to the projection site of @pr@. This is
            the case if the projection site occurs free (i.e., has no path to the
            global context).
        """
        hb = not self.has_bound(lp, gp)
        for prd in prs:
            if self.has_projected_bound(lp, prd, gp) \
                    or (hb and (gp.has_accessible_context(self.plabel, prd) or not gp.test_free_pvar(prd.plabel))):
                return False
        return True

    # Helper for PDRS.get_lambda_tuples()
    def _lambda_tuple(self, u):
        return self._ref._lambda_tuple(u)

    @property
    def var(self):
        return self._ref.var

    @property
    def ref(self):
        return self._ref

    @property
    def plabel(self):
        return self._plabel

    def increase_new(self):
        return PRef(self._plabel, self._ref.increase_new())

    def to_drsref(self):
        return self._ref.to_drsref()

    def show(self, notation):
        """Display for screen.

        Args:
            notation: An integer notation.

        Returns:
            A unicode string.
        """
        if notation == SHOW_BOX:
            return u'%i %s %s' % (self._plabel, self.modPointer, self._ref.show(notation))
        return u'<%i, %s>' % (self._plabel, self._ref.show(notation))


class AbstractPDRS(AbstractDRS):
    """Discourse Representation Structure"""

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/ProjectionGraph.hs">/Data/PDRS/ProjectionGraph.hs:edges</a>.
    def _edges(self, es):
        #  Derives a list of networkx.Graph edges from a PDRS
        return es

    # Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/ProjectionGraph.hs">/Data/PDRS/ProjectionGraph.hs:edges</a>.
    def _no_edges(self):
        return True

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Structure.hs">/Data/PDRS/Structure.hs:pdrsLabel</a>
    @property
    def label(self):
        """Get the projection label"""
        return 0

    ## @remarks original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Properties.hs">/Data/DRS/Properties.hs:isPurePDRS</a>.
    @property
    def ispure(self):
        """Test whether this DRS is pure, where:
        A DRS is pure iff it does not contain any otiose declarations of discourse referents
        (i.e. it does not contain any unbound, duplicate uses of referents).

        Returns:
            True if this DRS is pure.
        """
        return self == self.purify()

    ## @remarks original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Properties.hs">/Data/DRS/Properties.hs:isPresupPDRS</a>.
    @property
    def ispresup(self):
        """Test whether this PDRS is presuppositional, where a PDRS is presuppositional
        iff it contains free pointers.
        """
        raise NotImplementedError

    ## @remarks original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Properties.hs">/Data/DRS/Properties.hs:isPlainPDRS</a>.
    @property
    def isplain(self):
        """Test whether this PDRS is plain, where a PDRS is plain iff all projection pointers
        are locally bound.
        """
        raise NotImplementedError

    ## @remarks original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Properties.hs">/Data/DRS/Properties.hs:isSimplePDRS</a>.
    @property
    def issimple(self):
        """Test whether this PDRS is simple, where a PDRS is simple iff it
        does not contain free pointers.
        """
        return not self.ispresup

    ## @remarks original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Properties.hs">/Data/DRS/Properties.hs:isFOLDRS</a>.
    @property
    def isfol(self):
        """Test whether this DRS can be translated into a FOLForm instance."""
        return self.to_drs().isfol

    ## @remarks original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Structure.hs">/Data/PDRS/Structure.hs:isResolvedPDRS</a>.
    @property
    def isresolved(self):
        """Test whether this PDRS is resolved (containing no unresolved merges or lambdas)."""
        return False

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Structure.hs">/Data/PDRS/Structure.hs:emptyPDRS</a>.
    def get_empty(self):
        """Returns an empty PDRS, if possible with the same label as this one."""
        raise NotImplementedError

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Structure.hs">/Data/PDRS/Structure.hs:pdrsLabels</a>
    def get_labels(self, u=None):
        """Returns all the labels in a PDRS."""
        return u

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Variables.hs">/Data/PDRS/Variables.hs:pdrsPVars</a>
    def get_pvars(self, u=None):
        """Returns the list of all 'PVar's in an AbstractPDRS"""
        return u

    ## @remarks original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Binding.hs">/Data/PDRS/Binding.hs:pdrsFreePVars</a>.
    def get_free_pvars(self, gp, u=None):
        """Returns the list of all free PVar's in this PRDS, which is a sub PDRS of global PDRS gp."""
        return u

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Structure.hs">/Data/PDRS/Structure.hs:pdrsMAPs</a>
    def get_maps(self, u=None):
        return u

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/ProjectionGraph.hs">/Data/PDRS/ProjectionGraph.hs:projectionGraph</a>.
    def get_pgraph(self):
        """Derives a Projection Graph' for this PDRS

        Returns:
            A networkx.Graph instance
        """
        # get vertex count
        es = self._edges([])
        g = nx.Graph()
        g.add_edges_from(es)
        return g

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/LambdaCalculus.hs">/Data/PDRS/LambdaCalculus.hs:unboundDupPRefs</a>.
    def get_unbound_dup_prefs(self, gp, eps=None):
        """Returns a tuple of existing 'PRef's (eps) and unbound duplicate 'PRef's
        (dps) in a 'PDRS', based on a list of seen 'PRef's prs.

        Where pr = PRef(p. r) is duplicate in PDRS gp iff there exists a p'
        such that pr' = PRef(p',r) is an element prs, and pr and pr' are independent.
        """
        raise NotImplementedError

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/ProjectionGraph.hs">/Data/PDRS/ProjectionGraph.hs:pdrsIsAccessibleContext</a>.
    def has_accessible_context(self, p1, p2):
        """Test whether PDRS context p2 is accessible from PDRS context p1 in this PDRS"""
        pg = self.get_pgraph()
        vs = pg.nodes()
        return p1 in vs and p2 in vs and p2 in nx.dfs_postorder_nodes(pg, source=p1)

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Binding.hs">/Data/PDRS/Binding.hs:pdrsIsFreePVar</a>.
    def test_free_pvar(self, pv):
        """Test whether pv is a free projection variable in this PDRS,
        where: pv is free iff:
            - context pv is accessible from the global context, or
            - there is no context v that is accessible from pv and also from the global context.
        """
        if pv == self.label: return False
        pg = self.get_pgraph()
        vs = pg.nodes()
        if pv not in vs: return True
        this_scope = list(nx.dfs_postorder_nodes(pg, source=self.label))
        return pv in this_scope or not any([(x in nx.dfs_postorder_nodes(pg, source=pv) and x in this_scope) for x in vs])

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Binding.hs">/Data/PDRS/Binding.hs:pdrsBoundPVar</a>.
    def test_bound_pvar(self, pv, lp):
        """Test whether a pointer pv in local PDRS lp is bound by a label in this global PDRS."""
        return False

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/LambdaCalculus.hs">/Data/PDRS/LambdaCalculus.hs:purifyPVars</a>
    def purify_pvars(self, gp, pvs):
        raise NotImplementedError

    ## @remarks original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/LambdaCalculus.hs">/Data/PDRS/LambdaCalculus.hs:pdrsPurify</a>
    def purify(self):
        """Converts a PDRS into a pure PDRS by by first purifying its
        projection variables, and then purifying its projected referents,
        where a PDRS is pure iff there are no occurrences of duplicate, unbound uses
        of the same PVar or PDRSRef.
        """
        cgp, _ = self.purify_pvars(self, self.get_free_pvars(self))
        _, prs = cgp.get_unbound_dup_prefs(cgp)
        drs, _ = cgp.purify_refs(cgp, zip(prs, get_new_drsrefs(prs, cgp.get_variables())))
        return drs

    # Original haskell code in `https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/movePContent.hs`
    def _move_pcontent(self, lp, gp):
        """Moves projected content in PDRS to its interpretation site in PDRS lp
        based on global PDRS gp.
        """
        raise NotImplementedError

    # Original haskell code in `https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/insertPRefs.hs`
    def _insert_prefs(self, pref, gp):
        raise NotImplementedError

    # Original haskell code in `https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/insertPCon.hs`
    def _insert_pcond(self, pcon, gp):
        raise NotImplementedError

    ## @remarks original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Translate.hs">/Data/PDRS/Translate.hs:stripPVars</a>
    def strip_pvars(self):
        """Strips projection variables from this PDRS resulting in a DRS."""
        raise NotImplementedError

    def to_mfol(self, world):
        """Converts a PDRS to a modal FOL formula with world.

        Args:
            world: A ie.fol.FOLVar instance

        Returns:
            An ie.fol.FOLForm instance.

        Raises:
            ie.fol.FOLConversionError
        """
        return self.to_drs().to_mfol(world)

    def to_drs(self):
        """Translates a PDRS into a DRS."""
        gp = self.resolve_merges().purify()
        return gp._move_pcontent(gp.get_empty(), gp).strip_pvars()


class LambdaPDRS(AbstractPDRS):
    """A lambda PDRS."""
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
        return type(self) != type(other) or self._var != other._var or self._pos != other._pos

    def __eq__(self, other):
        return type(self) == type(other) and self._var == other._var and self._pos == other._pos

    def __repr__(self):
        return 'LambdaPDRS(%s,%i)' % (self._var, self._pos)

    def _isproper_subdrsof(self, d):
        """Help for isproper"""
        return True

    @property
    def islambda(self):
        """Test whether this PDRS is entirely a LambdaPDRS (at its top-level)."""
        return True

    ## @remarks original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Properties.hs">/Data/DRS/Properties.hs:isPresupPDRS</a>.
    @property
    def ispresup(self):
        """Test whether this PDRS is presuppositional, where a PDRS is presuppositional
        iff it contains free pointers.
        """
        return False

    ## @remarks original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Properties.hs">/Data/DRS/Properties.hs:isPlainPDRS</a>.
    @property
    def isplain(self):
        """Test whether this PDRS is plain, where a PDRS is plain iff all projection pointers
        are locally bound.
        """
        return True

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Structure.hs">/Data/PDRS/Structure.hs:emptyPDRS</a>.
    def get_empty(self):
        """Returns an empty PDRS, if possible with the same label as this one."""
        return self

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Variables.hs">/Data/PDRS/Variables.hs:pdrsVariables</a>.
    def get_variables(self, u=None):
        """Returns the list of all variables in a PDRS"""
        if u is None:
            return [PDRSRef(v) for v in self._var._set]
        return union_inplace(u, [PDRSRef(v) for v in self._var._set])

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Variables.hs">/Data/PDRS/Variables.hs:pdrsLambdas</a>.
    def get_lambda_tuples(self, u=None):
        """Returns the set of all lambda tuples in this DRS."""
        lt = LambdaTuple(self._var, self._pos)
        if u is None:
            return set([lt])
        u.add(lt)
        return u

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/LambdaCalculus.hs">/Data/PDRS/LambdaCalculus.hs::renameSubPDRS</a>
    def rename_subdrs(self, gd, rs, ps=None):
        """Applies alpha conversion to this PDRS which is a sub-PDRS of the global PDRS gd,
        on the basis of two conversion lists: PDRSRef's rs and PVar's ps.

        Args:
            gd: An PDRS|LambdaPDRS|AMerge|PMerge instance.
            rs: A conversion list of PDRSRef|LambaPDRSRef tuples.
            ps: A conversion list of integer tuples. Type signature has default of None to be compatible
                wth DRS, however for PDRS it cannot be None.

        Returns:
            A PDRS instance.
        """
        if any([x is None for x in [gd, rs, ps]]):
            raise TypeError
        return LambdaPDRS(LambdaDRSVar(self._var._var, [rename_var(PDRSRef(v), rs).var for v in self._var._set]), self._pos)

    ## @remarks original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Merge.hs">/Data/PDRS/Merge.hs:pdrsResolveMerges</a>.
    def resolve_merges(self):
        """ Resolves all unresolved merges in a PDRS."""
        return self

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/LambdaCalculus.hs">/Data/PDRS/LambdaCalculus.hs:purifyPRefs</a>
    def purify_refs(self, gd, pvs):
        return self

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/LambdaCalculus.hs">/Data/PDRS/LambdaCalculus.hs:purifyPVars</a>
    def purify_pvars(self, gp, pvs):
        return self, pvs

    # Original haskell code in `https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/movePContent.hs`
    def _move_pcontent(self, lp, gp):
        """Moves projected content in PDRS to its interpretation site in PDRS lp
        based on global PDRS gp.
        """
        return self

    # Original haskell code in `https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/insertPRefs.hs`
    def _insert_prefs(self, pref, gp):
        return self

    # Original haskell code in `https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/insertPCon.hs`
    def _insert_pcond(self, pcon, gp):
        return self

    ## @remarks original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Translate.hs">/Data/PDRS/Translate.hs:stripPVars</a>
    def strip_pvars(self):
        """Strips projection variables from this PDRS resulting in a DRS."""
        return LambdaDRS(self._var, self._pos)

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/LambdaCalculus.hs">/Data/PDRS/LambdaCalculus.hs:unboundDupPRefs</a>.
    def get_unbound_dup_prefs(self, gp, eps=None):
        """Returns a tuple of existing 'PRef's (eps) and unbound duplicate 'PRef's
        (dps) in a PDRS, based on a list of seen 'PRef's prs.

        Where pr = PRef(p. r) is duplicate in PDRS gp iff there exists a p'
        such that pr' = PRef(p',r) is an element prs, and pr and pr' are independent.
        """
        if eps is None:
            return [], []
        return eps, []

    ## @remarks Original haskell code in `https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Show.hs`
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
        return u'LambdaPDRS ' + self._var.to_string().decode('utf-8')


class GenericMerge(AbstractPDRS):
    """Common merge pattern"""
    def __init__(self, drsA, drsB):
        if not isinstance(drsA, AbstractPDRS) or not isinstance(drsB, AbstractPDRS):
            raise TypeError
        self._drsA = drsA
        self._drsB = drsB

    def __ne__(self, other):
        return type(self) != type(other) or self._drsA != other._drsA or self._drsB != other._drsB

    def __eq__(self, other):
        return type(self) == type(other) and self._drsA == other._drsA and self._drsB == other._drsB

    def __repr__(self):
        return 'GMerge(%s,%s)' % (repr(self._drsA), repr(self._drsB))

    def _isproper_subdrsof(self, gd):
        """Help for isproper"""
        return self._drsA._isproper_subdrsof(gd) and self._drsB._isproper_subdrsof(gd)

    # Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/ProjectionGraph.hs">/Data/PDRS/ProjectionGraph.hs:edges</a>.
    def _edges(self, es=None):
        es = self._drsA._edges(es)
        return self._drsB._edges(es)

    def _show_brackets(self, s):
        # show() helper
        return self.show_modifier(u'(', 2, self.show_concat(s, self.show_padding(u')\n')))

    @property
    def drs_a(self):
        return self._drsA

    @property
    def drs_b(self):
        return self._drsB

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Structure.hs">/Data/PDRS/Structure.hs:pdrsLabel</a>
    @property
    def label(self):
        """Get the projection label"""
        return self._drsA.label if self._drsA.islambda else self._drsB.label

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Structure.hs">/Data/PDRS/Structure.hs:isMergePDRS</a>
    @property
    def ismerge(self):
        """Test whether this PDRS is a AMerge or PMerge (at its top-level)."""
        return True

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Structure.hs">/Data/PDRS/Structure.hs:isLambdaPDRS</a>
    @property
    def islambda(self):
        """Test whether this DRS/PDRS is entirely a LambdaDRS/LambdaPDRS (at its top-level)."""
        return self._drsB.islambda and self._drsB.islambda

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Structure.hs">/Data/PDRS/Structure.hs:emptyPDRS</a>.
    def get_empty(self):
        """Returns an empty PDRS, if possible with the same label as this one."""
        if self._drsB.islambda:
            return type(self)(self._drsA.get_empty(), self._drsB)
        return self._drsB.get_empty()

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Binding.hs">/Data/PDRS/Binding.hs:pdrsBoundPVar</a>.
    def test_bound_pvar(self, pv, lp):
        """Test whether a pointer pv in local PDRS lp is bound by a label in this global PDRS."""
        return self._drsA.test_bound_pvar(pv, lp) or self._drsB.test_bound_pvar(pv, lp)

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Variables.hs">/Data/PDRS/Variables.hs:pdrsVariables</a>.
    def get_variables(self, u=None):
        """Returns the list of all variables in a PDRS"""
        u = self._drsA.get_variables(u)
        return self._drsB.get_variables(u)

    ## @remarks Rriginal haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Structure.hs">/Data/PDRS/Structure.hs:pdrsUniverses</a>.
    def get_universes(self, u=None):
        """Returns the list of DRSRef's from all universes in this DRS."""
        u = self._drsA.get_universes(u)
        return self._drsB.get_universes(u)

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Structure.hs">/Data/PDRS/Structure.hs:pdrsLabels</a>
    def get_labels(self, u=None):
        """Returns all the labels in a PDRS."""
        u = self._drsA.get_labels(u)
        return self._drsB.get_labels(u)

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Variables.hs">/Data/PDRS/Variables.hs:pdrsPVars</a>
    def get_pvars(self, u=None):
        """Returns the set of all 'PVar's in an AbstractPDRS"""
        u = self._drsA.get_pvars(u)
        return self._drsB.get_pvars(u)

    ## @remarks original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Binding.hs">/Data/PDRS/Binding.hs:pdrsFreePVars</a>.
    def get_free_pvars(self, gp, u=None):
        """Returns the set of all free PVar's in this PRDS, which is a sub PDRS of global PDRS gp."""
        u = self._drsA.get_free_pvars(gp, u)
        return self._drsB.get_free_pvars(gp, u)

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Structure.hs">/Data/PDRS/Structure.hs:pdrsMAPs</a>
    def get_maps(self, u=None):
        """Returns the list of MAPs of this PDRS."""
        u = self._drsA.get_pvars(u)
        return self._drsB.get_pvars(u)

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Variables.hs">/Data/PDRS/Variables.hs:pdrsLambdas</a>.
    def get_lambda_tuples(self, u=None):
        """Returns the set of all lambda tuples in this DRS."""
        u = self._drsA.get_lambda_tuples(u)
        return self._drsB.get_lambda_tuples(u)

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/LambdaCalculus.hs">/Data/PDRS/LambdaCalculus.hs::renameSubPDRS</a>
    def rename_subdrs(self, gd, rs, ps=None):
        """Applies alpha conversion to this PDRS which is a sub-PDRS of the global PDRS gd,
        on the basis of two conversion lists: PDRSRef's rs and PVar's ps.

        Args:
            gd: An PDRS|LambdaPDRS|AMerge|PMerge instance.
            rs: A conversion list of PDRSRef|LambaPDRSRef tuples.
            ps: A conversion list of integer tuples. Type signature has default of None to be compatible
                wth DRS, however for PDRS it cannot be None.

        Returns:
            A PDRS instance.
        """
        if any([x is None for x in [gd, rs, ps]]):
            raise TypeError
        return type(self)(self._drsA.rename_subdrs(gd, rs, ps), self._drsB.rename_subdrs(gd, rs, ps))

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/LambdaCalculus.hs">/Data/PDRS/LambdaCalculus.hs:purifyPRefs</a>
    def purify_refs(self, gd, ers):
        return type(self)(self._drsA.purify_refs(gd, ers), self._drsB.purify_refs(gd, ers))

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/LambdaCalculus.hs">/Data/PDRS/LambdaCalculus.hs:purifyPVars</a>
    def purify_pvars(self, gp, pvs):
        cd1, pvs1 = self._drsA.purify_pvars(gp, pvs)
        cd2, pvs2 = self._drsB.purify_pvars(gp, pvs1)
        return type(self)(cd1, cd2), pvs2

    # Original haskell code in `https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/movePContent.hs`
    def _move_pcontent(self, lp, gp):
        """Moves projected content in PDRS to its interpretation site in PDRS lp
        based on global PDRS gp.
        """
        return self._drsB._move_pcontent(self._drsA._move_pcontent(lp, gp), gp)

    # Original haskell code in `https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/insertPRefs.hs`
    def _insert_prefs(self, pref, gp):
        return type(self)(self._drsA._insert_prefs(pref, gp), self._drsB._insert_prefs(pref, gp))

    # Original haskell code in `https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/insertPCon.hs`
    def _insert_pcond(self, pcon, gp):
        return type(self)(self._drsA._insert_prefs(pcon, gp), self._drsB._insert_prefs(pcon, gp))

    ## @remarks original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Translate.hs">/Data/PDRS/Translate.hs:stripPVars</a>
    def strip_pvars(self):
        """Strips projection variables from this PDRS resulting in a DRS."""
        return Merge(self._drsA.strip_pvars(), self._drsB.strip_pvars())

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/LambdaCalculus.hs">/Data/PDRS/LambdaCalculus.hs:unboundDupPRefs</a>.
    def get_unbound_dup_prefs(self, gp, eps=None):
        """Returns a tuple of existing 'PRef's (eps) and unbound duplicate 'PRef's
        (dps) in a PDRS, based on a list of seen 'PRef's prs.

        Where pr = PRef(p. r) is duplicate in PDRS gp iff there exists a p'
        such that pr' = PRef(p',r) is an element prs, and pr and pr' are independent.
        """
        if eps is None:
            eps = []
        eps1, dps1 = self._drsA.get_unbound_dup_prefs(gp, eps)
        eps2, dps2 = self._drsA.get_unbound_dup_prefs(gp, eps1)
        dps1.extend(dps2)
        return eps2, dps1


class AMerge(GenericMerge):
    """An assertive merge between two PDRSs"""
    def __init__(self, drsA, drsB):
        super(AMerge, self).__init__(drsA, drsB)

    def __repr__(self):
        return 'AMerge(%s,%s)' % (repr(self._drsA), repr(self._drsB))

    ## @remarks original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Properties.hs">/Data/DRS/Properties.hs:isPresupPDRS</a>.
    @property
    def ispresup(self):
        """Test whether this PDRS is presuppositional, where a PDRS is presuppositional
        iff it contains free pointers.
        """
        return self._drsA.ispresup or self._drsB.ispresup

    ## @remarks original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Properties.hs">/Data/DRS/Properties.hs:isPlainPDRS</a>.
    @property
    def isplain(self):
        """Test whether this PDRS is plain, where a PDRS is plain iff all projection pointers
        are locally bound.
        """
        return self._drsA.isplain and self._drsB.isplain

    ## @remarks original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Merge.hs">/Data/PDRS/Merge.hs:pdrsResolveMerges</a>.
    def resolve_merges(self):
        """ Resolves all unresolved merges in a PDRS."""
        return amerge(self._drsA, self._drsB)

    ## @remarks Original haskell code in `https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Show.hs`
    def show(self, notation):
        """For pretty printing.

        Args:
            notation: An integer notation.

        Returns:
             A unicode string.
        """
        if notation == SHOW_BOX:
            if self._drsA.islambda and self._drsB.islambda:
                self.show_modifier(u'(', 0, self.show_concat(self.show_concat(self._drsA.show(notation),
                                            self.show_modifier(self.opAMerge, 0, self._drsB.show(notation))), u')'))
            elif not self._drsA.islambda and self._drsB.islambda:
                return self._show_brackets(self.show_concat(self._drsA.show(notation),
                                            self.show_modifier(self.opAMerge, 2, self._drsA.show(notation))))
            elif self._drsA.islambda and not self._drsB.islambda:
                self._show_brackets(self.show_concat(self.show_padding(self._drsA.show(notation)),
                                            self.show_modifier(self.opAMerge, 2, self._drsB.show(notation))))
            return self._show_brackets(self.show_concat(self._drsA.show(notation),
                                            self.show_modifier(self.opAMerge, 2, self._drsB.show(notation))))
        elif notation in [SHOW_LINEAR, SHOW_SET]:
            return self._drsA.show(notation) + u' ' + self.opAMerge + u' ' + self._drsB.show(notation)
        return u'AMerge (' + self._drsA.show(notation) + ') (' + self._drsB.show(notation) + u')'


class PMerge(GenericMerge):
    """A projective merge between two PDRSs"""
    def __init__(self, drsA, drsB):
        super(PMerge, self).__init__(drsA, drsB)

    def __repr__(self):
        return 'PMerge(%s,%s)' % (repr(self._drsA), repr(self._drsB))

    ## @remarks original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Properties.hs">/Data/DRS/Properties.hs:isPresupPDRS</a>.
    @property
    def ispresup(self):
        """Test whether this PDRS is presuppositional, where a PDRS is presuppositional
        iff it contains free pointers.
        """
        return True

    ## @remarks original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Properties.hs">/Data/DRS/Properties.hs:isPlainPDRS</a>.
    @property
    def isplain(self):
        """Test whether this PDRS is plain, where a PDRS is plain iff all projection pointers
        are locally bound.
        """
        return False

    ## @remarks original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Merge.hs">/Data/PDRS/Merge.hs:pdrsResolveMerges</a>.
    def resolve_merges(self):
        """ Resolves all unresolved merges in a PDRS."""
        return pmerge(self._drsA, self._drsB)

    ## @remarks Original haskell code in `https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Show.hs`
    def show(self, notation):
        """For pretty printing.

        Args:
            notation: An integer notation.

        Returns:
             A unicode string.
        """
        if notation == SHOW_BOX:
            if self._drsA.islambda and self._drsB.islambda:
                self.show_modifier(u'(', 0, self.show_concat(self.show_concat(self._drsA.show(notation),
                                            self.show_modifier(self.opPMerge, 0, self._drsB.show(notation))), u')'))
            elif not self._drsA.islambda and self._drsB.islambda:
                return self._show_brackets(self.show_concat(self._drsA.show(notation),
                                            self.show_modifier(self.opPMerge, 2, self._drsA.show(notation))))
            elif self._drsA.islambda and not self._drsB.islambda:
                self._show_brackets(self.show_concat(self.show_padding(self._drsA.show(notation)),
                                            self.show_modifier(self.opPMerge, 2, self._drsB.show(notation))))
            return self._show_brackets(self.show_concat(self._drsA.show(notation),
                                            self.show_modifier(self.opPMerge, 2, self._drsB.show(notation))))
        elif notation in [SHOW_LINEAR, SHOW_SET]:
            return self._drsA.show(notation) + u' ' + self.opPMerge + u' ' + self._drsB.show(notation)
        return u'PMerge (' + self._drsA.show(notation) + ') (' + self._drsB.show(notation) + u')'


class PDRS(AbstractPDRS):
    """Projective Discourse Representation Structure.

    A Projected Discourse Representation Structure (PDRS) consists of a PDRS
    label and three sets: a set of MAPs, a set of projected discourse
    referents and a set of projected conditions.

    Pointers of referents and conditions can indicate projection, and the set
    of MAPs can indicate constraints on projection: MAP(1,2) means that 2 is an
    accessible context from 1, i.e., context 1 is weakly subordinate to 2 ("1
    <= 2"). Equivalence between two contexts ("1 = 2") can be represented by
    introducing a reciprocal accessibility relation: MAP(1,2) and MAP(2,1).
    Finally, strict subordination between contexts ("1 < 2") can be
    represented by introducing a negative edge from 2 to 1: MAP(2,-1) (negative
    pointers are used to represent negative edges).
    """
    def __init__(self, label, mapper, referents, conditions):
        """Constructor.

        Args:
            label: An integer label
            mapper: A List of MAPS indicating constraints on projection.
            referents: A list of projected referents PRef's.
            conditions: A list of projected conditions PConds's.
        """
        if not iterable_type_check(referents, PRef) or not iterable_type_check(conditions, PCond) or \
                not isinstance(label, PVar) or not iterable_type_check(mapper, MAP):
            raise TypeError
        self._refs = referents
        self._conds = conditions
        self._label = label
        self._mapper = mapper # maps a PVar to a PVar

    def __ne__(self, other):
        return type(self) != type(other) or self._label != other._label or not compare_lists_eq(self._refs, other._refs) \
               or not compare_lists_eq(self._conds, other._conds)

    def __eq__(self, other):
        return type(self) == type(other) and self._label == other._label and compare_lists_eq(self._refs, other._refs) \
               and compare_lists_eq(self._conds, other._conds)

    def __repr__(self):
        return 'PDRS(%i,%s,%s)' % (self._label, repr(self._refs), repr(self._conds))

    def _isproper_subdrsof(self, gd):
        """Help for isproper"""
        return all([x._isproper_subdrsof(self, gd) for x in self._conds])

    # Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/ProjectionGraph.hs">/Data/PDRS/ProjectionGraph.hs:edges</a>.
    def _edges(self, es):
        es.append((self._label, self._label))
        es.extend([m.to_tuple() for m in self._mapper])
        for c in self._conds:
            es = c._edges(es, self._label)
        return es

    @property
    def referents(self):
        return [x for x in self._refs] # shallow copy

    @property
    def conditions(self):
        return [x for x in self._conds] # shallow copy

    @property
    def label(self):
        return self._label

    @property
    def mapper(self):
        return [x for x in self._mapper] # shallow copy

    ## @remarks original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Properties.hs">/Data/DRS/Properties.hs:isPresupPDRS</a>.
    @property
    def ispresup(self):
        """Test whether this PDRS is presuppositional, where a PDRS is presuppositional
        iff it contains free pointers.
        """
        return any([self.test_free_pvar(x) for x in self.get_pvars()])

    ## @remarks original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Properties.hs">/Data/DRS/Properties.hs:isPlainPDRS</a>.
    @property
    def isplain(self):
        """Test whether this PDRS is plain, where a PDRS is plain iff all projection pointers
        are locally bound.
        """
        if not all([x.plabel == self._label for x in self._refs]): return False
        for c in self._conds:
            if not (c.plabel == self._label and c._plain()): return False
        return True

    ## @remarks original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Structure.hs">/Data/PDRS/Structure.hs:isResolvedPDRS</a>.
    @property
    def isresolved(self):
        """Test whether this PDRS is resolved (containing no unresolved merges or lambdas)."""
        return all([x.isresolved for x in self._refs]) and all([x.isresolved for x in self._conds])

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/ProjectionGraph.hs">/Data/PDRS/ProjectionGraph.hs:edges</a>.
    def _no_edges(self):
        False

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Structure.hs">/Data/PDRS/Structure.hs:emptyPDRS</a>.
    def get_empty(self):
        """Returns an empty PDRS, if possible with the same label as this one."""
        return PDRS(self._label,[],[],[])

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Variables.hs">/Data/PDRS/Variables.hs:pdrsVariables</a>.
    def get_variables(self, u=None):
        """Returns the list of all variables in a PDRS"""
        if u is None:
            u = [x.ref for x in self._refs] # shallow copy
        else:
            u = union_inplace(u, [x.ref for x in self._refs]) # union to avoid duplicates
        for c in self._conds:
            u = c._variables(u)
        return u

    ## @remarks Rriginal haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Structure.hs">/Data/PDRS/Structure.hs:pdrsUniverses</a>.
    def get_universes(self, u=None):
        """Returns the list of DRSRef's from all universes in this DRS."""
        if u is None:
            u = [x for x in self._refs] # shallow copy
        else:
            u.extend(self._refs)
        for c in self._conds:
            u = c._universes(u)
        return u

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Structure.hs">/Data/PDRS/Structure.hs:pdrsLabels</a>
    def get_labels(self, u=None):
        """Returns a list of all the labels in this PDRS."""
        if u is None:
            u = [self._label]
        else:
            u.append(self._label)
        for c in self._conds:
            u = c._labels(u)
        return u

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Variables.hs">/Data/PDRS/Variables.hs:pdrsPVars</a>
    def get_pvars(self, u=None):
        """Returns the set of all PVar's in this PDRS"""
        if u is None:
            u = set([self._label])
        elif not self._label in u:
            u.add(self._label)
        for x,y in self._mapper:
            u.add(x)
            u.add(y)
        for r in self._refs:
            u.add(r.plabel)
        #u = union_inplace(u, [r.plabel for r in self._refs])
        for c in self._conds:
            u = c._pvars(u)
        return u

    ## @remarks original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Binding.hs">/Data/PDRS/Binding.hs:pdrsFreePVars</a>.
    def get_free_pvars(self, gp, u=None):
        """Returns the set of all free PVar's in this PDRS, which is a sub PDRS of global PDRS gp."""
        if u is None: u = []
        for x in self._mapper:
            u.extend(filter(lambda pv: not gp.test_bound_pvar(pv, self), x.to_list()))
        u = union_inplace(u, filter(lambda pv: not gp.test_bound_pvar(pv, self), [x.plabel for x in self._refs]))
        for c in self._conds:
            if not gp.test_bound_pvar(c.plabel, self):
                u = union_inplace(u, [c.plabel])
            u = c._get_free_pvars(gp, u)
        return u

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Structure.hs">/Data/PDRS/Structure.hs:pdrsMAPs</a>
    def get_maps(self, u=None):
        """Returns the list of MAPs of this PDRS."""
        if u is None:
            u = [x for x in self._mapper] # shallow copy
        else:
            u = union(self._mapper, u)
        for c in self._conds:
            u = c._maps(u)
        return u

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Variables.hs">/Data/PDRS/Variables.hs:pdrsLambdas</a>.
    def get_lambda_tuples(self, u=None):
        """Returns the set of all lambda tuples in this DRS."""
        if u is None:
            u = set()
        for r in self._refs:
            u = r._lambda_tuple(u)
        for c in self._conds:
            u = c._lambda_tuple(u)
        return u

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Binding.hs">/Data/PDRS/Binding.hs:pdrsBoundPVar</a>.
    def test_bound_pvar(self, pv, lp):
        """Test whether a pointer pv in local PDRS lp is bound by a label in this global PDRS."""

        # where pv is bound iff:
        # - is equal to the label of either @lp@ or @gp@; or
        # - there exists a PDRS @p@ with label @pv@, such that @p@ is a subPDRS
        #   of @gp@ and @p@ is accessible from @lp@.
        #
        # Note the correspondence to DRSRef.has_bound()        if u is None
        if pv == lp.label or pv == self._label:
            return True
        for c in self._conds:
            if c._bound(lp, pv): return True
        return False

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/LambdaCalculus.hs">/Data/PDRS/LambdaCalculus.hs::renameSubPDRS</a>
    def rename_subdrs(self, gd, rs, ps=None):
        """Applies alpha conversion to this PDRS which is a sub-PDRS of the global PDRS gd,
        on the basis of two conversion lists: PDRSRef's rs and PVar's ps.

        Args:
            gd: An PDRS|LambdaPDRS|AMerge|PMerge instance.
            rs: A conversion list of PDRSRef|LambaPDRSRef tuples.
            ps: A conversion list of integer tuples. Type signature has default of None to be compatible
                wth DRS, however for PDRS it cannot be None.

        Returns:
            A PDRS instance.
        """
        if any([x is None for x in [gd, rs, ps]]):
            raise TypeError
        return PDRS(rename_var(self._label, ps),
                    rename_mapper(self._mapper, self, gd, ps),
                    rename_universe(self._refs, self, gd, ps, rs),
                    map(lambda x: x._convert(self, gd, rs, None, ps), self._conds))

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/LambdaCalculus.hs">/Data/PDRS/LambdaCalculus.hs:purifyPRefs</a>
    def purify_refs(self, gd, prs):
        def convert(pr):
            for prd,npr in prs:
                if pr == prd or (pr.ref == prd.ref
                        and (pr.has_projected_bound(self, prd, gd)
                                or (not pr.has_bound(self, gd) and gd.has_accessible_context(pr.plabel, prd.plabel)))):
                    return npr
            return pr

        # Must return tuple to be compatible with AbstractDRS spec.
        return PDRS(self._label, self._mapper, [convert(r) for r in self._refs],
                    [c._purify(gd=gd, rs=prs, pv=None, ps=None)[0] for c in self._conds]), None

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/LambdaCalculus.hs">/Data/PDRS/LambdaCalculus.hs:purifyPVars</a>
    def purify_pvars(self, gp, pvs):
        ol = intersect([self._label], pvs)
        d1 = self.alpha_convert(zip(ol, get_new_pvars(ol, union_inplace(gp.get_pvars(), pvs))), [])
        pvs1 = [d1.label]
        mapper = d1.mapper # shallow copy
        referents = d1.referents # shallow copy
        for x in mapper:
            pvs1.extend(x.to_list())
        pvs1 = union_inplace(pvs1, [r.plabel for r in referents])
        pvs2 = union_inplace(pvs, pvs1)
        c2 = []
        for c in d1.conditions:
            x, pvs2 = c._purify_pvars(gp, None, pvs2)
            c2.append(x)
        return PDRS(d1.label, mapper, referents, c2), pvs2

    # Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Translate.hs">/Data/PDRS/Translate.hs:movePContent</a>
    def _move_pcontent(self, lp, gp):
        """Moves projected content in this PDRS to its interpretation site in PDRS lp
        based on global PDRS gp.
        """

        # FIXME: Haskell code uses `not r.has_bound(lp, gp)`
        lp = lp._insert_prefs(filter(lambda r: r.has_bound(lp, gp), self._refs), gp)
        for c in self._conds:
            lp = c._move_pcontent(lp, gp)
        return lp

    # Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Translate.hs">/Data/PDRS/Translate.hsinsertPRefs.hs:</a>
    def _insert_prefs(self, prs, gp):
        ni = len(prs)
        if ni == 0:
            return self
        labels = gp.get_labels()
        maps = gp.get_maps()
        refs = []
        lp = self
        i = 0
        while i < ni:
            pr = prs[i]
            ant = [m[1] for m in filter(lambda x: x[0] == pr.plabel and x[1] in labels, maps)]
            if len(ant) != 0:
                prs[i] = PRef(ant[0], pr.ref) # no increment of i
            elif lp._label == pr.plabel or gp.test_free_pvar(pr.plabel):
                lp = PDRS(lp._label, lp._mapper, union_inplace(lp.referents, [pr]), lp._conds)
                i += 1
            else:
                lp = PDRS(lp._label, lp._mapper, lp._refs, [c._insert_prefs([pr], gp) for c in lp._conds])
                i += 1
        return lp

    # Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Translate.hs">/Data/PDRS/Translate.hs:insertPCon</a>
    def _insert_pcond(self, pc, gp):
        labels = gp.get_labels()
        ant = [m[1] for m in filter(lambda x: x[0] == pc.plabel and x[1] in labels, gp.get_maps())]
        if len(ant) != 0:
            return self._insert_pcond(PCond(ant[0], pc.condition), gp)
        elif self._label == pc.plabel or gp.test_free_pvar(pc.plabel):
            conds = [c for c in self._conds]
            conds.append(pc)
            return PDRS(self._label, self._mapper, self._refs, conds)
        return PDRS(self._label, self._mapper, self._refs, [c._insert_pcond(pc, gp) for c in self._conds])

    ## @remarks original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Translate.hs">/Data/PDRS/Translate.hs:stripPVars</a>
    def strip_pvars(self):
        """Strips projection variables from this PDRS resulting in a DRS."""
        conds = []
        for c in self._conds:
            conds.append(c._strip_pvars())
        refs = [x.to_drsref() for x in self._refs]
        return DRS(refs, conds)

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/LambdaCalculus.hs">/Data/PDRS/LambdaCalculus.hs:unboundDupPRefs</a>.
    def get_unbound_dup_prefs(self, gp, eps=None):
        """Returns a tuple of existing 'PRef's (eps) and unbound duplicate 'PRef's
        (dps) in a PDRS, based on a list of seen 'PRef's prs.

        Where pr = PRef(p, r) is duplicate in PDRS gp iff there exists a pd
        such that prd = PRef(pd,r) is an element prs, and pr and prd are independent.
        """
        if eps is None:
            eps = []
        uu = filter(lambda x: not x.has_other_bound(self, gp), self._refs)
        eps1 = [x for x in eps] # shallow copy
        eps1.extend(uu)
        dps1 = []
        eps3 = []
        for c in self._conds:
            eps1, d1, e3 = c._dups(self, gp, eps1, None)
            dps1.extend(d1)
            eps3.extend(e3)
        uu = filter(lambda x: _dup(x, eps, self, gp), uu)
        uu.extend(dps1)
        eps1.extend(eps3)
        return eps1, uu

    # Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Show.hs">/Data/DRS/Show.hs::showUniverse</a>
    def _show_universe(self, d, notation):
        return d.join([x.var.show(notation) for x in self._refs])

    def _show_conditions(self, notation):
        if len(self._conds) == 0 and notation == SHOW_BOX:
            return u' '
        if notation == SHOW_BOX:
            return u''.join([x.show(notation) for x in self._conds])
        return u','.join([x.show(notation) for x in self._conds])

    # Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Show.hs">/Data/PDRS/Show.hs::{showMAPs, showMAPsTuples}</a>
    def _show_mapper(self, notation):
        if notation == SHOW_BOX:
            # Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Show.hs">/Data/PDRS/Show.hs::showMAPs</a>
            def unique1(m, ms, sms):
                if abs(m[1]) < 0:
                    sms.append([MAP(abs(m[1]), abs(m[0]))])
                    return u'%i %s %i' % (abs(m[1]), self.modStrictSubord, m[0])
                elif m.swap() in ms or MAP(m[1],-m[0]) in ms:
                    sms.append(m)
                    return u''
                elif m.swap() in sms:
                    sms.append(m)
                    return u'%i %s %i' % (abs(m[0]), self.modEquals, m[1])
                sms.append(m)
                return u'%i %s %i' % (abs(m[0]), self.modWeakSubord, m[1])
            sms = []
            return u'  '.join(filter(lambda x: len(x) > 0, [unique1(self._mapper[i], self._mapper[i+1:], sms) \
                                                            for i in range(len(self._mapper))]))
        elif notation in [SHOW_LINEAR, SHOW_SET]:
            # Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Show.hs">/Data/PDRS/Show.hs::showMAPsTuples</a>
            def unique2(m, ms, sms):
                if m.swap() in ms:
                    sms.append(m)
                    return u''
                elif m.swap() in sms:
                    sms.append(m)
                    return u'%s' % m.to_tuple()
                sms.append(m)
                return u'%i %s %i' % (abs(m[0]), self.modWeakSubord, m[1])
            sms = []
            return u','.join(filter(lambda x: len(x) > 0, [unique2(self._mapper[i], self._mapper[i + 1:], sms) \
                                                            for i in range(len(self._mapper))]))
        else:
            return 'PRDS(%i,%s)' % (self._label, self._mapper)

    ## @remarks original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Merge.hs">/Data/PDRS/Merge.hs:pdrsResolveMerges</a>.
    def resolve_merges(self):
        """Resolves all unresolved merges in thos PDRS."""
        return PDRS(self._label, self._mapper, self._refs, [x.resolve_merges() for x in self._conds])

    ## @remarks Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/Show.hs">/Data/DRS/Show.hs::showDRSBox</a>
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
            ml = self._show_mapper(notation) + u'\n'
            hl = u'%i' % self._label
            l = 4 + max(union(union(union(map(len, ul.split(u'\n')), map(len, cl.split(u'\n'))), map(len, ml.split(u'\n'))), [len(hl)+2]))
            return self.show_title_line(l, hl, self.boxTopLeft, self.boxTopRight) + \
                   self.show_content(l, ul) + u'\n' + self.show_horz_line(l, self.boxMiddleLeft, self.boxMiddleRight) + \
                   self.show_content(l, cl) + u'\n' + self.show_horz_line(l, self.boxMiddleLeft, self.boxMiddleRight) + \
                   self.show_content(l, ml) + u'\n' + self.show_horz_line(l, self.boxBottomLeft, self.boxBottomRight)
        elif notation == SHOW_LINEAR:
            ul = self._show_universe(',', notation)
            cl = self._show_conditions(notation)
            ml = self._show_mapper(notation)
            return u'%i:[%s|%s|%s]' % (self._label, ul, cl, ml)
        elif notation == SHOW_SET:
            ul = self._show_universe(',', notation)
            cl = self._show_conditions(notation)
            ml = self._show_mapper(notation)
            return u'<%i,{%s},{%s},{%s}>' % (self._label, ul, cl, ml)
        cl = self._show_conditions(notation)
        return u'PDRS ' + str(self._refs).decode('utf-8') + u' [' + cl + u']'


class IPDRSCond:
    """Additional Interface for PDRS Conditions"""
    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/ProjectionGraph.hs#edges.
    def _edges(self, es, pv):
        return es

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Variables.hs#pdrsPVars:pvars
    def _pvars(self, u):
        return u

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/LambdaCalculus.hs#purifyPVars:purify
    def _purify_pvars(self, gp, pv, ps):
        raise NotImplementedError

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Structure.hs#pdrsLabels:labels
    def _labels(self, u):
        return u

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Structure.hs#pdrsMAPs:maps
    def _maps(self, u):
        return u

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Binding.hs#pdrsBoundPVar:bound
    def _bound(self, lp, pv):
        return False

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/LambdaCalculus.hs#unboundDupPRefs:dups
    def _dups(self, lp, gp, eps, pv):
        return eps, [], []

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Properties.hs#isPlainPDRS:plain
    def _plain(self):
        return False

    def _showmod(self):
        return 0

    def _strip_pvars(self):
        raise NotImplementedError

    # Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/movePContent.hs">/Data/PDRS/movePContent.hs:move</a>
    def _move_pcontent(self, lp, gp):
        raise NotImplementedError

    # Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/insertPRefs.hs">/Data/PDRS/insertPRefs.hs:insert</a>
    def _insert_prefs(self, pr, gp):
        raise NotImplementedError

    # Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/insertPCon.hs">/Data/PDRS/insertPCon.hs:insert</a>
    def _insert_pcond(self, pc, gp):
        raise NotImplementedError

    # Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Binding.hs">/Data/PDRS/Binding.hs:pdrsFreePVars:free</a>.
    def _get_free_pvars(self, gd, u):
        raise NotImplementedError

    @property
    def condition(self):
        return self


class PCond(AbstractDRSCond, IPDRSCond):
    """A projected condition, consisting of a PVar and a AbstractDRSCond."""
    def __init__(self, label, cond):
        if not isinstance(label, PVar) or not isinstance(cond, AbstractDRSCond):
            raise TypeError
        self._plabel = label
        self._cond = cond

    def __ne__(self, other):
        return type(self) != type(other) or self._plabel != other._plabel or self._cond != other._cond

    def __eq__(self, other):
        return type(self) == type(other) and self._plabel == other._plabel and self._cond == other._cond

    def __repr__(self):
        return 'PCond(%i,%s)' % (self._plabel, repr(self._cond))

    def _isproper_subdrsof(self, sd, gd, pv=None):
        # Pass down to member condition
        assert pv is None
        return self._cond._isproper_subdrsof(sd, gd, self._plabel)

    def _universes(self, u):
        # Pass down to member condition
        return self._cond._universes(u)

    def _variables(self, u):
        # Pass down to member condition
        return self._cond._universes(u)

    # Helper for DRS.get_lambda_tuples()
    def _lambda_tuple(self, u):
        # Pass down to member condition
        return self._cond._lambda_tuple(u)

    # Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Binding.hs">/Data/PDRS/Binding.hs:pdrsFreePRefs:free</a>.
    def _get_freerefs(self, ld, gd, pv=None):
        # Pass down to member condition
        assert pv is None
        return self._cond._get_freerefs(ld, gd, self._plabel)

    # Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Binding.hs">/Data/PDRS/Binding.hs:pdrsFreePVars:free</a>.
    def _get_free_pvars(self, gd, u):
        # Pass down to member condition
        return self._cond._get_free_pvars(gd, u)

    # Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/ProjectionGraph.hs">/Data/PDRS/ProjectionGraph.hs:edges</a>.
    def _edges(self, es, pv):
        return union_inplace(self._cond._edges(es, self._plabel), [(pv, self._plabel)])

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Variables.hs#pdrsPVars:pvars
    def _pvars(self, u):
        u.add(self.plabel)
        return self._cond._pvars(u)

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/LambdaCalculus.hs#renamePCons:rename
    def _convert(self, ld, gd, rs, pv=None, ps=None):
        # Pass down to member condition
        assert pv is None
        return PCond(rename_pvar(self._plabel, ld, gd, ps), self._cond._convert(ld, gd, rs, self._plabel, ps))

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/LambdaCalculus.hs#purifyPRefs:purify
    def _purify(self, gd, rs, pv=None, ps=None):
        assert pv is None
        cond, _ = self._cond._purify(gd, rs, self._plabel, ps)
        # Must return tuple to be compatible with AbstractDRS spec
        return PCond(self._plabel, cond), None

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/LambdaCalculus.hs#purifyPVars:purify
    def _purify_pvars(self, gp, pv, ps):
        cond, ps = self._cond._purify_pvars(gp, self._plabel, ps)
        return PCond(self._plabel, cond), ps

    def _labels(self, u):
        return self._cond._labels(u)

    def _maps(self, u):
        return self._cond._maps(u)

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Binding.hs#pdrsBoundPVar:bound
    def _bound(self, lp, pv):
        return self._cond._bound(lp, pv)

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/LambdaCalculus.hs#unboundDupPRefs:dups
    def _dups(self, lp, gp, eps, pv):
        assert pv is None
        return self._cond._dups(lp, gp, eps, self._plabel)

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Properties.hs#isPlainPDRS:plain
    def _plain(self):
        return self._cond._plain()

    # Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Translate.hs">/Data/PDRS/Translate.hs:movePContent:move</a>
    def _move_pcontent(self, lp, gp):
        return lp._insert_pcond(PCond(self._plabel, self._cond._move_pcontent(lp, gp)), gp)

    # Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/insertPRefs.hs">/Data/PDRS/insertPRefs.hs:insert</a>
    def _insert_prefs(self, pr, gp):
        return PCond(self._plabel, self._cond._insert_prefs(pr, gp))

    # Original haskell code in <a href="https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/insertPCon.hs">/Data/PDRS/insertPCon.hs:insert</a>
    def _insert_pcond(self, pc, gp):
        return PCond(self._plabel, self._cond._insert_pcond(pc, gp))

    def _strip_pvars(self):
        return self._cond._strip_pvars()

    @property
    def plabel(self):
        return self._plabel

    @property
    def condition(self):
        return self._cond

    @property
    def isresolved(self):
        return self._cond.isresolved

    def resolve_merges(self):
        # Pass down to member condition
        return PCond(self._plabel, self._cond.resolve_merges())

    def _antecedent(self, ref, drs):
        raise NotImplementedError

    def _ispure(self, ld, gd, rs):
        raise NotImplementedError

    def to_mfol(self, world):
        raise NotImplementedError

    def show(self, notation):
        if notation == SHOW_BOX:
            mod = self._cond._showmod()
            s = self._cond.show(notation)
            if mod > 0:
                return self.show_modifier(u'%i %s' % (self._plabel, self.modPointer), mod, s)
            return u'%i %s %s' % (self._plabel, self.modPointer, s)
        elif notation in [SHOW_LINEAR, SHOW_SET]:
            return u'(%i,%s)' % (self._plabel, self._cond.show(notation))
        return u'PCond(%i,%s)' % (self._plabel, self._cond.show(notation))


class PRel(Rel, IPDRSCond):
    """A relation defined on a set of referents"""
    def __init__(self, drsRel, drsRefs):
        super(PRel, self).__init__(drsRel, drsRefs)

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Bindings.hs#pdrsFreePRefs:free
    def _get_freerefs(self, ld, gd, pv=None):
        return filter(lambda x: not PRef(pv, x).has_bound(ld, gd), self._refs)

    def _get_free_pvars(self, gd, u):
        return u

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Properties.hs#isProperPDRS:isProperSubPDRS
    def _isproper_subdrsof(self, sd, gd, pv=None):
        return all([PRef(pv, x).has_bound(sd, gd) for x in self._refs])

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/LambdaCalculus.hs#renamePCons:rename
    def _convert(self, ld, gd, rs, pv=None, ps=None):
        refs = [rename_pdrsref(pv, r, ld, gd, rs) for r in self._refs]
        return PRel(self._rel, refs)

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/LambdaCalculus.hs#purifyPRefs:purify
    def _purify(self, gd, prs, pv=None, ps=None):
        def convert(pr):
            for prd,npr in prs:
                if pr == prd or (pr.ref == prd.ref
                        and (pr.has_projected_bound(self, prd, gd)
                                or (not pr.has_bound(self, gd) and gd.has_accessible_context(pr.plabel, prd.plabel)))):
                    return npr
            return pr
       # Must return tuple to be compatible with AbstractDRS spec
        return PRel(self._rel, [convert(PRef(pv,r)).ref for r in self._refs]), None

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/LambdaCalculus.hs#purifyPVars:purify
    def _purify_pvars(self, gp, pv, ps):
        # TODO: check if ordering is important, haskell adds to front of list
        ps.append(pv)
        return self, ps

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/LambdaCalculus.hs#unboundDupPRefs:dups
    def _dups(self, lp, gp, eps, pv):
        # upd  = filter (\pr -> not (pdrsPBoundPRef pr lp gp)) (map (PRef p) d)
        upd = filter(lambda x: not x.has_other_bound(lp, gp), [PRef(pv, x) for x in self._refs])
        dps1 = filter(lambda x: _dup(x, eps, lp, gp), upd)
        eps.extend(upd) #eps2
        return eps, dps1, []

    def _plain(self):
        return True

    def _showmod(self):
        return -1

    def _move_pcontent(self, lp, gp):
        return self

    def _insert_prefs(self, pr, gp):
        return self

    def _insert_pcond(self, pc, gp):
        return self

    def _strip_pvars(self):
        return Rel(self._rel, [x.to_drsref() for x in self._refs])

    def _antecedent(self, ref, drs):
        raise NotImplementedError

    def _ispure(self, ld, gd, rs):
        raise NotImplementedError

    def to_mfol(self, world):
        raise NotImplementedError


class PNeg(Neg, IPDRSCond):
    """A negated DRS"""
    def __init__(self, drs):
        super(PNeg, self).__init__(drs)

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/ProjectionGraph.hs#edges.
    def _edges(self, es, pv):
        if self._drs._no_edges(): return es
        es = union_inplace(es, [(self._drs.label, pv)])
        return self._drs._edges(es)

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/LambdaCalculus.hs#purifyPVars:purify
    def _purify_pvars(self, gp, pv, ps):
        # TODO: check if ordering is important, haskell adds to pv front of ps list
        cp1, ps1 = self._drs.purify_pvars(gp, union_inplace(ps,[pv]))
        return PNeg(cp1), ps1

    def _labels(self, u):
        return self._drs.get_labels(u)

    def _maps(self, u):
        return self._drs.get_maps(u)

    def _bound(self, lp, pv):
        return self._drs.has_subdrs(lp) and self._drs.test_bound_pvar(pv, lp)

    def _dups(self, lp, gp, eps, pv):
        eps1, dps1 = self._drs.get_unbound_dup_prefs(gp, eps)
        return eps1, dps1, []

    def _plain(self):
        return self._drs.isplain

    def _showmod(self):
        return 0 if self._drs.islambda else 2

    def _strip_pvars(self):
        return Neg(self._drs.strip_pvars())

    def _move_pcontent(self, lp, gp):
        return PNeg(self._drs.get_empty())

    def _insert_prefs(self, pr, gp):
        return PNeg(self._drs.insert_prefs(pr, gp))

    def _insert_pcond(self, pc, gp):
        return PNeg(self._drs.insert_pconds(pc, gp))

    def _get_free_pvars(self, gp, u):
        return self._drs.get_free_pvars(gp, u)

    def _antecedent(self, ref, drs):
        raise NotImplementedError

    def _ispure(self, ld, gd, rs):
        raise NotImplementedError

    def to_mfol(self, world):
        raise NotImplementedError


class PImp(Imp, IPDRSCond):
    """An implication between two DRSs"""
    def __init__(self, drsA, drsB):
        super(PImp, self).__init__(drsA, drsB)

    def _purify(self, gd, rs, pv=None, ps=None):
        cd1, _ = self._drsA.purify_refs(gd, rs, ps)
        cd2, _ = self._drsB.purify_refs(gd, rs, ps)
        return PImp(cd1, cd2), None

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/ProjectionGraph.hs#edges.
    def _edges(self, es, pv):
        if self._drsA._no_edges() and self._drsB._no_edges():
            return es
        elif self._drsB._no_edges(): # True == not self._drsA._no_edges()
            es = union_inplace(es, [(self._drsA.label, pv)])
            return self._drsA._edges(es)
        elif self._drsB._no_edges(): # True == not self._drsB._no_edges()
            es = union_inplace(es, [(self._drsB.label, pv)])
            return self._drsB._edges(es)
        es = union_inplace(es, [(self._drsA.label, pv)])
        es = self._drsA._edges(es)
        es = union_inplace(es, [(self._drsB.label, pv)])
        return self._drsB._edges(es)

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/LambdaCalculus.hs#purifyPVars:purify
    def _purify_pvars(self, gp, pv, ps):
        # TODO: check if ordering is important, haskell adds to pv front of ps list
        ops = intersect(union_inplace(ps, [pv]), [self._drsA.label])
        nps = zip(ops, get_new_pvars(ops, union_inplace(gp.get_pvars(), ps)))
        cp1, ps1 = self._drsA.rename_subdrs(gp, [], nps).purify_pvars(gp, union_inplace(ps, [pv]))
        cp2, ps2 = self._drsB.rename_subdrs(gp, [], nps).purify_pvars(gp, ps1)
        return PImp(cp1, cp2), ps2

    def _labels(self, u):
        u = self._drsA.get_labels(u)
        return self._drsB.get_labels(u)

    def _maps(self, u):
        u = self._drsA.get_maps(u)
        return self._drsB.get_maps(u)

    def _bound(self, lp, pv):
        return (pv == self._drsA.label and self._drsB.has_subdrs(lp)) \
                or (self._drsA.has_subdrs(lp) and self._drsA.test_bound_pvar(pv, lp)) \
                or (self._drsB.has_subdrs(lp) and self._drsB.test_bound_pvar(pv, lp))

    def _dups(self, lp, gp, eps, pv):
        eps1, dps1 = self._drsA.get_unbound_dup_prefs(gp, eps)
        eps2, dps2 = self._drsB.get_unbound_dup_prefs(gp, eps1)
        dps1.extend(dps2)
        return eps2, dps1, []

    def _plain(self):
        return self._drsA.isplain and self._drsB.isplain

    def _showmod(self):
        return 0 if self._drsA.islambda and self._drsB.islambda else 2

    def _move_pcontent(self, lp, gp):
        return PImp(self._drsA.get_empty(), self._drsB.get_empty())

    def _insert_prefs(self, pr, gp):
        return PImp(self._drsA.insert_prefs(pr, gp), self._drsB.insert_prefs(pr, gp))

    def _insert_pcond(self, pc, gp):
        return PImp(self._drsA.insert_pconds(pc, gp), self._drsB.insert_pconds(pc, gp))

    def _strip_pvars(self):
        return Imp(self._drsA.strip_pvars(), self._drsB.strip_pvars())

    def _get_free_pvars(self, gp, u):
        u = self._drsA.get_free_pvars(gp, u)
        return self._drsB.get_free_pvars(gp, u)

    def _antecedent(self, ref, drs):
        raise NotImplementedError

    def _ispure(self, ld, gd, rs):
        raise NotImplementedError

    def to_mfol(self, world):
        raise NotImplementedError


class POr(Or, IPDRSCond):
    """A disjunction between two DRSs"""
    def __init__(self, drsA, drsB):
        super(POr, self).__init__(drsA, drsB)

    def _purify(self, gd, rs, pv=None, ps=None):
        cd1, _ = self._drsA.purify_refs(gd, rs, ps)
        cd2, _ = self._drsB.purify_refs(gd, rs, ps)
        return POr(cd1, cd2), None

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/ProjectionGraph.hs#edges.
    def _edges(self, es, pv):
        if self._drsA._no_edges() and self._drsB._no_edges():
            return es
        elif self._drsB._no_edges(): # True == not self._drsA._no_edges()
            es = union_inplace(es, [(self._drsA.label, pv)])
            return self._drsA._edges(es)
        elif self._drsB._no_edges(): # True == not self._drsB._no_edges()
            es = union_inplace(es, [(self._drsB.label, pv)])
            return self._drsB._edges(es)
        es = union_inplace(es, [(self._drsA.label, pv)])
        es = self._drsA._edges(es)
        es = union_inplace(es, [(self._drsB.label, pv)])
        return self._drsB._edges(es)

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/LambdaCalculus.hs#purifyPVars:purify
    def _purify_pvars(self, gp, pv, ps):
        ops = intersect(union_inplace(ps, [pv]), [self._drsA.label])
        nps = zip(ops, get_new_pvars(ops, union_inplace(gp.get_pvars(), ps)))
        cp1, ps1 = self._drsA.rename_subdrs(gp, [], nps).purify_pvars(gp, union_inplace(ps, [pv]))
        cp2, ps2 = self._drsB.rename_subdrs(gp, [], nps).purify_pvars(gp, ps1)
        return POr(cp1, cp2), ps2

    def _labels(self, u):
        u = self._drsA.get_labels(u)
        return self._drsB.get_labels(u)

    def _maps(self, u):
        u = self._drsA.get_maps(u)
        return self._drsB.get_maps(u)

    def _bound(self, lp, pv):
        return (self._drsA.has_subdrs(lp) and self._drsA.test_bound_pvar(pv, lp)) \
               or (self._drsB.has_subdrs(lp) and self._drsB.test_bound_pvar(pv, lp))

    def _dups(self, lp, gp, eps, pv):
        eps1, dps1 = self._drsA.get_unbound_dup_prefs(gp, eps)
        eps2, dps2 = self._drsB.get_unbound_dup_prefs(gp, eps1)
        dps1.extend(dps2)
        return eps2, dps1, []

    def _plain(self):
        return self._drsA.isplain and self._drsB.isplain

    def _showmod(self):
        return 0 if self._drsA.islambda and self._drsB.islambda else 2

    def _move_pcontent(self, lp, gp):
        return POr(self._drsA.get_empty(), self._drsB.get_empty())

    def _insert_prefs(self, pr, gp):
        return POr(self._drsA.insert_prefs(pr, gp), self._drsB.insert_prefs(pr, gp))

    def _insert_pcond(self, pc, gp):
        return POr(self._drsA.insert_pconds(pc, gp), self._drsB.insert_pconds(pc, gp))

    def _strip_pvars(self):
        return Or(self._drsA.strip_pvars(), self._drsB.strip_pvars())

    def _get_free_pvars(self, gp, u):
        u = self._drsA.get_free_pvars(gp, u)
        return self._drsB.get_free_pvars(gp, u)

    def _antecedent(self, ref, drs):
        raise NotImplementedError

    def _ispure(self, ld, gd, rs):
        raise NotImplementedError

    def to_mfol(self, world):
        raise NotImplementedError


class PProp(Prop, IPDRSCond):
    """A proposition DRS"""
    def __init__(self, drsRef, drs):
        super(PProp, self).__init__(drsRef, drs)

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/Binding.hs#pdrsFreePRefs:free.
    def _get_freerefs(self, ld, gd, pvar=None):
        return union(filter(lambda x: not x.has_bound(x, ld, gd), [PRef(pvar, self._ref)]), self._drs.get_freerefs(gd))

    def _isproper_subdrsof(self, sd, gd, pvar=None):
        return PRef(pvar, self._ref).has_bound(sd, gd) and self._drs._isproper_subdrsof(gd)

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/DRS/LambdaCalculus.hs#renameCons:convertCon
    def _convert(self, ld, gd, rs, pv=None, ps=None):
        return Prop(rename_pdrsref(pv, self._ref, ld, gd, rs), self._drs.rename_subdrs(gd, rs, ps))

    def _purify(self, gd, prs, pv=None, ps=None):
        def convert(pr):
            for prd,npr in prs:
                if pr == prd or (pr.ref == prd.ref
                        and (pr.has_projected_bound(self, prd, gd)
                                or (not pr.has_bound(self, gd) and gd.has_accessible_context(pr.plabel, prd.plabel)))):
                    return npr
            return pr
        # Must return tuple to be compatible with AbstractDRS spec
        return PProp(convert(PRef(pv, self._ref)).ref, self._drs.purify_refs(gd, prs, ps)), None

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/ProjectionGraph.hs#edges.
    def _edges(self, es, pv):
        if self._drs._no_edges(): return es
        es = union_inplace(es, [(self._drs.label, pv)])
        return self._drs._edges(es)

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/LambdaCalculus.hs#purifyPVars:purify
    def _purify_pvars(self, gp, pv, ps):
        cp1, ps1 = self._drs.purify_pvars(gp, union_inplace(ps,[pv]))
        return PProp(self._ref, cp1), ps1

    def _labels(self, u):
        return self._drs.get_labels(u)

    def _maps(self, u):
        return self._drs.get_maps(u)

    def _bound(self, lp, pv):
        return self._drs.has_subdrs(lp) and self._drs.test_bound_pvar(pv, lp)

    def _dups(self, lp, gp, eps, pv):
        eps1, dps1 = self._drs.get_unbound_dup_prefs(gp, eps)
        pr = [] if PRef(pv, self._ref).has_other_bound(lp, gp) else [PRef(pv, self._ref)]
        dps3 = filter(_dup(eps, lp, gp), pr)
        dps1.extend(dps3)
        return eps1, dps1, pr

    def _plain(self):
        return self._drs.isplain

    def _showmod(self):
        return 0 if self._drs.islambda else 2

    def _move_pcontent(self, lp, gp):
        return PProp(self._ref, self._drs.get_empty())

    def _insert_prefs(self, pr, gp):
        return PProp(self._rel, self._drs.insert_prefs(pr, gp))

    def _insert_pcond(self, pc, gp):
        return PProp(self._rel, self._drs.insert_pconds(pc, gp))

    def _strip_pvars(self):
        return Prop(self._ref.to_drsref(), self._drs.strip_pvars())

    def _get_free_pvars(self, gp, u):
        return self._drs.get_free_pvars(gp, u)

    def _antecedent(self, ref, drs):
        raise NotImplementedError

    def _ispure(self, ld, gd, rs):
        raise NotImplementedError

    def to_mfol(self, world):
        raise NotImplementedError


class PDiamond(Diamond, IPDRSCond):
    """A possible DRS"""
    def __init__(self, drs):
        super(PNeg, self).__init__(drs)

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/ProjectionGraph.hs#edges.
    def _edges(self, es, pv):
        if self._drs._no_edges(): return es
        es = union_inplace(es, [(self._drs.label, pv)])
        return self._drs._edges(es)

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/LambdaCalculus.hs#purifyPVars:purify
    def _purify_pvars(self, gp, pv, ps):
        cp1, ps1 = self._drs.purify_pvars(gp, union_inplace(ps,[pv]))
        return PDiamond(cp1), ps1

    def _labels(self, u):
        return self._drs.get_labels(u)

    def _maps(self, u):
        return self._drs.get_maps(u)

    def _bound(self, lp, pv):
        return self._drs.has_subdrs(lp) and self._drs.test_bound_pvar(pv, lp)

    def _dups(self, lp, gp, eps, pv):
        eps1, dps1 = self._drs.get_unbound_dup_prefs(gp, eps)
        return eps1, dps1, []

    def _plain(self):
        return self._drs.isplain

    def _showmod(self):
        return 0 if self._drs.islambda else 2

    def _move_pcontent(self, lp, gp):
        return PDiamond(self._drs.get_empty())

    def _insert_prefs(self, pr, gp):
        return PDiamond(self._drs.insert_prefs(pr, gp))

    def _insert_pcond(self, pc, gp):
        return PDiamond(self._drs.insert_pconds(pc, gp))

    def _strip_pvars(self):
        return Diamond(self._drs.strip_pvars())

    def _get_free_pvars(self, gp, u):
        return self._drs.get_free_pvars(gp, u)

    def _antecedent(self, ref, drs):
        raise NotImplementedError

    def _ispure(self, ld, gd, rs):
        raise NotImplementedError

    def to_mfol(self, world):
        raise NotImplementedError


class PBox(Box, IPDRSCond):
    """A necessary DRS"""
    def __init__(self, drs):
        super(PNeg, self).__init__(drs)

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/ProjectionGraph.hs#edges.
    def _edges(self, es, pv):
        if self._drs._no_edges(): return es
        es = union_inplace(es, [(self._drs.label, pv)])
        return self._drs._edges(es)

    # Original haskell code in https://github.com/hbrouwer/pdrt-sandbox/tree/master/src/Data/PDRS/LambdaCalculus.hs#purifyPVars:purify
    def _purify_pvars(self, gp, pv, ps):
        cp1, ps1 = self._drs.purify_pvars(gp, union_inplace(ps,[pv]))
        return PBox(cp1), ps1

    def _labels(self, u):
        return self._drs.get_labels(u)

    def _maps(self, u):
        return self._drs.get_maps(u)

    def _bound(self, lp, pv):
        return self._drs.has_subdrs(lp) and self._drs.test_bound_pvar(pv, lp)

    def _dups(self, lp, gp, eps, pv):
        eps1, dps1 = self._drs.get_unbound_dup_prefs(gp, eps)
        return eps1, dps1, []

    def _plain(self):
        return self._drs.isplain

    def _showmod(self):
        return 0 if self._drs.islambda else 2

    def _move_pcontent(self, lp, gp):
        return PBox(self._drs.get_empty())

    def _insert_prefs(self, pr, gp):
        return PBox(self._drs.insert_prefs(pr, gp))

    def _insert_pcond(self, pc, gp):
        return PBox(self._drs.insert_pconds(pc, gp))

    def _strip_pvars(self):
        return Box(self._drs.strip_pvars())

    def _get_free_pvars(self, gp, u):
        return self._drs.get_free_pvars(gp, u)

    def _antecedent(self, ref, drs):
        raise NotImplementedError

    def _ispure(self, ld, gd, rs):
        raise NotImplementedError

    def to_mfol(self, world):
        raise NotImplementedError




