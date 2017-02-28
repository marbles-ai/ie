# -*- coding: utf-8 -*-

from drs import DRS, DRSRef, Merge, Prop, Imp, Rel, Neg, Box, Diamond, Or
from drs import get_new_drsrefs
from utils import iterable_type_check, intersect, union, union_inplace, complement, compare_lists_eq, rename_var, \
    remove_dups
from common import SHOW_LINEAR
import collections, re
from parse import parse_drs, parse_ccgtype
import weakref

## @{
## @ingroup gconst
## @defgroup CCG to DRS Constants

## Compose option
CO_REMOVE_UNARY_PROPS = 0x1
CO_PRINT_DERIVATION = 0x2

## Function argument position
ArgRight = True

## Function argument position
ArgLeft  = False
## @}


class DrsComposeError(Exception):
    """Drs Composition Error."""
    pass


class Composition(object):
    """An abstract composition."""
    def __init__(self):
        self._lambda_refs = DRS([],[])
        self._options = 0

    def __eq__(self, other):
        return id(self) == id(other)

    @property
    def signature(self):
        """The drs type signature."""
        return 'T'

    @property
    def isempty(self):
        """Test if the composition is an empty."""
        return False

    @property
    def isfunction(self):
        """Test if this class is a function composition."""
        return False

    @property
    def iscombinator(self):
        """Test if this class is a function combinator. A combinator expects a functions as the argument."""
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
        """Get the DRS conditions for this composition."""
        return []

    @property
    def compose_options(self):
        """Get the compose options."""
        return self._options

    @property
    def isproper_noun(self):
        """Test if the composition resolved to a proper noun"""
        return False

    @property
    def iterator(self):
        """If a list then iterate the compositions in the list else return self."""
        yield self

    @property
    def size(self):
        """If a list then get the number of elements in the composition list else return 1."""
        return 1

    @property
    def contains_function(self):
        """If a list then return true if the list contains 1 or more functions, else returns isfunction()."""
        return self.isfunction

    def set_options(self, options):
        """Set the compose opions.

        Args:
            options: The compose options.
        """
        self._options = int(options)

    def set_lambda_refs(self, refs):
        """Set the lambda referents for this composition.

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
        """Perform alpha conversion on the composition data.

        Args:
            rs: A list of tuples, (old_name, new_name).
        """
        raise NotImplementedError


class DrsComposition(Composition):
    """A DRS composition."""
    def __init__(self, drs, properNoun=False):
        """Constructor.

        Args:
            drs: A marbles.ie.drt.DRS instance.
            properNoun: True is a proper noun.
        """
        super(DrsComposition, self).__init__()
        if not isinstance(drs, DRS):
            raise TypeError
        self._drs = drs
        self._nnp = properNoun

    def __repr__(self):
        #refs = self.lambda_refs
        #if len(refs) != 0:
        #    return ''.join(['λ'+v.var.to_string() for v in self.lambda_refs]) + '.' + self.drs.show(SHOW_LINEAR).encode('utf-8')
        return self.drs.show(SHOW_LINEAR).encode('utf-8')

    def __str__(self):
        return self.__repr__()

    @property
    def signature(self):
        """The drs type signature."""
        if len(self._drs.referents) == 1 and len(self._drs.conditions) == 1 and \
                isinstance(self._drs.conditions[0], Prop):
            return 'Z'
        return 'T'

    @property
    def lambda_refs(self):
        """Get the lambda function referents"""
        # For DRS we treat None as a special case meaning infer from DRS. This may not be always the best
        # policy so in the code we prefer to explicitly set which refs can be resolved during a merge
        if self._lambda_refs is None:
            r = self._drs.freerefs
            r.extend(self._drs.universe)
            return r
        return self._lambda_refs.universe

    @property
    def isproper_noun(self):
        """Test if the composition resolved to a proper noun"""
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
        """Test if the composition is an empty DRS."""
        return self._drs.isempty

    @property
    def conditions(self):
        """Get the DRS conditions for this composition."""
        return self._drs.conditions

    @property
    def drs(self):
        """Get the DRS data attached to this composition."""
        return self._drs

    def rename_vars(self, rs):
        """Perform alpha conversion on the composition data.

        Args:
            rs: A list of tuples, (old_name, new_name).
        """
        self._drs = self._drs.alpha_convert(rs)
        self._drs = self._drs.substitute(rs)
        self.rename_lambda_refs(rs)


class CompositionList(Composition):
    """A list of compositions."""
    def __init__(self, compList=None):
        super(CompositionList, self).__init__()
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
        return '<' + '##'.join([repr(x) for x in self._compList]) + '>'
        #lr = self.lambda_refs
        #if len(lr) == 0:
        #    return '<' + '#'.join([repr(x) for x in self._compList]) + '>'
        #return  ''.join(['λ'+v.var.to_string() for v in lr]) + '.<' + '#'.join([repr(x) for x in self._compList]) + '>'

    @property
    def isproper_noun(self):
        """Test if the composition resolved to a proper noun"""
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
        """Test if the composition is an empty DRS."""
        return len(self._compList) == 0

    @property
    def iterator(self):
        """Iterate the compositions in this list."""
        for c in self._compList:
            yield c

    @property
    def size(self):
        """Get the number of elements in this composition list."""
        return len(self._compList)

    @property
    def contains_function(self):
        for c in self._compList:
            if c.isfuncion:
                return True
        return False

    def clone(self):
        cl = CompositionList([x for x in self._compList])
        cl.set_options(self.compose_options)
        cl.set_lambda_refs(self.lambda_refs)
        return cl

    def flatten(self):
        """Merge subordinate CompositionList's into the current list."""
        compList = []
        for d in self._compList:
            if d.isempty:
                continue
            if isinstance(d, CompositionList):
                d = d.apply()
                if isinstance(d, CompositionList):
                    compList.extend(d._compList)
                else:
                    compList.append(d)
                #if len(d.freerefs) != 0 or len(d.universe) == 0:
                #    raise DrsComposeError('fl
            else:
                compList.append(d)
        self._compList = compList

    def rename_vars(self, rs):
        """Perform alpha conversion on the composition data.

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
            merge: True if other is a CompositionList instance and you want to
            merge lists (like extend). If False other is added as is (like append).

        Returns:
            The self instance.
        """
        if isinstance(other, DRS):
            other = DrsComposition(other)
        if merge and isinstance(other, CompositionList):
            self._compList.extend(other._compList)
        else:
            other.set_options(self.compose_options)
            self._compList.append(other)
        return self

    def push_left(self, other, merge=False):
        """Push an argument to the left of the list.

        Args:
            other: The argument to push.
            merge: True if other is a CompositionList instance and you want to
            merge lists (like extend). If False other is added as is (like append).

        Returns:
            The self instance.
        """
        if isinstance(other, DRS):
            other = DrsComposition(other)
        if merge and isinstance(other, CompositionList):
            compList = [x for x in other._compList]
            compList.extend(self._compList)
            self._compList = compList
        else:
            other.set_options(self.compose_options)
            compList = [other]
            compList.extend(self._compList)
            self._compList = compList
        return self

    def apply(self):
        """Applies all functions, runs merge, and returns a DrsComposition instance.

        Returns:
            A DrsComposition instance.
        """
        if len(self._compList) == 0:
            return None

        # alpha convert variables
        self.flatten()
        rstk = self._compList
        rstk.reverse()
        lstk = []
        self._compList = []
        # First process function composition left to right
        while len(rstk) != 0:
            d = rstk[-1]
            rstk.pop()
            if d.iscombinator:
                if d.isarg_right:
                    if len(rstk) == 0:
                        if len(lstk) != 0:
                            raise DrsComposeError('Combinator "%s" missing right argument' % repr(d))
                        return d
                    elif not d.isfunction:
                        raise DrsComposeError('Combinator "%s" expected right function argument' % repr(d))
                    d = d.apply(rstk[-1])
                    rstk.pop()
                    rstk.append(d)
                else:
                    if len(lstk) == 0:
                        if len(rstk) != 0:
                            raise DrsComposeError('Combinator "%s" missing left argument' % repr(d))
                        return d
                    elif not d.isfunction:
                        raise DrsComposeError('Combinator "%s" expected left function argument' % repr(d))
                    d = d.apply(lstk[-1])
                    lstk.pop()
                    rstk.append(d)
            else:
                lstk.append(d)

        # Now process function application right to left
        while len(lstk) != 0:
            d = lstk[-1]
            lstk.pop()
            if isinstance(d, FunctionComposition):
                if d.isarg_right:
                    if len(rstk) == 0:
                        if len(lstk) != 0:
                            raise DrsComposeError('Function "%s" missing right argument' % repr(d))
                        return d
                    d = d.apply(rstk[-1])
                    rstk.pop()
                    lstk.append(d)
                else:
                    if len(lstk) == 0:
                        if len(rstk) != 0:
                            raise DrsComposeError('Function "%s" missing left argument' % repr(d))
                        return d
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

        universe = []
        for i in range(len(rstk)):
            d = rstk[i]
            rn = intersect(d.universe, universe)
            if len(rn) != 0:
                # FIXME: should this be allowed?
                # Alpha convert bound vars in both self and arg
                xrs = zip(rn, get_new_drsrefs(rn, universe))
                d.rename_vars(xrs)
                for j in range(i+1,len(rstk)):
                    rstk[j].rename_vars(xrs)
            universe = union(universe, d.universe)

        universe = set(universe)
        lambda_refs = filter(lambda x: x in universe, self.lambda_refs)

        refs = []
        conds = []
        proper = len(rstk) != 0
        for d in reversed(rstk):
            proper = proper and d.isproper_noun
            refs.extend(d.drs.referents)
            conds.extend(d.drs.conditions)
        if proper:
            # Hyphenate name
            if len(refs) != 1 or any(filter(lambda x: not isinstance(x, Rel) or len(x.referents) != 1, conds)):
                raise DrsComposeError('bad proper noun in DRS condition')
            name = '-'.join([c.relation.to_string() for c in conds])
            conds = [Rel(name,refs)]
        lambda_refs = rstk[0].lambda_refs if len(rstk) != 0 else []
        drs = DRS(refs, conds).purify()
        if not drs.ispure:
            raise DrsComposeError('intermediate result has free referents - %s', drs.show(SHOW_LINEAR).encode('utf-8'))
        d = DrsComposition(drs, proper)
        if len(lambda_refs) != 0:
            d.set_lambda_refs(lambda_refs)
        return d


class FunctionComposition(Composition):
    """A function composition. All functions are curried."""
    def __init__(self, position, referent, composition=None):
        super(FunctionComposition, self).__init__()
        if composition is not None:
            if isinstance(composition, (DRS, Merge)):
                composition = DrsComposition(composition)
            elif not isinstance(composition, Composition):
                raise TypeError('Function argument must be a Composition type')
        self._signature = 'T'
        self._comp = composition
        self._pos = position or False
        if isinstance(referent, list):
            self._drsref = DRS(referent, [])
        else:
            self._drsref = DRS([referent], [])
        self._outer = None
        if self._comp is not None:
            if isinstance(self._comp, FunctionComposition):
                self._comp.set_outer(self)
            #else:   # Only set once we apply()
            #    self._comp.set_lambda_refs([])

    def set_outer(self, outer):
        if outer is not None:
            self._outer = weakref.ref(outer)
        else:
            self._outer = None

    def _repr_helper1(self, i):
        s = 'λ' + chr(i)
        if self._comp is not None and self._comp.isfunction:
            s = self._comp._repr_helper1(i+1) + s
        return s

    def _repr_helper2(self, i):
        v = chr(i)
        r = ','.join([x.var.to_string() for x in self._drsref.referents])
        if self._comp is not None:
            if self._comp.isfunction:
                s = self._comp._repr_helper2(i+1)
            else:
                s = str(self._comp)
            if self._pos:
                return '%s;%s(%s)' % (s, v, r)
            else:
                return '%s(%s);%s' % (v, r, s)
        else:
            return '%s(%s)' % (v, r)

    def __repr__(self):
        return self._repr_helper1(ord('P')) + ''.join(['λ'+v.var.to_string() for v in self.lambda_refs]) + \
               '.' + self._repr_helper2(ord('P'))

    def __str__(self):
        return self.__repr__()

    def _get_freerefs(self, u):
        if self._comp is not None:
            if self._comp.isfunction:
                u = self._comp._get_freerefs(u)
            else:
                u = union_inplace(u, self._comp.freerefs)
        return u

    def _get_universe(self, u):
        if self._comp is not None:
            if self._comp.isfunction:
                u = self._comp._get_universe(u)
            else:
                u = union_inplace(u, self._comp.universe)
        return u

    def _get_lambda_refs(self, u):
        # Get lambda vars ordered by function scope
        u.extend(self._drsref.referents)
        if self._comp is not None:
            if self._comp.isfunction:
                u.extend(self._comp._get_lambda_refs(u))
            else:
                u.extend(self._comp.lambda_refs)
        return u

    def _get_position(self):
        # Get position in function scope
        g = self
        i = 0
        while g.outer is not None:
            g = g.outer
            i += 1
        return i

    @property
    def local_lambda_refs(self):
        return self._drsref.universe

    @property
    def signature(self):
        return self._signature

    @property
    def global_scope(self):
        """Get the outer most function in this composition or self."""
        g = self
        while g.outer is not None:
            g = g.outer
        return g

    @property
    def outer(self):
        """The outer function or None."""
        return None if self._outer is None else self._outer() # weak deref

    @property
    def isempty(self):
        """Test if the composition is an empty DRS."""
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
        # Get unique referents, ordered by function scope
        # Reverse because we can have args [(x,e), (y,e), e] =>[x,e,y,e,e] => [x,y,e]
        r = self._get_lambda_refs([])
        r.reverse()
        r = remove_dups(r)
        r.reverse()
        return r

    @property
    def isarg_right(self):
        """Test if the function takes a right argument."""
        if self._comp is not None and self._comp.isfunction:
            return self._comp.isarg_right
        return self._pos

    @property
    def isarg_left(self):
        """Test if the function takes a left argument."""
        return not self.isarg_right

    @property
    def isfunction(self):
        """Test if this class is a function composition. Always True for FunctionComposition instances."""
        return True

    @property
    def iscombinator(self):
        """A combinator expects a function as the argument and returns a function."""
        s = self.signature
        return s[-1] == ')' and s[0] == '('

    def set_signature(self, sig):
        """Set the DRS category."""
        self._signature = sig

    def set_options(self, options):
        """Set the compose options.

        Args:
            options: The compose options.
        """
        # Pass down options to nested function
        super(FunctionComposition, self).set_options(options)
        if self._comp is not None:
            self._comp.set_options(options)

    def rename_vars(self, rs):
        """Perform alpha conversion on the composition data.

        Args:
            rs: A list of tuples, (old_name, new_name).
        """
        self._drsref = self._drsref.alpha_convert(rs)
        if self._comp is not None:
            self._comp.rename_vars(rs)

    def apply_null_left(self):
        """Apply a null left argument `$` to the function. This is necessary for processing
        the imperative form of a verb.

        Returns:
            A Composition instance.
        """
        # TODO: Check if we have a proper noun accessible to the right and left
        if self.isarg_right or self._comp is None or self._comp.isfunction:
            raise DrsComposeError('invalid apply null left to function')
        if self._comp is not None and isinstance(self._comp, CompositionList):
            self._comp = self._comp.apply()
        d = DrsComposition(DRS(self._drsref.universe, []))
        d = self.apply(d)
        return d

    def clear(self):
        self._comp = None
        self._drsref = DRS([], [])
        self.set_outer(None)

    def apply(self, arg):
        """Function application if arg is a DrsComposition or CompositionList. Otherwise function composition.

        Arg:
            The substitution argument.

        Returns:
            A Composition instance.
        """
        if self._comp is not None and self._comp.isfunction:
            self._comp = self._comp.apply(arg)
            if self._comp.isfunction:
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
        if len(sllr) == 1 and len(alr) != 1 and not arg.isfunction:
            # Add proposition
            p = PropComposition(ArgRight, slr[0])
            arg = p.apply(arg)
            alr = arg.lambda_refs

        if self.iscombinator:
            rs = zip(slr, alr)
            # Make sure names don't conflict with global scope
            ors = intersect(alr[len(rs):], complement(self.global_scope.lambda_refs, slr))
            if len(ors) != 0:
                xrs = zip(ors, get_new_drsrefs(ors, union(alr, slr)))
                self.rename_vars(xrs)
            self.rename_vars(rs)
        else:
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

        if arg.isfunction:
            # function composition
            arg.set_options(self.compose_options)
            if self._comp is not None:
                if arg._comp is None:
                    arg._comp = self._comp
                elif self.isarg_left and arg.isarg_left or \
                        (self.iscombinator and self.iscombinator and self.isarg_right and arg.isarg_left):
                    if isinstance(arg._comp, CompositionList):
                        arg._comp.push_right(self._comp, merge=True)
                    elif isinstance(self._comp, CompositionList):
                        self._comp.push_left(arg._comp, merge=True)
                        arg._comp = self._comp
                    else:
                        cl = CompositionList(arg._comp)
                        cl.set_options(self.compose_options)
                        cl.push_right(self._comp)
                        arg._comp = cl
                elif self.isarg_right and arg.isarg_right or \
                        (self.iscombinator and self.iscombinator and self.isarg_left and arg.isarg_right):
                    if isinstance(arg._comp, CompositionList):
                        arg._comp.push_left(self._comp, merge=True)
                    elif isinstance(self._comp, CompositionList):
                        self._comp.push_right(arg._comp, merge=True)
                        arg._comp = self._comp
                    else:
                        cl = CompositionList(self._comp)
                        cl.set_options(self.compose_options)
                        cl.push_right(arg._comp)
                        arg._comp = cl
                else:
                    raise DrsComposeError('Function composition requires same argument ordering')
            arg.global_scope.set_outer(self.outer)
            self.clear()
            if 0 != (self.compose_options & CO_PRINT_DERIVATION):
                print('          := %s' % repr(arg.global_scope))
            return arg

        # function application
        if self._comp is not None and arg.contains_function:
            raise DrsComposeError('Invalid function placement during function application')

        # Remove resolved referents from lambda refs list
        lr = complement(self.lambda_refs, self.local_lambda_refs)
        if self._comp is None:
            arg.set_options(self.compose_options)
            self.clear()
            arg.set_lambda_refs(lr)
            return arg
        elif isinstance(self._comp, CompositionList):
            c = self._comp
        else:
            c = CompositionList(self._comp)

        if self.isarg_right:
            c.push_right(arg)
        else:
            c.push_left(arg)

        c.set_options(self.compose_options)
        c = c.apply()
        c.set_lambda_refs(lr)
        self.clear()

        if 0 != (self.compose_options & CO_PRINT_DERIVATION):
            print('          := %s' % repr(c))

        return c


class PropComposition(FunctionComposition):
    """A proposition function."""
    def __init__(self, position, referent, composition=None):
        super(PropComposition, self).__init__(position, referent)

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
        raise DrsComposeError('cannot apply null left to a proposition function')

    def apply(self, arg):
        """Function application.

        Arg:
            The substitution argument.

        Returns:
            A Composition instance.
        """
        if self._comp is not None and self._comp.isfunction:
            self._comp = self._comp.apply(arg)
            if self._comp.isfunction:
                self._comp.set_outer(self)
            return self

        if 0 != (self.compose_options & CO_PRINT_DERIVATION):
            print('DERIVATION:= %s {%s=%s}' % (repr(self.global_scope), chr(ord('P')+self._get_position()), repr(arg)))
        if not isinstance(arg, CompositionList):
            arg = CompositionList([arg])
        d = arg.apply()
        assert isinstance(d, DrsComposition)
        # FIXME: removing proposition from a proper noun causes an exception during CompositionList.apply()
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
        dd = DrsComposition(DRS(self._drsref.referents, [Prop(self._drsref.referents[0], d.drs)]))
        dd.set_options(self.compose_options)
        g = self.global_scope
        self.clear()
        dd.set_lambda_refs(g.lambda_refs)
        if 0 != (self.compose_options & CO_PRINT_DERIVATION):
            print('          := %s' % repr(dd))
        return dd


## @cond
__pron = [
    # 1st person singular
    ('i',       '([x],[([],[i(x)])->([],[me(x)])])'),
    ('me',      '([x],[me(x)])'),
    ('myself',  '([x],[([],[myself(x)])->([],[me(x)])])'),
    ('mine',    '([],[([],[mine(x)])->([y],[me(y),owns(y,x)])])'),
    ('my',      '([],[([],[my(x)])->([y],[me(y),owns(y,x)])])'),
    # 2nd person singular
    ('you',     '([x],[you(x)])'),
    ('yourself','([x],[([],[yourself(x)])->([],[you(x)])])'),
    ('yours',   '([],[([],[yours(x)])->([y],[you(y),owns(y,x)])])'),
    ('your',    '([],[([],[your(x)])->([y],[you(y),owns(y,x)])])'),
    # 3rd person singular
    ('he',      '([x],[([],[he(x)])->([],[him(x)])])'),
    ('she',     '([x],[([],[she(x)])->([],[her(x)])])'),
    ('him',     '([x],[([],[him(x)])->([],[male(x)])])'),
    ('her',     '([x],[([],[her(x)])->([],[female(x)])])'),
    ('himself', '([x],[([],[himself(x)])->([],[him(x)])])'),
    ('herself', '([x],[([],[herself(x)])->([],[her(x)])])'),
    ('hisself', '([x],[([],[hisself(x)])->([],[himself(x)])])'),
    ('his',     '([],[([],[his(x)])->([y],[him(y),owns(y,x)])])'),
    ('hers',    '([],[([],[hers(x)])->([y],[her(y),owns(y,x)])])'),
    # 1st person plural
    ('we',      '([x],[([],[we(x)])->([],[us(x)])])'),
    ('us',      '([x],[us(x)])'),
    ('ourself', '([x],[([],[ourself(x)])->([],[our(x)])])'),
    ('ourselves','([x],[([],[ourselves(x)])->([],[our(x)])])'),
    ('ours',    '([],[([],[ours(x)])->([y],[us(y),owns(y,x)])])'),
    ('our',     '([],[([],[our(x)])->([y],[us(y),owns(y,x)])])'),
    # 2nd person plural
    ('yourselves', '([x],[([],[yourselves(x)])->([],[you(x),plural(x)])])'),
    # 3rd person plural
    ('they',    '([x],[([],[i(x)])->([],[them(x)])])'),
    ('them',    '([x],[them(x)])'),
    ('themself','([x],[([],[themself(x)])->([],[them(x)])])'),
    ('themselves','([x],[([],[themselves(x)])->([],[them(x)])])'),
    ('theirs',  '([x],[([],[theirs(x)])->([y],[them(y),owns(y,x)])])'),
    ('their',   '([],[([],[their(x)])->([y],[them(y),owns(y,x)])])'),
    # it
    ('it',      '([x],[it(x)])'),
    ('its',     '([x],[([],[its(x)])->([y],[it(y),owns(y,x)])])'),
    ('itself',  '([x],[([],[itself(x)])->([],[it(x)])])'),
]
_PRON = {}
for k,v in __pron:
    _PRON[k] = parse_drs(v, 'nltk')


__adv = [
    ('up',      '([x,e],[])', '([],[up(e),direction(e)])'),
    ('down',    '([x,e],[])', '([],[down(e),direction(e)])'),
    ('left',    '([x,e],[])', '([],[left(e),direction(e)])'),
    ('right',   '([x,e],[])', '([],[right(e),direction(e)])'),
]
_ADV = {}
for k,u,v in __adv:
    _ADV[k] = (parse_drs(v, 'nltk'), parse_drs(u, 'nltk').universe)
## endcond


class CcgTypeMapper(object):
    """Mapping from CCG types to DRS types and the construction rules.

    Construction Rules:
    -# We have two levels of construction.
        - Lambda construction rules apply to DRS, i.e. variables are DRS, not referents.
        - DRS construction is via merge operation, infix operator ';'
          Merge works like application in lambda calculus, i.e. right to left.
          <b>Note:</b> This is not the merge function in our python DRS implementation.
    -# We have two levels of binding.
       - Referents in the lambda definition.
         Given λPλx.P(x) with DRS P, x is always free in the lambda declaration
         but x can be a free variable in DRS P, or bound in P
       - Do not support free DRS in the lambda definition<br>
         i.e. λPλxλy.P(x);G(y) is not supported,<br>
         λPλGλxλy.P(x);G(y) is OK
    -# DRS constructions rules can be separated into class:
       - Functions: Rules which take DRS base types (T,Z) as arguments. Functions can return a base type, another
         function, or a combinator. Functions are always constructed from outer types to inner types. For example:
         the application order for (S\T)/T is: /T, \T, S
       - Combinators: Rules which take a function as the argument and return a function of the same type. Combinators
         are always constructed from inner types to outer types. For example: the application order of (S/T)/(S/T) is:
         /T, S, /(S/T)
       - When applying combinators the resultant must produce a function, or combinator, where the DRS merges are
         adjacent. For example:
         - (S/T)/(S/T) combinator:=λP.T[...];P(x) and (S/T) type:=λQ.R[...];Q(x)<br>
           => λQ.T[...];R[...];Q(x) which is OK<br>
         - (S/T)\(S/T) combinator:=λP.P(x);T[...] and (S/T) type:=λQ.R[...];Q(x)<br>
           => λQ.R[...];Q(x);T[...] which is not OK<br>
       - The CCG parse tree gives us the construction order so we don't need to differentiate between combinators and
         functions during composition.
    -# Lambda application:
       - λPλx.P(x) {P(x=x)=G[x|...]} == G[x|...]
       - λPλx.P(x) {P(x=y)=G[y|...])} == G[y|...]
    -# Lambda function composition
       - λPλx.P(x).λQλy.Q(y) == λPλQλxλy.P(x);Q(y) == read as P merge Q<br>
         iff x is a bound in DRS P and y is bound in DRS Q
       - λPλx.P(x).λQλy.Q(y) == λPλQλx.P(x);Q(x)<br>
         iff y is a free variable in DRS Q and x is bound, or free, in DRS P
       - λPλx.P(x).λQλy.Q(y) == λPλQλy.P(y);Q(y)<br>
         iff x is a free variable in DRS P and y is bound in DRS Q
    -# Merge is typically delayed until construction is complete, however we can do partial merge when all
       combinators have been applied at some point during the construction phase.<br>
       P[x|...];Q[x|...] := merge(P[x|...],Q[x|...])
    -# Promotion to a proposition. This is done to ensure the number of referents agree in a lambda definition.<br>
       λPλx.P(x);Q[x|...] {P=R[x,y|...]} := [u|u:R[x,y|...]];Q[u|...]<br>
       λQλx.P[x|...];Q(x) {Q=R[x,y|...]} := P[u|...];[u|u:R[x,y|...]]
    -# Proposition simplification.<br>
       [p|p:Q[x|...]] can be simplified to Q(x=p) if p is the only bound referent.
    """
    # FIXME: variable names set ordering in get_composer(). Should use left/right arg position to determine order.
    _AllTypes = {
        # DRS base types
        # ==============
        'Z':            None,
        'T':            None,
        'conj':         None,
        # Simple DRS functions
        # ====================
        r'Z/T':         [(PropComposition, ArgRight, DRSRef('p')), None],
        r'T/Z':         [(FunctionComposition, ArgRight, DRSRef('p')), None],
        r'T/T':         [(FunctionComposition, ArgRight, DRSRef('x')), None],
        r'T\T':         [(FunctionComposition, ArgLeft, DRSRef('x')), None],
        r'(T\T)/T':     [(FunctionComposition, ArgRight, DRSRef('y')), (FunctionComposition, ArgLeft, DRSRef('x')), None],
        r'(T/T)/T':     [(FunctionComposition, ArgRight, DRSRef('x')), (FunctionComposition, ArgRight, DRSRef('y')), None],
        r'(T/T)\T':     [(FunctionComposition, ArgLeft, DRSRef('x')), (FunctionComposition, ArgRight, DRSRef('y')), None],
        r'(T\T)\T':     [(FunctionComposition, ArgLeft, DRSRef('y')), (FunctionComposition, ArgLeft, DRSRef('x')), None],
        r'(T\T)/Z':     [(FunctionComposition, ArgRight, DRSRef('y')), (FunctionComposition, ArgLeft, DRSRef('x')), None],
        r'(T/T)/Z':     [(FunctionComposition, ArgRight, DRSRef('x')), (FunctionComposition, ArgRight, DRSRef('y')), None],
        # DRS Verb functions
        # ==================
        r'S/T':         [(FunctionComposition, ArgRight, DRSRef('x')), DRSRef('e')],
        r'S\T':         [(FunctionComposition, ArgLeft, DRSRef('x')), DRSRef('e')],
        r'(S/T)/T':     [(FunctionComposition, ArgRight, DRSRef('x')),
                         (FunctionComposition, ArgRight, DRSRef('y')), DRSRef('e')],
        r'(S/T)\T':     [(FunctionComposition, ArgLeft, DRSRef('x')),
                         (FunctionComposition, ArgRight, DRSRef('y')), DRSRef('e')],
        r'(S\T)/T':     [(FunctionComposition, ArgRight, DRSRef('y')),
                         (FunctionComposition, ArgLeft, DRSRef('x')), DRSRef('e')],
        r'(S\T)\T':     [(FunctionComposition, ArgLeft, DRSRef('y')),
                         (FunctionComposition, ArgLeft, DRSRef('x')), DRSRef('e')],
        r'(S\T)/Z':     [(FunctionComposition, ArgRight, DRSRef('y')),
                         (FunctionComposition, ArgLeft, DRSRef('x')), DRSRef('e')],
        r'(S/T)/Z':     [(FunctionComposition, ArgRight, DRSRef('x')),
                         (FunctionComposition, ArgRight, DRSRef('y')), DRSRef('e')],
        r'S\S':         [(FunctionComposition, ArgLeft, DRSRef('x')), DRSRef('e')],
        r'S/S':         [(FunctionComposition, ArgRight, DRSRef('x'))],
        r'(((S\T)/Z)/T)/T': [(FunctionComposition, ArgRight, DRSRef('y')),
                             (FunctionComposition, ArgRight, DRSRef('z')),
                             (FunctionComposition, ArgRight, DRSRef('p')),
                             (FunctionComposition, ArgLeft, DRSRef('x')), DRSRef('e')],
        r'((S\T)/Z)/T': [(FunctionComposition, ArgRight, DRSRef('y')), (FunctionComposition, ArgRight, DRSRef('z')),
                             (FunctionComposition, ArgLeft, DRSRef('x')), DRSRef('e')],
        r'((S\T)\(S\T))/T': [(FunctionComposition, ArgRight, DRSRef('y')), (FunctionComposition, ArgLeft,
                                                                            [DRSRef('x'), DRSRef('e')]), DRSRef('e')],
        # Simple combinators
        # ==================
        # S\T:=λQλx.Q(x);U[...], combinator(S\T)\(S\T):=λPλx.P(x);T[...]
        # => λQλx.Q(x);U[...];T[...]
        r'(S\T)\(S\T)': [(FunctionComposition, ArgLeft, [DRSRef('x'), DRSRef('e')]), DRSRef('e')],
        r'(S\T)/(S\T)': [(FunctionComposition, ArgRight, [DRSRef('x'), DRSRef('e')]), DRSRef('e')],
        # S\T:=λQλx.Q(x);U[...], combinator(S\T)/(S\T):=λPλx.T[...];P(x) => λQλx.T[...];Q(x);U[...]
        # combinator((S\T)/(S\T))/((S\T)/(S\T)):=λP'λx.T'[...];P'(x) => λQλx.T'[...];T[...];Q(x);U[...]
        # combinator(((S\T)/(S\T))/((S\T)/(S\T)))/(((S\T)/(S\T))/((S\T)/(S\T))):=λP''λx.T''[...];P''(x)
        # => λQλx.T''[...];T'[...];T[...];Q(x);U[...]
        # r'(((S\T)/(S\T))/((S\T)/(S\T)))/(((S\T)/(S\T))/((S\T)/(S\T)))': [(Combinator, ArgRight, DRSRef('x'))],
        # Functions returning combinators
        # ===============================
        # (((S\T)/(S\T))/(S\T))/T
        # (*)/T:=λx.U[...];Q(x), S\T:=λQ'λx.Q'(x);U'[...]
        # combinator(*)/(S\T):=λPλx.T[...];P(x) => λQ'λx.T[...];Q'(x);U'[...]
        # combinator(S\T)/(S\T):=λP'λx.T'[...];P'(x) => λQ'λx.T'[...];T[...];Q'(x);U'[...]

        r'(((S\T)/(S\T))/(S\T))/T': [(FunctionComposition, ArgRight, DRSRef('y')), (FunctionComposition, ArgRight,
                                                                                    DRSRef('x')), DRSRef('e')],
        r'(((S\T)/(S\T))/Z)/T': [(FunctionComposition, ArgRight, DRSRef('y')), (PropComposition, ArgRight, DRSRef('p')),
                                 (FunctionComposition, ArgRight, DRSRef('x')), DRSRef('e')],
        r'(((S\T)/S)/(S\T))/T': [(FunctionComposition, ArgRight, DRSRef('y')), (FunctionComposition, ArgRight,
                                                                                DRSRef('x')), DRSRef('e')],
        #r'(((S\T)/Z)/Z)/(S\T)':
    }
    _EventPredicates = ['agent', 'theme', 'extra']
    _TypeChangerAll = re.compile(r'S\[adj\]|NP(?:\[[a-z]+\])?|N(?:\[[a-z]+\])?|PP')
    _TypeChangerNoPP = re.compile(r'S\[adj\]|NP(?:\[[a-z]+\])?|N(?:\[[a-z]+\])?')
    _TypeSimplyS = re.compile(r'S(?!\[adj\])(?:\[[a-z]+\])?')
    _TypeSimplyN = re.compile(r'N(?:\[[a-z]+\])?')
    _TypeMonth = re.compile(r'^((Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?|January|February|March|April|June|July|August|September|October|December)$')

    def __init__(self, ccgTypeName, word, posTags=None):
        self._ccgTypeName = ccgTypeName
        self._pos  = posTags or []
        self._drsTypeName = self.get_drs_typename(ccgTypeName)
        if self.isproper_noun:
            self._word = word.title().rstrip('?.,:;')
        else:
            self._word = word.lower().rstrip('?.,:;')

        if not self._AllTypes.has_key(self._drsTypeName):
            raise DrsComposeError('CCG type "%s" maps to unknown DRS composition type "%s"' %
                                  (ccgTypeName, self._drsTypeName))

    def __repr__(self):
        return '<' + self._word + ' ' + self.partofspeech + ' ' + self._ccgTypeName + '->' + self._drsTypeName + '>'

    @staticmethod
    def iscombinator_signature(signature):
        """Test if a DRS, or CCG type, is a combinator. A combinator expects a function as the argument and returns a
        function.

        Args:
            signature: The DRS signature.

        Returns:
            True if the signature is a combinator
        """
        return signature[-1] == ')' and signature[0] == '('

    @staticmethod
    def isfunction_signature(signature):
        """Test if a DRS, or CCG type, is a function.
r
        Args:
            signature: The DRS signature.

        Returns:
            True if the signature is a function.
        """
        return len(signature.replace('\\', '/').split('/')) > 1

    @staticmethod
    def split_signature(signature):
        """Split a DRS, or CCG type, into argument and return types.

        Args:
            signature: The DRS signature.

        Returns:
            A 3-tuple of <return type>, [\/], <argument type>
        """
        b = 0
        for i in reversed(range(len(signature))):
            if signature[i] == ')':
                b += 1
            elif signature[i] == '(':
                b -= 1
            elif b == 0 and signature[i] in ['/', '\\']:
                ret = signature[0:i]
                arg = signature[i+1:]
                if ret[-1] == ')' and ret[0] == '(':
                    ret = ret[1:-1]
                if arg[-1] == ')' and arg[0] == '(':
                    arg = arg[1:-1]
                return ret, signature[i], arg
        return None

    @staticmethod
    def join_signature(sig):
        """Join a split signature.

        Args:
            sig: The split signature tuple returned from split_signature().

        Returns:
            A signature string.

        See Also:
            split_signature()
        """
        assert len(sig) == 3 and isinstance(sig, tuple)
        fr = CcgTypeMapper.isfunction_signature(sig[0])
        fa = CcgTypeMapper.isfunction_signature(sig[2])
        if fr and fa:
            return '(%s)%s(%s)' % sig
        elif fr:
            return '(%s)%s%s' % sig
        elif fa:
            return '%s%s(%s)' % sig
        else:
            return '%s%s%s' % sig

    @classmethod
    def get_drs_typename(cls, ccgTypeName):
        """Get the DRS type from a CCG type.

        Args:
            ccgTypeName: A CCG type.

        Returns:
            A DRS type.
        """
        return cls._TypeChangerAll.sub('Z', cls._TypeChangerNoPP.sub('T', cls._TypeSimplyS.sub('S', ccgTypeName)))

    @classmethod
    def convert_model_categories(cls, ccg_categories):
        """Convert the list of CCG categories to DRS categories.

        Args:
            ccg_categories: The list of CCG categories. This can be obtained by reading the model
                categories at ext/easysrl/model/text/categories.

        Returns:
            A list of CCG categories that could not be converted or None.

        Remarks:
            Categories starting with # and empty categories are silently ignored.
        """
        results = []
        for ln in ccg_categories:
            c = ln.strip()
            if len(c) == 0 or c[0] == '#':
                continue
            # TODO: handle punctuation
            if c in ['.', '.', ':', ';']:
                continue
            d = cls.get_drs_typename(c)
            if d in cls._AllTypes:
                continue
            if cls.iscombinator_signature(d):
                sig = cls.split_signature(d)
                if sig[0] == sig[2]:
                    if sig[0] in cls._AllTypes:
                        cls._AllTypes[d] = cls._AllTypes[sig[0]]
                        continue

                elif len(sig[0]) < len(sig[2]) and sig[0] in sig[2] and cls.iscombinator_signature(sig[0]):
                    sig2 = cls.split_signature(sig[2])
                    if sig2[0] == sig[0] and sig2[2] == sig[0]:
                        if sig[0] in cls._AllTypes:
                            cls._AllTypes[d] = cls._AllTypes[sig[0]]
                            continue
                elif len(sig[2]) < len(sig[0]) and sig[2] in sig[0] and cls.iscombinator_signature(sig[2]):
                    sig0 = cls.split_signature(sig[0])
                    if sig0[0] == sig[2] and sig0[2] == sig[2]:
                        if sig[2] in cls._AllTypes:
                            cls._AllTypes[d] = cls._AllTypes[sig[2]]
                            continue
            results.append(c)
        return results if len(results) != 0 else None

    @classmethod
    def add_model_categories(cls, filename):
        """Add the CCG categories file and update the DRS types.

        Args:
            filename: The categories file from the model folder.

        Returns:
            A list of CCG categories that could not be added to the types dictionary or None.
        """
        with open(filename, 'r') as fd:
            lns = fd.readlines()

        lns_prev = []
        while lns is not None and len(lns_prev) != len(lns):
            lns_prev = lns
            lns = cls.convert_model_categories(lns)
        return lns

    @property
    def ispronoun(self):
        """Test if the word attached to this category is a pronoun."""
        return (self._pos is not None and self._pos and self._pos[0] in ['PRP', 'PRP$', 'WP', 'WP$']) or \
                    _PRON.has_key(self._word)
    @property
    def ispreposition(self):
        """Test if the word attached to this category is a preposition."""
        return self.partofspeech == 'IN'

    @property
    def isadverb(self):
        """Test if the word attached to this category is an adverb."""
        return self.partofspeech in ['RB', 'RBR', 'RBS']

    @property
    def isverb(self):
        """Test if the word attached to this category is a verb."""
        return self.partofspeech in ['VB', 'VBD', 'VBN', 'VBP', 'VBZ']

    @property
    def isconj(self):
        """Test if the word attached to this category is a conjoin."""
        return self._ccgTypeName == 'conj'

    @property
    def isgerund(self):
        """Test if the word attached to this category is a gerund."""
        return self.partofspeech == 'VBG'

    @property
    def isproper_noun(self):
        """Test if the word attached to this category is a proper noun."""
        return self.partofspeech == 'NNP'

    @property
    def isnumber(self):
        """Test if the word attached to this category is a number."""
        return self.partofspeech == 'CD'

    @property
    def isadjective(self):
        """Test if the word attached to this category is an adjective."""
        return self.partofspeech == 'JJ'

    @property
    def partofspeech(self):
        """Get part of speech of the word attached to this category."""
        return self._pos[0] if self._pos is not None else 'UNKNOWN'

    @property
    def ccgtype(self):
        """Get the CCG category type."""
        return self._ccgTypeName

    def build_predicates(self, p_vars, refs, evt=None, conds=None):
        """Build the DRS conditions for a noun, noun phrase, or adjectival phrase. Do
        not use this for verbs or adverbs.

        Args:
            p_vars: DRSRef's used in the predicates.
            refs: lambda refs for curried function, excluding evt.
            evt: An optional event DRSRef.
            conds: A list of existing DRS conditions.

        Returns:
            A list if marbles.ie.drt.Rel instances.
        """
        assert p_vars is not None
        assert refs is not None
        if conds is None:
            conds = []
        if isinstance(p_vars, DRSRef):
            p_vars = [p_vars]
        evt_vars = None
        if evt is not None:
            evt_vars = []
            evt_vars.extend(p_vars)
            evt_vars.append(evt)

        if self.iscombinator_signature(self._drsTypeName):
            if evt is not None:
                refs.append(evt)
            conds.append(Rel(self._word, refs))
        elif self.isadjective:
            if evt_vars is not None:
                raise DrsComposeError('Adjective "%s" with signature "%s" does not expect an event variable'
                                      % (self._word, self._drsTypeName))
            conds.append(Rel(self._word, refs))
        else:
            conds.append(Rel(self._word, p_vars))
            if self.isproper_noun:
                if self._TypeMonth.match(self._word):
                    conds.append(Rel('is.date', p_vars))
                    if evt_vars is not None:
                        conds.append(Rel('event.date', evt_vars))
                        evt_vars = None
            elif self.isnumber:
                conds.append(Rel('is.number', p_vars))

            if evt_vars is not None:
                # Undefined relationship
                conds.append(Rel('event.related', evt_vars))
        return conds

    def get_composer(self):
        """Get the composition model for this category.

        Returns:
            A Composition instance.
        """
        compose = self._AllTypes[self._drsTypeName]
        if compose is None:
            # Simple type
            # Handle prepositions 'Z'
            if self.isconj:
                if self._word in ['or', 'nor']:
                    raise NotImplementedError
                return CompositionList()
            elif self.ispronoun:
                d = DrsComposition(_PRON[self._word])
                d.set_lambda_refs(d.drs.universe)
                return d
            elif self._ccgTypeName == 'N':
                d = DrsComposition(DRS([DRSRef('x')], [Rel(self._word, [DRSRef('x')])]), properNoun=self.isproper_noun)
                d.set_lambda_refs(d.drs.universe)
                return d
            elif self._TypeSimplyN.match(self._ccgTypeName):
                if self.isnumber:
                    d = DrsComposition(DRS([DRSRef('x')], [Rel(self._word, [DRSRef('x')]), Rel('is.number', [DRSRef('x')])]))
                else:
                    d = DrsComposition(DRS([DRSRef('x')], [Rel(self._word, [DRSRef('x')])]))
                d.set_lambda_refs(d.drs.universe)
                return d
            elif self.isadverb and _ADV.has_key(self._word):
                adv = _ADV[self._word]
                d = DrsComposition(adv[0], [x for x in adv[1]])
                d.set_lambda_refs(d.drs.universe)
                return d
            else:
                d = DrsComposition(DRS([], [Rel(self._word, [DRSRef('x')])]))
                d.set_lambda_refs(d.drs.universe)
                return d
        else:
            # Functions
            ev = compose[-1]
            if self._ccgTypeName == 'NP/N':
                if self._word in ['a', 'an']:
                    fn = FunctionComposition(ArgRight, DRSRef('x'), DRS([], [Rel('exists.maybe', [DRSRef('x')])]))
                elif self._word in ['the', 'thy']:
                    fn = FunctionComposition(ArgRight, DRSRef('x'), DRS([], [Rel('exists', [DRSRef('x')])]))
                else:
                    fn = FunctionComposition(ArgRight, DRSRef('x'), DRS([], [Rel(self._word, [DRSRef('x')])]))
                fn.set_signature('T/T')
                if ev is not None:
                    fn.set_lambda_refs([ev])
                return fn
            if compose[0][0] == FunctionComposition:
                refs = []
                signatures = []
                s = self._drsTypeName
                refs_without_combinator = None
                for c in compose[:-1]:
                    if refs_without_combinator is None and self.iscombinator_signature(s):
                        refs_without_combinator = refs
                    s = self.split_signature(s)
                    signatures.append(s)
                    s = s[0]
                    if c[1]:
                        # arg right
                        if isinstance(c[2], list):
                            refs.extend(c[2])
                        else:
                            refs.append(c[2])
                    else:   # arg left
                        if isinstance(c[2], list):
                            r = [x for x in c[2]]
                        else:
                            r = [c[2]]
                        r.extend(refs)
                        refs = r

                refs_without_combinator = refs_without_combinator or refs
                if ev is not None and ev in refs:
                    refs = filter(lambda a: a != ev, refs)

                if self.isverb:
                    if ev is None:
                        raise DrsComposeError('Verb signature "%s" does not include event variable' % self._drsTypeName)
                    elif self.iscombinator_signature(self._drsTypeName):
                        # passive case
                        refs.append(ev)
                        fn = DrsComposition(DRS([], [Rel(self._word, refs)]))
                    else:
                        # TODO: use verbnet to get semantics
                        conds = [Rel('event', [ev]), Rel(self._word, [ev])]
                        for v,e in zip(refs, self._EventPredicates):
                            conds.append(Rel('event.' + e, [ev, v]))
                        if len(refs) > len(self._EventPredicates):
                            for i in range(len(self._EventPredicates), len(refs)):
                                conds.append(Rel('event.extra.%d' % i, [ev, refs[i]]))
                        fn = DrsComposition(DRS([ev], conds))
                        fn.set_lambda_refs([ev])
                elif self.isadverb:
                    if ev is None:
                        raise DrsComposeError('Adverb signature "%s" does not include event variable' % self._drsTypeName)
                    if _ADV.has_key(self._word):
                        adv = _ADV[self._word]
                        fn = DrsComposition(adv[0], [x for x in adv[1]])
                    else:
                        fn = DrsComposition(DRS([], self.build_predicates(compose[0][2], refs, ev)))
                    fn.set_lambda_refs([ev])
                else:
                    fn = DrsComposition(DRS([], self.build_predicates(compose[0][2], refs, ev)),
                                        properNoun=self.isproper_noun)
                    if ev is not None:
                        fn.set_lambda_refs([ev])

                for c, s in zip(compose[:-1], signatures):
                    if (c[1] and s[1] != '/') or (not c[1] and s[1] != '\\'):
                        raise DrsComposeError('signature %s%s%s does not match function prototype' % s)
                    fn = c[0](c[1], c[2], fn)
                    fn.set_signature(self.join_signature(s))
                return fn
            else:
                assert compose[0][0] == PropComposition
                fn = compose[0][0](compose[0][1], compose[0][2])
                fn.set_signature(self._drsTypeName)
                if ev is not None:
                    fn.set_lambda_refs([ev])
                return fn


def _process_ccg_node(pt, cl):
    """Internal helper for recursively processing the CCG parse tree.

    See Also:
        process_ccg_pt()
    """
    if pt[-1] == 'T':
        cl2 = CompositionList()
        cl2.set_options(cl.compose_options)
        n = 0
        for nd in pt[1:-1]:
            # FIXME: prefer tail end recursion
            n += _process_ccg_node(nd, cl2)
        if n == 0:
            # n == 0 means we possibly can do a partial application on cl2
            cl3 = cl2.clone()
            try:
                cl2 = cl2.apply()
            except Exception:
                cl2 = cl3
            cl.push_right(cl2, merge=True)
            return 0
        elif n < 0:
            # n <= 0 means we cannot do a partial application on cl2
            cl.push_right(cl2, merge=True)
            return 0
        else:
            # n != 0 means we can do a partial application before adding to main composition list
            cl.push_right(cl2.apply())
            return 0

    # L Node in parse tree
    assert pt[-1] == 'L'
    if pt[0] in [',', '.', ':', ';']:
        return 0    # TODO: handle punctuation
    ccgt = CcgTypeMapper(ccgTypeName=pt[0], word=pt[1], posTags=pt[2:-1])
    cl.push_right(ccgt.get_composer())
    return -10000 if ccgt.isconj else 1


def process_ccg_pt(pt, options=None):
    """Process the CCG parse tree.

    Args:
        pt: The parse tree returned from marbles.ie.drt.parse.parse_ccg.
        options: None or CO_REMOVE_UNARY_PROPS to simplify propositions.

    Returns:
        A DrsComposition instance.
    """
    if pt is None or len(pt) == 0:
        return None
    cl = CompositionList()
    if options is not None:
        cl.set_options(options)
    _process_ccg_node(pt, cl)
    d = cl.apply()
    # Handle verbs with null left arg
    if d.isfunction and d.isarg_left:
        return d.apply_null_left()
    return d


