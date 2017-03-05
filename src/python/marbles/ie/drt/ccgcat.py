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
    _TypeSimplify = re.compile(r'(?<=NP)\[(nb|conj)\]|(?<=S)\[pss\]')
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
    """A CCG rule"""

    def __init__(self, ruleName, ruleClass=None):
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
    ## @endcond


## @cond
RL_FA = Rule('FA', 'OTHER')
RL_BA = Rule('BA', 'OTHER')
RL_FC = Rule('FC')
RL_BX = Rule('BX')
RL_GFC = Rule('GFC')
RL_GBX = Rule('GBX')
RL_CONJ = Rule('CONJ')
RL_RP = Rule('RP')
RL_LP = Rule('LP')
RL_FORWARD_TYPERAISE = Rule('FORWARD_TYPERAISE')
RL_BACKWARD_TYPE_RAISE = Rule('BACKWARD_TYPE_RAISE')
RL_TYPE_CHANGE = Rule('TYPE_CHANGE', 'OTHER')
RL_PASS = Rule('PASS')
## @endcond


def get_rule(left, right, result):
    """Check if arg can be combined with this category and return the rule.

    Args:
        left: The left category.
        right: The right category:

    Returns:
        A tuple of (functor position, rule), where functor position is True if its the right category, and False if
        its the left category. A none result indicates the rule could not be found.
    """
    assert isinstance(left, Category)
    assert isinstance(right, Category)
    if left.isconj and left == right:
        return True, RL_PASS
    elif right.isconj and left == right:
        return False, RL_PASS
    elif left == CAT_EMPTY:
        return True, RL_PASS
    elif right == CAT_EMPTY:
        return False, RL_PASS
    elif left.isarg_right and left.argument_category == right and left.result_category == result:
        if right.isfunctor:
            return False, RL_FC
        else:
            return False, RL_FA
    elif right.isarg_left and right.argument_category == left and right.result_category == result:
        if left.isfunctor:
            return True, RL_BX
        else:
            return True, RL_BA

    return None




