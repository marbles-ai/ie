# -*- coding: utf-8 -*-
"""CCG Categories and Rules"""
import re


def iscombinator_signature(signature):
    """Test if a DRS, or CCG type, is a combinator. A combinator expects a function as the argument and returns a
    function.

    Args:
        signature: The DRS signature.

    Returns:
        True if the signature is a combinator
    """
    return len(signature) > 2 and signature[-1] == ')' and signature[0] == '('


def isfunction_signature(signature):
    """Test if a DRS, or CCG type, is a function.

    Args:
        signature: The DRS or CCG signature.

    Returns:
        True if the signature is a function.
    """
    return len(signature.replace('\\', '/').split('/')) > 1


def split_signature(signature):
    """Split a DRS, or CCG type, into argument and return types.

    Args:
        signature: The DRS or CCG signature.

    Returns:
        A 3-tuple of <return type>, [\/], <argument type>. Basic non-functor types are encoded:
        <basic-type>, '', ''
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
    return signature, '', ''


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
    fr = isfunction_signature(sig[0])
    fa = isfunction_signature(sig[2])
    if fr and fa:
        return '(%s)%s(%s)' % sig
    elif fr:
        return '(%s)%s%s' % sig
    elif fa:
        return '%s%s(%s)' % sig
    else:
        return '%s%s%s' % sig


class AbstractCategoryClass(object):
    """Class of categories."""

    def __eq__(self, other):
        return isinstance(other, Category) and self.ismember(other)

    def ismember(self, category):
        """Test if a category is a member of this class.

        Args:
            category: A Category instance.

        Returns:
            True if in the class.
        """
        raise NotImplementedError


class RegexCategoryClass(AbstractCategoryClass):
    """Class of categories determined by a regular expression."""

    def __init__(self, regex):
        """Constructor.

        Args:
            regex: A regular expression.
        """
        self._srch = re.compile(regex)

    def __eq__(self, other):
        return isinstance(other, Category) and self.ismember(other)

    def ismember(self, category):
        """Test if a category is a member of this class.

        Args:
            category: A Category instance.

        Returns:
            True if in the class.
        """
        return self._srch.match(category.ccg_signature)


class Category(object):
    """CCG Category"""
    ## @cond
    _TypeChangerAll = re.compile(r'S\[adj\]|NP(?:\[[a-z]+\])?|N(?:\[[a-z]+\])?|PP')
    _TypeChangerNoPP = re.compile(r'S\[adj\]|NP(?:\[[a-z]+\])?|N(?:\[[a-z]+\])?')
    _TypeChangerS = re.compile(r'S(?!\[adj\])(?:\[[a-z]+\])?')
    _TypeSimplify = re.compile(r'(?<=NP)\[(nb|conj)\]|(?<=S)\[([a-z]+)\]')
    _TypeChangeNtoNP = re.compile(r'N(?=\\|/|\)|$)')
    _CleanPredArg1 = re.compile(r':[A-Z]')
    _CleanPredArg2 = re.compile(r'\)_\d+')
    _CleanPredArg3 = re.compile(r'_\d+')
    ## @endcond

    def __init__(self, signature=None, conj=False):
        """Constructor.

        Args:
            signature: A CCG type signature string.
            conj: Internally used by simplify. Never set this explicitly.
        """
        if signature is None:
            self._signature = ''
            self._splitsig = '', '', ''
            self._isconj = False
        else:
            self._isconj = 'conj' in signature or conj
            self._signature = signature.replace('[conj]', '')
            self._splitsig = split_signature(self._signature)
            # Don't need to handle | (= any) because parse tree has no ambiguity
            assert self._splitsig[1] in ['/', '\\', '']

            ## @cond
    def __str__(self):
        return self._signature

    def __repr__(self):
        return self._signature

    def __eq__(self, other):
        return (isinstance(other, Category) and str(self) == str(other)) or \
               (isinstance(other, AbstractCategoryClass) and other.ismember(self))

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        return isinstance(other, Category) and str(self) < str(other)

    def __le__(self, other):
        return isinstance(other, Category) and str(self) <= str(other)

    def __gt__(self, other):
        return not self.__le__(other)

    def __ge__(self, other):
        return not self.__lt__(other)

    def __hash__(self):
        return hash(str(self))
    ## @endcond

    @classmethod
    def combine(cls, left, slash, right):
        """Combine two categories with a slash operator.

        Args:
            left: The left category (result).
            right: The right category (argument).
            slash: The slash operator.

        Returns:
            A Category instance.
        """
        # Don't need to handle | (= any) because parse tree has no ambiguity
        assert slash in ['/', '\\']
        assert not left.isempty
        if right.isempty:
            return left
        c = Category()
        c._splitsig = left.ccg_signature, slash, right.ccg_signature
        c._signature = join_signature(c._splitsig)
        return c

    @property
    def isarg_right(self):
        """If a functor then return True if it accepts a right argument."""
        return self._splitsig[1] == '/'

    @property
    def isarg_left(self):
        """If a functor then return True if it accepts a left argument."""
        return self._splitsig[1] == '\\'

    @property
    def isempty(self):
        """Test if this is the empty category."""
        return len(self._signature) == 0

    @property
    def ismodifier(self):
        """Test if the CCG category is a modifier."""
        return self._splitsig[0] == self._splitsig[2] and self.isfunctor

    @property
    def isconj(self):
        return self._isconj

    @property
    def istype_raised(self):
        """Test if the CCG category is type raised."""
        # X|(X|Y), where | = any slash
        r = self.argument_category
        return r.isfunctor and r.result_category == self.result_category

    @property
    def isbackward_type_raised(self):
        return self.isarg_left and self.istype_raised

    @property
    def isforward_type_raised(self):
        return self.isarg_right and self.istype_raised

    @property
    def isfunctor(self):
        """Test if the category is a function."""
        return self._splitsig[1] in ['/', '\\']

    @property
    def isatom(self):
        """Test if the category is an atom."""
        return not self.isfunctor and not self.isempty

    @property
    def iscombinator(self):
        """A combinator is a function which take a function argument and returns another function."""
        return iscombinator_signature(self._signature) and not self.ismodifier

    @property
    def issentence(self):
        """True if the result of all applications is a sentence, i.e. an S[?] type."""
        return not self.isempty and self.extract_unify_atoms()[-1][0] == CAT_Sany

    @property
    def result_category(self):
        """Get the return category if a functor."""
        return Category(self._splitsig[0]) if self.isfunctor else CAT_EMPTY

    @property
    def argument_category(self):
        """Get the argument category if a functor."""
        return Category(self._splitsig[2]) if self.isfunctor else CAT_EMPTY

    @property
    def slash(self):
        """Get the slash for a functor category."""
        return self._splitsig[1]

    @property
    def ccg_signature(self):
        """Get the CCG type as a string."""
        return self._signature

    @property
    def drs_signature(self):
        """Get the DRS type as a string."""
        return self._TypeChangerAll.sub('Z', self._TypeChangerNoPP.sub('T',
                                                                       self._TypeChangerS.sub('S', self._signature)))
    def simplify(self):
        """Simplify the CCG category. Required to determine production rules.

        Returns:
            A Category instance.
        """
        return Category(self._TypeChangeNtoNP.sub('NP', self._TypeSimplify.sub('', self._signature)), conj=self.isconj)

    def clean(self, deep=False):
        """Clean predicate-argument tags from a category.

        Args:
            deep: If True clean atoms and functor tags, else only clean functor tags.

        Returns:
            A Category instance.
        """
        if deep:
            return Category(self._CleanPredArg1.sub('', self._CleanPredArg3.sub('', self.ccg_signature)))
        return Category(self._CleanPredArg1.sub('', self._CleanPredArg2.sub(')', self.ccg_signature)))

    def _extract_atoms_helper(self, atoms):
        if self.isfunctor:
            atoms = self.argument_category._extract_atoms_helper(atoms)
            return self.result_category._extract_atoms_helper(atoms)
        else:
            atoms.append(self)
            return atoms

    def _extract_slash_helper(self, slashes):
        if self.isfunctor:
            slashes.append(self.slash)
            slashes = self.argument_category._extract_slash_helper(slashes)
            return self.result_category._extract_slash_helper(slashes)
        else:
            return slashes

    def extract_unify_atoms(self, follow=True):
        """Extract the atomic categories for unification.

        Args:
            follow: If True, return atoms for argument and result functors recursively. If false return the atoms
                for the category.

        Returns:
            A list of sub-lists containing atomic categories. Each sub-list is ordered for unification at the functor
            scope it is applied. The order matches the lambda variables at that scope. Functor scope is: argument,
            result.argument, result.result.argument, ..., result.result...result.

        See Also:
            can_unify()

        Remarks:
            This method is used to create a marbles.ie.drt.compose.FunctorProduction from a category.
        """
        if self.isatom:
            return [[self]] if follow else [self]
        elif self.isfunctor:
            if follow:
                cat = self
                atoms = []
                while cat.isfunctor:
                    aa = cat.argument_category._extract_atoms_helper([])
                    atoms.append(aa)
                    cat = cat.result_category
                atoms.append([cat])
                return atoms
            else:
                return self._extract_atoms_helper([])
        return None

    def can_unify_atom(self, other):
        """Test if other can unify with self. Both self and other must be atomic types.

        Args:
            other: A atomic category.

        Returns:
            True if other and self can unify.

        See Also:
            can_unify()
        """
        if not self.isatom or not other.isatom:
            return False
        if self in [CAT_PP, CAT_NP, CAT_Sadj] and other in [CAT_PP, CAT_NP, CAT_Sadj]:
            return True
        s1 = self.ccg_signature
        s2 = other.ccg_signature
        if s1 == s2 or (s1[0] == 'N' and s2[0] == 'N'):
            return True
        if s1[0] == 'S' and s2[0] == 'S':
            return (len(s1) == 1 or len(s2) == 1) or (self == CAT_Sto and other == CAT_Sb) or \
                   (self == CAT_Sb and other == CAT_Sto)
        return False

    def can_unify(self, other):
        """Test if other can unify with self. Both self and other must be of the same class: atomic or functor.

        Args:
            other: A category.

        Returns:
            True if other and self can unify.

        See Also:
            can_unify_atom()
        """
        if self.isfunctor and other.isfunctor:
            fa = self.extract_unify_atoms()
            ga = other.extract_unify_atoms()
            if len(fa) != len(ga):
                return False
            # fa and ga are lists of lists of atoms
            for f, g in zip(fa, ga):
                # f and g are lists of atoms, now zip atoms
                if len(f) != len(g):
                    return False
                for a, b in zip(f, g):
                    if not a.can_unify_atom(b):
                        return False
            return ''.join(self._extract_slash_helper([])) == ''.join(other._extract_slash_helper([]))
        return self.can_unify_atom(other)


## @{
## @ingroup gconst
## @defgroup ccgcat CCG Categories

CAT_NUM = Category('N[num]')
CAT_EMPTY = Category()
CAT_COMMA = Category(',')
CAT_CONJ = Category('conj')
CAT_LQU = Category('LQU')
CAT_RQU = Category('RQU')
CAT_LRB = Category('LRB')
CAT_N = Category('N')
CAT_NP = Category('NP')
CAT_NPthr = Category('NP[thr]')
CAT_NPexpl = Category('NP[expl]')
CAT_PP = Category('PP')
CAT_PR = Category('PR')
CAT_PREPOSITION = Category('PP/NP')
CAT_SEMICOLON = Category(';')
CAT_Sadj = Category('S[adj]')
CAT_Sdcl = Category('S[dcl]')
CAT_Sq = Category('S[q]')
CAT_Sb = Category('S[b]')
CAT_Sto = Category('S[to]')
CAT_Swq = Category('S[wq]')
CAT_ADVERB = Category(r'(S\NP)\(S\NP)')
CAT_POSSESSIVE_ARGUMENT = Category(r'(NP/(N/PP))\NP')
CAT_POSSESSIVE_PRONOUN = Category('NP/(N/PP)')
CAT_S = Category('S')
CAT_ADJECTIVE = Category('N/N')
CAT_DETERMINER = Category('NP[nb]/N')
CAT_INFINITIVE = Category(r'(S[to]\NP)/(S[b]\NP)')
CAT_NOUN = RegexCategoryClass(r'^N(?:\[[a-z]+\])?$')
CAT_NP_N = RegexCategoryClass(r'^NP(?:\[[a-z]+\])?/N$')
CAT_NP_NP = RegexCategoryClass(r'^NP(?:\[[a-z]+\])?/NP$')
CAT_Sany = RegexCategoryClass(r'^S(?:\[[a-z]+\])?$')
CAT_PPNP = Category('PP/NP')
## @}


class Rule(object):
    """A CCG production rule.

    See Also:
        \ref ccgrule
    """
    def __init__(self, ruleName, ruleClass=None):
        """Rule constructor.

        Args:
            ruleName: The rule name as a string. This must be unique amongst all rules.
            ruleClass: The class string for a rule. Possible classes are:
                - 'C': composition
                - 'A': application
                - 'GC': generalized composition
                - 'S': substitution
        """
        self._ruleName = ruleName
        self._ruleClass = ruleClass if not None else ruleName

    ## @cond
    def __repr__(self):
        return self._ruleName

    def __str__(self):
        return self._ruleName

    def __eq__(self, other):
        return isinstance(other, Rule) and str(self) == str(other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        return isinstance(other, Rule) and str(self) < str(other)

    def __le__(self, other):
        return isinstance(other, Rule) and str(self) <= str(other)

    def __gt__(self, other):
        return not self.__le__(other)

    def __ge__(self, other):
        return not self.__lt__(other)

    def __hash__(self):
        return hash(str(self))
    ## @endcond

## @{
## @ingroup gconst
## @defgroup ccgrule CCG Composition Rules

## Forward Application
## @verbatim
## X/Y:f Y:a => X: f(a)
## @endverbatim
RL_FA = Rule('FA', 'A')

## Backward Application
## @verbatim
## Y:a X\Y:f => X: f(a)
## @endverbatim
RL_BA = Rule('BA', 'A')

## Forward Composition
## @verbatim
## X/Y:f Y/Z:g => X/Z: λx􏰓.f(g(x))
## @endverbatim
RL_FC = Rule('FC', 'C')

## Forward Crossing Composition
## @verbatim
## X/Y:f Y\Z:g => X\Z: λx􏰓.f(g(x))
## @endverbatim
RL_FX = Rule('FX', 'C')

## Backward Composition
## @verbatim
## Y\Z:g X\Y:f => X\Z: λx􏰓.f(g(x))
## @endverbatim
RL_BC = Rule('BC', 'C')

## Backward Crossing Composition
## @verbatim
## Y/Z:g X\Y:f => X/Z: λx􏰓.f(g(x))
## @endverbatim
RL_BX = Rule('BX', 'C')

## Forward Type-raising
## @verbatim
## X:a => T/(T\X): λxf.f(a)
## @endverbatim
RL_FORWARD_TYPE_RAISE = Rule('FORWARD_TYPERAISE')

## Backward Type-raising
## @verbatim
## X:a => T\(T/X): λxf.f(a)
## @endverbatim
RL_BACKWARD_TYPE_RAISE = Rule('BACKWARD_TYPE_RAISE')

## Generalized Forward Composition
## @verbatim
## X/Y:f (Y/Z)/$:...λz.gz... => (X\Z)/$: ...λz.f(g(z...))
## @endverbatim
RL_GFC = Rule('GFC', 'GC')

## Generalized Forward Crossing Composition
## @verbatim
## X/Y:f (Y\Z)$:...λz.gz... => (X\Z)$: ...λz.f(g(z...))
## @endverbatim
RL_GFX = Rule('GFX', 'GC')

## Generalized Backward Composition
## @verbatim
## (Y\Z)/$:...λz.gz... X\Y:f => (X\Z)/$: ...λz.f(g(z...))
## @endverbatim
RL_GBC = Rule('GBC', 'GC')

## Generalized Backrward Crossing Composition
## @verbatim
## (Y\Z)\$:...λz.gz... X\Y:f => (X\Z)\$: ...λz.f(g(z...))
## @endverbatim
RL_GBX = Rule('GBX', 'GC')

## Forward Substitution
## @verbatim
## (X/Y)/Z:f Y/Z:g => X/Z: λx􏰓.fx􏰨(g􏰨(x􏰩􏰩))
## @endverbatim
RL_FS = Rule('FS', 'S')

## Backward Substitution
## @verbatim
## Y\Z:g (X\Y)\Z:g => X\Z: λx􏰓.fx􏰨(g􏰨(x􏰩􏰩))
## @endverbatim
RL_BS = Rule('FS', 'S')

## Forward Crossing Substitution
## @verbatim
## (X/Y)\Z:f Y\Z:g => X\Z: λx􏰓.fx􏰨(g􏰨(x􏰩􏰩))
## @endverbatim
RL_FXS = Rule('FXS', 'S')

## Backward Crossing Substitution
## @verbatim
## Y/Z:g (X\Y)/Z:f => X/Z: λx􏰓.fx􏰨(g􏰨(x􏰩􏰩))
## @endverbatim
RL_BXS = Rule('BXS', 'S')

## Special rule for punctuation.
RL_LPASS = Rule('LP', 'PASS')

## Special rule for CONJ.
RL_LCONJ = Rule('LCONJ', 'PASS')

## Special rule for punctuation.
RL_RPASS = Rule('RP', 'PASS')

## Special rule for CONJ.
RL_RCONJ = Rule('RCONJ', 'PASS')

## Special rule for numbers
RL_RNUM = Rule('RNUM')
RL_LNUM = Rule('LNUM')

## Special type changing rule. See LDC manual 2005T13.
RL_TYPE_CHANGE_VPMOD = Rule('TYPE_CHANGE_VPMOD')
RL_TYPE_CHANGE_NP_NP = Rule('TYPE_CHANGE_NP_NP')
RL_TYPE_CHANGE_MOD = Rule('TYPE_CHANGE_MOD')
RL_TYPE_CHANGE_SNP = Rule('TYPE_CHANGE_SNP')
## @}

# Special type changing rules - see LDC2005T13 document

## @cond
CAT_S_NP_TypeChange = RegexCategoryClass(r'^S\[(pss|adj|ng|dcl)\]\\NP(?:\[conj\])?$')
CAT_NP_NP = Category(r'NP\NP')
CAT_SdclNP = Category(r'S[dcl]/NP')
CAT_Sng_NP = Category(r'S[ng]\NP')
CAT_S_NPS_NP = Category(r'(S\NP)/(S\NP)')
CAT_Sadj_NP = Category(r'S[adj]\NP')
CAT_S_NP = Category(r'S\NP')
## @endcond


def get_rule(left, right, result):
    """Check if left can be combined with right to produce result.

    Args:
        left: The left category.
        right: The right category.
        result: The result category.

    Returns:
        A production rule instance or None if the rule could not be found.
    """

    # Useful logic for category X.
    # - If X is not a functor, then X.result_category == X

    assert isinstance(left, Category)
    assert isinstance(right, Category)
    assert isinstance(result, Category)

    if left.isconj:
        if right == CAT_EMPTY and left == result:
            return RL_LPASS
        elif left.can_unify(right):
            return RL_LCONJ
        elif left == CAT_CONJ:
            if result.ismodifier and result.iscombinator and result.argument_category == right:
                return RL_TYPE_CHANGE_MOD
            elif right.can_unify(result):
                return RL_RPASS
            elif right.isatom and result.isfunctor and result.argument_category.isatom and \
                    result.result_category.isatom:
                # NP => S[adj]\NP, S[dcl] => S[dcl]\S[dcl]
                return RL_TYPE_CHANGE_SNP
    elif right.isconj:
        if left.can_unify(right):
            return RL_RCONJ
        elif right == CAT_CONJ and result.ismodifier and result.argument_category == left:
            return RL_TYPE_CHANGE_MOD
    elif left == CAT_EMPTY:
        return RL_RPASS
    elif left == CAT_NP_NP and right == CAT_NUM:
        return RL_RNUM
    elif right == CAT_EMPTY:
        if result.result_category == result.argument_category.result_category and \
                        left.can_unify(result.argument_category.argument_category):
            if result.isarg_right and result.argument_category.isarg_left:
                # X:a => T/(T\X): λxf.f(a)
                return RL_FORWARD_TYPE_RAISE
            elif result.isarg_left and result.argument_category.isarg_right:
                # X:a => T\(T/X): λxf.f(a)
                return RL_BACKWARD_TYPE_RAISE
        elif left == CAT_Sadj_NP and result == CAT_NP_NP:
            return RL_TYPE_CHANGE_NP_NP
        elif left == CAT_Sng_NP and result == CAT_S_NPS_NP:
            # See LDC 2005T13 manual, section 3.8
            return RL_TYPE_CHANGE_VPMOD
        elif left == CAT_SdclNP and result == CAT_NP_NP:
            # See LDC 2005T13 manual, section 3.8
            # S[dcl]/NP => NP\NP
            raise NotImplementedError
        elif left == CAT_S_NP_TypeChange and result == CAT_NP_NP:
            # See LDC 2005T13 manual, section 3.8
            # S[pss]\NP => NP\NP
            # S[adj]\NP => NP\NP
            # S[ng]\NP => NP\NP
            raise NotImplementedError
        return RL_LPASS

    elif left.isarg_right and left.argument_category.can_unify(right) and left.result_category.can_unify(result):
        # Forward Application  X/Y:f Y:a => X: f(a)
        return RL_FA
    elif left.isarg_right and right.isfunctor and left.argument_category.can_unify(right.result_category) and \
                Category.combine(left.result_category, right.slash, right.argument_category).can_unify(result):
        if right.isarg_right:
            # Forward Composition  X/Y:f Y/Z:g => X/Z: λx􏰓.f(g(x))
            return RL_FC
        else:
            # Forward Crossing Composition  X/Y:f Y\Z:g => X\Z: λx􏰓.f(g(x))
            return RL_FX

    elif right.isarg_left and right.argument_category.can_unify(left) and right.result_category.can_unify(result):
        # Backward Application  Y:a X\Y:f => X: f(a)
        return RL_BA
    elif right.isarg_left and left.isfunctor and right.argument_category.can_unify(left.result_category) and \
                Category.combine(right.result_category, left.slash, left.argument_category).can_unify(result):
        if left.isarg_left:
            # Backward Composition  Y\Z:g X\Y:f => X\Z: λx􏰓.f(g(x))
            return RL_BC
        else:
            # Backward Crossing Composition  Y/Z:g X\Y:f => X/Z: λx􏰓.f(g(x))
            return RL_BX

    elif left.argument_category.can_unify(right.argument_category) and left.result_category.isarg_right and \
            left.slash == right.slash and left.result_category.argument_category.can_unify(right.result_category) and \
            Category.combine(left.result_category.result_category, left.slash, left.argument_category).can_unify(result):
        if right.isarg_right:
            # Forward Substitution  (X/Y)/Z:f Y/Z:g => X/Z: λx􏰓.fx􏰨(g􏰨(x􏰩􏰩))
            return RL_FS
        else:
            # Forward Crossing Substitution  (X/Y)\Z:f Y\Z:g => X\Z: λx􏰓.fx􏰨(g􏰨(x􏰩􏰩))
            return RL_FXS

    elif right.argument_category.can_unify(left.argument_category) and right.result_category.isarg_left and \
            left.slash == right.slash and right.result_category.argument_category.can_unify(left.result_category) and \
            Category.combine(right.result_category.result_category, left.slash, right.argument_category).can_unify(result):
        if right.isarg_left:
            # Backward Substitution  Y\Z:g (X\Y)\Z:g => X/Z: λx􏰓.fx􏰨(g􏰨(x􏰩􏰩))
            return RL_BS
        else:
            # Backward Crossing Substitution  Y/Z:g (X\Y)/Z:f => X/Z: λx􏰓.fx􏰨(g􏰨(x􏰩􏰩))
            return RL_BXS

    elif left.isarg_right and right.isarg_right and \
            left.argument_category.can_unify(right.result_category.result_category) and \
            Category.combine(Category.combine(left.result_category, right.result_category.slash,
                                              right.result_category.argument_category), right.slash,
                             right.argument_category).can_unify(result):
        if right.result_category.isarg_right:
            # Generalized Forward Composition  X/Y:f (Y/Z)/$:...λz.gz... => (X/Z)/$: ...λz.f(g(z...))
            # Forward Composition  X/Y:f Y/Z:g => X/Z: λx􏰓.f(g(x))
            return RL_GFC
        else:
            # Generalized Forward Crossing Composition  X/Y:f (Y\Z)|$:...λz.gz... => (X/Z)|$: ...λz.f(g(z...))
            # Forward Crossing Composition  X/Y:f Y\Z:g => X/Z: λx􏰓.f(g(x))
            return RL_GFX

    elif right.isarg_left and left.isarg_left and \
            right.argument_category.can_unify(left.result_category.result_category) and \
            Category.combine(right.result_category, left.slash, left.argument_category).can_unify(result):
        if left.result_category.isarg_left:
            # Generalized Backward Composition  (Y\Z)/$:...λz.gz... X\Y:f => (X\Z)/$: ...λz.f(g(z...))
            # Backward Composition  Y\Z:g X\Y:f => X\Z: λx􏰓.f(g(x))
            return RL_GBC
        else:
            # Generalized Backrward Crossing Composition  (Y\Z)\$:...λz.gz... X\Y:f => (X\Z)\$: ...λz.f(g(z...))
            # Backward Crossing Composition  Y/Z:g X\Y:f => X/Z: λx􏰓.f(g(x))
            return RL_GBX

    return None





