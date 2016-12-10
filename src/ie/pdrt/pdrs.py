from utils import iterable_type_check, union, union_inplace, intersect, rename_var
from common import SHOW_BOX, SHOW_LINEAR, SHOW_SET, SHOW_DEBUG
from common import DRSVar, LambdaDRSVar, Showable
from drs import AbstractDRSRef, DRSRef, LambdaDRSRef, AbstractDRSCond, AbstractDRS, LambdaTuple
from drs import Rel, Neg, Imp, Or, Diamond, Box, Prop
# Note: get_new_drsrefs() works on any AbstractPDRSRef.
from drs import get_new_drsrefs
import networkx as nx


PVar = int


## @remarks Original haskell code in `/pdrt-sandbox/src/Data/PDRS/Variables.hs:newPVars`
def get_new_pvars(opvs, epvs):
    """Returns a list of new projection variables for a list of old
    PVar's opvs, based on a list of existing PVar's epvs.
    """
    if len(epvs) == 0: return opvs
    n = max(epvs) + 1
    return [x+n for x in range(len(opvs))]


## @remarks Original haskell code in `/pdrt-sandbox/src/Data/PDRS/LambdaCalculus.hs:renamePVar`
def rename_pvar(pv, lp, gp, ps):
    """Converts a PVar into a new PVar in case it occurs bound in
    local PDRS lp in global PDRS gp.
    """
    if not gp.test_bound_pvar(abs(pv), lp):
        return pv
    if pv < 0:
        return rename_var(abs(pv), ps)
    return rename_var(pv, ps)


## @remarks Original haskell code in `/pdrt-sandbox/src/Data/PDRS/LambdaCalculus.hs:renamePDRSRef`
def rename_pdrsref(pv, r, lp, gp, rs):
    """Applies alpha conversion to a projected referent PRef(pv,r), in
    local PDRS lp which is in global PDRS gp, on the basis of two conversion lists
    for projection variables ps and PDRS referents rs
    """
    u = gp.get_universes()
    prtest = PRef(pv, r)
    if any([prtest.has_projected_bound(lp, pr, gp) and gp.test_free_pvar(pr.label) for pr in u]) or \
            not prtest.has_bound(lp, gp):
        return r
    return rename_var(r, rs)


## @remarks Original haskell code in `/pdrt-sandbox/src/Data/PDRS/LambdaCalculus.hs:renameMAPs`
def rename_mapper(m, lp, gp, ps):
    """Applies alpha conversion to a list of MAP's m, on the basis of a
    conversion list for projection variables ps.
    """
    return filter(lambda x: (rename_pvar(x[0], lp, gp, ps), rename_pvar(x[1], lp, gp, ps)), m)


## @remarks Original haskell code in `/pdrt-sandbox/src/Data/PDRS/LambdaCalculus.hs:renameUniverse`
def rename_universe(u, lp, gp, ps, rs):
    """Applies alpha conversion to a list of PRef's u, on the basis of
    a conversion list for PVar's ps and PDRSRef's rs.
    """
    return filter(lambda r: PRef(rename_pvar(r.label, lp, gp, ps), rename_pdrsref(r.label, r.ref, lp, gp, rs)), u)


class PDRSRef(DRSRef):
    """A PDRS referent"""
    def __init__(self, drsVar):
        super(PDRSRef,self).__init__(drsVar)

    def __repr__(self):
        return 'PDRSRef(%s,%i)' % (self._var, self._pos)

    def _has_antecedent(self, drs, conds):
        return False

    def has_bound(self, drsLD, drsGD):
        """Disabled for PDRS. Always returns False."""
        return False

    def increase_new(self):
        r = super(PDRSRef, self).increase_new()
        return PDRSRef(r._var)

    ## @remarks Original haskell code in `/pdrt-sandbox/src/Data/PDRS/Variables.hs:pdrsRefToDRSRef`
    def to_drsref(self):
        """Converts a PDRSRef into a DRSRef"""
        return DRSRef(self._var)


class LambdaPDRSRef(LambdaDRSRef):
    """A lambda PDRS referent"""
    def __init__(self, lambdaVar, pos):
        super(LambdaPDRSRef,self).__init__(lambdaVar, pos)

    def __repr__(self):
        return 'LambdaPDRSVar(%s,%s)' % (self._var.to_string(), self._set)

    def _has_antecedent(self, drs, conds):
        return False

    def has_bound(self, drsLD, drsGD):
        """Disabled for PDRS. Always returns False."""
        return False

    def increase_new(self):
        r = super(LambdaPDRSRef, self).increase_new()
        return LambdaPDRSRef(r._var, r._pos)

    ## @remarks Original haskell code in `/pdrt-sandbox/src/Data/PDRS/Variables.hs:pdrsRefToDRSRef`
    def to_drsref(self):
        """Converts a PDRSRef into a DRSRef"""
        return LambdaDRSRef(self._var, self._pos)


class PRef(AbstractDRSRef):
    """A projected referent, consisting of a PVar and a AbstractPDRSRef"""
    def __init__(self, label, drsRef):
        if not isinstance(label, PVar) or not isinstance(drsRef, [PDRSRef, LambdaPDRSRef]):
            raise TypeError
        self._label = label
        self._ref = drsRef

    def __ne__(self, other):
        return self.__class__ != other.__class__ or self._label != other._label or self._ref != other._ref

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self._label == other._label and self._ref == other._ref

    def _has_antecedent(self, drs, conds):
        # Not required for PRef's
        return False

    ## @remarks Original haskell code in `/pdrt-sandbox/src/Data/PDRS/Binding.hs:pdrsBoundPRef`
    def has_bound(self, drsLP, drsGP):
        """Test whether this PRef in context drsLP is bound in the PDRS drsGP."""

        # Where this PRef is bound iff there exists a context pv, such that:
        #  - pv is accessible from the introduction site of @pr@ drsLP; and
        #  - pv is accessible from the interpretation site of @pr@ (@this@); and
        # - together with the PDRSRef of @pr@ (@r@), @pv@ forms a 'PRef'
        #   that is introduced in some universe in drsGP.
        if not isinstance(drsLP, AbstractPDRS) or not isinstance(drsLP, AbstractPDRS):
            raise TypeError
        pg = drsGP.get_pgraph()
        vs = pg.nodes()
        if drsLP.label in vs and self._label in vs:
            u = drsGP.get_universes()
            for pv in vs:
                if pv in nx.dfs_postorder_nodes(pg, source=drsLP.label) and \
                    pv in nx.dfs_postorder_nodes(pg, source=self.label):
                    if PRef(pv,self._ref) in u: return True
        return False

    ## @remarks Original haskell code in `/pdrt-sandbox/src/Data/PDRS/Binding.hs:pdrsPRefBoundByPRef`
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
               pdrs2.has_accessible_context(self.label, pr2.label) and \
               pdrs2.has_accessible_context(pdrs1.label, pr2.label)

    ## @remarks Original haskell code in `/pdrt-sandbox/src/Data/PDRS/Binding.hs:pdrsPBoundPRef`
    def has_other_bound(self, drsLP, drsGP):
        """Test whether a referent is bound by some other referent than itself."""
        u = drsGP.get_universes()
        u.remove(self)
        return any([self.has_projected_bound(drsLP, x, drsGP) for x in u])

    ## @remarks Original haskell code in `/pdrt-sandbox/src/Data/PDRS/LambdaCalculus.hs:independentPRefs`
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
        raise NotImplementedError

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
    def label(self):
        return self._label

    def increase_new(self):
        return PRef(self._label, self._ref.increase_new())

    def to_drsref(self):
        return DRSRef(self._ref)


class AbstractPDRS(AbstractDRS):
    """Discourse Representation Structure"""

    ## @remarks Original haskell code in `/pdrt-sandbox/src/Data/PDRS/ProjectionGraph.hs:edges`.
    def _edges(self, es):
        #  Derives a list of networkx.Graph edges from a PDRS
        return es

    # Original haskell code in `/pdrt-sandbox/src/Data/PDRS/ProjectionGraph.hs:edges`.
    def _no_edges(self):
        return True

    ## @remarks Original haskell code in `/pdrt-sandbox/src/Data/PDRS/Structure.hs:pdrsLabel
    @property
    def label(self):
        """Get the projection label"""
        return 0

    ## @remarks original haskell code in `/pdrt-sandbox/src/Data/DRS/Properties.hs:isPurePDRS`.
    @property
    def ispure(self):
        """Test whether this DRS is pure, where:
        A DRS is pure iff it does not contain any otiose declarations of discourse referents
        (i.e. it does not contain any unbound, duplicate uses of referents).

        Returns:
            True if this DRS is pure.
        """
        return self == self.purify()

    ## @remarks original haskell code in `/pdrt-sandbox/src/Data/PDRS/LambdaCalculus.hs:pdrsPurify`
    def purify(self):
        """Converts a PDRS into a pure PDRS by purifying its PRef's,

        where a PDRS is pure iff there are no occurrences of duplicate, unbound uses
        of the same PRef.
        """
        raise NotImplementedError

    ## @remarks Original haskell code in `/pdrt-sandbox/src/Data/PDRS/Structure.hs:emptyPDRS`.
    def get_empty(self):
        """Returns an empty PDRS, if possible with the same label as this one."""
        raise NotImplementedError

    ## @remarks Original haskell code in `/pdrt-sandbox/src/Data/PDRS/Structure.hs:pdrsLabels`
    def get_labels(self, u=None):
        """Returns all the labels in a PDRS."""
        return u

    ## @remarks Original haskell code in `/pdrt-sandbox/src/Data/PDRS/Variables.hs:pdrsPVars`
    def get_pvars(self, u=None):
        """Returns the list of all 'PVar's in an AbstractPDRS"""
        return u

    ## @remarks original haskell code in `/pdrt-sandbox/src/Data/PDRS/Binding.hs:pdrsFreePVars`.
    def get_free_pvars(self, gp, u=None):
        """Returns the list of all free PVar's in this PRDS, which is a sub PDRS of global PDRS gp."""
        return []

    ## @remarks Original haskell code in `/pdrt-sandbox/src/Data/PDRS/Structure.hs:pdrsMAPs`
    def get_maps(self, u=None):
        return u

    ## @remarks Original haskell code in `/pdrt-sandbox/src/Data/PDRS/ProjectionGraph.hs:projectionGraph`.
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

    ## @remarks Original haskell code in `/pdrt-sandbox/src/Data/PDRS/LambdaCalculus.hs:unboundDupPRefs`.
    def get_unbound_dup_prefs(self, gp, eps):
        """Returns a tuple of existing 'PRef's @eps@ and unbound duplicate 'PRef's
        @dps@ in a 'PDRS', based on a list of seen 'PRef's @prs@, where:

        [@pr = ('PRef' p r)@ is duplicate in 'PDRS' @gp@ /iff/]

        * There exists a @p'@, such that @pr' = ('PRef' p' r)@ is an element
        of @prs@, and @pr@ and @pr'@ are /independent/.
        """
        raise NotImplementedError

    ## @remarks Original haskell code in `/pdrt-sandbox/src/Data/PDRS/ProjectionGraph.hs:pdrsIsAccessibleContext`.
    def has_accessible_context(self, p1, p2):
        """Test whether PDRS context p2 is accessible from PDRS context p1 in this PDRS"""
        pg = self.get_graph()
        vs = pg.nodes()
        return p1 in vs and p2 in vs and pg.dfs_postorder_nodes(pg, source=p1)

    ## @remarks Original haskell code in `/pdrt-sandbox/src/Data/PDRS/Binding.hs:pdrsIsFreePVar`.
    def test_free_pvar(self, pv):
        """Test whether pv is a free projection variable in this PDRS,
        where: pv is free iff:
            - context pv is accessible from the global context, or
            - there is no context v that is accessible from pv and also from the global context.
        """
        if pv == self.label: return False
        pg = self.get_graph()
        vs = pg.nodes()
        if pv not in vs: return True
        this_scope = pg.dfs_postorder_nodes(pg, source=self.label)
        return pv in this_scope or not any([(x in pg.dfs_postorder_nodes(pg, source=pv) and x in this_scope) for x in vs])

    ## @remarks Original haskell code in `/pdrt-sandbox/src/Data/PDRS/Binding.hs:pdrsBoundPVar`.
    def test_bound_pvar(self, pv, lp):
        """Test whether a pointer pv in local PDRS lp is bound by a label in this global PDRS."""
        return False

    def get_empty(self):
        """Returns an empty PDRS, if possible with the same label."""
        raise NotImplementedError

    ## @remarks Original haskell code in `/pdrt-sandbox/src/Data/PDRS/LambdaCalculus.hs:purifyPVars`
    def purify_pvars(self, gp, pvs):
        raise NotImplementedError


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
        return self.__class__ != other.__class__ or self._var != other._var or self._pos != other._pos

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self._var == other._var and self._pos == other._pos

    def __repr__(self):
        return 'LambdaPDRS(%s,%i)' % (self._var, self._pos)

    def _isproper_subdrsof(self, d):
        """Help for isproper"""
        return True

    @property
    def isresolved(self):
        """Test whether this PDRS is resolved (containing no unresolved merges or lambdas)"""
        return False

    @property
    def islambda(self):
        """Test whether this PDRS is entirely a LambdaPDRS (at its top-level)."""
        return True

    ## @remarks Original haskell code in `/pdrt-sandbox/src/Data/PDRS/Structure.hs:emptyPDRS`.
    def get_empty(self):
        """Returns an empty PDRS, if possible with the same label as this one."""
        return self

    ## @remarks Original haskell code in `/pdrt-sandbox/src/Data/PDRS/Variables.hs:pdrsVariables`.
    def get_variables(self, u=None):
        """Returns the list of all variables in a PDRS"""
        if u is None:
            return [PDRSRef(v) for v in self._var._set]
        return union_inplace(u, [PDRSRef(v) for v in self._var._set])

    ## @remarks Original haskell code in `/pdrt-sandbox/src/Data/PDRS/Variables.hs:pdrsLambdas`.
    def get_lambda_tuples(self, u=None):
        """Returns the set of all lambda tuples in this DRS."""
        lt = LambdaTuple(self._var, self._pos)
        if u is None: return set([lt])
        u.add(lt)
        return u

    ## @remarks Original haskell code in `/pdrt-sandbox/src/Data/PDRS/LambdaCalculus.hs::renameSubPDRS`
    def rename_subdrs(self, gd, rs, ps):
        """Applies alpha conversion to this PDRS which is a sub-PDRS of the global PDRS gd,
        on the basis of two conversion lists: PDRSRef's rs and PVar's ps.

        Args:
            gd: An PDRS|LambdaPDRS|AMerge|PMerge instance.
            rs: A conversion list of PDRSRef|LambaPDRSRef tuples.
            ps: A conversion list of integer tuples.

        Returns:
            A PDRS instance.
        """
        return LambdaPDRS(LambdaDRSVar(self._var._var, [rename_var(PDRSRef(v,[]), rs).var for v in self._var._set]), self._pos)

    ## @remarks Original haskell code in `/pdrt-sandbox/src/Data/PDRS/LambdaCalculus.hs:purifyPRefs`
    def purify_refs(self, gd, pvs):
        return self

    ## @remarks Original haskell code in `/pdrt-sandbox/src/Data/PDRS/LambdaCalculus.hs:purifyPVars`
    def purify_pvars(self, gp, pvs):
        return self, pvs


class GenericMerge(AbstractPDRS):
    """Common merge pattern"""
    def __init__(self, drsA, drsB):
        if not isinstance(drsA, AbstractPDRS) or not isinstance(drsB, AbstractPDRS):
            raise TypeError
        self._drsA = drsA
        self._drsB = drsB

    def __ne__(self, other):
        return self.__class__ != other.__class__ or self._drsA != other._drsA or self._drsB != other._drsB

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self._drsA == other._drsA and self._drsB == other._drsB

    def __repr__(self):
        return 'GMerge(%s,%s)' % (self._drsA, self._drsB)

    def _isproper_subdrsof(self, gd):
        """Help for isproper"""
        return self._drsA._isproper_subdrsof(gd) and self._drsB._isproper_subdrsof(gd)

    # Original haskell code in `/pdrt-sandbox/src/Data/PDRS/ProjectionGraph.hs:edges`.
    def _edges(self, es=None):
        es = self._drsA._edges(es)
        return self._drsB._edges(es)

    # Original haskell code in `/pdrt-sandbox/src/Data/PDRS/ProjectionGraph.hs:edges`.
    def _no_edges(self):
        return self._drsA._no_edges() and self._drsB._no_edges()

    ## @remarks Original haskell code in `/pdrt-sandbox/src/Data/PDRS/Structure.hs:pdrsLabel
    @property
    def label(self):
        """Get the projection label"""
        return self._drsA.label if self._drsA.islambda else self._drsB.label

    ## @remarks Original haskell code in `/pdrt-sandbox/src/Data/PDRS/Structure.hs:isMergePDRS
    @property
    def ismerge(self):
        """Test whether this PDRS is a AMerge or PMerge (at its top-level)."""
        return True

    ## @remarks Original haskell code in `/pdrt-sandbox/src/Data/PDRS/Structure.hs:isLambdaPDRS
    @property
    def islambda(self):
        """Test whether this DRS/PDRS is entirely a LambdaDRS/LambdaPDRS (at its top-level)."""
        return self._drsB.islambda and self._drsB.islambda

    ## @remarks Original haskell code in `/pdrt-sandbox/src/Data/PDRS/Structure.hs:emptyPDRS`.
    def get_empty(self):
        """Returns an empty PDRS, if possible with the same label as this one."""
        if self._drsB.islambda:
            return type(self)(self._drsA.get_empty(), self._drsB)
        return self._drsB.get_empty()

    ## @remarks Original haskell code in `/pdrt-sandbox/src/Data/PDRS/Binding.hs:pdrsBoundPVar`.
    def test_bound_pvar(self, pv, lp):
        """Test whether a pointer pv in local PDRS lp is bound by a label in this global PDRS."""
        return self._drsA.test_bound_pvar(pv, lp) or self._drsB.test_bound_pvar(pv, lp)

    ## @remarks Original haskell code in `/pdrt-sandbox/src/Data/PDRS/Structure.hs:pdrsLabels`
    def get_labels(self, u=None):
        """Returns all the labels in a PDRS."""
        u = self._drsA.get_labels(u)
        return self._drsB.get_labels(u)

    ## @remarks Original haskell code in `/pdrt-sandbox/src/Data/PDRS/Variables.hs:pdrsPVars`
    def get_pvars(self, u=None):
        """Returns the set of all 'PVar's in an AbstractPDRS"""
        u = self._drsA.get_pvars(u)
        return self._drsB.get_pvars(u)

    ## @remarks original haskell code in `/pdrt-sandbox/src/Data/PDRS/Binding.hs:pdrsFreePVars`.
    def get_free_pvars(self, gp, u=None):
        """Returns the set of all free PVar's in this PRDS, which is a sub PDRS of global PDRS gp."""
        u = self._drsA.get_pvars(u)
        return self._drsB.get_pvars(u)

    ## @remarks Original haskell code in `/pdrt-sandbox/src/Data/PDRS/Structure.hs:pdrsMAPs`
    def get_maps(self, u=None):
        """Returns the list of MAPs of this PDRS."""
        u = self._drsA.get_pvars(u)
        return self._drsB.get_pvars(u)

    ## @remarks original haskell code in `/pdrt-sandbox/src/Data/PDRS/Variables.hs:pdrsVariables`.
    def get_variables(self, u=None):
        """Returns the list of all variables in a PDRS"""
        u = self._drsA.get_variables(u)
        return self._drsB.get_variables(u)

    ## @remarks Original haskell code in `/pdrt-sandbox/src/Data/PDRS/Variables.hs:pdrsLambdas`.
    def get_lambda_tuples(self, u=None):
        """Returns the set of all lambda tuples in this DRS."""
        u = self._drsA.get_lambda_tuples(u)
        return self._drsB.get_lambda_tuples(u)

    ## @remarks Original haskell code in `/pdrt-sandbox/src/Data/PDRS/LambdaCalculus.hs::renameSubPDRS`
    def rename_subdrs(self, gd, rs, ps):
        """Applies alpha conversion to this PDRS which is a sub-PDRS of the global PDRS gd,
        on the basis of two conversion lists: PDRSRef's rs and PVar's ps.

        Args:
            gd: An PDRS|LambdaPDRS|AMerge|PMerge instance.
            rs: A conversion list of PDRSRef|LambaPDRSRef tuples.
            ps: A conversion list of integer tuples.

        Returns:
            A PDRS instance.
        """
        return type(self)(self._drsA.rename_subdrs(gd, rs, ps), self._drsB.rename_subdrs(gd, rs, ps))

    ## @remarks Original haskell code in `/pdrt-sandbox/src/Data/PDRS/LambdaCalculus.hs:purifyPRefs`
    def purify_refs(self, gd, ers):
        return type(self)(self._drsA.purify_refs(gd, ers), self._drsB.purify_refs(gd, ers))

    ## @remarks Original haskell code in `/pdrt-sandbox/src/Data/PDRS/LambdaCalculus.hs:purifyPVars`
    def purify_pvars(self, gp, pvs):
        cd1, pvs1 = self._drsA.purify_refs(gp, pvs)
        cd2, pvs2 = self._drsB.purify_refs(gp, pvs1)
        return type(self)(cd1, cd2), pvs2


class AMerge(GenericMerge):
    """An assertive merge between two PDRSs"""
    def __init__(self, drsA, drsB):
        super(AMerge, self).__init__(drsA, drsB)

    def __repr__(self):
        return 'AMerge(%s,%s)' % (self._drsA, self._drsB)


class PMerge(GenericMerge):
    """A projective merge between two PDRSs"""
    def __init__(self, drsA, drsB):
        super(PMerge, self).__init__(drsA, drsB)

    def __repr__(self):
        return 'PMerge(%s,%s)' % (self._drsA, self._drsB)


class PDRS(AbstractPDRS):
    """Projective Discourse Representation Structure."""
    def __init__(self, label, mapper, drsRefs, drsConds):
        if not iterable_type_check(drsRefs, PRef) or not iterable_type_check(drsConds, PCond):
            raise TypeError
        if not isinstance(label, PVar):
            raise TypeError
        self._refs = drsRefs
        self._conds = drsConds
        self._label = label
        self._mapper = mapper # maps a PVar to a PVar

    def __ne__(self, other):
        return self.__class__ != other.__class__ or self._refs != other._refs or self._conds != other._conds

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self._refs == other._refs and self._conds == other._conds

    def __repr__(self):
        return 'PDRS(%i,%s,%s)' % (self._label, self._refs, self._conds)

    def _isproper_subdrsof(self, gd):
        """Help for isproper"""
        return all(filter(lambda x: x._isproper_subdrsof(self, gd), self._conds))

    # Original haskell code in `/pdrt-sandbox/src/Data/PDRS/ProjectionGraph.hs:edges`.
    def _edges(self, es):
        es.append((self._label, self._label))
        es.extend(self._mapper)
        for c in self._conds:
            es = c._edges(es, self._label)
        return es

    @property
    def label(self):
        return self._label

    ## @remarks Original haskell code in `/pdrt-sandbox/src/Data/PDRS/ProjectionGraph.hs:edges`.
    def _no_edges(self):
        return len(self._conds) == 0 and len(self._refs) == 0 and len(self._mapper) == 0

    ## @remarks Original haskell code in `/pdrt-sandbox/src/Data/PDRS/Structure.hs:emptyPDRS`.
    def get_empty(self):
        """Returns an empty PDRS, if possible with the same label as this one."""
        return PDRS(self._label,[],[],[])

    ## @remarks Original haskell code in `/pdrt-sandbox/src/Data/PDRS/Structure.hs:pdrsLabels`
    def get_labels(self, u=None):
        """Returns a list of all the labels in this PDRS."""
        if u is None:
            u = [self._label]
        else:
            u.append(self._label)
        for c in self._cond:
            u = c._labels(u)
        return u

    ## @remarks Original haskell code in `/pdrt-sandbox/src/Data/PDRS/Variables.hs:pdrsPVars`
    def get_pvars(self, u=None):
        """Returns the set of all PVar's in an AbstractPDRS"""
        if u is None:
            u = set([self._label])
        elif not self._label in u:
            u.add(self._label)
        for x,y in self._mapper:
            u.add(x)
            u.add(y)
        for r in self._refs:
            u.add(r.label)
        #u = union_inplace(u, [r.label for r in self._refs])
        for c in self._conds:
            u = c._pvars(u)
        return u

    ## @remarks original haskell code in `/pdrt-sandbox/src/Data/PDRS/Binding.hs:pdrsFreePVars`.
    def get_free_pvars(self, gp, u=None):
        """Returns the set of all free PVar's in this PRDS, which is a sub PDRS of global PDRS gp."""
        if u is None: u = set()
        for x,y in self._mapper:
            u.add(x)
            u.add(y)
        # TODO: complete implementation
        raise NotImplementedError

    ## @remarks Original haskell code in `/pdrt-sandbox/src/Data/PDRS/Structure.hs:pdrsMAPs`
    def get_maps(self, u=None):
        """Returns the list of MAPs of this PDRS."""
        if u is None:
            u = [x for x in self._mapper] # shallow copy
        else:
            u = union(self._mapper, u)
        for c in self._conds:
            u = c._maps(u)
        return u

    ## @remarks Original haskell code in `/pdrt-sandbox/src/Data/PDRS/Variables.hs:pdrsVariables`.
    def get_variables(self, u=None):
        """Returns the list of all variables in a PDRS"""
        if u is None:
            u = [x.ref for x in self._refs] # shallow copy
        else:
            u = union_inplace(u, [x.ref for x in self._refs]) # union to avoid duplicates
        for c in self._conds:
            u = c._variables(u)
        return u

    ## @remarks Original haskell code in `/pdrt-sandbox/src/Data/PDRS/Variables.hs:pdrsLambdas`.
    def get_lambda_tuples(self, u=None):
        """Returns the set of all lambda tuples in this DRS."""
        if u is None:
            u = set()
        for r in self._refs:
            u = r._lambda_tuple(u)
        for c in self._conds:
            u = c._lambda_tuple(u)

    ## @remarks Original haskell code in `/pdrt-sandbox/src/Data/PDRS/Binding.hs:pdrsBoundPVar`.
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
        any(filter(lambda x: x._bound(lp), self._conds))
        for c in self._conds:
            if c._bound(lp, pv): return True
        return False

    ## @remarks Original haskell code in `/pdrt-sandbox/src/Data/PDRS/LambdaCalculus.hs::renameSubPDRS`
    def rename_subdrs(self, gd, rs, ps):
        """Applies alpha conversion to this PDRS which is a sub-PDRS of the global PDRS gd,
        on the basis of two conversion lists: PDRSRef's rs and PVar's ps.

        Args:
            gd: An PDRS|LambdaPDRS|AMerge|PMerge instance.
            rs: A conversion list of PDRSRef|LambaPDRSRef tuples.
            ps: A conversion list of integer tuples.

        Returns:
            A PDRS instance.
        """
        return PDRS(rename_var(self._label, ps), \
                    rename_mapper(self._mapper, self, gd, ps), \
                    rename_universe(self._refs, self, gd, ps, rs), \
                    filter(lambda x: x._convert(self, gd, rs, None, ps), self._conds))

    ## @remarks Original haskell code in `/pdrt-sandbox/src/Data/PDRS/LambdaCalculus.hs:purifyPRefs`
    def purify_refs(self, gd, ers):
        def convert(prs, pr):
            for prd,npr in prs:
                if pr.ref == prd.ref \
                        and (pr.has_projected_bound(self, prd, gd) \
                                or (pr.has_bound(self, gd) and gd.has_accessible_context(pr.label, prd.label))):
                    return npr
            return pr
        # Must return tuple to be compatible with AbstractDRS spec.
        return PDRS(self._label, self._mapper, [convert(gd, r) for r in self._refs],
                    [c._purify(gd, r) for c in self._conds]), None

    ## @remarks Original haskell code in `/pdrt-sandbox/src/Data/PDRS/LambdaCalculus.hs:purifyPVars`
    def purify_pvars(self, gp, pvs):
        ol = intersect([self.label], pvs)
        d1 = self.alpha_convert(zip(ol, get_new_pvars(ol, union_inplace(gp.get_pvars(), pvs))))
        pvs1 = [d1.label]
        pvs1.extend([x for x,y in d1.mapper])
        pvs1.extend([y for x,y in d1.mapper])
        pvs1 = union(pvs1, [r.label for r in d1.referents])
        pvs2 = union(pvs, pvs1)
        c2 = []
        for c in d1.conds:
            x, pvs2 = c._purify_pvars(gp, None, pvs2)
            c2.append(x)
        return PDRS(d1.label, d1.mapper, d1.referents, c2), pvs2


class IPDRSCond(object):
    """Additional Interface for PDRS Conditions"""
    # Original haskell code in /pdrt-sandbox/src/Data/PDRS/ProjectionGraph.hs:edges.
    def _edges(self, es, pv):
        return es

    # Original haskell code in /pdrt-sandbox/src/Data/PDRS/Variables.hs:pdrsPVars:pvars
    def _pvars(self, u):
        return u

    # Original haskell code in /pdrt-sandbox/src/Data/PDRS/LambdaCalculus.hs:purifyPVars:purify
    def _purify_pvars(self, gp, pv, ps):
        raise NotImplementedError

    # Original haskell code in /pdrt-sandbox/src/Data/PDRS/Structure.hs:pdrsLabels:labels
    def _labels(self, u):
        return u

    # Original haskell code in /pdrt-sandbox/src/Data/PDRS/Structure.hs:pdrsMAPs:maps
    def _maps(self, u):
        return u

    # Original haskell code in /pdrt-sandbox/src/Data/PDRS/Binding.hs:pdrsBoundPVar:bound
    def _bound(self, lp, pv):
        return False


class PCond(AbstractDRSCond, IPDRSCond):
    """A projected condition, consisting of a PVar and a AbstractDRSCond."""
    def __init__(self, label, cond):
        if not isinstance(label, PVar) or not isinstance(cond, AbstractDRSCond):
            raise TypeError
        self._label = label
        self._cond = cond

    def __ne__(self, other):
        return self.__class__ != other.__class__ or self._label != other._label or self._cond != other._cond

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self._label == other._label and self._cond == other._cond

    def __repr__(self):
        return 'PCond(%i,%s)' % (self._label, self._conds)

    def _isproper_subdrsof(self, sd, gd, pv):
        # Pass down to member condition
        assert pv is None
        return self._cond._isproper_subdrsof(sd, gd, self._label)

    def _universes(self, u):
        # Pass down to member condition
        return self._cond._universes(u)

    def _variables(self, u):
        # Pass down to member condition
        return self._cond._universes(u)

    # Helper for DRS.get_lambda_tuples()
    def _lambda_tuple(self, u):
        # Pass down to member condition
        return self._cond.lambda_tuple(u)

    # Original haskell code in `/pdrt-sandbox/src/Data/PDRS/Binding.hs:pdrsFreePRefs:free`.
    def _get_freerefs(self, ld, gd, pv):
        # Pass down to member condition
        assert pv is None
        return self._cond._get_freerefs(ld, gd, self._label)

    # Original haskell code in `/pdrt-sandbox/src/Data/PDRS/ProjectionGraph.hs:edges`.
    def _edges(self, es, pv):
        return union_inplace(self._cond._edges(es, self._label), [(pv, self._label)])

    # Original haskell code in /pdrt-sandbox/src/Data/PDRS/Variables.hs:pdrsPVars:pvars
    def _pvars(self, u):
        u.add(self.label)
        return self._cond._pvars(u)

    # Original haskell code in /pdrt-sandbox/src/Data/PDRS/LambdaCalculus.hs:renamePCons:rename
    def _convert(self, ld, gd, rs, pv, ps):
        # Pass down to member condition
        assert pv is None
        return PCond(rename_pvar(self._label, ld, gd, ps), self._cond._convert(ld, gd, rs, self._label, ps))

    # Original haskell code in /pdrt-sandbox/src/Data/PDRS/LambdaCalculus.hs:purifyPRefs:purify
    def _purify(self, gd, rs, pv, ps):
        assert pv is None
        cond, _ = self._cond._purify(gd, rs, self._label, ps)
        # Must return tuple to be compatible with AbstractDRS spec
        return PCond(self._label, cond), None

    # Original haskell code in /pdrt-sandbox/src/Data/PDRS/LambdaCalculus.hs:purifyPVars:purify
    def _purify_pvars(self, gp, pv, ps):
        cond, ps = self._cond._purify_pvars(gp, self._label, ps)
        return PCond(self._label, cond), ps

    def _labels(self, u):
        return self._cond._labels(u)

    def _maps(self, u):
        return self._cond._maps(u)

    # Original haskell code in /pdrt-sandbox/src/Data/PDRS/Binding.hs:pdrsBoundPVar:bound
    def _bound(self, lp, pv):
        return self._cond._bound(lp, pv)

    @property
    def label(self):
        return self._label

    @property
    def drscond(self):
        return self._cond

    def resolve_merges(self):
        # Pass down to member condition
        return PCond(self._label, self._cond.resolve_merges())

    def _antecedent(self, ref, drs):
        raise NotImplementedError

    def _ispure(self, ld, gd, rs):
        raise NotImplementedError

    def to_mfol(self, world):
        raise NotImplementedError

    def show(self, notation):
        raise NotImplementedError


class PRel(Rel, IPDRSCond):
    """A relation defined on a set of referents"""
    def __init__(self, drsRel, drsRefs):
        super(PRel, self).__init__(drsRel, drsRefs)

    # Original haskell code in /pdrt-sandbox/src/Data/PDRS/Bindings.hs:pdrsFreePRefs:free
    def _get_freerefs(self, ld, gd, pv):
        return filter(lambda x: not PRef(pv, x).has_bound(ld, gd), self._refs)

    # Original haskell code in /pdrt-sandbox/src/Data/PDRS/Properties.hs:isProperPDRS:isProperSubPDRS
    def _isproper_subdrsof(self, sd, gd, pv):
        return all(filter(lambda x: not PRef(pv, x).has_bound(sd, gd), self._refs))

    # Original haskell code in /pdrt-sandbox/src/Data/PDRS/LambdaCalculus.hs:renamePCons:rename
    def _convert(self, ld, gd, rs, pv, ps):
        refs = [rename_pdrsref(pv, r, ld, gd, rs) for r in self._refs]
        return PRel(self._rel, refs)

    # Original haskell code in /pdrt-sandbox/src/Data/PDRS/LambdaCalculus.hs:purifyPRefs:purify
    def _purify(self, gd, rs, pv, ps):
        def convert(prs, pr):
            for prd,npr in prs:
                if pr.ref == prd.ref \
                        and (pr.has_projected_bound(self, prd, gd) \
                                or (pr.has_bound(self, gd) and gd.has_accessible_context(pr.label, prd.label))):
                    return npr.ref
            return pr.ref
        # Must return tuple to be compatible with AbstractDRS spec
        return PRel(self._rel, [convert(PRef(pv,r)) for r in self._refs]), None

    # Original haskell code in /pdrt-sandbox/src/Data/PDRS/LambdaCalculus.hs:purifyPVars:purify
    def _purify_pvars(self, gp, pv, ps):
        ps.append(pv)
        return self

    def _antecedent(self, ref, drs):
        raise NotImplementedError

    def _ispure(self, ld, gd, rs):
        raise NotImplementedError

    def to_mfol(self, world):
        raise NotImplementedError

    def show(self, notation):
        raise NotImplementedError


class PNeg(Neg, IPDRSCond):
    """A negated DRS"""
    def __init__(self, drs):
        super(PNeg, self).__init__(drs)

    # Original haskell code in /pdrt-sandbox/src/Data/PDRS/ProjectionGraph.hs:edges.
    def _edges(self, es, pv):
        if self._drs._no_edges(): return es
        es = union_inplace(es, [(self._drs.label, pv)])
        return self._drs._edges(es)

    # Original haskell code in /pdrt-sandbox/src/Data/PDRS/LambdaCalculus.hs:purifyPVars:purify
    def _purify_pvars(self, gp, pv, ps):
        cp1, ps1 = self._drs.purify_pvars(gp, union(ps,[pv]))
        return PNeg(cp1), ps1

    def _labels(self, u):
        return self._drs.get_labels(u)

    def _maps(self, u):
        return self._drs.get_maps(u)

    def _bound(self, lp, pv):
        return self._drs.has_subdrs(lp) and self._drs.test_bound_pvar(pv, lp)

    def _antecedent(self, ref, drs):
        raise NotImplementedError

    def _ispure(self, ld, gd, rs):
        raise NotImplementedError

    def to_mfol(self, world):
        raise NotImplementedError

    def show(self, notation):
        raise NotImplementedError


class PImp(Imp, IPDRSCond):
    """An implication between two DRSs"""
    def __init__(self, drsA, drsB):
        super(PImp, self).__init__(drsA, drsB)

    def _purify(self, gd, rs, pv, ps):
        cd1, _ = self._drsA.purify_refs(gd, rs, ps)
        cd2, _ = self._drsB.purify_refs(gd, rs, ps)
        return PImp(cd1, cd2), None

    # Original haskell code in /pdrt-sandbox/src/Data/PDRS/ProjectionGraph.hs:edges.
    def _edges(self, es, pv):
        if self._drsA._no_edges() and self._drsA._no_edges():
            return es
        elif self._drsA._no_edges():
            es = union_inplace(es, [(self._drsB.label, pv)])
            return self._drsB._edges(es)
        elif self._drsB._no_edges():
            es = union_inplace(es, [(self._drsA.label, pv)])
            return self._drsA._edges(es)
        es = union_inplace(es, [(self._drsA.label, pv)])
        es = self._drsA._edges(es)
        es = union_inplace(es, [(self._drsB.label, pv)])
        return self._drsB._edges(es)

    # Original haskell code in /pdrt-sandbox/src/Data/PDRS/LambdaCalculus.hs:purifyPVars:purify
    def _purify_pvars(self, gp, pv, ps):
        ops = intersect(union_inplace(ps, [pv]), [self._drsA.label])
        nps = zip(ops, get_new_pvars(ops, union(gp.get_pvars(), ps)))
        cp1, ps1 = self._drsA.rename_subdrs(gp, [], ps).purify_pvars(gp, union_inplace(ps, [pv]))
        cp2, ps2 = self._drsA.rename_subdrs(gp, [], ps).purify_pvars(gp, ps1)
        return PImp(cp1, cp2), ps2

    def _labels(self, u):
        u = self._drsA.get_labels(u)
        return self._drsB.get_labels(u)

    def _maps(self, u):
        u = self._drsA.get_maps(u)
        return self._drsB.get_maps(u)

    def _bound(self, lp, pv):
        return (self._drsA.has_subdrs(lp) and self._drsA.test_bound_pvar(pv, lp)) \
               or (self._drsB.has_subdrs(lp) and self._drsB.test_bound_pvar(pv, lp))

    def _antecedent(self, ref, drs):
        raise NotImplementedError

    def _ispure(self, ld, gd, rs):
        raise NotImplementedError

    def to_mfol(self, world):
        raise NotImplementedError

    def show(self, notation):
        raise NotImplementedError


class POr(Or, IPDRSCond):
    """A disjunction between two DRSs"""
    def __init__(self, drsA, drsB):
        super(POr, self).__init__(drsA, drsB)

    def _purify(self, gd, rs, pv, ps):
        cd1, _ = self._drsA.purify_refs(gd, rs, ps)
        cd2, _ = self._drsB.purify_refs(gd, rs, ps)
        return POr(cd1, cd2), None

    # Original haskell code in /pdrt-sandbox/src/Data/PDRS/ProjectionGraph.hs:edges.
    def _edges(self, es, pv):
        if self._drsA._no_edges() and self._drsA._no_edges():
            return es
        elif self._drsA._no_edges():
            es = union_inplace(es, [(self._drsB.label, pv)])
            return self._drsB._edges(es)
        elif self._drsB._no_edges():
            es = union_inplace(es, [(self._drsA.label, pv)])
            return self._drsA._edges(es)
        es = union_inplace(es, [(self._drsA.label, pv)])
        es = self._drsA._edges(es)
        es = union_inplace(es, [(self._drsB.label, pv)])
        return self._drsB._edges(es)

    # Original haskell code in /pdrt-sandbox/src/Data/PDRS/LambdaCalculus.hs:purifyPVars:purify
    def _purify_pvars(self, gp, pv, ps):
        ops = intersect(union_inplace(ps, [pv]), [self._drsA.label])
        nps = zip(ops, get_new_pvars(ops, union(gp.get_pvars(), ps)))
        cp1, ps1 = self._drsA.rename_subdrs(gp, [], ps).purify_pvars(gp, union_inplace(ps, [pv]))
        cp2, ps2 = self._drsA.rename_subdrs(gp, [], ps).purify_pvars(gp, ps1)
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

    def _antecedent(self, ref, drs):
        raise NotImplementedError

    def _ispure(self, ld, gd, rs):
        raise NotImplementedError

    def to_mfol(self, world):
        raise NotImplementedError

    def show(self, notation):
        raise NotImplementedError


class PProp(Prop, IPDRSCond):
    """A proposition DRS"""
    def __init__(self, drsRef, drs):
        super(PProp, self).__init__(drsRef, drs)

    # Original haskell code in /pdrt-sandbox/src/Data/PDRS/Binding.hs:pdrsFreePRefs:free.
    def _get_freerefs(self, ld, gd, pvar):
        return union(filter(lambda x: not x.has_bound(x, ld, gd), [PRef(pvar, self._ref)]), self._drs.get_freerefs(gd))

    def _isproper_subdrsof(self, sd, gd, pvar):
        return PRef(pvar, self._ref).has_bound(sd, gd) and self._drs._isproper_subdrsof(gd)

    # Original haskell code in /pdrt-sandbox/src/Data/DRS/LambdaCalculus.hs:renameCons:convertCon
    def _convert(self, ld, gd, rs, pv, ps):
        return Prop(rename_pdrsref(pv, self._ref, ld, gd, rs), self._drs.rename_subdrs(gd, rs, ps))

    def _purify(self, gd, rs, pv, ps):
        def convert(prs, pr):
            for prd,npr in prs:
                if pr.ref == prd.ref \
                        and (pr.has_projected_bound(self, prd, gd) \
                                or (pr.has_bound(self, gd) and gd.has_accessible_context(pr.label, prd.label))):
                    return npr.ref
            return pr.ref
        # Must return tuple to be compatible with AbstractDRS spec
        return PProp(convert(PRef(pv, self._ref)), self._drs.purify_refs(gd, rs, ps)), None

    # Original haskell code in /pdrt-sandbox/src/Data/PDRS/ProjectionGraph.hs:edges.
    def _edges(self, es, pv):
        if self._drs._no_edges(): return es
        es = union_inplace(es, [(self._drs.label, pv)])
        return self._drs._edges(es)

    # Original haskell code in /pdrt-sandbox/src/Data/PDRS/LambdaCalculus.hs:purifyPVars:purify
    def _purify_pvars(self, gp, pv, ps):
        cp1, ps1 = self._drs.purify_pvars(gp, union(ps,[pv]))
        return PProp(self._ref, cp1), ps1

    def _labels(self, u):
        return self._drs.get_labels(u)

    def _maps(self, u):
        return self._drs.get_maps(u)

    def _bound(self, lp, pv):
        return self._drs.has_subdrs(lp) and self._drs.test_bound_pvar(pv, lp)

    def _antecedent(self, ref, drs):
        raise NotImplementedError

    def _ispure(self, ld, gd, rs):
        raise NotImplementedError

    def to_mfol(self, world):
        raise NotImplementedError

    def show(self, notation):
        raise NotImplementedError


class PDiamond(Diamond, IPDRSCond):
    """A possible DRS"""
    def __init__(self, drs):
        super(PNeg, self).__init__(drs)

    # Original haskell code in /pdrt-sandbox/src/Data/PDRS/ProjectionGraph.hs:edges.
    def _edges(self, es, pv):
        if self._drs._no_edges(): return es
        es = union_inplace(es, [(self._drs.label, pv)])
        return self._drs._edges(es)

    # Original haskell code in /pdrt-sandbox/src/Data/PDRS/LambdaCalculus.hs:purifyPVars:purify
    def _purify_pvars(self, gp, pv, ps):
        cp1, ps1 = self._drs.purify_pvars(gp, union(ps,[pv]))
        return PDiamond(cp1), ps1

    def _labels(self, u):
        return self._drs.get_labels(u)

    def _maps(self, u):
        return self._drs.get_maps(u)

    def _bound(self, lp, pv):
        return self._drs.has_subdrs(lp) and self._drs.test_bound_pvar(pv, lp)

    def _antecedent(self, ref, drs):
        raise NotImplementedError

    def _ispure(self, ld, gd, rs):
        raise NotImplementedError

    def to_mfol(self, world):
        raise NotImplementedError

    def show(self, notation):
        raise NotImplementedError

class PBox(Box, IPDRSCond):
    """A necessary DRS"""
    def __init__(self, drs):
        super(PNeg, self).__init__(drs)

    # Original haskell code in /pdrt-sandbox/src/Data/PDRS/ProjectionGraph.hs:edges.
    def _edges(self, es, pv):
        if self._drs._no_edges(): return es
        es = union_inplace(es, [(self._drs.label, pv)])
        return self._drs._edges(es)

    # Original haskell code in /pdrt-sandbox/src/Data/PDRS/LambdaCalculus.hs:purifyPVars:purify
    def _purify_pvars(self, gp, pv, ps):
        cp1, ps1 = self._drs.purify_pvars(gp, union(ps,[pv]))
        return PBox(cp1), ps1

    def _labels(self, u):
        return self._drs.get_labels(u)

    def _maps(self, u):
        return self._drs.get_maps(u)

    def _bound(self, lp, pv):
        return self._drs.has_subdrs(lp) and self._drs.test_bound_pvar(pv, lp)

    def _antecedent(self, ref, drs):
        raise NotImplementedError

    def _ispure(self, ld, gd, rs):
        raise NotImplementedError

    def to_mfol(self, world):
        raise NotImplementedError

    def show(self, notation):
        raise NotImplementedError




