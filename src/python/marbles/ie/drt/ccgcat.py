# -*- coding: utf-8 -*-
"""CCG and DRS signature functions"""
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
    _TypeSimplify = re.compile(r'(?<=NP)\[(nb|conj)\]|(?<=S)\[(pss|b|dcl)\]')
    _TypeChangeNtoNP = re.compile(r'N(?=\\|/|\)|$)')
    ## @endcond

    def __init__(self, signature=None, conj=False):
        """Constructor.

        Args:
            signature: A CCG type signature string.
            conj: Internally used by simplify.
        """
        if signature is None:
            self._signature = ''
            self._splitsig = '', '', ''
            self._isconj = False
        else:
            self._signature = signature
            self._splitsig = split_signature(signature)
            self._isconj = 'conj' in self._splitsig[2] or conj

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
        """Combine two categories with a slash operator

        Args:
            left: The left category (result).
            right: The right category (argument).
            slash: The slash operator.

        Returns:
            A Category instance.
        """
        assert slash in ['/', '\\']
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
        return self._splitsig[0] == self._splitsig[2]

    @property
    def isconj(self):
        return self._isconj

    @property
    def istype_raised(self):
        """Test if the CCG category is type raised."""
        # X|(X|Y)
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
        return self._splitsig[1] in ['/', '\\', '|']

    @property
    def iscombinator(self):
        """A combinator is a function which take a function argument and returns another function."""
        return iscombinator_signature(self._signature) and not self.ismodifier

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


## @{
## @ingroup gconst
## @defgroup ccgcat CCG Categories

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
CAT_Sdcl = Category('S[dcl]')
CAT_Sq = Category('S[q]')
CAT_Swq = Category('S[wq]')
CAT_ADVERB = Category(r'(S\NP)\(S\NP)')
CAT_POSSESSIVE_ARGUMENT = Category(r'(NP/(N/PP))\NP')
CAT_POSSESSIVE_PRONOUN = Category('NP/(N/PP)')
CAT_S = Category('S')
CAT_ADJECTIVE = Category('N/N')
CAT_DETERMINER = Category('NP[nb]/N')
CAT_NOUN = RegexCategoryClass(r'^N(?:\[[a-z]+\])?$')
CAT_NP_N = RegexCategoryClass(r'^NP(?:\[[a-z]+\])?/N$')

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

## Special rule for CONJ and punctuation.
RL_LPASS = Rule('LP', 'PASS')

## Special rule for CONJ and punctuation.
RL_RPASS = Rule('RP', 'PASS')
## @}


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

    if left.isconj and left == right:
        return RL_RPASS
    elif right.isconj and left == right:
        return RL_LPASS
    elif left == CAT_EMPTY:
        return RL_RPASS
    elif right == CAT_EMPTY:
        if result.result_category == result.argument_category.result_category and \
                        left == result.argument_category.argument_category:
            if result.isarg_right and result.argument_category.isarg_left:
                # X:a => T/(T\X): λxf.f(a)
                return RL_FORWARD_TYPE_RAISE
            elif result.isarg_left and result.argument_category.isarg_right:
                # X:a => T\(T/X): λxf.f(a)
                return RL_BACKWARD_TYPE_RAISE
        else:
            return RL_LPASS
    elif left.isarg_right and left.argument_category == right and left.result_category == result:
        # Forward Application  X/Y:f Y:a => X: f(a)
        return RL_FA
    elif left.isarg_right and right.isfunctor and left.argument_category == right.result_category and \
                Category.combine(left.result_category, right.slash, right.argument_category) == result:
        if right.isarg_right:
            # Forward Composition  X/Y:f Y/Z:g => X/Z: λx􏰓.f(g(x))
            return RL_FC
        else:
            # Forward Crossing Composition  X/Y:f Y\Z:g => X\Z: λx􏰓.f(g(x))
            return RL_FX
    elif right.isarg_left and right.argument_category == left and right.result_category == result:
        # Backward Application  Y:a X\Y:f => X: f(a)
        return RL_BA
    elif right.isarg_left and left.isfunctor and right.argument_category == left.result_category and \
                Category.combine(right.result_category, left.slash, left.argument_category) == result:
        if left.isarg_left:
            # Backward Composition  Y\Z:g X\Y:f => X\Z: λx􏰓.f(g(x))
            return RL_BC
        else:
            # Backward Crossing Composition  Y/Z:g X\Y:f => X/Z: λx􏰓.f(g(x))
            return RL_BX
    elif left.argument_category == right.argument_category and left.result_category.isarg_right and \
                left.slash == right.slash and left.result_category.argument_category == right.result_category and \
                Category.combine(left.result_category.result_category, left.slash, left.argument_category) == result:
        if right.isarg_right:
            # Forward Substitution  (X/Y)/Z:f Y/Z:g => X/Z: λx􏰓.fx􏰨(g􏰨(x􏰩􏰩))
            return RL_FS
        else:
            # Forward Crossing Substitution  (X/Y)\Z:f Y\Z:g => X\Z: λx􏰓.fx􏰨(g􏰨(x􏰩􏰩))
            return RL_FXS
    elif right.argument_category == left.argument_category and right.result_category.isarg_left and \
                left.slash == right.slash and right.result_category.argument_category == left.result_category and \
                Category.combine(right.result_category.result_category, left.slash, right.argument_category) == result:
        if right.isarg_left:
            # Backward Substitution  Y\Z:g (X\Y)\Z:g => X/Z: λx􏰓.fx􏰨(g􏰨(x􏰩􏰩))
            return RL_BS
        else:
            # Backward Crossing Substitution  Y/Z:g (X\Y)/Z:f => X/Z: λx􏰓.fx􏰨(g􏰨(x􏰩􏰩))
            return RL_BXS


    elif left.isarg_right and right.isarg_right and left.argument_category == right.result_category.result_category and \
                    Category.combine(Category.combine(left.result_category, right.result_category.slash, \
                                                      right.result_category.argument_category), right.slash, \
                                     right.argument_category) == result:
        if right.result_category.isarg_right:
            # Generalized Forward Composition  X/Y:f (Y/Z)/$:...λz.gz... => (X/Z)/$: ...λz.f(g(z...))
            # Forward Composition  X/Y:f Y/Z:g => X/Z: λx􏰓.f(g(x))
            return RL_GFC
        else:
            # Generalized Forward Crossing Composition  X/Y:f (Y\Z)$:...λz.gz... => (X/Z)$: ...λz.f(g(z...))
            # Forward Crossing Composition  X/Y:f Y\Z:g => X\Z: λx􏰓.f(g(x))
            return RL_GFX
    elif right.isarg_left and left.isarg_left and right.argument_category == left.result_category.result_category and \
                    Category.combine(right.result_category, left.slash, left.argument_category) == result:
        if left.result_category.isarg_left:
            # Generalized Backward Composition  (Y\Z)/$:...λz.gz... X\Y:f => (X\Z)/$: ...λz.f(g(z...))
            # Backward Composition  Y\Z:g X\Y:f => X\Z: λx􏰓.f(g(x))
            return RL_GBC
        else:
            # Generalized Backrward Crossing Composition  (Y\Z)\$:...λz.gz... X\Y:f => (X\Z)\$: ...λz.f(g(z...))
            # Backward Crossing Composition  Y/Z:g X\Y:f => X/Z: λx􏰓.f(g(x))
            return RL_GBX

    # TODO: Implement all production rules. Also need to handle in CompositionList.apply().
    raise NotImplementedError('CCG Rule %s * %s => %s' % (left, right, result))
    return None





