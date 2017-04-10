# -*- coding: utf-8 -*-
"""Compositional DRT"""

import weakref

from common import SHOW_LINEAR, DRSConst
from drs import AbstractDRS, DRS, DRSRef, Prop, Rel
from drs import get_new_drsrefs
from marbles.ie.ccg.ccgcat import Category, CAT_EMPTY, CAT_NP, CAT_CONJ, CAT_PPNP, \
    RL_RPASS, RL_LPASS, RL_FA, RL_BA, RL_BC, RL_FC, RL_BX, RL_FX, RL_BS, RL_BXS, RL_FS, RL_FXS, RL_GFC, RL_GFX, \
    RL_GBC, RL_GBX, RL_TYPE_RAISE, RL_RNUM, RL_RCONJ, RL_LCONJ, \
    RL_TC_CONJ
from utils import iterable_type_check, intersect, union, union_inplace, remove_dups

## @{
## @ingroup gconst
## @defgroup ccg2drs_const CCG to DRS Constants

## Compose option: remove propositions containing single referent in the subordinate DRS.
CO_REMOVE_UNARY_PROPS = 0x1
## Compose option: print derivations to stdout during production
CO_PRINT_DERIVATION = 0x2
## Compose option: verify signature during production
CO_VERIFY_SIGNATURES = 0x4

## @}


## @{
## @ingroup gconst
## @defgroup reftypes DRS Referent Types

RT_PROPERNAME    = 0x0000000000000001
RT_ENTITY        = 0x0000000000000002
RT_EVENT         = 0x0000000000000004
RT_LOCATION      = 0x0000000000000008
RT_DATE          = 0x0000000000000010
RT_WEEKDAY       = 0x0000000000000020
RT_MONTH         = 0x0000000000000040
RT_HUMAN         = 0x0000000000000080
RT_ANAPHORA      = 0x0000000000000100
RT_NUMBER        = 0x0000000000000200

RT_RELATIVE      = 0x8000000000000000
RT_PLURAL        = 0x4000000000000000
RT_MALE          = 0x2000000000000000
RT_FEMALE        = 0x1000000000000000


## @}

class DrsComposeError(Exception):
    """Production Error."""
    pass


def identity_functor(category, ref=None, dep=None):
    """Return the identity functor `λx.P(x)`.

    Args:
        category: A functor category where the result and argument are atoms.
        ref: optional DRSRef to use as identity referent.
        dep: optional dependency tree.

    Returns:
        A FunctorProduction instance.

    Remarks:
        This can be used for atomic unary rules.
    """
    assert category.result_category.isatom
    assert category.argument_category.isatom
    d = DrsProduction(DRS([], []), category=category.result_category)
    if ref is None:
        ref = DRSRef('x1')
    d.set_lambda_refs([ref])
    return FunctorProduction(category, ref, d, dep=dep)


class Dependency(object):
    def __init__(self, drsref, word, typeid, idx=0):
        """Constructor.

        Args:
            drsref: Key for dictionary.
            word: Noun or Proper Name.
            typeid: An integer type id.
            idx: position in sentence
        """
        if isinstance(drsref, str):
            drsref = DRSRef(drsref)
        self._ref = drsref
        self._word = word
        self._mask = typeid
        self._head = None
        self._children = set()

    def _repr_heads(self, s):
        if self._ref is None:
            s = '[()<=(%s)]' % s
        else:
            s = '[(%s,%s)<=(%s)]' % (self._ref.var.to_string(), self._word, s)
        if self.head is None:
            return s
        return self.head._repr_heads(s)

    def _repr_children(self):
        if self._children is not None:
            nds = ','.join([x._repr_children() for x in self._children])
        else:
            nds = ''
        if self._ref is None:
            return '[()<-(%s)]' % nds
        else:
            return '[(%s,%s)<-(%s)]' % (self._ref, self._word, nds)

    def __repr__(self):
        s = self._repr_children()
        if self.head is not None:
            return self.head._repr_heads(s)
        return s

    @property
    def head(self):
        return self._head() if self._head is not None else None

    @property
    def children(self):
        return sorted(self._children)

    @property
    def descendants(self):
        u = set()
        u = u.union(self._children)
        for c in self._children:
            u = u.union(c.descendants)
        return sorted(u)

    @property
    def root(self):
        r = self
        while r.head is not None:
            r = r.head
        return r

    def set_head(self, head):
        if head != self.head:
            self._head = weakref.ref(head)
        head._children.add(self)
        return head

    def _update_referent(self, oldref, newref):
        if oldref == self._ref:
            self._ref = newref
            return True
        else:
            for c in self._children:
                if c._update_referent(oldref, newref):
                    return True
        return False

    def update_referent(self, oldref, newref):
        """Update a referent in the dependency tree.

        Args:
            oldref: Old referent name.
            newref: New referent name.
        """
        if isinstance(oldref, str):
            drsref = DRSRef(oldref)
        if isinstance(newref, str):
            drsref = DRSRef(newref)

        if oldref != newref:
            self.root._update_referent(oldref, newref)

    def _update_mapping(self, drsref, word, typeid):
        if drsref == self._ref:
            if word is not None:
                self._word = word
            self._mask |= typeid
            return True
        else:
            for c in self._children:
                if c._update_mapping(drsref, word, typeid):
                    return True
        return False

    def update_mapping(self, drsref, word, typeid=0):
        """Update a referents mapping in the dependency tree.

        Args:
            drsref: Key for dictionary.
            word: Noun or Proper Name.
            typeid: An optional integer type id.
        """
        if isinstance(drsref, str):
            drsref = DRSRef(drsref)
        if drsref == self._ref:
            if word is not None:
                self._word = word
            self._mask |= typeid
        else:
            self.root._update_mapping(drsref, word, typeid)

    def _get_mapping(self, drsref):
        if drsref == self._ref:
            return (self._word, self._mask)
        else:
            for c in self._children:
                result = c._get_mapping(drsref)
                if result is not None:
                    return result
        return None

    def get_mapping(self, drsref):
        """Get the referent mapping."""
        if drsref == self._ref:
            return self._get_mapping(drsref)
        return self.root._get_mapping(drsref)

    def get(self):
        """Get the referent mapping."""
        return self._ref, self._word, self._mask

    def _remove_ref(self, drsref):
        if drsref == self._ref:
            hd = self.head
            if hd is None:
                self._ref = DRSRef('ROOT')
                self._word = ''
                self._mask = 0
            else:
                hd._children = hd._children.difference([self])
                for c in self._children:
                    c.set_head(hd)
                self._children = None
                self._head = None
            return True
        else:
            for c in self._children:
                if c._remove_ref(drsref):
                    return True
        return False

    def remove_ref(self, drsref):
        if drsref == self._ref:
            self._remove_ref(drsref)
        else:
            self.root._remove_ref(drsref)


class Production(object):
    """An abstract production."""
    def __init__(self, category=None, dep=None):
        self._lambda_refs = None
        self._options = 0
        if category is None:
            self._category = CAT_EMPTY
        elif isinstance(category, Category):
            self._category = category
        else:
            raise TypeError('category must be instance of Category')
        if dep is None or isinstance(dep, Dependency):
            self._dep = dep
        else:
            raise TypeError('dep must be instance of DepManager')

    def __eq__(self, other):
        return id(self) == id(other)

    @staticmethod
    def nodups(rs):
        return filter(lambda x: x[0] != x[1], rs)

    @property
    def category(self):
        """The CCG category"""
        return self._category

    @property
    def dep(self):
        """The dependency node."""
        return self._dep

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

    def set_dependency(self, dep):
        """Set the dependency"""
        oldep = self._dep
        self._dep = dep
        return oldep

    def get_scope_count(self):
        """Get the number of scopes in a functor. Zero for non functor types"""
        return 0

    def remove_proper_noun(self):
        pass

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
        if self._lambda_refs is not None:
            self._lambda_refs = self._lambda_refs.alpha_convert(rs)
            #self._lambda_refs = self._lambda_refs.substitute(rs)
        if self._dep:
            for o, n in rs:
               self._dep.update_referent(o, n)

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
            nrs = get_new_drsrefs(ors, union(ers, ers2))
            xrs = self.nodups(zip(ors, nrs))
            self.rename_vars(xrs)


class DrsProduction(Production):
    """A DRS production."""
    def __init__(self, drs, properNoun=False, category=None, dep=None):
        """Constructor.

        Args:
            drs: A marbles.ie.drt.DRS instance.
            properNoun: True is a proper noun.
        """
        super(DrsProduction, self).__init__(category, dep)
        if not isinstance(drs, AbstractDRS):
            raise TypeError('DrsProduction expects DRS')
        self._drs = drs
        self._nnp = properNoun

    def __repr__(self):
        lr = [r.var.to_string() for r in self.lambda_refs]
        if len(lr) == 0:
            return self.drs.show(SHOW_LINEAR).encode('utf-8')
        return 'λ' + 'λ'.join(lr) + '.' + self.drs.show(SHOW_LINEAR).encode('utf-8')

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
        return union(self._drs.universes, self._drs.freerefs, self.lambda_refs)

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

    def verify(self):
        """Test helper."""
        if len(self.lambda_refs) != 1 or not self.category.isatom:
            pass
        return len(self.lambda_refs) == 1 and self.category.isatom

    def remove_proper_noun(self):
        self._nnp = False

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
        """Resolve anaphora and purify the underlying DRS instance.

        Returns:
            A Production instance representing purified result.
        """
        if self.dep is not None:
            # Find anaphora
            anap_h = []
            anap_nh = []
            pn = []

            root = self.dep.root
            for nd in root.descendants:
                r, w, t = nd.get()
                if (t & (RT_ANAPHORA | RT_HUMAN)) == (RT_ANAPHORA | RT_HUMAN):
                    # he, she
                    anap_h.append((nd, r, w, t))
                elif (t & RT_PROPERNAME) != 0:
                    pn.append((nd, r, w, t))
                elif (t & RT_ANAPHORA) != 0:
                    # it
                    anap_nh.append((nd, r, w, t))

            # Resolve it
            rs = []
            for dep, r, w, t in anap_nh:
                for nd in dep.descendants:
                    rr, ww, tt = nd.get()
                    if (t & (RT_ENTITY | RT_PLURAL)) == RT_ENTITY:
                        rs.append((r, rr))
                        break
            if len(rs) != 0:
                self.rename_vars(rs)

            # Make proper names constants
            rs = []
            for dep, r, w, t in pn:
                fc = self._drs.find_condition(Rel(w, [r]))
                if fc is not None:
                    self._drs.remove_condition(fc)
                    rs.append((r, DRSRef(DRSConst(w))))
                    dep.remove_ref(r)
            if len(rs) != 0:
                self.rename_vars(rs)

        # Remainder are unresolved
        fr = self._drs.freerefs
        if len(fr) != 0:
            self._drs = DRS(union(self._drs.universe, fr), self._drs.conditions)
        self._drs = self._drs.purify()
        return self


class ProductionList(Production):
    """A list of productions."""

    def __init__(self, compList=None, category=None, dep=None):
        super(ProductionList, self).__init__(category, dep)
        if compList is None:
            compList = []
        if isinstance(compList, AbstractDRS):
            compList = [DrsProduction(compList)]
        elif isinstance(compList, Production):
            compList = [compList]
        elif iterable_type_check(compList, AbstractDRS):
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

    def iterator(self):
        """Iterate the productions in this list."""
        for c in self._compList:
            yield c

    def reversed_iterator(self):
        """Iterate the productions in this list."""
        for c in reversed(self._compList):
            yield c

    def clone(self):
        cl = ProductionList([x for x in self._compList], dep=self.dep)
        cl.set_options(self.compose_options)
        cl.set_lambda_refs(self.lambda_refs)
        return cl

    def flatten(self):
        """Unify subordinate ProductionList's into the current list."""
        compList = []
        for d in self._compList:
            if d.isempty:
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
        if isinstance(other, AbstractDRS):
            other = DrsProduction(other, )
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
        if isinstance(other, AbstractDRS):
            other = DrsProduction(other, )
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

    def apply_forward(self):
        """Forward application.

        Remarks:
            Executes a single production rule.
        """
        if len(self._compList) == 0:
            return self
        fn = self._compList[0]
        if not fn.isfunctor:
            pass
        if len(self._compList) == 1:
            # This can happen with punctuation etc. Empty productions are removed
            # after a unify so we must simulate application with empty.
            d = fn.pop()
            g = fn.pop()
            if g is not None:
                g.push(d)
                d = g
        else:
            arg = self._compList[1]
            self._compList = self._compList[1:]
            d = fn.apply(arg)
        self._compList[0] = d
        self.set_lambda_refs(d.lambda_refs)
        self.set_category(d.category)
        return self

    def apply_backward(self, enableException=False):
        """Backward application.

        Remarks:
            Executes a single production rule.
        """
        if len(self._compList) == 0:
            return self
        fn = self._compList.pop()
        if not fn.isfunctor:
            pass
        if len(self._compList) == 0:
            # This can happen with punctuation etc. Empty productions are removed
            # after a unify so we must simulate application with empty.
            d = fn.pop()
            g = fn.pop()
            if g is not None:
                g.push(d)
                d = g
        else:
            arg = self._compList.pop()
            d = fn.apply(arg)

        self._compList.append(d)
        self.set_lambda_refs(d.lambda_refs)
        self.set_category(d.category)
        return self

    def unify(self):
        """Finalize the production by performing a unification right to left.

        Returns:
            A Production instance.
        """
        ml = [x.unify() for x in self._compList]
        self._compList = []
        if len(ml) == 1:
            if not self.islambda_inferred:
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
        pconds = []     # proper nouns
        oconds = []     # other predicates
        lastr = DRSRef('$$$$')
        proper = 0
        for d in ml:
            if d.isproper_noun:
                # FIXME: may not be true if we promote to a proposition
                ctmp = d.drs.conditions
                if isinstance(d.drs.conditions[0], Rel):
                    nextr = ctmp[0].referents[0]
                else:
                    nextr = DRSRef('$$$$')
                if nextr != lastr:
                    # Hyphenate name
                    lastr = nextr
                    proper += 1
                    if len(pconds) != 0:
                        name = '-'.join([c.relation.to_string() for c in pconds])
                        self.dep.update_mapping(lastr, name)
                        conds.append(Rel(name, [lastr]))
                        conds.extend(oconds)
                    pconds = [ctmp[0]]
                    oconds = ctmp[1:]
                else:
                    pconds.append(ctmp[0])
                    oconds.extend(ctmp[1:])
            else:
                # FIXME: proper-noun followed by noun, for example Time magazine, should we collate?
                if len(pconds) != 0:
                    name = '-'.join([c.relation.to_string() for c in pconds])
                    if self.dep is None:
                        pass
                    self.dep.update_mapping(lastr, name)
                    conds.append(Rel(name, [lastr]))
                    conds.extend(oconds)
                lastr = DRSRef('$$$$')
                pconds = []
                oconds = []
                conds.extend(d.drs.conditions)
                proper += 1
            refs.extend(d.drs.referents)
        # FIXME: Boc Raton and Hot Springs => Boca-Raton(x) Hot-Springs(x1)
        # Hyphenate name
        if len(pconds) != 0:
            name = '-'.join([c.relation.to_string() for c in pconds])
            if self.dep is None:
                pass
            self.dep.update_mapping(lastr, name)
            conds.append(Rel(name, [lastr]))
            conds.extend(oconds)

        if len(refs) == 0 and len(conds) == 0:
            return self

        drs = DRS(refs, conds).purify()
        d = DrsProduction(drs, proper == 1, dep=self.dep)
        if not self.islambda_inferred:
            d.set_lambda_refs(self.lambda_refs)
        elif not ml[0].islambda_inferred:
            d.set_lambda_refs(ml[0].lambda_refs)
        d.set_category(self.category)
        return d
    
    def compose_forward(self, generalized=False):
        """Forward composition and forward crossing composition.

        Args:
            generalized: If True use generalized versions.

        Remarks:
            Executes a single production rule.
        """
        assert len(self._compList) >= 2
        fn = self._compList[0]
        arg = self._compList[1]
        c = self._compList[1:]
        if generalized:
            # CALL[X/Y](Y|Z)$
            # Generalized Forward Composition           X/Y:f (Y/Z)/$ => (X/Z)/$
            # Generalized Forward Crossing Composition  X/Y:f (Y\Z)$: => (X\Z)$
            d = fn.generalized_compose(arg)
        else:
            # CALL[X/Y](Y|Z)
            # Forward Composition           X/Y:f Y/Z:g => X/Z: λx􏰓.f(g(x))
            # Forward Crossing Composition  X/Y:f Y\Z:g => X\Z: λx􏰓.f(g(x))
            d = fn.compose(arg)
        c[0] = d
        self._compList = c
        self.set_lambda_refs(d.lambda_refs)
        self.set_category(d.category)
        return self

    def compose_backward(self, generalized=False):
        """Backward composition and forward crossing composition.

        Args:
            generalized: If True use generalized versions.

        Remarks:
            Executes a single production rule.
        """
        assert len(self._compList) >= 2
        fn = self._compList[-1]
        arg = self._compList[-2]
        c = self._compList[0:-1]
        if generalized:
            # CALL[X\Y](Y|Z)$
            # Generalized Backward Composition          (Y\Z)$  X\Y:f => (X\Z)$
            # Generalized Backward Crossing Composition (Y/Z)/$ X\Y:f => (X/Z)/$
            d = fn.generalized_compose(arg)
        else:
            # CALL[X\Y](Y|Z)
            # Backward Composition          Y\Z:g X\Y:f => X\Z: λx􏰓.f(g(x))
            # Backward Crossing Composition Y/Z:g X\Y:f => X/Z: λx􏰓.f(g(x))
            d = fn.compose(arg)
        c[-1] = d
        self._compList = c
        self.set_lambda_refs(d.lambda_refs)
        self.set_category(d.category)
        return self

    def substitute_forward(self):
        """Forward substitution and forward crossing substitution.

        Remarks:
            Executes a single production rule.
        """
        assert len(self._compList) >= 2
        fn = self._compList[0]
        arg = self._compList[1]
        c = self._compList[1:]
        # CALL[(X/Y)|Z](Y|Z)
        # Forward Substitution          (X/Y)/Z:f Y/Z:g => X/Z: λx􏰓.fx􏰨(g􏰨(x􏰩􏰩))
        # Forward Crossing Substitution (X/Y)\Z:f Y\Z:g => X\Z: λx􏰓.fx􏰨(g􏰨(x􏰩􏰩))
        d = fn.substitute(arg)
        c[0] = d
        self._compList = c
        self.set_lambda_refs(d.lambda_refs)
        self.set_category(d.category)
        return self

    def substitute_backward(self):
        """Backward substitution and backward crossing substitution.

        Remarks:
            Executes a single production rule.
        """
        assert len(self._compList) >= 2
        fn = self._compList[-1]
        arg = self._compList[-2]
        c = self._compList[0:-1]
        # CALL[(X\Y)|Z](Y|Z)
        # Backward Substitution             Y\Z:g (X\Y)\Z:g => X/Z: λx􏰓.fx􏰨(g􏰨(x􏰩􏰩))
        # Backward Crossing Substitution    Y/Z:g (X\Y)/Z:f => X/Z: λx􏰓.fx􏰨(g􏰨(x􏰩􏰩))
        d = fn.substitute(arg)
        c[-1] = d
        self._compList = c
        self.set_lambda_refs(d.lambda_refs)
        self.set_category(d.category)
        return self

    def conjoin_forward(self):
        """Forward conjoin of like types."""
        if len(self._compList) <= 1:
            return
        f = self._compList[0]
        g = self._compList[1]
        c = self._compList[1:]
        if f.isfunctor:
            d = f.conjoin(g, False)
            c[0] = d
            self._compList = c
            self.set_lambda_refs(d.lambda_refs)
            self.set_category(d.category)
        elif g.isfunctor:
            d = g.conjoin(f, True)
            c[0] = d
            self._compList = c
            self.set_lambda_refs(d.lambda_refs)
            self.set_category(d.category)
        else:
            d = ProductionList(f, dep=self.dep)
            d.push_right(g)
            d = d.unify()
            c[0] = d
            self.set_category(f.category)
        return self

    def conjoin_backward(self):
        """Backward conjoin of like types."""
        if len(self._compList) <= 1:
            return
        g = self._compList.pop()
        f = self._compList.pop()
        c = self._compList
        if f.isfunctor:
            d = f.conjoin(g, False)
            c.append(d)
            self._compList = c
            self.set_lambda_refs(d.lambda_refs)
            self.set_category(d.category)
        elif g.isfunctor:
            d = g.conjoin(f, True)
            c.append(d)
            self._compList = c
            self.set_lambda_refs(d.lambda_refs)
            self.set_category(d.category)
        else:
            d = ProductionList(f, dep=self.dep)
            d.push_right(g)
            c.append(d.unify())
            self.set_category(f.category)
        return self

    def special_type_change(self, rule):
        """Special type change rules. See section 3.7-3.8 of LDC 2005T13 manual. These rules are required
        to process the CCG conversion of the Penn Treebank. They are not required for EasySRL or EasyCCG.

        Args:
            rule: A Rule instance.

        Remarks:
            Executes a single production rule.
        """
        assert len(self._compList) >= 2
        template = self._compList.pop()
        vp_or_np = self._compList[-1]
        c = self._compList
        if rule == RL_TC_CONJ:
            # Section 3.7.2
            d = template.type_change_np_snp(vp_or_np)
        else:
            assert False
        c[-1] = d
        self._compList = c
        self.set_lambda_refs(d.lambda_refs)
        self.set_category(d.category)
        return self

    def type_raise(self):
        """Type raising.

        Remarks:
            Executes a single production rule.
        """
        assert len(self._compList) >= 2
        template = self._compList.pop()
        np = self._compList[-1]
        c = self._compList
        d = template.type_raise(np)
        c[-1] = d
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
            self.compose_forward(False)
        elif rule in [RL_BC, RL_BX]:
            self.compose_backward(False)
        elif rule == RL_LCONJ:
            self.conjoin_backward()
        elif rule == RL_RCONJ:
            self.conjoin_forward()
        elif rule == RL_TC_CONJ:
            self.special_type_change(rule)
        elif rule == RL_TYPE_RAISE:
            self.type_raise()
        elif rule in [RL_FS, RL_FXS]:
            self.substitute_forward()
        elif rule in [RL_BS, RL_BXS]:
            self.substitute_backward()
        elif rule in [RL_GFC, RL_GFX]:
            self.compose_forward(True)
        elif rule in [RL_GBC, RL_GBX]:
            self.compose_backward(True)
        else:
            # TODO: handle all rules
            raise NotImplementedError

        if len(self._compList) == 0:
            return self

        if len(self._compList) == 1:
            d = self._compList[0]
            self._compList = []
            if d.isfunctor:
                if d.get_scope_count() != d.category.get_scope_count():
                    pass
                if d.get_scope_count() != self.category.get_scope_count():
                    pass
                d.inner_scope.set_category(self.category)
            else:
                if d.get_scope_count() != self.category.get_scope_count():
                    pass
                d.set_category(self.category)
            return d
        return self


class FunctorProduction(Production):
    """A functor production. Functors are curried where the inner most functor is the inner scope."""
    def __init__(self, category, referent, production=None, dep=None):
        """Constructor.

        Args:
            category: A marbles.ie.drt.ccgcat.Category instance.
            referent: Either a list of, or a single, marbles.ie.drt.drs.DRSRef instance.
            production: Optionally a marbles.ie.drt.drs.DRS instance or a Production instance. The DRS will be converted
                to a DrsProduction. If production is a functor then the combination is a curried functor.
        """
        if production is not None:
            if isinstance(production, AbstractDRS):
                production = DrsProduction(production, )
            elif not isinstance(production, Production):
                raise TypeError('production argument must be a Production type')
        if category is None :
            raise TypeError('category cannot be None for functors')
        if dep is None and production is not None:
            dep = production.dep
        super(FunctorProduction, self).__init__(category, dep)
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
        s = 'λ' + chr(i)
        if self._comp is not None and self._comp.isfunctor:
            s = self._comp._repr_helper1(i+1) + s
        return s

    def _repr_helper2(self, i):
        v = chr(i)
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
               + '.(' + self._repr_helper2(ord('P')) + ')'

    def _get_variables(self, u):
        if self._comp is not None:
            if self._comp.isfunctor:
                u = self._comp._get_variables(u)
            else:
                u = u.union(self._comp.variables)
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
        u = self._get_variables(set(self.lambda_refs))
        return sorted(u)

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

    def set_dependency(self, dep):
        """Set the dependency"""
        if self._comp is not None:
            self._dep = dep
            return self._comp.set_dependency(dep)

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
                if len(c.lambda_refs) > 1:
                    pass
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
        self._category = cat
        # sanity check

        # FIXME: This check can fail for rules FX, FC, BX, BC. At the moment we dont use this method for those rules.
        if (cat.isarg_left and prev.isarg_right) or (cat.isarg_right and prev.isarg_left):
            raise DrsComposeError('Signature %s does not match %s argument position, prev was %s' %
                                 (cat, 'right' if prev.isarg_right else 'left', prev))

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
        self.rename_lambda_refs(rs)
        if self._comp is not None:
            self._comp.rename_vars(rs)

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
            A Production instance.
        """
        # TODO: Check if we have a proper noun accessible to the right and left
        if self.isarg_right or self._comp is None or self._comp.isfunctor:
            raise DrsComposeError('invalid apply null left to functor')
        if self._comp is not None and isinstance(self._comp, ProductionList):
            self._comp = self._comp.apply()
        d = DrsProduction(drs=DRS(self._lambda_refs.universe, []), category=CAT_NP)
        d = self.apply(d)
        return d

    def pop(self, level=-1):
        """Remove an inner functor and return the production.

        Args:
            level: Level relative to outer less 1. If -1 then pop the inner scope.

        Returns:
            A Production instance.

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
            nrs = get_new_drsrefs(ors, union(ers, ers2))
            xrs = self.nodups(zip(ors, nrs))
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
        if not isinstance(np, DrsProduction):
            pass
        assert isinstance(np, DrsProduction)
        lr = np.lambda_refs
        if len(lr) == 0:
            lr = np.drs.universe
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

    def type_raise(self, np):
        """Special type change. See LDC manual section 3.7.2.

        Args:
            np: The noun phrase. Must be a NP category.

        Remarks:
            self is a template. The inner DrsProduction will be discarded.
        """
        ## Forward   X:np => T/(T\X): λxf.f(np)
        ## Backward  X:np => T\(T/X): λxf.f(np)
        self.make_vars_disjoint(np)
        slr = self.inner_scope._comp.lambda_refs
        assert isinstance(np, DrsProduction)
        assert not np.isfunctor
        lr = np.lambda_refs
        if len(lr) == 0:
            lr = np.universe
            np.set_lambda_refs(lr)
        if len(lr) != 1:
            # Add proposition
            p = PropProduction(category=np.category, referent=slr[0])
            np = p.apply(np)
        else:
            rs = zip(slr, lr)
            self.rename_vars(rs)

        fc = self.pop()
        np.set_lambda_refs(fc.lambda_refs)
        np.set_category(self.category.extract_unify_atoms(False)[-1])
        self.push(np)
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
            raise DrsComposeError('composition argument must be a functor')
        assert g.outer is None  # must be outer scope

        # Create a new category
        cat = Category.combine(self.category.result_category, g.category.slash, g.category.argument_category)

        # Rename so f names are disjoint with g names.
        # Try to keep var subscripts increasing left to right.
        if self.isarg_left:
            self.outer_scope.make_vars_disjoint(g)
        else:
            g.make_vars_disjoint(self.outer_scope)

        # Get scopes before we modify f and g
        fv = self.category.argument_category.extract_unify_atoms(False)
        gv = g.category.result_category.extract_unify_atoms(False)

        fc = self.pop()
        assert fc is not None
        yflr = self.inner_scope.get_unify_scopes(False)

        # Get lambdas
        gc = g.pop()
        zg = g.pop()
        if zg is None:
            # Y is an atom (i.e. Y=gc) and functor scope is exhausted
            assert g.category.result_category.isatom
            zg = g
            glr = gc.lambda_refs
        else:
            # Get Y unification lambdas
            g.push(gc)
            glr = g.get_unify_scopes(False)
            g.pop()
            assert gc is not None
        zg._category = cat

        if len(yflr) != len(glr):
            pass
        assert len(yflr) == len(glr)

        # Set Y unification
        assert len(fv) == len(gv)
        assert len(fv) == len(yflr)
        uy = map(lambda x: (x[2], x[3]), filter(lambda x: x[0].can_unify_atom(x[1]),
                                                zip(gv, fv, yflr, glr)))
        # Unify
        assert len(uy) != 0
        fc.rename_vars(uy)

        # Build
        pl = ProductionList(dep=self.dep)
        pl.set_category(fc.category)
        pl.set_lambda_refs(fc.lambda_refs)
        pl.push_right(fc)
        pl.push_right(gc)
        pl = pl.unify()
        assert isinstance(pl, DrsProduction)
        zg.push(pl)
        # Handle atomic X. If X is an atomic type next push() fails because the functor scope
        # is exhausted after this pop()
        fy = self.pop()
        if fy is None:
            # X is atomic
            assert self.category.result_category.isatom
            return zg
        self.push(zg)
        return self

    def generalized_compose(self, g):
        """Generalized function Composition.

        Arg:
            g: The (Y|Z)$ functor where self (f) is the X|Y functor.

        Returns:
            A Production instance.

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
        resultcat = Category.combine(self.category.result_category, g.category.result_category.slash,
                                     g.category.result_category.argument_category)
        cat = Category.combine(resultcat, g.category.slash, g.category.argument_category)

        # Rename so f names are disjoint with g names.
        # Try to keep var subscripts increasing left to right.
        if self.isarg_left:
            self.outer_scope.make_vars_disjoint(g)
        else:
            g.make_vars_disjoint(self.outer_scope)

        # Get scopes before we modify f and g
        fv = self.category.argument_category.extract_unify_atoms(False)
        gv = g.category.result_category.result_category.extract_unify_atoms(False)

        # Get lambdas
        gc = g.pop()
        assert gc is not None
        dollar = g.pop()
        dollar._category = cat
        zg = g.pop()
        if zg is None:
            # Y is an atom (i.e. Y=gc) and functor scope is exhausted
            assert g.category.result_category.isatom
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

        if len(yflr) != len(glr):
            pass
        assert len(yflr) == len(glr)

        # Set Y unification
        assert len(fv) == len(gv)
        assert len(fv) == len(yflr)
        uy = map(lambda x: (x[2], x[3]), filter(lambda x: x[0].can_unify_atom(x[1]),
                                                zip(gv, fv, yflr, glr)))
        # Unify
        assert len(uy) != 0
        fc.rename_vars(uy)

        # Build
        pl = ProductionList(dep=self.dep)
        pl.set_category(fc.category)
        pl.set_lambda_refs(fc.lambda_refs)
        pl.push_right(fc)   # first entry sets lambdas
        pl.push_right(gc)
        pl = pl.unify()
        assert isinstance(pl, DrsProduction)
        dollar.push(pl)
        zg.push(dollar)

        # Handle atomic X. If X is an atomic type next push() fails because the functor scope
        # is exhausted after this pop()
        fy = self.pop()
        if fy is None:
            # X is atomic
            assert self.category.result_category.isatom
            return zg
        self.push(zg)
        return self

    def substitute(self, g):
        """Functional Substitution.

        Arg:
            g: The Y|Z functor where self (f) is the (X|Y)|Z functor.

        Returns:
            A Production instance.

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
        cat = Category.combine(self.category.result_category.result_category, self.category.slash,
                               g.category.argument_category)

        # Rename so f names are disjoint with g names.
        # Try to keep var subscripts increasing left to right.
        if self.category.result_category.isarg_right:
            self.outer_scope.make_vars_disjoint(g)
        else:
            g.make_vars_disjoint(self.outer_scope)

        # Get scopes before we modify f and g
        fv = self.category.argument_category.extract_unify_atoms(False)
        gv = g.category.result_category.extract_unify_atoms(False)

        # Get lambdas
        gc = g.pop()
        zg = g.pop()
        if zg is None:
            # Y is an atom (i.e. Y=gc) and functor scope is exhausted
            assert g.category.result_category.isatom
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
        if len(yflr) != len(glr):
            pass
        assert len(yflr) == len(glr)

        # Set Y unification
        assert len(fv) == len(gv)
        assert len(fv) == len(yflr)
        uy = map(lambda x: (x[2], x[3]), filter(lambda x: x[0].can_unify_atom(x[1]),
                                                zip(gv, fv, yflr, glr)))
        # Unify
        assert len(uy) != 0
        self.rename_vars(uy)
        self.pop()

        # Build
        pl = ProductionList(dep=self.dep)
        pl.set_category(fc.category)
        pl.set_lambda_refs(fc.lambda_refs)
        pl.push_right(fc)   # first in list sets lambdas
        pl.push_right(gc)
        pl = pl.unify()
        assert isinstance(pl, DrsProduction)
        zg.push(pl)
        # Handle atomic X. If X is an atomic type next push() fails because the functor scope
        # is exhausted after this pop()
        yf = self.pop()
        if yf is None:
            # X is atomic
            assert self.category.result_category.isatom
            return zg
        self.push(zg)
        return self

    def conjoin(self, g, glambdas):
        """Conjoin Composition.

        Arg:
            g: The X2|Y2 functor where self (f) is the X1|Y1 functor.
            glambdas: If True set lambda from g, else set from self.

        Returns:
            A Production instance.

        Remarks:
            CALL[X1|Y1](X2|Y2)
        """
        assert self.outer is None
        if g.category.simplify() != self.category.simplify():
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

            c = ProductionList(fc, dep=self.dep)
            c.push_right(gc)
            c.set_lambda_refs(glr if glambdas else flr)
            c.set_category(gc.category if glambdas else fc.category)
            self.push(c.unify())
        else:
            # Rename f so disjoint with g names
            self.make_vars_disjoint(g)
            glr = g.lambda_refs
            g.set_lambda_refs([])
            fc = self.pop()
            flr = fc.lambda_refs
            c = ProductionList(fc, dep=self.dep)
            c.push_right(g)
            if glambdas and len(glr) != len(flr):
                # FIXME: A Production should always have lambda_refs set.
                c.set_lambda_refs(flr)
                c.set_category(fc.category)
            else:
                c.set_lambda_refs(glr if glambdas else flr)
            c.set_category(fc.category)
            self.push(c.unify())

        return self

    def apply(self, g):
        """Function application.

        Arg:
            g: The application argument.

        Returns:
            A Production instance.
        """
        if self._comp is not None and self._comp.isfunctor:
            self._comp = self._comp.apply(g)
            if self._comp.isfunctor:
                self._comp._set_outer(self)
            return self

        assert self._comp is not None

        if 0 != (self.compose_options & CO_PRINT_DERIVATION):
            print('DERIVATION:= %s {%s=%s}' % (repr(self.outer_scope), chr(ord('P')+self._get_position()), repr(g)))

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
            fs = self.category.argument_category.extract_unify_atoms(False)
            gs = g.category.extract_unify_atoms(False)
            if gs is None or fs is None:
                pass
            assert fs is not None
            assert gs is not None and len(gs) == len(fs)

            rs = map(lambda x: (x[2], x[3]), filter(lambda x: x[0].can_unify_atom(x[1]),
                                                    zip(fs, gs, glr, flr)))
            # Unify
            g.rename_vars(self.nodups(rs))

        ors = intersect(g.universe, self.universe)
        if len(ors) != 0:
            # FIXME: Partial unification requires at least one variable
            #if len(rs) == len(ors):
            #    raise DrsComposeError('unification not possible')
            ers = union(g.variables, self.outer_scope.variables)
            nrs = get_new_drsrefs(ors, ers)
            g.rename_vars(zip(ors, nrs))

        if g.isfunctor:
            assert g.inner_scope._comp is not None
            # functor production
            cl = ProductionList(dep=self.dep)
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
            return cl.unify()

        # Remove resolved referents from lambda refs list
        assert len(self._lambda_refs.referents) != 0
        if isinstance(self._comp, ProductionList):
            c = self._comp
        else:
            c = ProductionList(self._comp, dep=self.dep)

        if self.isarg_right:
            c.push_right(g)
        else:
            c.push_left(g)

        lr = self._comp.lambda_refs
        c.set_options(self.compose_options)
        c = c.unify()
        c.set_lambda_refs(lr)
        c.set_category(self._comp.category)
        self.clear()

        if 0 != (self.compose_options & CO_PRINT_DERIVATION):
            print('          := %s' % repr(c))

        return c


class PropProduction(FunctorProduction):
    """A proposition functor."""
    def __init__(self, category, referent, production=None, dep=None):
        super(PropProduction, self).__init__(category, referent, production, dep)

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
        if not isinstance(d, DrsProduction):
            pass
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
        dd = DrsProduction(DRS(lr, [Prop(self._lambda_refs.referents[0], d.drs)]), )
        dd.set_options(self.compose_options)
        self.clear()
        dd.set_lambda_refs(lr)
        dd.set_category(self.category.result_category)
        if 0 != (self.compose_options & CO_PRINT_DERIVATION):
            print('          := %s' % repr(dd))
        return dd


class OrProduction(FunctorProduction):
    """An Or functor."""
    def __init__(self, negate=False, dep=None):
        super(OrProduction, self).__init__(CAT_CONJ, [], dep=dep)
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
            c = ProductionList(arg, dep=self.dep)
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
        cl = ProductionList(dep=self.dep)
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
