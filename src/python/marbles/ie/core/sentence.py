from __future__ import unicode_literals, print_function

import collections
import requests
import time
import wikipedia

import marbles.ie.drt
import marbles.ie.utils.cache
from marbles.ie.ccg import *
from marbles.ie.core import constituent_types as ct
from marbles.ie.kb import google_search
from marbles.log import ExceptionRateLimitedLogAdaptor

_actual_logger = logging.getLogger(__name__)
_logger = ExceptionRateLimitedLogAdaptor(_actual_logger)
_NNPSPLIT = re.compile(r'for|and|of')

# Remove extra info from wikipedia topic
_WTOPIC = re.compile(r'http://.*/(?P<topic>[^/]+(\([^)]+\))?)')

# Rate limit wiki requests
wikipedia.set_rate_limiting(rate_limit=True)


class Wikidata(object):
    def __init__(self, page):
        if page is not None:
            self.title = page.title
            self.summary = page.summary
            # TODO: filter wikipedia categories
            self.categories = page.categories
            self.pageid = page.pageid
            self.url = page.url
        else:
            self.title = None
            self.summary = None
            self.categories = None
            self.pageid = None
            self.url = None

    def get_json(self):
        return {
            'title': self.title,
            'summary': self.summary,
            'page_categories': self.categories,
            'pageid': self.pageid,
            'url': self.url
        }

    @classmethod
    def from_json(self, data):
        wd = Wikidata(None)
        wd.title = data['title']
        wd.summary = data['summary']
        wd.categories = data['page_categories']
        wd.pageid = data['pageid']
        wd.url = data['url']
        return wd


class AbstractLexeme(object):

    def __init__(self, c=None):
        if c is not None:
            self.head = c.head
            self.idx = c.idx
            self.mask = c.mask
            self.refs = [r for r in c.refs]
            self.pos = c.pos
            self.word = c.word
            self.stem = c.stem
            self.drs = c.drs
            self.category = c.category
            self.wiki_data = c.wiki_data
        else:
            self.head = -1
            self.idx = -1
            self.mask = 0
            self.refs = []
            self.pos = None
            self.word = None
            self.stem = None
            self.drs = None
            self.category = None
            self.wiki_data = None

    @property
    def isroot(self):
        return self.idx == self.head

    @property
    def ispunct(self):
        """Test if the word attached to this lexeme is a punctuation mark."""
        raise NotImplementedError

    @property
    def ispronoun(self):
        """Test if the word attached to this lexeme is a pronoun."""
        raise NotImplementedError

    @property
    def ispreposition(self):
        """Test if the word attached to this lexeme is a preposition."""
        raise NotImplementedError

    @property
    def isadverb(self):
        """Test if the word attached to this lexeme is an adverb."""
        raise NotImplementedError

    @property
    def isverb(self):
        """Test if the word attached to this lexeme is a verb."""
        # Verbs can behave as adjectives
        raise NotImplementedError

    @property
    def isgerund(self):
        """Test if the word attached to this lexeme is a gerund."""
        raise NotImplementedError

    @property
    def isproper_noun(self):
        """Test if the word attached to this lexeme is a proper noun."""
        raise NotImplementedError

    @property
    def isnumber(self):
        """Test if the word attached to this lexeme is a number."""
        raise NotImplementedError

    @property
    def isadjective(self):
        """Test if the word attached to this lexeme is an adjective."""
        raise NotImplementedError

    def clone(self):
        raise NotImplementedError

    def set_wiki_entry(self, page):
        self.wiki_data = Wikidata(page)


class BasicLexeme(AbstractLexeme):

    def __init__(self, c=None):
        super(BasicLexeme, self).__init__(c)

    @property
    def ispunct(self):
        """Test if the word attached to this lexeme is a punctuation mark."""
        return self.pos in POS_LIST_PUNCT

    @property
    def ispronoun(self):
        """Test if the word attached to this lexeme is a pronoun."""
        return (self.pos in POS_LIST_PRONOUN)  # or self._word in _PRON

    @property
    def ispreposition(self):
        """Test if the word attached to this lexeme is a preposition."""
        return self.category == POS_PREPOSITION

    @property
    def isadverb(self):
        """Test if the word attached to this lexeme is an adverb."""
        return self.category == CAT_ADVERB

    @property
    def isverb(self):
        """Test if the word attached to this lexeme is a verb."""
        # Verbs can behave as adjectives
        return (self.pos in POS_LIST_VERB and self.category != CAT_ADJECTIVE) or \
               (self.category.result_category() == CAT_VPdcl and not self.category.ismodifier)

    @property
    def isgerund(self):
        """Test if the word attached to this lexeme is a gerund."""
        return self.pos == POS_GERUND

    @property
    def isproper_noun(self):
        """Test if the word attached to this lexeme is a proper noun."""
        return self.pos == POS_PROPER_NOUN or self.pos == POS_PROPER_NOUN_S

    @property
    def isnumber(self):
        """Test if the word attached to this lexeme is a number."""
        return self.pos == POS_NUMBER

    @property
    def isadjective(self):
        """Test if the word attached to this lexeme is an adjective."""
        return self.category == CAT_ADJECTIVE

    def from_json(self, d):
        self.pos = POS.from_cache(d['pos'])
        self.category = Category.from_cache(d['category'])
        self.word = d['word']
        self.stem = d['stem']
        self.head = d['head']
        self.idx = d['idx']
        self.mask = d['mask']
        self.refs = d['refs']
        self.drs = None
        if 'wiki' in d:
            self.wiki_data = Wikidata.from_json(d['wiki'])

    def clone(self):
        return BasicLexeme(self)


def _compare_lex_range(r1, r2):
    if r1 is None and r2 is None:
        return 0
    # Longest span is less
    if r1 is not None and r2 is not None:
        x = r1[0] - r2[0]
        return x if x != 0 else r2[1] - r1[1]
    return -1 if r1 is None else 1


def _lex_limit_le(r1, r2):
    # Longest span is less
    if r1 is not None and r2 is not None:
        return r1[1] <= r2[1]
    return False


class ConstituentTreeNode(object):

    def __init__(self, constituent):
        super(STreeNode, self).__init__(idx, depth)
        self.rule = rule
        self._result_category = result_category
        self._child_nodes = child_nodes
        self._head = head
        self._lex_range = lex_range

    def __repr__(self):
        return b'<STreeNode>:(%d, %s %s)' % (len(self.child_nodes), self.rule, self.category)

    @property
    def category(self):
        return self._result_category

    @property
    def lex_range(self):
        return self._lex_range

    @property
    def children(self):
        return self._child_nodes

    @property
    def isbinary(self):
        return len(self._child_nodes) == 2

    @property
    def head_idx(self):
        """Return the head of the phrase"""
        return self._head

    def iternodes(self):
        """Iterate the syntax tree nodes unordered"""
        stk = [self]
        while len(stk) != 0:
            nd = stk.pop()
            if not nd.isleaf:
                stk.extend(nd.children)
            yield nd


class AbstractConstituentNode(object):
    """Base class for constituents and sytax tree nodes."""
    def __init__(self, ndtype):
        self.ndtype = ndtype

    @property
    def children(self):
        """Get a list of the child nodes."""
        return None

    @property
    def isleaf(self):
        """Test if this is a leaf node."""
        return self.children is None

    @property
    def head_idx(self):
        """Return the lexical head of the phrase"""
        raise NotImplementedError

    @property
    def parent_idx(self):
        """Return the parent node index"""
        raise NotImplementedError

    @property
    def lex_range(self):
        """Return the lexical range (span) of the constituent"""
        raise NotImplementedError

    def get_json(self):
        result = {
            'ndtype': self.ndtype.signature,
            'chead': self.parent_idx,
            'dhead': self.head_idx,
            'lex_range': self.lex_range if self.lex_range is not None else [],
        }
        return result

    def iternodes(self):
        """Iterate the tree nodes unordered"""
        if self.isleaf:
            yield self
        else:
            stk = [self]
            while len(stk) != 0:
                nd = stk.pop()
                if not nd.isleaf:
                    stk.extend(nd.children)
                yield nd

    def contains(self, ndtypes):
        """Return true if the node or any children have type in ndtypes"""
        return self.ndtype in ndtypes or any([c.contains(ndtypes) for c in self.iternodes()])


class ConstituentNode(AbstractConstituentNode):
    """Base class for constituents."""
    def __init__(self, ndtype, lex_range, parent_idx, head_idx):
        super(ConstituentNode, self).__init__(ndtype)
        self._head_idx = head_idx
        self._parent_idx = parent_idx
        self._lex_range = lex_range

    @property
    def children(self):
        """Get a list of the child nodes."""
        return None

    @property
    def head_idx(self):
        """Return the lexical head of the phrase"""
        return self._head_idx

    @property
    def parent_idx(self):
        """Return the parent node index"""
        self._parent_idx

    @property
    def lex_range(self):
        """Return the lexical range (span) of the constituent"""
        return self._lex_range

    @classmethod
    def from_json(self, data):
        lex_range=data['lex_range']
        if len(lex_range) != 2:
            lex_range = None
        return ConstituentNode(ct.Typeof[data['ndtype']], lex_range=lex_range,
                                       parent_idx=data['chead'], head_idx=data['dhead'])


class Constituent(object):
    """A constituent is a sentence span and a phrase type."""
    def __init__(self, sentence, node):
        if sentence is not None and not isinstance(sentence, AbstractSentence):
            raise TypeError('sentence not instance of AbstractSentence')
        if node is not None and not isinstance(node, AbstractConstituentNode):
            raise TypeError('tree node not instance of AbstractConstituentNode')
        self.sentence = sentence
        self.node = node

    def __unicode__(self):
        return self.node.ndtype.signature + u'(' + u' '.join([safe_utf8_decode(x.word) for x in self.span]) + u')'

    def __str__(self):
        return safe_utf8_encode(self.__unicode__())

    def __repr__(self):
        return str(self)

    def __hash__(self):
        h = hash(id(self.sentence))
        h ^= hash(self.node.ndtype)
        if self.node.lex_range is not None:
            for i in self.node.lex_range:
                h = h ^ hash(i)
        return h

    def __eq__(self, other):
        return self.node.ndtype is other.node.ndtype \
               and 0 == _compare_lex_range(self.node.lex_range, other.node.lex_range)

    def __ne__(self, other):
        return self.node.ndtype is other.node.ndtype \
               or 0 != _compare_lex_range(self.node.lex_range, other.node.lex_range)

    def __lt__(self, other):
        cmp = _compare_lex_range(self.node.lex_range, other.node.lex_range)
        return cmp < 0 or (0 == cmp and self.node.ndtype < other.node.ndtype)

    def __gt__(self, other):
        cmp = _compare_lex_range(self.node.lex_range, other.node.lex_range)
        return cmp > 0 or (0 == cmp and self.node.ndtype > other.node.ndtype)

    def __le__(self, other):
        return not self.__gt__()

    def __ge__(self, other):
        return not self.__lt__()

    def __contains__(self, other):
        return _compare_lex_range(self.node.lex_range, other.node.lex_range) < 0 and \
                _lex_limit_le(other.node.lex_range, self.node.lex_range)

    @property
    def isempty(self):
        return self.node.lex_range is None

    @property
    def isroot(self):
        """Test if this is the root constituent."""
        return self is self.sentence.constituent_at(self.node.parent_idx)

    @property
    def ndtype(self):
        return self.node.ndtype

    @property
    def span(self):
        return Span(self.sentence, self.node.lex_range[0], self.node.lex_range[1]) \
            if self.node.lex_range is not None else Span(self.sentence, self.node.head_idx, self.node.head_idx+1)

    def clone(self):
        return Constituent(self.sentence, self.node)

    def head(self):
        """Get the head lexeme of the constituent.

        Returns:
            A Lexeme instance.
        """
        return self.sentence[self.node.head_idx]

    def chead(self):
        """Get the head constituent.

        Returns:
            A Constituent instance or None if the root constituent.
        """
        chd = self.sentence.constituent_at(self.node.parent_idx)
        return None if chd is self else chd

    def marked_text(self, mark='#'):
        """Get the constituent text with the the head marked."""
        if self.isempty:
            return ''
        hd = self.head()
        span = self.span
        txt = [mark + span[0].word if span[0] is hd else span[0].word]
        for tok in span[1:]:
            if not tok.ispunct:
                txt.append(' ')
            txt.append(mark + tok.word if tok is hd else tok.word)
        return ''.join(txt)


class AbstractSpan(collections.Sequence):
    """Abstract lexical span"""

    def __unicode__(self):
        return safe_utf8_decode(self.text)

    def __str__(self):
        return safe_utf8_encode(self.text)

    def __repr__(self):
        return self.text

    def __len__(self):
        raise NotImplementedError

    def __getitem__(self, slice_i_j):
        raise NotImplementedError

    def __iter__(self):
        raise NotImplementedError

    @property
    def text(self):
        if len(self) == 0:
            return ''
        txt = [self[0].word]
        for tok in self[1:]:
            if not tok.ispunct:
                txt.append(' ')
            txt.append(tok.word)
        return ''.join(txt)


class AbstractSentence(AbstractSpan):
    """AbstractSentence"""

    def __init__(self, msgid=None):
        self.msgid = msgid  # for logging

    def constituent_at(self, idx):
        raise NotImplementedError

    def iterconstituents(self):
        raise NotImplementedError

    def safe_wikipage(self, query):
        global _logger
        try:
            return wikipedia.page(title=query)
        except wikipedia.PageError as e:
            if self.msgid is not None:
                _logger.warning('[msgid=%s] wikipedia.page(%s) - %s', self.msgid, query, str(e))
            else:
                _logger.warning('wikipedia.page(%s) - %s', query, str(e))

        return None


class Sentence(AbstractSentence):
    """A sentence."""

    def __init__(self, lexemes=None, constituents=None, msgid=None):
        super(Sentence, self).__init__(msgid)
        if lexemes is not None:
            self._lexemes = lexemes
            self._constituents = [] if constituents is None else constituents
        else:
            self._lexemes = []
            self._constituents = []

    def __len__(self):
        return len(self._lexemes)

    def __getitem__(self, slice_i_j):
        if isinstance(slice_i_j, slice):
            indexes = [i for i in range(len(self))]
            return Span(self, indexes[slice_i_j])
        return self._lexemes[slice_i_j]

    def __iter__(self):
        for i in range(len(self)):
            yield self._lexemes[i]

    def iterconstituents(self):
        for nd in self._constituents:
            yield Constituent(self, nd)

    def get_constituent_tree(self):
        """Get the constituent tree as an adjacency list of lists."""
        constituents = self._constituents
        if len(constituents) == 0:
            return []

        # Each node is a tuple (constituency index, [adjacency tuples])
        nodes = [(i, []) for i in range(len(constituents))] # create empty
        seen = [[] for i in range(len(constituents))]
        root = 0
        for i in range(len(constituents)):
            nd = constituents[i]
            if nd.parent_idx != i:
                if i not in seen[nd.parent_idx]:
                    nodes[nd.parent_idx][1].append(nodes[i])
                    seen[nd.parent_idx].append(i)
            else:
                root = nd.parent_idx
        return nodes[root]

    def print_constituent_tree(self, ctree, level=0):
        """Print the constituent tree."""
        indent = '' if level == 0 else ' ' * level
        c = self._constituents[ctree[0]]
        print('%s%02d %s(%s)' % (indent, ctree[0], c.ndtype.signature, c.span.text))
        for nd in ctree[1]:
            self.print_constituent_tree(nd, level+3)

    def _get_constituent_tree_as_string_helper(self, ctree, level, result):
        indent = '' if level == 0 else ' ' * level
        c = self._constituents[ctree[0]]
        result.append('%s%02d %s(%s)' % (indent, ctree[0], c.ndtype.signature, c.span.text))
        for nd in ctree[1]:
            self._get_constituent_tree_as_string_helper(nd, level+3, result)
        return result

    def get_constituent_tree_as_string(self, ctree):
        """Get the constituent tree as a string."""
        result = self._get_constituent_tree_as_string_helper(ctree, 0, [])
        return '\n'.join(result)

    def get_dependency_tree(self):
        """Get the dependency tree as an adjacency list of lists."""
        if len(self) == 0:
            return []

        # Each node is a tuple (constituency index, [adjacency tuples])
        nodes = [(i, []) for i in range(len(self))] # create empty
        seen = [[] for i in range(len(self))]
        root = 0
        for i in range(len(self)):
            nd = self._lexemes[i]
            if nd.head != i:
                if i not in seen[nd.head]:
                    nodes[nd.head][1].append(nodes[i])
                    seen[nd.head].append(i)
            else:
                root = nd.head
        return nodes[root]

    def dependency_node_to_span(self, dtree):
        """Convert a dependency node in an adjacency list to a span."""
        stk = [dtree[0]]
        indexes = []
        while len(stk) != 0:
            nd = stk.pop()
            indexes.append(nd[0])
            stk.extend(nd[1])
        return Span(self, indexes)

    def print_dependency_tree(self, dtree, level=0):
        """Print the constituent tree."""
        indent = '' if level == 0 else ' ' * level
        lex = self._lexemes[dtree[0]]
        print('%s%02d %-4s(%s)' % (indent, dtree[0], lex.pos, lex.word))
        for nd in dtree[1]:
            self.print_dependency_tree(nd, level+3)

    def _get_dependency_tree_as_string_helper(self, dtree, level, result):
        indent = '' if level == 0 else ' ' * level
        lex = self._lexemes[dtree[0]]
        result.append('%s%02d %-4s(%s)' % (indent, dtree[0], lex.pos, lex.word))
        for nd in dtree[1]:
            self._get_dependency_tree_as_string_helper(nd, level+3, result)
        return result

    def get_dependency_tree_as_string(self, ctree):
        """Get the dependency tree as a string."""
        result = self._get_dependency_tree_as_string_helper(ctree, 0, [])
        return '\n'.join(result)


class AbstractSpan(AbstractSpan):

    @property
    def sentence(self):
        raise NotImplementedError

    @property
    def isempty(self):
        raise NotImplementedError

    def clear(self):
        raise NotImplementedError

    def indexes(self):
        raise NotImplementedError

    def clone(self):
        raise NotImplementedError

    def union(self, other):
        raise NotImplementedError

    def add(self, idx):
        raise NotImplementedError

    def remove(self, idx):
        raise NotImplementedError

    def difference(self, other):
        raise NotImplementedError

    def intersection(self, other):
        raise NotImplementedError

    def subspan(self, required, excluded=0):
        raise NotImplementedError

    def contiguous_subspans(self, required, excluded=0):
        raise NotImplementedError

    def fullspan(self):
        raise NotImplementedError

    def get_drs(self, nodups=False):
        raise NotImplementedError

    def get_head_span(self, strict=False):
        raise NotImplementedError

    def search_wikipedia(self, max_results=1, google=True, browser=None):
        raise NotImplementedError


class Span(AbstractSpan):
    """View of a discourse."""
    def __init__(self, sentence, indexes=None, end=None):
        if not isinstance(sentence, AbstractSentence):
            raise TypeError('Span constructor requires AbstractSentence type')
        self._sent = sentence
        if indexes is None:
            self._indexes = []
        elif isinstance(indexes, set):
            self._indexes = sorted(indexes)
        elif end is not None:
            if not isinstance(end, (int, long)) or not isinstance(indexes, (int, long)):
                TypeError('Span() accepts index list or range')
            self._indexes = [x for x in xrange(indexes, end)]
        else:
            self._indexes = sorted(set([x for x in indexes]))

    def __eq__(self, other):
        return other is not None and self.sentence is other.sentence and len(self) == len(other) \
               and (len(self._indexes) == 0 or (self._indexes[0] == other._indexes[0] and self._indexes[-1] == other._indexes[-1]) == 0)

    def __hash__(self):
        h = hash(id(self.sentence))
        for i in self._indexes:
            h = h ^ hash(i)
        return h

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        if self.sentence is not other.sentence:
            return id(self.sentence) < id(other.sentence)
        for i, j in zip(self._indexes, other._indexes):
            if i == j:
                continue
            return i < j
        # The longer sentence is less - important for constituent ordering
        return len(self) > len(other)

    def __gt__(self, other):
        if self.sentence is not other.sentence:
            return id(self.sentence) > id(other.sentence)
        for i, j in zip(self._indexes, other._indexes):
            if i == j:
                continue
            return i > j
        # The shorter sentence is greater - important for constituent ordering
        return len(self) < len(other)

    def __le__(self, other):
        return not self.__gt__(other)

    def __ge__(self, other):
        return not self.__lt__(other)

    def __len__(self):
        return len(self._indexes)

    def __getitem__(self, i):
        if isinstance(i, slice):
            return Span(self._sent, self._indexes[i])
        return self._sent[self._indexes[i]]

    def __iter__(self):
        for k in self._indexes:
            yield self._sent[k]

    def __contains__(self, item):
        if isinstance(item, Span):
            return len(item) != 0 and len(set(item._indexes).difference(self._indexes)) == 0
        elif isinstance(item, int):
            return item in self._indexes
        elif not isinstance(item, AbstractLexeme):
            raise TypeError('Span.__contains__ expects a Span, Lexeme, or int type')
        # Lexeme
        return item.idx in self._indexes

    @property
    def text(self):
        if len(self._indexes) == 0:
            return ''
        txt = [self._sent[self._indexes[0]].word]
        for i in self._indexes[1:]:
            tok = self._sent[i]
            if not tok.ispunct:
                txt.append(' ')
            txt.append(tok.word)
        return ''.join(txt)

    @property
    def sentence(self):
        return self._sent

    @property
    def isempty(self):
        return len(self._indexes) == 0

    def clear(self):
        """Make the span empty."""
        self._indexes = []

    def iterindexes(self):
        for x in self._indexes:
            yield x

    def indexes(self):
        """Get the list of indexes in this span."""
        return [x for x in self._indexes]

    def clone(self):
        """Do a shallow copy and clone the span."""
        return Span(self._sent, self._indexes)

    def union(self, other):
        """Union two spans."""
        if other is None or len(other) == 0:
            return self
        return Span(self._sent, set(self._indexes).union(other._indexes))

    def add(self, idx):
        """Add an index to the span."""
        u = set(self._indexes)
        if isinstance(idx, AbstractLexeme):
            u.add(idx.idx)
        else:
            u.add(idx)
        self._indexes = sorted(u)
        return self

    def remove(self, idx):
        """Remove an index from the span."""
        u = set(self._indexes)
        if isinstance(idx, AbstractLexeme):
            u.remove(idx.idx)
        else:
            u.remove(idx)
        self._indexes = sorted(u)
        return self

    def difference(self, other):
        """Remove other from this span."""
        if other is None or len(other) == 0:
            return self
        return Span(self._sent, set(self._indexes).difference(other._indexes))

    def intersection(self, other):
        """Find common span."""
        if other is None or len(other) == 0:
            return Span(self._sent)
        return Span(self._sent, set(self._indexes).intersection(other._indexes))

    def subspan(self, required, excluded=0):
        """Refine the span with `required` and `excluded` criteria's.

        Args:
            required: A mask of RT_? bits.
            excluded: A mask of RT_? bits.

        Returns:
            A Span instance.
        """
        return Span(self._sent, filter(lambda i: 0 != (self._sent[i].mask & required) and \
                                                 0 == (self._sent[i].mask & excluded), self._indexes))

    def contiguous_subspans(self, required, excluded=0):
        """Refine the span with `required` and `excluded` criteria's.

        Args:
            required: A mask of RT_? bits.
            excluded: A mask of RT_? bits.

        Returns:
            A list of Span instance.
        """
        indexes = self.subspan(required, excluded).indexes()
        if len(indexes) == 0:
            return []
        csp = []
        spi = [indexes[0]]
        for i in indexes[1:]:
            if (i-1) == spi[-1]:
                spi.append(i)
            else:
                csp.append(Span(self._sent, spi))
                spi = [i]
        csp.append(Span(self._sent, spi))
        return csp

    def fullspan(self):
        """Return the span which is a superset of this span but where the indexes are contiguous.

        Returns:
            A Span instance.
        """
        if len(self._indexes) <= 1:
            return self
        return Span(self._sent, [x for x in range(self._indexes[0], self._indexes[-1] + 1)])

    def get_drs(self, nodups=False):
        """Get a DRS view of the span.

        Returns:
            A DRS instance.
        """
        conds = []
        refs = []
        for tok in self:
            if tok.drs:
                conds.extend(tok.drs.conditions)
                refs.extend(tok.drs.referents)
        return marbles.ie.drt.drs.DRS(refs, conds)

    def get_head_span(self, strict=False):
        """Get the head lexemes of the span.

        Args:
            strict: If true then heads must point to a lexeme within the span. If false then some
                head must point to a lexeme within the span.

        Returns:
            A span of Lexeme instances.
        """
        # Handle singular case
        if len(self._indexes) == 1:
            return self

        indexes = set(self._indexes)
        hds = set()
        if strict:
            for lex in self:
                if lex.isroot or lex.head not in indexes:
                    hds.add(lex.idx)
        else:
            for lex in self:
                if lex.isroot:
                    hds.add(lex.idx)
                elif lex.head not in indexes:
                    hd = self._sent[lex.head]
                    while hd.head not in indexes and not hd.isroot:
                        hd = self._sent[hd.head]
                    if hd.head not in indexes:
                        hds.add(lex.idx)
        return Span(self._sent, hds)

    def search_wikipedia(self, max_results=1, google=True, browser=None):
        """Find a wikipedia topic from this span.

        Args:
            max_results: The maximum number of results to return
            google: If no results are found on wikipedia then do a google search if this is True.
            browser: If set then google search uses this as the headless browser.

        Returns: A wikipedia topic.
        """
        global _logger
        retry = True
        attempts = 0
        while retry:
            try:
                txt = self.text.replace('-', ' ')
                topics = []
                result = wikipedia.search(txt, results=max_results)
                if result is not None and len(result) != 0:
                    for t in result:
                        wr = self.sentence.safe_wikipage(t)
                        if wr is not None:
                            topics.append(wr)

                if len(topics) == 0:
                    # Get suggestions from wikipedia
                    query = wikipedia.suggest(txt)
                    if query is not None:
                        result = self.sentence.safe_wikipage(query)
                        if result is not None:
                            return [result]
                    if google and (result is None or len(result) == 0):
                        # Try google search - hopefully will fix up spelling or ignore irrelevent words
                        scraper = google_search.GoogleScraper(browser)
                        spell, urls = scraper.search(txt, 'wikipedia.com')
                        if spell is not None:
                            result = wikipedia.search(txt, results=max_results)
                            if result is not None and len(result) != 0:
                                for t in result:
                                    wr = self.sentence.safe_wikipage(t)
                                    if wr is not None:
                                        topics.append(wr)

                            if len(topics) == 0:
                                # Get suggestions from wikipedia
                                query = wikipedia.suggest(txt)
                                if query is not None:
                                    result = self.sentence.safe_wikipage(query)
                                    if result is not None and len(result) != 0:
                                        return [result]
                            else:
                                return topics
                        seen = set()
                        for u in urls:
                            m = _WTOPIC.match(u)
                            if m is not None:
                                t = m.group('topic')
                                if t not in seen:
                                    seen.add(t)
                                    wr = self.sentence.safe_wikipage(t.replace('_', ' '))
                                    if wr:
                                        topics.append(wr)
                                        if len(topics) >= max_results:
                                            break
                return topics if len(topics) != 0 else None
            except requests.exceptions.ConnectionError as e:
                attempts += 1
                retry = attempts <= 3
                if self.sentence.msgid is not None:
                    _logger.exception('[msgid=%s] Span.search_wikipedia', self.sentence.msgid, exc_info=e)
                else:
                    _logger.exception('Span.search_wikipedia', exc_info=e)
                time.sleep(0.25)
            except wikipedia.exceptions.DisambiguationError as e:
                # TODO: disambiguation
                retry = False
            except wikipedia.exceptions.HTTPTimeoutError as e:
                attempts += 1
                retry = attempts <= 3
                if self.sentence.msgid is not None:
                    _logger.exception('[msgid=%s] Span.search_wikipedia', self.sentence.msgid, exc_info=e)
                else:
                    _logger.exception('Span.search_wikipedia', exc_info=e)
                time.sleep(0.25)

        return None
