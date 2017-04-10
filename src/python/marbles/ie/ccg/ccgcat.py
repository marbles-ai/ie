# -*- coding: utf-8 -*-
"""CCG Categories and Rules"""
import re
import os
from marbles.ie.utils.cache import Cache


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
        return self._srch.match(category.signature)


class Category(object):
    """CCG Category"""
    ## @cond
    _TypeChangerAll = re.compile(r'S\[adj\]|NP(?:\[[a-z]+\])?|N(?:\[[a-z]+\])?|PP')
    _TypeChangerNoPP = re.compile(r'S\[adj\]|NP(?:\[[a-z]+\])?|N(?:\[[a-z]+\])?')
    _TypeChangerS = re.compile(r'S(?!\[adj\])(?:\[[a-z]+\])?')
    _TypeSimplify = re.compile(r'(?<=NP)\[(nb|conj)\]|(?<=S)\[([a-z]+|X)\]')
    _TypeChangeNtoNP = re.compile(r'N(?=\\|/|\)|$)')
    _CleanPredArg1 = re.compile(r':[A-Z]')
    _CleanPredArg2 = re.compile(r'\)_\d+')
    _CleanPredArg3 = re.compile(r'_\d+')
    _TrailingFunctorPredArgTag = re.compile(r'^.*\)_(?P<idx>\d+)$')
    _Wildcard = re.compile(r'[X]')
    _Feature = re.compile(r'\[([a-z]+|X)\]')
    _cache = Cache()
    _use_cache = False
    _OP_REMOVE_UNIFY_FALSE = 0
    _OP_REMOVE_UNIFY_TRUE = 1
    _OP_REMOVE_WILDCARDS = 2
    _OP_SIMPLIFY = 3
    _OP_REMOVE_FEATURES = 4
    _OP_SLASH = 5
    _OP_COUNT = 6
    ## @endcond

    def __init__(self, signature=None, conj=False):
        """Constructor.

        Args:
            signature: A CCG type signature string.
            conj: Internally used by simplify. Never set this explicitly.
        """
        self._ops_cache = None
        if signature is None:
            self._signature = ''
            self._splitsig = '', '', ''
            self._isconj = False
        else:
            if isinstance(signature, str):
                self._isconj = 'conj' in signature or conj
                self._signature = signature.replace('[conj]', '')
            else:
                self._signature = signature.signature
                self._isconj = signature.isconj
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
    def from_cache(cls, signature):
        if not cls._use_cache:
            if isinstance(signature, Category):
                return signature
            return Category(signature)
        if isinstance(signature, Category):
            signature = signature.signature
        try:
            return cls._cache[signature]
        except KeyError:
            cat = Category(signature)
            retcat = cat
            # Add to list to avoid initialize_ops_cache() calling from_cache() and getting another KeyError.
            todo = []
            while cat.isfunctor:
                todo.append(cat)
                todo.append(cat.simplify())
                todo.append(cat.remove_features())
                todo.append(cat.remove_wildcards())
                cat = cat.result_category
            for c in todo:
                cls._cache[c.signature] = c
            cls._cache[cat.signature] = cat
            cls._cache[cat.simplify().signature] = cat.simplify()
            cls._cache[cat.remove_features().signature] = cat.remove_features()
            cls._cache[cat.remove_wildcards().signature] = cat.remove_wildcards()
            for c in todo:
                cls._cache[c.signature].initialize_ops_cache()
            return retcat

    @classmethod
    def save_cache(cls, filename):
        """Save the cache to a file.

        Args:
            filename: The file name and path.

        Remarks:
            Is threadsafe.
        """
        if cls._use_cache:
            with open(filename, 'w') as fd:
                for k, v in cls._cache:
                    fd.write(k)
                    fd.write('\n')

    @classmethod
    def load_cache(cls, filename):
        """Load the cache from a file.

        Args:
            filename: The file name and path.

        Remarks:
            Not threadsafe.
        """
        with open(filename, 'r') as fd:
            cache = Cache()
            sigs = fd.readlines()
            pairs = [(x, Category(x)) for x in filter(lambda s: len(s) != 0 and s[0] != '#', map(lambda p: p.strip(), sigs))]
            cache.initialize(pairs)
        cls._cache = cache
        cls._use_cache = True
        for k, v in pairs:
            v.initialize_ops_cache()

    @classmethod
    def initialize_cache(cls, cats):
        """Initialize the cache with categories.

        Args:
            cats: A list of categories.
        """
        pairs = []
        for cat in cats:
            if isinstance(cat, str):
                cat = Category(cat)
            while cat.isfunctor:
                pairs.append((cat.signature, cat))
                # Avoid copying string in key, value
                c = cat.simplify()
                pairs.append((c.signature, c))
                c = cat.remove_features()
                pairs.append((c.signature, c))
                c = cat.remove_wildcards()
                pairs.append((c.signature, c))
                cat = cat.result_category
            pairs.append((cat.signature, cat))
            c = cat.remove_features()
            pairs.append((c.signature, c))
            c = cat.remove_wildcards()
            pairs.append((c.signature, c))
        cls._cache.initialize(pairs)
        cls._use_cache = True

    @classmethod
    def combine(cls, left, slash, right, cacheable=True):
        """Combine two categories with a slash operator.

        Args:
            left: The left category (result).
            right: The right category (argument).
            slash: The slash operator.
            cacheable: Optional flag indicating the result can be added to the cache.

        Returns:
            A Category instance.
        """
        # Don't need to handle | (= any) because parse tree has no ambiguity
        assert slash in ['/', '\\']
        assert not left.isempty
        if right.isempty:
            return left
        signature = join_signature((left.signature, slash, right.signature))
        if cls._use_cache and cacheable:
            return cls.from_cache(signature)
        return Category(signature)

    @property
    def ispunct(self):
        """Test if punctuation."""
        return self._signature in [',', '.', ':', ';'] or self in [CAT_LRB, CAT_RRB, CAT_LQU, CAT_RQU]

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
        if self._use_cache:
            return self.from_cache(self._splitsig[0]) if self.isfunctor else CAT_EMPTY
        return Category(self._splitsig[0]) if self.isfunctor else CAT_EMPTY

    @property
    def argument_category(self):
        """Get the argument category if a functor."""
        if self._use_cache:
            return self.from_cache(self._splitsig[2]) if self.isfunctor else CAT_EMPTY
        return Category(self._splitsig[2]) if self.isfunctor else CAT_EMPTY

    @property
    def slash(self):
        """Get the slash for a functor category."""
        return self._splitsig[1]

    @property
    def signature(self):
        """Get the CCG type as a string."""
        return self._signature

    def initialize_ops_cache(self):
        if not self._use_cache or self._ops_cache is not None:
            return self
        ops_cache = [None] * self._OP_COUNT
        ops_cache[self._OP_SLASH] = ''.join(self._extract_slash_helper([]))
        ops_cache[self._OP_REMOVE_FEATURES] = self.from_cache(self.remove_features())
        ops_cache[self._OP_SIMPLIFY] = self.from_cache(self.simplify())
        ops_cache[self._OP_REMOVE_WILDCARDS] = self.from_cache(self.remove_wildcards())
        ops_cache[self._OP_REMOVE_UNIFY_FALSE] = [self.from_cache(x) for x in self.extract_unify_atoms(False)]
        uatoms = self.extract_unify_atoms(True)
        catoms = []
        for u in uatoms:
            catoms.append([self.from_cache(a) for a in u])
        ops_cache[self._OP_REMOVE_UNIFY_TRUE] = catoms
        self._ops_cache = ops_cache
        return self

    def simplify(self):
        """Simplify the CCG category. Removes features and converts non-sentence atoms to NP.

        Returns:
            A Category instance.
        """
        if self._ops_cache is not None:
            return self._ops_cache[self._OP_SIMPLIFY]
        return Category(self._TypeChangeNtoNP.sub('NP', self._TypeSimplify.sub('', self._signature)), conj=self.isconj)

    def clean(self, deep=False):
        """Clean predicate-argument tags from a category.

        Args:
            deep: If True clean atoms and functor tags, else only clean functor tags.

        Returns:
            A Category instance.
        """
        if deep:
            newcat = Category(self._CleanPredArg1.sub('', self._CleanPredArg3.sub('', self.signature)))
        else:
            newcat = Category(self._CleanPredArg1.sub('', self._CleanPredArg2.sub(')', self.signature)))
        while not newcat.isfunctor and newcat.signature[0] == '(' and newcat.signature[-1] == ')':
            newcat = Category(newcat.signature[1:-1])
        return newcat

    def complete_tags(self, tag=900):
        """Add predicate argument tags to atoms that don't have a tag.

        Args:
            tag: Optional starting integer tag.

        Returns:
            A Category instance.
        """
        atoms = self.extract_unify_atoms(False)
        chg = []
        orig = tag
        for a in atoms:
            ca = a.clean(True)
            if ca == a:
                chg.append('%s_%d' % (a.signature, tag))
                tag += 1
            else:
                chg.append(a.signature)
        if tag == orig:
            return self
        sig = self._signature
        for a in atoms:
            sig = sig.replace(a.signature, '%s')
        chg.reverse()
        sig %= tuple(chg)
        cat = Category(sig)
        assert cat.clean(True) == self.clean(True)
        return cat

    def trim_functor_tag(self):
        """Trim functor predarg tags.

        Returns:
            A tuple of the trimmed category and the tag. If no tag was found None is returned as the tag.
        """
        if not self.isfunctor:
            if self._signature[0] == '(':
                m = self._TrailingFunctorPredArgTag.match(self._signature)
                if m is not None:
                    tag = m.group('idx')
                    return Category(self._signature[1:-len(tag)-2]), tag
        return self, None

    def remove_wildcards(self):
        """Remove wildcards from the category.

        Returns:
            A Category instance.
        """
        if self._ops_cache is not None:
            return self._ops_cache[self._OP_REMOVE_WILDCARDS]
        if '[X]' in self._signature:
            return Category(self._signature.replace('[X]', ''), self.isconj)
        return self

    def remove_features(self):
        """Remove features and wildcards from the category.

        Returns:
            A Category instance.
        """
        if self._ops_cache is not None:
            return self._ops_cache[self._OP_REMOVE_FEATURES]
        return Category(self._Feature.sub('', self._signature))

    def _extract_atoms_helper(self, atoms):
        if self.isfunctor:
            atoms = self.argument_category._extract_atoms_helper(atoms)
            return self.result_category._extract_atoms_helper(atoms)
        else:
            atoms.append(self)
            return atoms

    def _extract_slash_helper(self, slashes):
        if self.isfunctor:
            slashes = self.argument_category._extract_slash_helper(slashes)
            slashes.append(self.slash)
            slashes = self.result_category._extract_slash_helper(slashes)
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
            if self._ops_cache is not None:
                return self._ops_cache[int(follow)]
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
        if self == other:
            return True
        if self in [CAT_PP, CAT_NP, CAT_Sadj, CAT_N] and other in [CAT_PP, CAT_NP, CAT_Sadj, CAT_N]:
            return True
        s1 = self.signature
        s2 = other.signature
        if s1 == s2 or (s1[0] == 'N' and s2[0] == 'N'):
            return True
        if s1[0] == 'S' and s2[0] == 'S':
            return (len(s1) == 1 or len(s2) == 1) \
                   or (self == CAT_Sto and other == CAT_Sb) \
                   or (self == CAT_Sb and other == CAT_Sto) \
                   or (self == CAT_Sdcl and other == CAT_Sem) \
                   or (self == CAT_Sem and other == CAT_Sdcl)
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
            slash1 = ''.join(self._extract_slash_helper([])) if self._ops_cache is None \
                else self._ops_cache[self._OP_SLASH]
            slash2 = ''.join(other._extract_slash_helper([])) if other._ops_cache is None \
                else other._ops_cache[other._OP_SLASH]
            return slash1 == slash2
        return self.can_unify_atom(other)

    def get_scope_count(self):
        """Get the number of scopes in a functor."""
        n = 0
        cat = self
        while cat.isfunctor:
            cat = cat.result_category
            n += 1
        return n


# Load cache after we have created the Category class
try:
    Category.load_cache(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'categories.dat'))
except Exception as e:
    # TODO: log warning
    print(e)


## @{
## @ingroup gconst
## @defgroup ccgcat CCG Categories

CAT_NUM = Category.from_cache('N[num]')
CAT_EMPTY = Category()
CAT_COMMA = Category.from_cache(',')
CAT_CONJ = Category.from_cache('conj')
CAT_CONJ_CONJ = Category.from_cache(r'conj\conj')
CAT_CONJCONJ = Category.from_cache(r'conj/conj')
CAT_LQU = Category.from_cache('LQU')
CAT_RQU = Category.from_cache('RQU')
CAT_LRB = Category.from_cache('LRB')
CAT_RRB = Category.from_cache('RRB')
CAT_N = Category.from_cache('N')
CAT_NP = Category.from_cache('NP')
CAT_NPthr = Category.from_cache('NP[thr]')
CAT_NPexpl = Category.from_cache('NP[expl]')
CAT_PP = Category.from_cache('PP')
CAT_PR = Category.from_cache('PR')
CAT_PREPOSITION = Category.from_cache('PP/NP')
CAT_SEMICOLON = Category.from_cache(';')
CAT_Sadj = Category.from_cache('S[adj]')
CAT_Sdcl = Category.from_cache('S[dcl]')
CAT_Sem = Category.from_cache('S[em]')
CAT_Sq = Category.from_cache('S[q]')
CAT_Sb = Category.from_cache('S[b]')
CAT_Sto = Category.from_cache('S[to]')
CAT_Swq = Category.from_cache('S[wq]')
CAT_ADVERB = Category.from_cache(r'(S\NP)\(S\NP)')
CAT_POSSESSIVE_ARGUMENT = Category.from_cache(r'(NP/(N/PP))\NP')
CAT_POSSESSIVE_PRONOUN = Category.from_cache('NP/(N/PP)')
CAT_S = Category.from_cache('S')
CAT_ADJECTIVE = Category.from_cache('N/N')
CAT_DETERMINER = Category.from_cache('NP[nb]/N')
CAT_INFINITIVE = Category.from_cache(r'(S[to]\NP)/(S[b]\NP)')
CAT_NOUN = RegexCategoryClass(r'^N(?:\[[a-z]+\])?$')
CAT_NP_N = RegexCategoryClass(r'^NP(?:\[[a-z]+\])?/N$')
CAT_NP_NP = RegexCategoryClass(r'^NP(?:\[[a-z]+\])?/NP$')
CAT_Sany = RegexCategoryClass(r'^S(?:\[[a-z]+\])?$')
CAT_PPNP = Category.from_cache('PP/NP')
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
                - 'PASS': unary pass through
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

    @property
    def ruleclass(self):
        return self._ruleClass

    @property
    def rulename(self):
        return self._ruleName

    def apply_rule_to_category(self, left, right):
        """Apply the rule to left and right categories and return a new result category

        Args:
            left: A Category instance.
            right: A Category instance.

        Returns:
            A Category instance.
        """
        if self == RL_LPASS:
            return left
        elif self == RL_RPASS:
            return right
        elif self in [RL_FX, RL_FC]:
            return Category.combine(left.result_category, right.slash, right.argument_category)
        elif self == RL_BA:
            return right.result_category
        elif self == RL_FA:
            return left.result_category
        elif self in [RL_BX, RL_BC]:
            return Category.combine(right.result_category, left.slash, left.argument_category)
        elif self in [RL_FS, RL_FXS]:
            return Category.combine(left.result_category.result_category, left.slash, right.argument_category)
        elif self in [RL_BS, RL_BXS]:
            return Category.combine(right.result_category.result_category, left.slash, left.argument_category)
        elif self in [RL_GFC, RL_GFX]:
            return Category.combine(Category.combine(left.result_category, right.result_category.slash,
                                                     right.result_category.argument_category),
                                    right.slash, right.argument_category)
        elif self in [RL_GBC, RL_GBX]:
            return Category.combine(Category.combine(right.result_category, left.result_category.slash,
                                                     left.result_category.argument_category),
                                    left.slash, left.argument_category)
        elif self == RL_LCONJ:
            return left
        elif self == RL_RCONJ:
            return right
        return None


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

## Forward and backward type-raising
## @verbatim
## Forward   X:a => T/(T\X): λxf.f(a)
## Backward  X:a => T\(T/X): λxf.f(a)
## @endverbatim
RL_TYPE_RAISE = Rule('TR')

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
RL_BS = Rule('BS', 'S')

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

## Special type changing rule.
## See LDC manual 2005T13 and unaryRules in EasySRL model folder.
RL_TC_CONJ = Rule('CONJ_TC')
RL_TC_ATOM = Rule('ATOM_TC')
RL_TCL_UNARY = Rule('L_UNARY_TC')
RL_TCR_UNARY = Rule('R_UNARY_TC')
## @}

# Special type changing rules - see LDC2005T13 document

## @cond
CAT_Sany__NP = RegexCategoryClass(r'^S(\[[a-z]+\])?[\\/]NP(\[conj\])?$')
CAT_NP_NP = Category.from_cache(r'NP\NP')
CAT_NPNP = Category.from_cache(r'NP/NP')
CAT_NP__NP = RegexCategoryClass(r'^(NP[\\/]NP(?:\[conj\])?|N[\\/]N)$')
CAT_Sng_NP = Category.from_cache(r'S[ng]\NP')
CAT_Sany_NP = RegexCategoryClass(r'S(?:\[[a-z]+\])?\\NP')
CAT_Sany_Sany = RegexCategoryClass(r'^S(?:\[[a-z]+\])?\\S(?:\[[a-z]+\])?$')
CAT_SanySany = RegexCategoryClass(r'^S(?:\[[a-z]+\])?\\S(?:\[[a-z]+\])?$')
CAT_SanySany = RegexCategoryClass(r'^S(?:\[[a-z]+\])?\\S(?:\[[a-z]+\])?$')
CAT_Sany_NP__Sany_NP = RegexCategoryClass(r'^\(S(\[[a-z]+\])?\\NP\)[\\/]\(S(\[[a-z]+\])?\\NP\)$')
CAT_S_NP_S_NP = Category.from_cache(r'(S\NP)\(S\NP)')
CAT_S_NPS_NP = Category.from_cache(r'(S\NP)/(S\NP)')
CAT_Sadj_NP = Category.from_cache(r'S[adj]\NP')
CAT_S_NP = Category.from_cache(r'S\NP')
CAT_S_S = Category.from_cache(r'S\S')
## @endcond


def get_rule(left, right, result, exclude=None):
    """Check if left can be combined with right to produce result.

    Args:
        left: The left category.
        right: The right category.
        result: The result category.
        exclude: A list of exclusion id's. This is only used during testing.

    Returns:
        A production rule instance or None if the rule could not be found.
    """

    # Useful logic for category X.
    # - If X is not a functor, then X.result_category == X

    assert isinstance(left, Category)
    assert isinstance(right, Category)
    assert isinstance(result, Category)

    # Exclusion id's allow us to call this function multiple times on the same input.
    # This allows us to test whether the if-else logic has ambiguity. A test in ccg_test.py
    # parses the entire ccgbank and checks whether only one rule interpretation is possible. A 
    # repeated call should return None of we have no ambiguity in our logic, because the if-else
    # path is excluded after the first call.
    def notexcluded(x, num):
        return x is None or num not in x
    def xupdate(x, num):
        if x is not None:
            x.append(num)

    # Handle punctuation
    if left.ispunct and notexcluded(exclude, 13):
        xupdate(exclude, 13)
        if right.ispunct:
            return RL_LPASS
        elif right == CAT_EMPTY:
            return RL_LPASS
        elif right in [CAT_CONJ, CAT_CONJCONJ, CAT_CONJ_CONJ]:
            assert result == right
            return RL_RPASS
        elif right.can_unify(result):
            return RL_RPASS
        else:
            return RL_TCR_UNARY
    elif right.ispunct and notexcluded(exclude, 14):
        if exclude is not None:
            if left.ispunct:
                return None     # don't count as duplicate
        xupdate(exclude, 14)
        if left in [CAT_CONJ, CAT_CONJCONJ, CAT_CONJ_CONJ]:
            assert result == left
            return RL_LPASS
        elif left.can_unify(result) or left.ispunct:
            return RL_LPASS
        elif left.isatom and result.isatom:
            return RL_TC_ATOM
        elif result.result_category == result.argument_category.result_category and \
                left.can_unify(result.argument_category.argument_category):
            if result.isarg_right and result.argument_category.isarg_left:
                # X:a => T/(T\X): λxf.f(a)
                return RL_TYPE_RAISE
            elif result.isarg_left and result.argument_category.isarg_right:
                # X:a => T\(T/X): λxf.f(a)
                return RL_TYPE_RAISE
        else:
            return RL_TCL_UNARY

    if left.isconj and right != CAT_EMPTY and not right.ispunct and notexcluded(exclude, 0):
        if left == CAT_CONJ:
            if right == CAT_CONJ_CONJ:
                xupdate(exclude, 0)
                return RL_BA
            elif right.can_unify(result):
                #return RL_RCONJ
                xupdate(exclude, 0)
                assert right != CAT_CONJ
                return RL_RPASS
            elif result.ismodifier and result.argument_category.can_unify(right):
                xupdate(exclude, 0)
                return RL_TCR_UNARY
            elif result.isconj:
                # Section 3.7.2 LDC2005T13 manual
                xupdate(exclude, 0)
                return RL_TC_CONJ
        elif left == CAT_CONJCONJ and right == CAT_CONJ:
            xupdate(exclude, 0)
            return RL_FA
        elif left.can_unify(right):
            xupdate(exclude, 0)
            return RL_LCONJ
    elif right.isconj and not left.ispunct and notexcluded(exclude, 1):
        if exclude is not None:
            if left in [CAT_CONJ, CAT_CONJCONJ]:
                return None     # don't count as ambiguous rule
            exclude.append(1)
        if right == CAT_CONJ:
            if not left.can_unify(result):
                pass
            assert left.can_unify(result)
            return RL_LCONJ
            #return RL_TCL_UNARY
        elif left.can_unify(right):
            return RL_RCONJ
    elif left == CAT_EMPTY and notexcluded(exclude, 2):
        xupdate(exclude, 2)
        return RL_RPASS
    elif left == CAT_NP_NP and right == CAT_NUM and notexcluded(exclude, 3):
        xupdate(exclude, 3)
        return RL_RNUM
    elif right == CAT_EMPTY and notexcluded(exclude, 4):
        xupdate(exclude, 4)
        if result.result_category == result.argument_category.result_category and \
                        left.can_unify(result.argument_category.argument_category):
            if result.isarg_right and result.argument_category.isarg_left:
                # X:a => T/(T\X): λxf.f(a)
                return RL_TYPE_RAISE
            elif result.isarg_left and result.argument_category.isarg_right:
                # X:a => T\(T/X): λxf.f(a)
                return RL_TYPE_RAISE
        elif left.can_unify(result):
            return RL_LPASS
        elif left.isatom and result.isatom:
            return RL_TC_ATOM
        else:
            return RL_TCL_UNARY

    elif left.isarg_right and left.argument_category.can_unify(right) and \
            left.result_category.can_unify(result) and notexcluded(exclude, 5):
        xupdate(exclude, 5)
        # Forward Application
        # X/Y:f Y:a => X: f(a)
        return RL_FA
    elif left.isarg_right and right.isfunctor and left.argument_category.can_unify(right.result_category) and \
            Category.combine(left.result_category, right.slash, right.argument_category).can_unify(result) \
            and notexcluded(exclude, 6):
        if exclude is not None:
            if left == right and left.argument_category == right.argument_category \
                    and (left.isconj or right.isconj):
                return None # don't count as ambiguous rule N/N[conj] N/N => N/N
            exclude.append(6)
        if right.isarg_right:
            # Forward Composition
            # X/Y:f Y/Z:g => X/Z: λx􏰓.f(g(x))
            return RL_FC
        else:
            # Forward Crossing Composition
            # X/Y:f Y\Z:g => X\Z: λx􏰓.f(g(x))
            return RL_FX

    elif right.isarg_left and right.argument_category.can_unify(left) and right.result_category.can_unify(result) \
            and notexcluded(exclude, 7):
        xupdate(exclude, 7)
        # Backward Application
        # Y:a X\Y:f => X: f(a)
        return RL_BA
    elif right.isarg_left and left.isfunctor and right.argument_category.can_unify(left.result_category) \
            and Category.combine(right.result_category, left.slash, left.argument_category).can_unify(result) \
            and notexcluded(exclude, 8):
        if exclude is not None:
            if left == right and left.argument_category == right.argument_category \
                    and (left.isconj or right.isconj):
                return None
            exclude.append(8)
        if left.isarg_left:
            # Backward Composition
            # Y\Z:g X\Y:f => X\Z: λx􏰓.f(g(x))
            return RL_BC
        else:
            # Backward Crossing Composition
            # Y/Z:g X\Y:f => X/Z: λx􏰓.f(g(x))
            return RL_BX

    elif left.argument_category.can_unify(right.argument_category) and left.result_category.isarg_right and \
            left.slash == right.slash and left.result_category.argument_category.can_unify(right.result_category) and \
            Category.combine(left.result_category.result_category, left.slash, right.argument_category).can_unify(result) \
            and notexcluded(exclude, 9):
        xupdate(exclude, 9)
        if right.isarg_right:
            # Forward Substitution
            # (X/Y)/Z:f Y/Z:g => X/Z: λx􏰓.fx􏰨(g􏰨(x􏰩􏰩))
            return RL_FS
        else:
            # Forward Crossing Substitution
            # (X/Y)\Z:f Y\Z:g => X\Z: λx􏰓.fx􏰨(g􏰨(x􏰩􏰩))
            return RL_FXS

    elif right.argument_category.can_unify(left.argument_category) and right.result_category.isarg_left and \
            left.slash == right.slash and right.result_category.argument_category.can_unify(left.result_category) and \
            Category.combine(right.result_category.result_category, left.slash, left.argument_category).can_unify(result) \
            and notexcluded(exclude, 10):
        xupdate(exclude, 10)
        if right.isarg_left:
            # Backward Substitution
            # Y\Z:g (X\Y)\Z:g => X/Z: λx􏰓.fx􏰨(g􏰨(x􏰩􏰩))
            return RL_BS
        else:
            # Backward Crossing Substitution
            # Y/Z:g (X\Y)/Z:f => X/Z: λx􏰓.fx􏰨(g􏰨(x􏰩􏰩))
            return RL_BXS

    elif left.isarg_right and right.result_category.slash == result.result_category.slash and \
            left.argument_category.can_unify(right.result_category.result_category) and \
            Category.combine(Category.combine(left.result_category, right.result_category.slash,
                                              right.result_category.argument_category), right.slash,
                             right.argument_category).can_unify(result) \
            and notexcluded(exclude, 11):
        xupdate(exclude, 11)
        if right.result_category.isarg_right:
            # Generalized Forward Composition
            # X/Y:f (Y/Z)/$:...λz.gz... => (X/Z)/$: ...λz.f(g(z...))
            return RL_GFC
        else:
            # Generalized Forward Crossing Composition
            # X/Y:f (Y\Z)$:...λz.gz... => (X\Z)$: ...λz.f(g(z...))
            return RL_GFX

    elif right.isarg_left and left.result_category.slash == result.result_category.slash and \
            right.argument_category.can_unify(left.result_category.result_category) and \
            Category.combine(Category.combine(right.result_category, left.result_category.slash,
                                              left.result_category.argument_category), left.slash,
                             left.argument_category).can_unify(result) \
            and notexcluded(exclude, 12):
        xupdate(exclude, 12)
        if left.result_category.isarg_left:
            # Generalized Backward Composition
            # (Y\Z)$:...λz.gz... X\Y:f => (X\Z)$: ...λz.f(g(z...))
            return RL_GBC
        else:
            # Generalized Backward Crossing Composition
            # (Y/Z)/$:...λz.gz... X\Y:f => (X/Z)/$: ...λz.f(g(z...))
            return RL_GBX
    # TODO: generalized substitution

    return None




