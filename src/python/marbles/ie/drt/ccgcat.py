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
    return signature[-1] == ')' and signature[0] == '('


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
        return self._srch.match(category)


class Category(object):
    """CCG Category"""
    ## @cond
    _TypeChangerAll = re.compile(r'S\[adj\]|NP(?:\[[a-z]+\])?|N(?:\[[a-z]+\])?|PP')
    _TypeChangerNoPP = re.compile(r'S\[adj\]|NP(?:\[[a-z]+\])?|N(?:\[[a-z]+\])?')
    _TypeChangerS = re.compile(r'S(?!\[adj\])(?:\[[a-z]+\])?')
    ## @endcond

    def __init__(self, signature=None):
        """Constructor.

        Args:
            signature: A CCG type signature string.
        """
        if signature is None:
            self._signature = ''
            self._splitsig = '', '', ''
        else:
            self._signature = signature
            self._splitsig = split_signature(signature)

    ## @cond
    def __str__(self):
        return self._signature

    def __repr__(self):
        return self._signature

    def __eq__(self, other):
        return (isinstance(other, Category) and self._signature == other.ccg_signature) or \
               (isinstance(other, AbstractCategoryClass) and other.ismember(self))

    def __lt__(self, other):
        return isinstance(other, Category) and self._signature < other.ccg_signature

    def __le__(self, other):
        return isinstance(other, Category) and self._signature <= other.ccg_signature

    def __gt__(self, other):
        return isinstance(other, Category) and self._signature > other.ccg_signature

    def __ge__(self, other):
        return isinstance(other, Category) and self._signature >= other.ccg_signature

    def __hash__(self):
        return hash(self._signature)
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
    def istype_raised(self):
        """Test if the CCG category is type raised."""
        # X|(X|Y)
        r = self.argument_category
        return r.isfunctor and r.return_category == self.return_category

    def isfunctor(self):
        """Test if the category is a function."""
        return self._splitsig[1] in ['/', '\\', '|']

    @property
    def iscombinator(self):
        """A combinator is a function which take a function argument and returns another function."""
        return iscombinator_signature(self._signature)

    @property
    def return_category(self):
        """Get the return category if a functor."""
        return Category(self._splitsig[0])

    @property
    def argument_category(self):
        """Get the argument category if a functor."""
        return Category(self._splitsig[0])

    @property
    def ccg_signature(self):
        """Get the CCG type as a string."""
        return self._signature

    @property
    def drs_signature(self):
        """Get the DRS type as a string."""
        return self._TypeChangerAll.sub('Z', self._TypeChangerNoPP.sub('T',
                                                                       self._TypeChangerS.sub('S', self._signature)))

## @{
## @ingroup gconst
## @defgroup ccgcat CCG Categories

EMPTY = Category()
COMMA = Category(',')
CONJ = Category('conj')
LQU = Category('LQU')
RQU = Category('RQU')
LRB = Category('LRB')
N = Category('N')
NP = Category('NP')
NPthr = Category('NP[thr]')
NPexpl = Category('NP[expl]')
PP = Category('PP')
PR = Category('PR')
PREPOSITION = Category('PP/NP')
SEMICOLON = Category(';')
Sdcl = Category('S[dcl]')
Sq = Category('S[q]')
Swq = Category('S[wq]')
ADVERB = Category(r'(S\NP)\(S\NP)')
POSSESSIVE_ARGUMENT = Category(r'(NP/(N/PP))\NP')
POSSESSIVE_PRONOUN = Category('NP/(N/PP)')
S = Category('S')
ADJECTIVE = Category('N/N')
DETERMINER = Category('NP[nb]/N')
NOUN = RegexCategoryClass(r'^N(?:\[[a-z]+\])?$')
NP_N = RegexCategoryClass(r'^NP(?:\[[a-z]+\])?/N$')

## @}
