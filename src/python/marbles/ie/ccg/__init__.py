# -*- coding: utf-8 -*-
"""CCG Categories, Rules, and CCGBANK parser"""
from __future__ import unicode_literals, print_function

import os
import re

import datapath
import logging
from marbles import safe_utf8_encode, safe_utf8_decode, future_string
from marbles.ie.utils.cache import Cache, Freezable
from marbles.ie.utils.vmap import Dispatchable

_logger = logging.getLogger(__name__)


ISCONJMASK   = 0x00000001
FEATURE_CONJ = 0x00000002
FEATURE_ADJ  = 0x00000004
FEATURE_PSS  = 0x00000008
FEATURE_NG   = 0x00000010
FEATURE_EM   = 0x00000020
FEATURE_DCL  = 0x00000040
FEATURE_TO   = 0x00000080
FEATURE_B    = 0x00000100
FEATURE_BEM  = 0x00000100
FEATURE_ASUP = 0x00000200
FEATURE_FOR  = 0x00000400
FEATURE_POSS = 0x00000800
FEATURE_PT   = 0x00001000
FEATURE_Q    = 0x00002000
FEATURE_WQ   = 0x00004000
FEATURE_QEM  = 0x00008000
FEATURE_INV  = 0x00010000
FEATURE_NUM  = 0x00020000
FUNCTOR_RETURN_PREP_CHECKED = 0x80000000
FUNCTOR_RETURN_PREP = 0x40000000
FUNCTOR_RETURN_MOD_CHECKED = 0x20000000
FUNCTOR_RETURN_MOD = 0x10000000
FUNCTOR_RETURN_ENTITY_MOD_CHECKED = 0x08000000
FUNCTOR_RETURN_ENTITY_MOD = 0x04000000


WS = re.compile(r'\s*')
NDS = re.compile(r'(?:\s*\(<)|(?:\s*>\s*\)\s*)', re.MULTILINE)


## @ingroup gfn
def parse_ccg_derivation2(ccgbank, nbest=1):
    """Parse a ccg derivation and return a parse tree."""
    nodes = filter(lambda y: len(y) != 0, map(lambda x: x.strip(), NDS.split(ccgbank)))
    root = []
    stk = [root]
    level = 0
    for nd in nodes:
        pt = stk[-1]
        if nd[0] == 'T':
            assert nd[-1] == '>'
            level += 1
            pt.append([])
            pt = pt[-1]
            stk.append(pt)
            toks = WS.split(nd[0:-1])
            # Nodes contain 3 fields + T
            # <T CCGcat head count>
            assert len(toks) == 4
            pt.append([toks[1], int(toks[2]), int(toks[3])])
        elif nd[0] == 'L':
            toks = WS.split(nd)
            # Leaf nodes contain five fields + L
            # <L CCGcat mod_POS-tag orig_POS-tag word PredArgCat>
            assert len(toks) == 6
            pt.append([toks[1], toks[4], toks[2], toks[3], toks[5], 'L'])
        else:
            assert nd[0] == ')'
            toks = WS.split(nd)
            level -= len(toks)
            assert level >= 0
            for i in range(len(toks)):
                pt.append('T')
                stk.pop()
                pt = stk[-1]
    assert level == 0
    # nbest parsing returns multiple trees
    assert len(root) == nbest
    return root[0] if len(root) == 1 else root


## @ingroup gfn
def extract_features(signature):
    """Extract features from a signature.

    Args:
        signature: The CCG signature.

    Returns:
        A tuple of the modified signature and the feature mask.
    """
    features = FEATURE_CONJ if '[conj]' in signature else 0
    #if features:
    #    signature = signature.replace('[conj]', '')
    features |= FEATURE_ADJ if '[adj]' in signature else 0
    features |= FEATURE_PSS if '[pss]' in signature else 0
    features |= FEATURE_NG if '[ng]' in signature else 0
    features |= FEATURE_EM if '[em]' in signature else 0
    features |= FEATURE_DCL if '[dcl]' in signature else 0
    features |= FEATURE_TO if '[to]' in signature else 0
    features |= FEATURE_B if '[b]' in signature else 0
    features |= FEATURE_BEM if '[bem]' in signature else 0
    features |= FEATURE_ASUP if '[asup]' in signature else 0
    features |= FEATURE_FOR if '[for]' in signature else 0
    features |= FEATURE_POSS if '[poss]' in signature else 0
    features |= FEATURE_PT if '[pt]' in signature else 0
    features |= FEATURE_Q if '[q]' in signature else 0
    features |= FEATURE_WQ if '[wq]' in signature else 0
    features |= FEATURE_QEM if '[qem]' in signature else 0
    features |= FEATURE_INV if '[inv]' in signature else 0
    features |= FEATURE_NUM if '[num]' in signature else 0
    return signature, features

## @ingroup gfn
def iscombinator_signature(signature):
    """Test if a CCG type is a combinator. A combinator expects a function as the argument and returns a
    function.

    Args:
        signature: The CCG signature.

    Returns:
        True if the signature is a combinator

    See Also:
        marbles.ie.ccg.cat.Category
    """

    return len(signature) > 2 and signature[0] == '(' and (signature.endswith(')') or signature.endswith(')[conj]'))


## @ingroup gfn
def isfunction_signature(signature):
    """Test if a DRS, or CCG type, is a function.

    Args:
        signature: The DRS or CCG signature.

    Returns:
        True if the signature is a function.

    See Also:
        marbles.ie.ccg.ccgcat.Category
    """
    return len(signature.replace('\\', '/').split('/')) > 1


## @ingroup gfn
def split_signature(signature):
    """Split a DRS, or CCG type, into argument and return types.

    Args:
        signature: The DRS or CCG signature.

    Returns:
        A 3-tuple of <return type>, [\/], <argument type>. Basic non-functor types are encoded:
        <basic-type>, '', ''

    See Also:
        marbles.ie.ccg.ccgcat.Category
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
            if ret.endswith(')') and ret.startswith('('):
                ret = ret[1:-1]
            if arg.startswith('('):
                if arg.endswith(')'):
                    arg = arg[1:-1]
                elif arg.endswith(')[conj]'):
                    arg = arg[1:-7]
            elif arg.endswith('[conj]'):
                arg = arg[0:-6]
            return ret, signature[i], arg
    return signature[0:-6], '', '' if signature.endswith('[conj]') else signature, '', ''


## @ingroup gfn
def join_signature(sig):
    """Join a split signature.

    Args:
        sig: The split signature tuple returned from split_signature().

    Returns:
        A signature string.

    See Also:
        split_signature()
        marbles.ie.ccg.ccgcat.Category
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
        return self._srch.match(category.signature) is not None


## @cond
_TypeChangerAll = re.compile(r'S\[adj\]|NP(?:\[[a-z]+\])?|N(?:\[[a-z]+\])?|PP')
_TypeChangerNoPP = re.compile(r'S\[adj\]|NP(?:\[[a-z]+\])?|N(?:\[[a-z]+\])?')
_TypeChangerS = re.compile(r'S(?!\[adj\])(?:\[[a-z]+\])?')
_TypeSimplify = re.compile(r'(?<=NP)\[(nb|conj)\]|(?<=S)\[([a-z]+|X)\]')
_TypeChangeNtoNP = re.compile(r'N(?=\\|/|\)|$)')
_CleanPredArg1 = re.compile(r':[A-Z]|\{_\*\}')
_CleanPredArg2 = re.compile(r'\)_\d+')
_CleanPredArg3 = re.compile(r'_\d+')
_TrailingFunctorPredArgTag = re.compile(r'^.*\)_(?P<idx>\d+)$')
_Wildcard = re.compile(r'[X]')
_Feature = re.compile(r'\[([a-z]+|X)\]')
_Wildtag = re.compile(r'\{_.*\}')
_cache = Cache()
_use_cache = 0
_Isconj = re.compile(r'(?<!\[)conj')
_OP_EXTRACT_UNIFY_FALSE = 0 # Must be zero
_OP_EXTRACT_UNIFY_TRUE = 1  # Must be one
_OP_REMOVE_WILDCARDS = 2
_OP_SIMPLIFY = 3
_OP_REMOVE_FEATURES = 4
_OP_SLASH = 5
_OP_RESULT_CAT = 6
_OP_ARG_CAT = 7
_OP_REMOVE_CONJ_FEATURE = 8
_OP_ADD_CONJ_FEATURE = 9
_OP_COUNT = 10
## @endcond


class Category(Freezable):
    """CCG Category"""
    def __init__(self, signature=None, features=0):
        """Constructor.

        Args:
            signature: A CCG type signature string.
            features: Internally used by simplify. Never set this explicitly.
        """
        super(Category, self).__init__()
        self._ops_cache = None
        if signature is None:
            self._signature = ''
            self._splitsig = '', '', ''
            self._features = FUNCTOR_RETURN_PREP_CHECKED | FUNCTOR_RETURN_MOD_CHECKED
        else:
            if isinstance(signature, (str, unicode)):
                self._signature, self._features = extract_features(signature)
                self._features |= features
                self._features |= ISCONJMASK if _Isconj.match(signature) is not None else 0
            else:
                self._signature = signature.signature
                self._features = signature._features | features
            self._splitsig = split_signature(self._signature)
            # Don't need to handle | (= any) because parse tree has no ambiguity
            assert self._splitsig[1] in ['/', '\\', '']

    ## @cond
    def __str__(self):
        return safe_utf8_encode(self._signature)

    def __unicode__(self):
        return safe_utf8_decode(self._signature)

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        if isinstance(other, AbstractCategoryClass):
            return other.ismember(self)
        elif self.isfrozen and other.isfrozen:
            return self is other
        return self._signature == other.signature

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(future_string(self))
    ## @endcond

    @classmethod
    def from_cache(cls, signature):
        if 0 == cls._use_cache:
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
                if cat.isconj:
                    todo.append(cat.remove_conj_feature())
                cat = cat.result_category()
            todo.append(cat)
            todo.append(cat.simplify())
            todo.append(cat.remove_features())
            todo.append(cat.remove_wildcards())
            if cat.isconj:
                todo.append(cat.remove_conj_feature())
            todo = set(todo)
            if cls._use_cache > 0:
                for c in todo:
                    if c.signature not in cls._cache:
                        cls._cache[c.signature] = c
            else:
                for c in todo:
                    cls._cache.addinit((c.signature, c))
            for c in todo:
                cat = cls._cache[c.signature]
                cat.initialize_ops_cache()
            for c in todo:
                cat = cls._cache[c.signature]
                cat.freeze()
            return retcat

    @classmethod
    def save_cache(cls, filename):
        """Save the cache to a file.

        Args:
            filename: The file name and path.

        Remarks:
            Is threadsafe.
        """
        if 0 != cls._use_cache:
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

            # Ensure these are in the read only section
            sigs.append('conj')
            sigs.append(r'conj\conj')
            sigs.append(r'conj/conj')
            sigs.append(',')
            sigs.append('.')
            sigs.append(':')
            sigs.append(';')
            sigs.append('N[conj]')
            sigs.append('N[num]')
            sigs.append('NP[expl]')
            sigs.append('NP[conj]')
            sigs.append('NP[thr]')
            sigs.append('PR')
            sigs.append('LQU')
            sigs.append('RQU')
            sigs.append('LRB')
            sigs.append('RRB')
            sigs.append('S[for]')
            sigs.append('S[X]')
            sigs.append('S')

            sigs.append(r'NP/PR')
            sigs.append(r'NP/(S[b]/NP)')
            sigs.append(r'N\N')
            sigs.append(r'NP\NP')
            sigs.append(r'(NP/(N/PP))\NP')
            sigs.append(r'NP/(N/PP)')
            sigs.append(r'S[X]\NP')
            sigs.append(r'S\NP')
            sigs.append(r'S/NP')
            sigs.append(r'S[pt]/NP')
            sigs.append(r'S\(S/NP)')
            sigs.append(r'S[pt]')
            sigs.append(r'(S\NP)/((S\NP)\PP)')
            sigs.append(r'(S\NP)\PP')
            sigs.append(r'(S\NP)\((S\NP)/PP)')

            # wildcards
            sigs.append(r'S[X]\NP')
            sigs.append(r'(S[X]\NP)/(S[X]\NP)')
            sigs = set(sigs)

            pairs = [(x, Category(x)) for x in filter(lambda s: len(s) != 0 and s[0] != '#',
                                                      map(lambda p: p.strip(), sigs))]
            #conj = [y[0]+'[conj]' for y in filter(lambda x: not x[1].isconj, pairs)]
            #pairs.extend(map(lambda x: (x, Category(x)), conj))
            cache.initialize(pairs)
        cls._cache = cache
        cls._use_cache = -1
        for k, v in pairs:
            v.initialize_ops_cache()
            v.freeze()

        cls._use_cache = 1

    @classmethod
    def finalize_cache(cls):
        """Call after loading of the cache but before module import completes.

        Remarks:
            Not threadsafe.
        """
        cls._use_cache = -1

        # Cache can change size during iteration so get key,values first
        cats = [v for k, v in cls._cache]
        for v in cats:
            v.test_returns_modifier()
            v.test_returns_preposition()
            v.test_returns_entity_modifier()

        cls._use_cache = 1

    @classmethod
    def clear_cache(cls):
        """Clear the category cache.

        Remarks:
            Not threadsafe.
        """
        cls._use_cache = 0
        oldcache = cls._cache
        cls._cache = Cache()
        for k, v in oldcache:
            v.freeze(False)
            v.clear_ops_cache()

    @classmethod
    def copy_cache(cls):
        """Copy the category cache.

        Returns:
            A list of key,value tuples.

        Remarks:
            Threadsafe.
        """
        return [x for x in cls._cache]

    @classmethod
    def initialize_cache(cls, cats):
        """Initialize the cache with categories.

        Args:
            cats: A list of categories.
        """
        cls._use_cache = 0
        pairs = {}
        for cat in cats:
            if isinstance(cat, (str, unicode)):
                cat = Category(cat)
            stk = [cat]
            while len(stk) != 0:
                cat = stk.pop()
                if cat.isfunctor:
                    stk.append(cat.result_category())
                    stk.append(cat.argument_category())
                pairs[cat.signature] = cat
                # Avoid copying string in key, value
                c = cat.simplify()
                pairs[c.signature] = c
                c = cat.remove_features()
                pairs[c.signature] = c
                c = cat.remove_wildcards()
                pairs[c.signature] = c
                if cat.isconj:
                    c = cat.remove_conj_feature()
                    pairs[c.signature] = c
        cls._cache.initialize(pairs.iteritems())
        cls._use_cache = 1

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
        if 0 != cls._use_cache and cacheable:
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
        return self.has_any_features(ISCONJMASK | FEATURE_CONJ)

    @property
    def istype_raised(self):
        """Test if the CCG category is type raised."""
        # X|(X|Y), where | = any slash
        r = self.argument_category()
        return r.isfunctor and r.result_category() == self.result_category()

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
    def issentence(self):
        """True if the result of all applications is a sentence, i.e. an S[?] type."""
        return not self.isempty and self.extract_unify_atoms()[-1][0] == CAT_Sany

    @property
    def slash(self):
        """Get the slash for a functor category."""
        return self._splitsig[1]

    @property
    def signature(self):
        """Get the CCG type as a string."""
        return self._signature

    def has_all_features(self, features):
        """Test if the category has all the features specified."""
        return features != 0 and (self._features & features) == features

    def has_any_features(self, features):
        """Test if the category has any of the features specified."""
        return (self._features & features) != 0

    def result_category(self, cacheable=True):
        """Get the return category if a functor.

        Args:
            cacheable: Optional flag indicating the result can be added to the cache.

        Returns:
            A Category instance.
        """
        if 0 != self._use_cache and cacheable:
            if self._ops_cache:
                return self._ops_cache[_OP_RESULT_CAT]
            return self.from_cache(self._splitsig[0]) if self.isfunctor else CAT_EMPTY
        return Category(self._splitsig[0]) if self.isfunctor else CAT_EMPTY

    def argument_category(self, cacheable=True):
        """Get the argument category if a functor.

        Args:
            cacheable: Optional flag indicating the result can be added to the cache.

        Returns:
            A Category instance.
        """
        if 0 != self._use_cache and cacheable:
            if self._ops_cache:
                return self._ops_cache[_OP_ARG_CAT]
            return self.from_cache(self._splitsig[2]) if self.isfunctor else CAT_EMPTY
        return Category(self._splitsig[2]) if self.isfunctor else CAT_EMPTY

    def clear_ops_cache(self):
        self._ops_cache = None

    def initialize_ops_cache(self):
        if 0 >= self._use_cache or self._ops_cache is not None:
            return self
        ops_cache = [None] * _OP_COUNT
        ops_cache[_OP_SLASH] = ''.join(self._extract_slash_helper([]))
        ops_cache[_OP_REMOVE_FEATURES] = self.from_cache(self.remove_features())
        ops_cache[_OP_REMOVE_CONJ_FEATURE] = self.from_cache(self.remove_conj_feature())
        ops_cache[_OP_ADD_CONJ_FEATURE] = self.from_cache(self.add_conj_feature())
        ops_cache[_OP_SIMPLIFY] = self.from_cache(self.simplify())
        ops_cache[_OP_REMOVE_WILDCARDS] = self.from_cache(self.remove_wildcards())
        if self.extract_unify_atoms(False) is None:
            pass
        ops_cache[_OP_EXTRACT_UNIFY_FALSE] = [self.from_cache(x) for x in self.extract_unify_atoms(False)]
        ops_cache[_OP_RESULT_CAT] = self.result_category()
        ops_cache[_OP_ARG_CAT] = self.argument_category()
        uatoms = self.extract_unify_atoms(True)
        catoms = []
        for u in uatoms:
            catoms.append([self.from_cache(a) for a in u])
        ops_cache[_OP_EXTRACT_UNIFY_TRUE] = catoms
        self._ops_cache = ops_cache
        return self

    def simplify(self):
        """Simplify the CCG category. Removes features and converts non-sentence atoms to NP.

        Returns:
            A Category instance.
        """
        if self._ops_cache is not None:
            return self._ops_cache[_OP_SIMPLIFY]
        return Category(_TypeChangeNtoNP.sub('NP', _TypeSimplify.sub('', self._signature)), features=self._features)

    def clean(self, deep=False):
        """Clean predicate-argument tags from a category.

        Args:
            deep: If True clean atoms and functor tags, else only clean functor tags.

        Returns:
            A Category instance.
        """
        if deep:
            newcat = Category(_CleanPredArg1.sub('', _CleanPredArg3.sub('', self.signature)))
        else:
            newcat = Category(_CleanPredArg1.sub('', _CleanPredArg2.sub(')', self.signature)))
        while not newcat.isfunctor and len(newcat.signature) >= 2 \
                and newcat.signature[0] == '(' and newcat.signature[-1] == ')':
            newcat = Category(newcat.signature[1:-1])
        return newcat if not deep else Category.from_cache(newcat.signature)

    def complete_tags(self, tag=900):
        """Add predicate argument tags to atoms that don't have a tag.

        Args:
            tag: Optional starting integer tag.

        Returns:
            A Category instance.
        """
        atoms = self.extract_unify_atoms(follow=False, cacheable=False)
        chg = []
        orig = tag
        if self.ismodifier:
            seen = {}
            for a in atoms:
                ca = a.clean(True)
                if ca == a:
                    try:
                        sig = seen[a]
                        chg.append(sig)
                    except Exception:
                        sig = '%s_%d' % (a.signature, tag)
                        chg.append(sig)
                        seen[a] = sig
                        tag += 1
                else:
                    chg.append(a.signature)
        else:
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
                m = _TrailingFunctorPredArgTag.match(self._signature)
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
            return self._ops_cache[_OP_REMOVE_WILDCARDS]
        if '[X]' in self._signature:
            return Category(self._signature.replace('[X]', ''), self._features)
        return self

    def remove_features(self):
        """Remove features and wildcards from the category.

        Returns:
            A Category instance.
        """
        if self._ops_cache is not None:
            return self._ops_cache[_OP_REMOVE_FEATURES]
        return Category(_Feature.sub('', self._signature))

    def add_conj_feature(self):
        """Add [conj] to a category.

        Returns:
             A Category instance with the feature
        """
        if self._ops_cache is not None:
            return self._ops_cache[_OP_ADD_CONJ_FEATURE]
        if self.has_any_features(FEATURE_CONJ):
            return self
        elif self.isatom and self in [CAT_N, CAT_PP, CAT_NP]:
            return Category(self._signature + '[conj]')
        else:
            args = [(self.result_category(), self.slash)]
            cat = self.argument_category()
            while cat.isfunctor and not cat.simplify().can_unify(CAT_S_NP):
                args.append((cat.result_category(), cat.slash))
                cat = cat.argument_category()
            if cat.isatom and cat in [CAT_N, CAT_PP, CAT_NP]:
                cat = Category(cat.signature + '[conj]')
                while args:
                    rcat = args.pop()
                    cat = Category.combine(rcat[0], rcat[1], cat, cacheable=False)
                return cat
        return self

    def remove_conj_feature(self):
        """Remove conj feature from the category.

        Returns:
            A Category instance without the feature.
        """
        if self._ops_cache is not None:
            return self._ops_cache[_OP_REMOVE_CONJ_FEATURE]
        return Category(self._signature.replace('[conj]', ''))

    def _extract_atoms_helper(self, atoms, cacheable):
        # Recursive but only gets called during module load, after which its in the ops cache.
        if self.isfunctor:
            atoms = self.argument_category(cacheable)._extract_atoms_helper(atoms, cacheable)
            return self.result_category(cacheable)._extract_atoms_helper(atoms, cacheable)
        else:
            atoms.append(self)
            return atoms

    def _extract_slash_helper(self, slashes):
        # Recursive but only gets called during module load, after which its in the ops cache.
        if self.isfunctor:
            slashes = self.argument_category()._extract_slash_helper(slashes)
            slashes.append(self.slash)
            slashes = self.result_category()._extract_slash_helper(slashes)
        return slashes

    def extract_unify_atoms(self, follow=True, cacheable=True):
        """Extract the atomic categories for unification.

        Args:
            follow: If True, return atoms for argument and result functors recursively. If false return the atoms
                for the category.
            cacheable: Optional flag indicating the result can be added to the cache.

        Returns:
            A list of sub-lists containing atomic categories. Each sub-list is ordered for unification at the functor
            scope it is applied. The order matches the lambda variables at that scope. Functor scope is: argument,
            result.argument, result.result.argument, ..., result.result...result.

        See Also:
            can_unify()

        Remarks:
            This method is used to create a marbles.ie.drt.compose.FunctorProduction from a category.
        """
        if self.isempty:
            return []
        elif self.isatom:
            return [[self]] if follow else [self]
        elif self.isfunctor:
            if self._ops_cache is not None:
                return self._ops_cache[int(follow)]
            if follow:
                cat = self
                atoms = []
                while cat.isfunctor:
                    aa = cat.argument_category(cacheable)._extract_atoms_helper([], cacheable)
                    atoms.append(aa)
                    cat = cat.result_category(cacheable)
                atoms.append([cat])
                return atoms
            else:
                return self._extract_atoms_helper([], cacheable)
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
        if self.remove_features() in [CAT_PP, CAT_NP, CAT_N] and other.remove_features() in [CAT_PP, CAT_NP, CAT_N]:
            return True
        s1 = self.remove_conj_feature()
        s2 = other.remove_conj_feature()
        if s1 == s2 or (s1.signature[0] == 'N' and s2.signature[0] == 'N'):
            return True
        if s1.signature[0] == 'S' and s2.signature[0] == 'S':
            return (len(s1.signature) == 1 or len(s2.signature) == 1) \
                   or (s1 == CAT_Sto and other == CAT_Sb) \
                   or (s1 == CAT_Sb and other == CAT_Sto) \
                   or (s1 == CAT_Sdcl and s2 == CAT_Sem) \
                   or (s1 == CAT_Sem and s2 == CAT_Sdcl) \
                   or s1 == CAT_SX or s2 == CAT_SX
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
                else self._ops_cache[_OP_SLASH]
            slash2 = ''.join(other._extract_slash_helper([])) if other._ops_cache is None \
                else other._ops_cache[_OP_SLASH]
            return slash1 == slash2
        return self.can_unify_atom(other)

    def get_scope_count(self):
        """Get the number of scopes in a functor."""
        n = 0
        cat = self
        while cat.isfunctor:
            cat = cat.result_category()
            n += 1
        return n

    def test_returns_modifier(self):
        """Test if the functor returns a modifier.

        Returns:
            True if a functor and it returns a modifier category.
        """
        # Cache result
        features = self._features
        if 0 == (features & FUNCTOR_RETURN_MOD_CHECKED):
            result = self
            while not result.isatom:
                result = result.result_category()
                if result.ismodifier:
                    features |= FUNCTOR_RETURN_MOD
                    break
            features |= FUNCTOR_RETURN_MOD_CHECKED
            self._features = features
        return 0 != (features & FUNCTOR_RETURN_MOD)

    def test_returns_preposition(self):
        """Test if the functor returns a preposition.

        Returns:
            True if a functor and it returns a CAT_PP category.
        """
        # Cache result
        features = self._features
        if 0 == (features & FUNCTOR_RETURN_PREP_CHECKED):
            if self == CAT_POSSESSIVE_ARGUMENT or self == CAT_POSSESSIVE_PRONOUN:
                features |= FUNCTOR_RETURN_PREP
            else:
                result = self
                ismod = False
                while not result.isatom:
                    ismod = result.ismodifier   # but not a (PP|PP)|$
                    result = result.result_category()
                if not ismod and result == CAT_PP:
                    features |= FUNCTOR_RETURN_PREP
            features |= FUNCTOR_RETURN_PREP_CHECKED
            self._features = features
        return 0 != (features & FUNCTOR_RETURN_PREP)

    def test_returns_entity_modifier(self):
        """Test if the functor returns any of: (N|N)$, (NP|NP)$, (PP|PP)$, (NP|PP)$, (PP|NP)$.

        Returns:
            True if a functor and it returns a entity modifier category.
        """
        # Cache result
        # Even though we don't do any locking this function is still threadsafe in that worst case
        # the caching doesnt work because of overwriting self._features. Eventually it will work
        # though and then its set forever. In addition we call this function when we add categories
        # to the category cache so it should always be set.
        features = self._features
        if 0 == (features & FUNCTOR_RETURN_ENTITY_MOD_CHECKED):
            result = self
            while not result.isatom:
                new_result = result.result_category()
                if new_result.isatom and new_result in [CAT_PP, CAT_NP, CAT_N] \
                        and result.argument_category() in [CAT_NP, CAT_PP, CAT_N]:
                    features |= FUNCTOR_RETURN_ENTITY_MOD
                    break
                result = new_result
            features |= FUNCTOR_RETURN_ENTITY_MOD_CHECKED
            self._features = features
        return 0 != (features & FUNCTOR_RETURN_ENTITY_MOD)

    def test_return(self, result_category, exact=False):
        """Test if the functor matches result_category or if it returns a category that matches result_category.
        The wildcard feature [X] can be used to match.

        Args:
            exact: If True then use equality test else use can_unify() test.

        Returns:
            True if a functor and it returns a category matching result_category.
        """
        return self.test_return_and_get(result_category, exact) is not None

    def test_return_and_get(self, result_category, exact=False):
        """Test if the functor matches result_category or if it returns a category that matches result_category. If
        True then return the matching category else return None. The wildcard feature [X] can be used to match.

        Args:
            exact: If True then use equality test else use can_unify() test.

        Returns:
            A category matching result_category.
        """
        # FIXME: Don't need recursion - use extract_unify_atoms(True)
        if (exact and self == result_category) or (not exact and self.can_unify(result_category)):
            return self
        elif self.isatom:
            return None
        return self.result_category().test_return_and_get(result_category, exact)


## @cond
# Load cache after we have created the Category class
# Need CAT_EMPTY for load_cache()
CAT_EMPTY = Category()
CAT_EMPTY.freeze()
try:
    Category.load_cache(os.path.join(datapath.DATA_PATH, 'categories.dat'))
    # Need these for finalize_cache()
    CAT_PP = Category.from_cache('PP')
    CAT_NP = Category.from_cache('NP')
    CAT_N = Category.from_cache('N')
    CAT_POSSESSIVE_ARGUMENT = Category.from_cache(r'(NP/(N/PP))\NP')
    CAT_POSSESSIVE_PRONOUN = Category.from_cache('NP/(N/PP)')
    Category.finalize_cache()
except Exception as e:
    _logger.exception('Exception caught', exc_info=e)
    CAT_PP = Category.from_cache('PP')
    CAT_NP = Category.from_cache('NP')
    CAT_N = Category.from_cache('N')
    CAT_POSSESSIVE_ARGUMENT = Category.from_cache(r'(NP/(N/PP))\NP')
    CAT_POSSESSIVE_PRONOUN = Category.from_cache('NP/(N/PP)')

CAT_NUM = Category.from_cache('N[num]')
CAT_NPconj = Category.from_cache('NP[conj]')
CAT_Nconj = Category.from_cache('N[conj]')
CAT_COMMA = Category.from_cache(',')
CAT_CONJ = Category.from_cache('conj')
CAT_CONJ_CONJ = Category.from_cache(r'conj\conj')
CAT_CONJCONJ = Category.from_cache(r'conj/conj')
CAT_LQU = Category.from_cache('LQU')
CAT_RQU = Category.from_cache('RQU')
CAT_LRB = Category.from_cache('LRB')
CAT_RRB = Category.from_cache('RRB')
CAT_NPthr = Category.from_cache('NP[thr]')
CAT_NPexpl = Category.from_cache('NP[expl]')
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
CAT_Sfor = Category.from_cache('S[for]')
CAT_SX = Category.from_cache('S[X]')    # wildcard
CAT_ADVERB = Category.from_cache(r'(S\NP)\(S\NP)')
CAT_MODAL = Category.from_cache(r'(S\NP)/(S\NP)')
CAT_S = Category.from_cache('S')
CAT_ADJECTIVE = Category.from_cache('N/N')
CAT_DETERMINER = Category.from_cache('NP[nb]/N')
CAT_INFINITIVE = Category.from_cache(r'(S[to]\NP)/(S[b]\NP)')
CAT_NOUN = RegexCategoryClass(r'^N(?:\[[a-z]+\])?$')
CAT_NP_N = RegexCategoryClass(r'^NP(?:\[[a-z]+\])?/N$')
CAT_NP_NP = RegexCategoryClass(r'^NP(?:\[[a-z]+\])?/NP$')
CAT_Sany = RegexCategoryClass(r'^S(?:\[[a-z]+\])?$')
CAT_PPNP = Category.from_cache('PP/NP')
# Verb phrase
CAT_VP = Category.from_cache(r'S\NP')
CAT_VPdcl = Category.from_cache(r'S[dcl]\NP')
CAT_VPb = Category.from_cache(r'S[b]\NP')
CAT_VPto = Category.from_cache(r'S[to]\NP')
# Adjectival phrase
CAT_AP = Category.from_cache(r'S[adj]\NP')

# Transitive verb
CAT_TV = Category.from_cache(r'(S\NP)/NP')
# Ditransitive verb
CAT_DTV = Category.from_cache(r'(S\NP)/NP/NP')
# Copular verb
CAT_COPULAR = [Category.from_cache(r'(S[dcl]\NP)/(S[adj]\NP)'),
               Category.from_cache(r'(S[b]\NP)/(S[adj]\NP)')]
# EasySRL prepositions
CAT_ESRL_PP = Category.from_cache(r'(NP\NP)/NP')
CAT_PP_ADVP = Category.from_cache(r'((S\NP)\(S\NP))/NP')
CAT_VP_MOD = Category.from_cache(r'(S\NP)\(S\NP)')
# CAT_AP
# Adjectival prepositional phrase
CAT_AP_PP = Category.from_cache(r'(S[adj]\NP)/PP')
# Past participle
CAT_MODAL_PAST = Category.from_cache(r'(S[dcl]\NP)/(S[pt]\NP)')
# If then
CAT_IF_THEN = Category.from_cache(r'(S/S)/S[dcl]')
# Extras
CAT_S_NP_S_NP = Category.from_cache(r'(S\NP)\(S\NP)')
CAT_S_NPS_NP = Category.from_cache(r'(S\NP)/(S\NP)')
CAT_Sadj_NP = Category.from_cache(r'S[adj]\NP')
CAT_S_NP = Category.from_cache(r'S\NP')
CAT_S_S = Category.from_cache(r'S\S')
CAT_SS = Category.from_cache(r'S/S')

FEATURE_VARG = FEATURE_PSS | FEATURE_NG | FEATURE_EM | FEATURE_DCL | FEATURE_TO | FEATURE_B | FEATURE_BEM
FEATURE_VRES = FEATURE_NG | FEATURE_EM | FEATURE_DCL | FEATURE_B |FEATURE_BEM
CAT_VPMODX = Category.from_cache(r'(S[X]\NP)/(S[X]\NP)')
CAT_VP_MODX = Category.from_cache(r'(S[X]\NP)\(S[X]\NP)')
CAT_VPX = Category.from_cache(r'S[X]\NP')
## @endcond


class Rule(Dispatchable):
    """A CCG production rule.

    See Also:
        \ref ccgrule
    """
    _counter = 0
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
        super(Rule, self).__init__(Rule._counter)
        self._name = ruleName
        self._rclass = ruleClass if not None else ruleName
        Rule._counter += 1

    ## @cond
    def __repr__(self):
        return str(self)

    def __str__(self):
        return safe_utf8_encode(self._name)

    def __unicode__(self):
        return safe_utf8_decode(self._name)

    def __eq__(self, other):
        return isinstance(other, Rule) and future_string(self) == future_string(other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        return isinstance(other, Rule) and future_string(self) < future_string(other)

    def __le__(self, other):
        return isinstance(other, Rule) and future_string(self) <= future_string(other)

    def __gt__(self, other):
        return not self.__le__(other)

    def __ge__(self, other):
        return not self.__lt__(other)

    def __hash__(self):
        return hash(future_string(self))
    ## @endcond

    @classmethod
    def rule_count(cls):
        return cls._counter

    @property
    def i(self):
        return self._idx

    @property
    def ruleclass(self):
        return self._rclass

    @property
    def rulename(self):
        return self._name

    def apply_rule_to_category(self, left, right):
        """Apply the rule to left and right categories and return a new result category

        Args:
            left: A Category instance.
            right: A Category instance.

        Returns:
            A Category instance.
        """
        if self == RL_RP:
            return left
        elif self == RL_LP:
            return right
        elif self in [RL_FX, RL_FC]:
            return Category.combine(left.result_category(), right.slash, right.argument_category())
        elif self == RL_BA:
            return right.result_category()
        elif self == RL_FA:
            return left.result_category()
        elif self in [RL_BX, RL_BC]:
            return Category.combine(right.result_category(), left.slash, left.argument_category())
        elif self in [RL_FS, RL_FXS]:
            return Category.combine(left.result_category().result_category(), left.slash, right.argument_category())
        elif self in [RL_BS, RL_BXS]:
            return Category.combine(right.result_category().result_category(), left.slash, left.argument_category())
        elif self in [RL_GFC, RL_GFX]:
            return Category.combine(Category.combine(left.result_category(), right.result_category().slash,
                                                     right.result_category().argument_category()),
                                    right.slash, right.argument_category())
        elif self in [RL_GBC, RL_GBX]:
            return Category.combine(Category.combine(right.result_category(), left.result_category().slash,
                                                     left.result_category().argument_category()),
                                    left.slash, left.argument_category())
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
RL_RP = Rule('RP', 'PASS')

## Special rule for punctuation.
RL_LP = Rule('LP', 'PASS')

## No operation - only used when post processing
RL_NOP = Rule('NOP', 'PASS')

## Special rule for CONJ.
RL_LCONJ = Rule('LCONJ', 'PASS')

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
CAT_NPNP = Category.from_cache(r'NP/NP')
CAT_NP__NP = RegexCategoryClass(r'^(NP[\\/]NP(?:\[conj\])?|N[\\/]N)$')
CAT_Sng_NP = Category.from_cache(r'S[ng]\NP')
CAT_Sany_NP = RegexCategoryClass(r'S(?:\[[a-z]+\])?\\NP')
CAT_Sany_Sany = RegexCategoryClass(r'^S(?:\[[a-z]+\])?\\S(?:\[[a-z]+\])?$')
CAT_SanySany = RegexCategoryClass(r'^S(?:\[[a-z]+\])?\\S(?:\[[a-z]+\])?$')
CAT_Sany_NP__Sany_NP = RegexCategoryClass(r'^\(S(\[[a-z]+\])?\\NP\)[\\/]\(S(\[[a-z]+\])?\\NP\)$')
## @endcond


## @ingroup gfn
def get_rule(left, right, result, exclude=None):
    """Check if left can be combined with right to produce result.

    Args:
        left: The left category.
        right: The right category.
        result: The result category.
        exclude: A list of exclusion id's. This is only used during testing.

    Returns:
        A production rule instance or None if the rule could not be found.

    See Also:
        marbles.ie.ccg.ccgcat.Rule
    """

    # Useful logic for category X.
    # - If X is not a functor, then X.result_category() == X

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
            return RL_RP
        elif right == CAT_EMPTY:
            return RL_LP
        elif right in [CAT_CONJ, CAT_CONJCONJ, CAT_CONJ_CONJ]:
            assert result == right
            return RL_LP
        elif right.can_unify(result):
            return RL_LP
        else:
            return RL_TCR_UNARY # unary type change to right argument
    elif right.ispunct and notexcluded(exclude, 14):
        if exclude is not None:
            if left.ispunct:
                return None     # don't count as duplicate
        xupdate(exclude, 14)
        if left in [CAT_CONJ, CAT_CONJCONJ, CAT_CONJ_CONJ]:
            assert result == left
            return RL_RP
        elif left.can_unify(result) or left.ispunct:
            return RL_RP
        elif left.isatom and result.isatom:
            return RL_TC_ATOM
        elif result.result_category() == result.argument_category().result_category() and \
                left.can_unify(result.argument_category().argument_category()):
            if result.isarg_right and result.argument_category().isarg_left:
                # X:a => T/(T\X): λxf.f(a)
                return RL_TYPE_RAISE
            elif result.isarg_left and result.argument_category().isarg_right:
                # X:a => T\(T/X): λxf.f(a)
                return RL_TYPE_RAISE
        else:
            return RL_TCL_UNARY # unary type change to left argument

    if left.isconj and right != CAT_EMPTY and not right.ispunct and notexcluded(exclude, 0):
        if left == CAT_CONJ:
            if right == CAT_CONJ_CONJ:
                xupdate(exclude, 0)
                return RL_BA
            elif right.can_unify(result):
                #return RL_RCONJ
                xupdate(exclude, 0)
                assert right != CAT_CONJ
                return RL_LP
            elif result.ismodifier and result.argument_category().can_unify(right):
                xupdate(exclude, 0)
                return RL_TCR_UNARY
            elif right.isatom and result.isatom:
                # Simple unary type change
                xupdate(exclude, 0)
                return RL_TC_ATOM
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
            assert left.can_unify(result)
            return RL_RP
        elif left.can_unify(right):
            return RL_RCONJ
    elif left == CAT_EMPTY and notexcluded(exclude, 2):
        xupdate(exclude, 2)
        return RL_LP
    elif left == CAT_NP_NP and right == CAT_NUM and notexcluded(exclude, 3):
        xupdate(exclude, 3)
        return RL_RNUM
    elif right == CAT_EMPTY and notexcluded(exclude, 4):
        xupdate(exclude, 4)
        if result.result_category() == result.argument_category().result_category() and \
                left.can_unify(result.argument_category().argument_category()):
            if result.isarg_right and result.argument_category().isarg_left:
                # X:a => T/(T\X): λxf.f(a)
                return RL_TYPE_RAISE
            elif result.isarg_left and result.argument_category().isarg_right:
                # X:a => T\(T/X): λxf.f(a)
                return RL_TYPE_RAISE
        elif left.can_unify(result):
            return RL_RP
        elif left.isatom and result.isatom:
            return RL_TC_ATOM
        return RL_TCL_UNARY

    elif left.isarg_right and left.argument_category().can_unify(right) and \
            left.result_category().can_unify(result) and notexcluded(exclude, 5):
        xupdate(exclude, 5)
        # Forward Application
        # X/Y:f Y:a => X: f(a)
        return RL_FA
    elif left.isarg_right and right.isfunctor and left.argument_category().can_unify(right.result_category()) and \
            Category.combine(left.result_category(), right.slash, right.argument_category()).can_unify(result) \
            and notexcluded(exclude, 6):
        if exclude is not None:
            if left.remove_features() == right.remove_features() and (left.isconj or right.isconj):
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

    elif right.isarg_left and right.argument_category().can_unify(left) and right.result_category().can_unify(result) \
            and notexcluded(exclude, 7):
        xupdate(exclude, 7)
        # Backward Application
        # Y:a X\Y:f => X: f(a)
        return RL_BA
    elif right.isarg_left and left.isfunctor and right.argument_category().can_unify(left.result_category()) \
            and Category.combine(right.result_category(), left.slash, left.argument_category()).can_unify(result) \
            and notexcluded(exclude, 8):
        if exclude is not None:
            if left.remove_features() == right.remove_features() and (left.isconj or right.isconj):
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

    elif left.argument_category().can_unify(right.argument_category()) and left.result_category().isarg_right and \
                    left.slash == right.slash and left.result_category().argument_category().can_unify(right.result_category()) and \
            Category.combine(left.result_category().result_category(), left.slash, right.argument_category()).can_unify(result) \
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

    elif right.argument_category().can_unify(left.argument_category()) and right.result_category().isarg_left and \
                    left.slash == right.slash and right.result_category().argument_category().can_unify(left.result_category()) and \
            Category.combine(right.result_category().result_category(), left.slash, left.argument_category()).can_unify(result) \
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

    elif left.isarg_right and right.result_category().slash == result.result_category().slash and \
            left.argument_category().can_unify(right.result_category().result_category()) and \
            Category.combine(Category.combine(left.result_category(), right.result_category().slash,
                                              right.result_category().argument_category()), right.slash,
                             right.argument_category()).can_unify(result) \
            and notexcluded(exclude, 11):
        xupdate(exclude, 11)
        if right.result_category().isarg_right:
            # Generalized Forward Composition
            # X/Y:f (Y/Z)/$:...λz.gz... => (X/Z)/$: ...λz.f(g(z...))
            return RL_GFC
        else:
            # Generalized Forward Crossing Composition
            # X/Y:f (Y\Z)$:...λz.gz... => (X\Z)$: ...λz.f(g(z...))
            return RL_GFX

    elif right.isarg_left and left.result_category().slash == result.result_category().slash and \
            right.argument_category().can_unify(left.result_category().result_category()) and \
            Category.combine(Category.combine(right.result_category(), left.result_category().slash,
                                              left.result_category().argument_category()), left.slash,
                             left.argument_category()).can_unify(result) \
            and notexcluded(exclude, 12):
        xupdate(exclude, 12)
        if left.result_category().isarg_left:
            # Generalized Backward Composition
            # (Y\Z)$:...λz.gz... X\Y:f => (X\Z)$: ...λz.f(g(z...))
            return RL_GBC
        else:
            # Generalized Backward Crossing Composition
            # (Y/Z)/$:...λz.gz... X\Y:f => (X/Z)/$: ...λz.f(g(z...))
            return RL_GBX
    # TODO: generalized substitution

    return None


class POS(Freezable):
    """Penn Treebank Part-Of-Speech."""
    _cache = Cache()

    def __init__(self, tag):
        super(POS, self).__init__()
        self._tag = tag

    def __eq__(self, other):
        if self._freeze and other.isfrozen:
            return self is other
        return self._tag == other.tag

    def __ne__(self, other):
        if self._freeze and other.isfrozen:
            return self is not other
        return self._tag != other.tag

    def __hash__(self):
        return hash(self._tag)

    def __str__(self):
        return safe_utf8_encode(self._tag)

    def __unicode__(self):
        return safe_utf8_decode(self._tag)

    def __repr__(self):
        return str(self)

    @property
    def tag(self):
        """Readonly access to POS tag."""
        return self._tag

    @classmethod
    def from_cache(cls, tag):
        """Get the cached POS tag"""
        if isinstance(tag, POS):
            tag = tag.tag
        try:
            return cls._cache[tag]
        except KeyError:
            pos = POS(tag)
            cls._cache[pos.tag] = pos
            pos.freeze()
            return pos

_tags = [
    'CC', 'CD', 'DT', 'EX', 'FW', 'IN', 'JJ', 'JJR', 'JJS', 'LS', 'MD', 'NN', 'NNS', 'NNP', 'NNPS',
    'PDT', 'POS', 'PRP', 'PRP$', 'RB', 'RBR', 'RBS', 'RP', 'SYM', 'TO', 'UH', 'VB', 'VBD', 'VBG', 'VBN',
    'VBP', 'VBZ', 'WDT', 'WP', 'WP$', 'WRB', 'UNKNOWN', ',', '.', ':', ';', '?', '$', 'SO'
]

# Initialize POS cache
for _t in _tags:
    POS._cache.addinit((_t, POS(_t)))
for _t in _tags:
    POS.from_cache(_t).freeze()

POS_DETERMINER = POS.from_cache('DT')
POS_LIST_PERSON_PRONOUN = [POS.from_cache('PRP'), POS.from_cache('PRP$')]
POS_LIST_PRONOUN = [POS.from_cache('PRP'), POS.from_cache('PRP$'), POS.from_cache('WP'), POS.from_cache('WP$')]
POS_LIST_VERB = [POS.from_cache('VB'), POS.from_cache('VBD'), POS.from_cache('VBN'), POS.from_cache('VBP'),
                 POS.from_cache('VBZ')]
POS_LIST_ADJECTIVE = [POS.from_cache('JJ'), POS.from_cache('JJR'), POS.from_cache('JJS')]
POS_GERUND = POS.from_cache('VBG')
POS_PROPER_NOUN = POS.from_cache('NNP')
POS_PROPER_NOUN_S = POS.from_cache('NNPS')
POS_NOUN = POS.from_cache('NN')
POS_NOUN_S = POS.from_cache('NNS')
POS_MODAL = POS.from_cache('MD')
POS_UNKNOWN = POS.from_cache('UNKNOWN')
POS_NUMBER = POS.from_cache('CD')
POS_PREPOSITION = POS.from_cache('IN')
POS_LIST_PUNCT = [POS.from_cache(','), POS.from_cache('.'), POS.from_cache('?'), POS.from_cache(':'),
                  POS.from_cache(';')]
POS_POSSESSIVE = POS.from_cache('POS')
