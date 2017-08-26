from __future__ import unicode_literals, print_function

import collections
import requests
import time
import wikipedia
import itertools
import bisect

try:
    # Not visible in website
    from marbles.ie import drt
except:
    pass
from marbles.ie.ccg import *
from marbles.ie.core import constituent_types as ct
from marbles.ie import kb
from marbles import log

_actual_logger = logging.getLogger(__name__)
_logger = log.ExceptionRateLimitedLogAdaptor(_actual_logger)
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


def _compare_simple_span(r1, r2):
    if r1 is None and r2 is None:
        return 0
    # Longest span is less
    if r1 is not None and r2 is not None:
        x = r1.begin - r2.begin
        return x if x != 0 else r2.end - r1.end
    return -1 if r1 is None else 1


class SimpleSpan(object):
    """A set of contiguous indexes in a sentence span."""
    def __init__(self, begin, end=None):
        """Constructor.

        :param begin: Start index
        :param end: Stop inde
        """
        if isinstance(begin, (tuple, list)):
            assert end is None
            self.begin = begin[0]
            self.end = max(begin)
        else:
            self.begin = begin
            self.end = (begin + 1) if end is None else max([end, begin])

    def __eq__(self, other):
        return self.begin == other.begin and self.end == other.end

    def __ne__(self, other):
        return self.begin != other.begin or self.end != other.end

    def __lt__(self, other):
        return self.begin < other.begin or (self.begin == other.begin and self.end > other.end)

    def __gt__(self, other):
        return self.begin > other.begin or (self.begin == other.begin and self.end < other.end)

    def __le__(self, other):
        return not self.__gt__(other)

    def __ge__(self, other):
        return not self.__lt__(other)

    def __hash__(self):
        return hash((self.begin, self.end))

    def __unicode__(self):
        return u'(%d:%d)' % (self.begin, self.end)

    def __str__(self):
        return safe_utf8_encode(self.__unicode__())

    def __repr__(self):
        return str(self)

    @property
    def width(self):
        return self.end - self.begin

    def __union(self, other):
        if not isinstance(other, SimpleSpan):
            raise TypeError('other is not a SimpleSpan')
        if other.width == 0:
            return self.begin, self.end
        elif self.width == 0:
            return other.begin, other.end
        return min(other.begin, self.begin), max(other.end, self.end)

    def __difference(self, other):
        if not isinstance(other, SimpleSpan):
            raise TypeError('other is not a SimpleSpan')
        if other.width == 0 or self.width == 0 or other.end <= self.begin or \
                other.begin >= self.end:
            return self.begin, self.end
        elif other.begin <= self.begin and other.end > self.begin:
            # left overlap
            return min(other.end, self.end), self.end
        elif other.end >= self.end and other.begin < self.end:
            # right overlap
            return self.begin, max(self.begin, other.begin)
        # simple span can't support these overlaps
        # Return left and right results
        s1 = self.__difference(SimpleSpan(self.begin, other.begin))
        s2 = self.__difference(SimpleSpan(other.begin, self.end))
        return s1, s2

    def __intersection(self, other):
        if not isinstance(other, SimpleSpan):
            raise TypeError('other is not a SimpleSpan')
        if self.width == 0 or other.width == 0:
            return self.begin, self.begin
        elif other.end <= self.end:
            return max(self.begin, other.begin), max(self.begin, other.end)
        elif other.begin > self.begin:
            return min(self.end, other.begin), min(self.end, other.end)
        return self.begin, self.end

    def iterindexes(self, anysort=False):
        # anysort required for compaibility with SimpleIndexSpan
        for i in xrange(self.begin, self.end):
            yield i

    def to_list(self):
        return [self.begin, self.end]

    def clone(self):
        return SimpleSpan(self.begin, self.end)

    def union(self, other):
        return SimpleSpan(self.__union(other))

    def union_inplace(self, other):
        self.begin, self.end = self.__union(other)
        return self

    def intersection(self, other):
        return SimpleSpan(self.__intersection(other))

    def intersection_inplace(self, other):
        self.begin, self.end = self.__intersection(other)
        return self

    def difference(self, other):
        s1, s2 = self.__difference(other)
        assert not isinstance(s1, SimpleSpan)
        return SimpleSpan(s1, s2)

    def difference_inplace(self, other):
        s1, s2 = self.__difference(other)
        assert not isinstance(s1, SimpleSpan)
        self.begin, self.end = s1, s2
        return self

    def at(self, i):
        if i >= self.width:
            raise IndexError('index %d out of bounds' % i)
        return self.begin + i

    def contains_index(self, i):
        return i >= self.begin and i < self.end

    def contains_span(self, other):
        return self.intersection(other).width == other.width


class AbstractConstituentNode(object):
    """Base class for constituents and sytax tree nodes."""
    def __init__(self, ndtype):
        self.ndtype = ndtype

    @property
    def child_nodes(self):
        """Get a list of the child nodes."""
        return None

    @property
    def isleaf(self):
        """Test if this is a leaf node."""
        return self.child_nodes is None

    @property
    def head_idx(self):
        """Return the lexical head of the phrase"""
        raise NotImplementedError

    @property
    def parent_idx(self):
        """Return the parent node index"""
        raise NotImplementedError

    @property
    def simple_span(self):
        """Return the lexical range (span) of the constituent"""
        raise NotImplementedError

    def get_json(self):
        result = {
            'ndtype': self.ndtype.signature,
            'chead': self.parent_idx,
            'dhead': self.head_idx,
            'span': self.simple_span if self.simple_span is not None else [],
        }
        return result

    def iternodes(self):
        """Depth first iteration over the tree nodes."""
        if self.isleaf:
            yield self
        else:
            stk = [self]
            while len(stk) != 0:
                nd = stk.pop()
                if not nd.isleaf:
                    stk.extend(nd.child_nodes)
                yield nd

    def contains(self, ndtypes):
        """Return true if the node or any children have type in ndtypes"""
        return self.ndtype in ndtypes or any([c.contains(ndtypes) for c in self.iternodes()])


class ConstituentNode(AbstractConstituentNode):
    """Base class for constituents."""
    def __init__(self, ndtype, idx, simple_span, parent_idx, head_idx, children=None):
        super(ConstituentNode, self).__init__(ndtype)
        self._idx = idx
        self._head_idx = head_idx
        self._parent_idx = parent_idx
        self._simple_span = simple_span
        self._child_nodes = children

    def __unicode__(self):
        return u'%s%s' % (self.ndtype.signature, self.simple_span)

    def __str__(self):
        return safe_utf8_encode(self.__unicode__())

    def __repr__(self):
        return str(self)

    @property
    def child_nodes(self):
        """Get a list of the child nodes."""
        return self._child_nodes

    @property
    def isnary(self):
        """Return true is the node is not a leaf or unary."""
        return not self.isleaf and len(self.child_nodes) > 1

    @property
    def idx(self):
        """Return the index of this node"""
        return self._idx

    @property
    def head_idx(self):
        """Return the lexical head of the phrase"""
        return self._head_idx

    @property
    def parent_idx(self):
        """Return the parent node index"""
        return self._parent_idx

    @property
    def simple_span(self):
        """Return the lexical range (span) of the constituent"""
        return self._simple_span

    @classmethod
    def from_json(self, data):
        simple_span=data['span']
        if len(simple_span) != 2:
            simple_span = None
        return ConstituentNode(ct.Typeof[data['ndtype']], simple_span=simple_span,
                                       parent_idx=data['chead'], head_idx=data['dhead'])
    def clone(self):
        """Deep copy of object"""
        return ConstituentNode(self.ndtype, self.idx, self.simple_span, self.parent_idx, self.head_idx)

    def remove_child(self, index):
        """Remove the child at index and return it."""
        child = None
        if self._child_nodes is not None:
            child = self._child_nodes[index]
            self._simple_span.difference_inplace(child.simple_span)
            if index == 0:
                self._child_nodes = self._child_nodes[1:]
            elif index == (len(self._child_nodes)-1):
                self._child_nodes.pop()
            else:
                self._child_nodes = self._child_nodes[0:index]
                self._child_nodes.extend(self._child_nodes[index+1:])
        if len(self._child_nodes) == 0:
            self._child_nodes = None
            assert self.simple_span.width == 0

        return child

    def insert_child(self, index, child):
        """Insert child (or child_nodes) at index."""
        if self._child_nodes is None:
            if index != 0:
                raise IndexError('child insert %d out of bounds' % index)
            self._child_nodes = [child] if not isinstance(child, collections.Iterable) else [x for x in child]
            for ch in self._child_nodes:
                self._simple_span.union_inplace(ch.simple_span)
                ch._parent_idx = self._idx
        elif isinstance(child, collections.Iterable):
            tmp = self._child_nodes[index:]
            self._child_nodes = self._child_nodes[0:index]
            self._child_nodes.extend(child)
            self._child_nodes.extend(tmp)
            for ch in child:
                self._simple_span.union_inplace(ch.simple_span)
                ch._parent_idx = self._idx
        else:
            self._child_nodes.insert(index, child)
            self._simple_span.union_inplace(child.simple_span)
            child._parent_idx = self._idx


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
        if self.node.simple_span is not None:
            for i in self.node.simple_span:
                h = h ^ hash(i)
        return h

    def __eq__(self, other):
        return self.node.ndtype is other.node.ndtype \
               and 0 == _compare_simple_span(self.node.simple_span, other.node.simple_span)

    def __ne__(self, other):
        return self.node.ndtype is other.node.ndtype \
               or 0 != _compare_simple_span(self.node.simple_span, other.node.simple_span)

    def __lt__(self, other):
        cmp = _compare_simple_span(self.node.simple_span, other.node.simple_span)
        return cmp < 0 or (0 == cmp and self.node.ndtype < other.node.ndtype)

    def __gt__(self, other):
        cmp = _compare_simple_span(self.node.simple_span, other.node.simple_span)
        return cmp > 0 or (0 == cmp and self.node.ndtype > other.node.ndtype)

    def __le__(self, other):
        return not self.__gt__()

    def __ge__(self, other):
        return not self.__lt__()

    def __contains__(self, other):
        return other is not None and other.width != 0 and self.width != 0 and \
               _compare_simple_span(self.node.simple_span, other.node.simple_span) <= 0

    @property
    def isempty(self):
        return self.node.simple_span is None

    @property
    def isroot(self):
        """Test if this is the root constituent."""
        return self is self.sentence.constituent_at(self.node.parent_idx)

    @property
    def isleaf(self):
        return self.node.isleaf

    @property
    def ndtype(self):
        return self.node.ndtype

    @property
    def span(self):
        return Span(self.sentence, self.node.simple_span) \
            if self.node.simple_span is not None else Span(self.sentence, self.node.head_idx, self.node.head_idx+1)

    @property
    def head(self):
        """Get the head lexeme of the constituent.

        Returns:
            A Lexeme instance.
        """
        return self.sentence[self.node.head_idx]

    @property
    def chead(self):
        """Get the head constituent.

        Returns:
            A Constituent instance or None if the root constituent.
        """
        chd = self.sentence.constituent_at(self.node.parent_idx)
        return None if chd is self else chd

    def marked_text(self, mark='#', minimal=True):
        """Get the constituent text with the the head marked."""
        if self.isempty:
            return ''
        hd = self.head
        span = self.span
        if minimal:
            txt = [mark + span[0].word if span[0] is hd else span[0].word]
            for tok in span[1:]:
                if not tok.ispunct:
                    txt.append(' ')
                txt.append(mark + tok.word if tok is hd else tok.word)
            return ''.join(txt)
        return ' '.join(itertools.imap(lambda x: mark + x.word if x is hd else x.word, span))

    def children(self):
        ch = self.node.child_nodes
        return None if ch is None else [Constituent(self._sent, x) for x in ch]


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

    def iterconstituents(self, dfs=True):
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
    """A sentence comprised of lexemes and constituents.

    Remarks:
        The constituents are ordered such that the leaves match their lexeme indexes.
    """
    def __init__(self, lexemes, constituents=None, msgid=None):
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

    @property
    def constituent_count(self):
        return len(self._constituents)

    def iterconstituents(self, dfs=True):
        """DFS iteration from root or linear iteration from root."""
        if len(self._constituents) == 0:
            return
        if dfs:
            # Root is last index
            for nd in self._constituents[-1].iternodes():
                yield Constituent(self, nd)
        else:
            # Linear iteration
            for nd in reversed(self._constituents):
                yield Constituent(self, nd)

    def constituent_root(self):
        """Return the root node"""
        return self._constituents[-1] if len(self._constituents) != 0 else None

    def find_constituent(self, span):
        """Find the constituent containing the span argument.

        Args:
            span: A Span instance.

        Returns:
            A Constituent instance or None if not found.
        """
        # leaves are first
        if span.isempty:
            return None
        # constituents are sorted by lexeme index, then span
        start, end = (0, len(self._lexemes)) if len(span) == 1 else (len(self._lexemes), len(self._constituents))
        for nd in itertools.ifilter(lambda nd: nd.simple_span.width >= len(span), self._constituents[start:end]):
            c = Constituent(self, nd)
            if span in c.span:
                return c
        return None

    def find_span(self, text, ignorecase=True):
        """Find the span containing the given text.

        Args:
            text: A string.
            ignorecase: Case sensitivity of search.

        Returns:
            A Span instance or None if not found.
        """
        if ignorecase:
            tokens = [x.strip() for x in text.lower().split()]
        else:
            tokens = [x.strip() for x in text.split()]
        k = len(tokens)
        lexicon = set(tokens)
        m = filter(lambda i: tokens[i] == tokens[-1], range(len(tokens)-1))
        m.append(k-1)
        m = m[0] + 1
        n = len(self._lexemes)
        i = k
        while i < n:
            w = self._lexemes[i].word.lower() if ignorecase else self._lexemes[i]
            if tokens[-1] == w:
                if all(itertools.imap(lambda x: x[0] == x[1].word.lower(), zip(tokens, self._lexemes[i-k+1:i]))):
                    return Span(self, i-k+1, i+1)
                i += m
            elif w in lexicon:
                i += 1
            else:
                i += m


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


class SimpleIndexSpan(object):
    """A set of non-contiguous indexes in a sentence span."""
    def __init__(self, indexes=None, issorted=False):
        """Constructor.

        :param indexes: The indexes
        :param issorted: True if the indexes are sorted
        """
        self.issorted = False
        if indexes is None:
            self.indexes = []
            self.issorted = True
        elif isinstance(indexes, set):
            self.indexes = indexes
        elif isinstance(indexes, collections.Iterator):
            self.indexes = set(indexes)
        elif issorted or (len(indexes) != 0 and len(indexes) == (1 + indexes[-1] - indexes[0])):
            self.indexes = indexes
            self.issorted = True
        else:
            self.indexes = set(indexes)

    def _resort(self):
        if not self.issorted:
            self.indexes = sorted(self.indexes)
            self.issorted = True

    def _reset(self):
        if self.issorted:
            self.indexes = set(self.indexes)
            self.issorted = False

    def __unicode__(self):
        if not self.issorted:
            indexes = [unicode(x) for x in sorted(self.indexes)]
        else:
            indexes = [unicode(x) for x in self.indexes]
        return u'(%s)' % ','.join(indexes)

    def __str__(self):
        return safe_utf8_encode(self.__unicode__())

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        self._resort()
        return self.begin == other.begin and self.end == other.end

    def __ne__(self, other):
        self._resort()
        return self.begin != other.begin or self.end != other.end

    def __lt__(self, other):
        self._resort()
        return self.begin < other.begin or (self.begin == other.begin and self.end > other.end)

    def __gt__(self, other):
        self._resort()
        return self.begin > other.begin or (self.begin == other.begin and self.end < other.end)

    def __le__(self, other):
        return not self.__gt__(other)

    def __ge__(self, other):
        return not self.__lt__(other)

    def __hash__(self):
        self._resort()
        h = 0
        for i in self.indexes:
            h = h ^ hash(i)
        return h

    @property
    def begin(self):
        self._resort()
        return 0 if len(self.indexes) == 0 else self.indexes[0]

    @property
    def end(self):
        self._resort()
        return 0 if len(self.indexes) == 0 else self.indexes[-1]+1

    @property
    def width(self):
        return len(self.indexes)

    def iterindexes(self, anysort=False):
        if not anysort:
            self._resort()
        for i in self.indexes:
            yield i

    def clone(self):
        if self.issorted:
            return SimpleIndexSpan(self.indexes, issorted=True)
        # Copy set incase add or remove are called
        return SimpleIndexSpan(self.iterindexes(anysort=True), issorted=False)

    def union(self, other):
        self._reset()
        indexes = self.indexes.union(other.iterindexes(anysort=True))
        return SimpleIndexSpan(indexes)

    def union_inplace(self, other):
        self._reset()
        self.indexes = self.indexes.union(other.iterindexes(anysort=True))
        return self

    def intersection(self, other):
        self._reset()
        indexes = self.indexes.intersection(other.iterindexes(anysort=True))
        return SimpleIndexSpan(indexes)

    def intersection_inplace(self, other):
        self._reset()
        self.indexes = self.indexes.intersection(other.iterindexes(anysort=True))
        return self

    def difference(self, other):
        self._reset()
        indexes = self.indexes.difference(other.iterindexes(anysort=True))
        return SimpleIndexSpan(indexes)

    def difference_inplace(self, other):
        self._reset()
        self.indexes = self.indexes.difference(other.iterindexes(anysort=True))
        return self

    def at(self, i):
        self._resort()
        return self.indexes[i]

    def add(self, idx):
        """Add an index to the span."""
        self._reset()
        if isinstance(idx, AbstractLexeme):
            self.indexes.add(idx.idx)
        else:
            self.indexes.add(idx)
        return self

    def remove(self, idx):
        """Remove an index from the span."""
        self._reset()
        if isinstance(idx, AbstractLexeme):
            self.indexes.remove(idx.idx)
        else:
            self.indexes.remove(idx)
        return self

    def contains_index(self, idx):
        if self.issorted:
            i = bisect.bisect_left(self.indexes, idx)
            return i != len(self.indexes) and self.indexes[i] == idx
        return idx in self.indexes

    def contains_span(self, other):
        return self.intersection(other).width == other.width


class Span(AbstractSpan):
    """A container for a sentence span."""
    def __init__(self, sentence, begin=None, end=None, issorted=False):
        if not isinstance(sentence, AbstractSentence):
            raise TypeError('Span constructor requires AbstractSentence type')
        self._sent = sentence
        if isinstance(begin, (SimpleSpan, SimpleIndexSpan)):
            self.spobj = begin.clone()  # SimpleIndexSpan(begin.iterindexes())
        elif isinstance(begin, (int, long)):
            self.spobj = SimpleSpan(begin, end) # SimpleIndexSpan(xrange(begin, end))
        else:
            assert end is None
            self.spobj = SimpleIndexSpan(begin)

        '''
        if isinstance(begin, (SimpleSpan, SimpleIndexSpan)):
            self.spobj = begin
            self._compress()
        elif isinstance(begin, (int, long)):
            self.spobj = SimpleSpan(begin, end)
        else:
            assert end is None
            self.spobj = SimpleIndexSpan(begin, issorted=self.issorted)
            self._compress()
        '''

    def _compress(self):
        if isinstance(self.spobj, SimpleIndexSpan) and len(self) != 0 and \
                (self.spobj.begin + self.spobj.width) == self.spobj.end:
            self.spobj = SimpleSpan(self.spobj.begin, self.spobj.end)

    def _decompress(self):
        if isinstance(self.spobj, SimpleSpan):
            self.spobj = SimpleIndexSpan(self.spobj.iterindexes() if len(self) != 0 else None)

    def __hash__(self):
        return hash(id(self._sent)) ^ hash(self.spobj)

    def __eq__(self, other):
        return  self._sent is other._sent and \
                self.spobj.width == other.spobj.width and \
               (self.intersection(other).spobj.width == self.spobj.width)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        if self._sent is not other._sent:
            return id(self._sent) < id(other._sent)
        return self.spobj.begin < other.spobj.begin or \
               (self.spobj.begin == other.spobj.begin and self.spobj.end > other.spobj.end)

    def __gt__(self, other):
        if self._sent is not other._sent:
            return id(self._sent) > id(other._sent)
        return self.spobj.begin > other.spobj.begin or \
               (self.spobj.begin == other.spobj.begin and self.spobj.end < other.spobj.end)

    def __le__(self, other):
        return not self.__gt__(other)

    def __ge__(self, other):
        return not self.__lt__(other)

    def __len__(self):
        return self.spobj.width

    def __getitem__(self, i):
        if isinstance(i, slice):
            if isinstance(self.spobj, SimpleIndexSpan):
                self.spobj._resort()
                return Span(self._sent, self.spobj.indexes[i], issorted=True)
            elif i.step is not None and i.step != 1:
                indexes = [x for x in self.spobj.iterindexes()]
                return Span(self._sent, indexes[i], issorted=True)
            else:
                start = self.spobj.begin if i.start is None else (self.spobj.begin + i.start)
                stop  = self.spobj.end if i.stop is None else (self.spobj.end + i.stop)
                sp = Span(self._sent, self.spobj.intersection(SimpleSpan(start, stop)))
                sp2 = Span(self._sent, SimpleIndexSpan(range(start, stop)).intersection(self.spobj))
                assert sp.intersection(sp2) == sp
                return sp
        return self._sent[self.spobj.at(i)]

    def __iter__(self):
        for k in self.spobj.iterindexes():
            yield self._sent[k]

    def __contains__(self, item):
        if isinstance(item, Span):
            if isinstance(item.spobj, SimpleIndexSpan):
                return item.spobj.intersection(self.spobj).width == item.spobj.width
            return self.spobj.intersection(item.spobj).width == item.spobj.width
        elif isinstance(item, int):
            return self.spobj.contains_index(item)
        elif not isinstance(item, AbstractLexeme):
            raise TypeError('Span.__contains__ expects a Span, Lexeme, or int type')
        # Lexeme
        return self.spobj.contains_index(item.idx)

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

    @property
    def sentence(self):
        return self._sent

    @property
    def isempty(self):
        return len(self) == 0

    def clear(self):
        """Make the span empty."""
        self.spobj = SimpleIndexSpan([])

    def iterindexes(self):
        return self.spobj.iterindexes()

    def indexes(self):
        """Get the list of indexes in this span."""
        return [x for x in self.spobj.iterindexes()]

    def clone(self):
        """Do a shallow copy and clone the span."""
        return Span(self._sent, self.spobj.clone())

    def union(self, other):
        """Union two spans."""
        assert self._sent is other._sent
        if other is None or len(other) == 0:
            return self
        if isinstance(other.spobj, SimpleIndexSpan):
            return Span(self._sent, other.spobj.union(self.spobj))
        sp = Span(self._sent, self.spobj.union(other.spobj))
        sp2 = Span(self._sent, SimpleIndexSpan(self.spobj.iterindexes()).union(other.spobj))
        assert sp == sp2
        return Span(self._sent, self.spobj.union(other.spobj))

    def add(self, idx):
        """Add an index to the span."""
        if isinstance(self.spobj, SimpleSpan):
            if (idx+1) == self.spobj.begin or idx == self.spobj.end:
                self.spobj = self.spobj.union_inplace(SimpleSpan(idx))
            else:
                self.spobj = SimpleIndexSpan(self.spobj.iterindexes()).add(idx)
        else:
            self.spobj.add(idx)
        return self

    def remove(self, idx):
        """Remove an index from the span."""
        if isinstance(self.spobj, SimpleSpan):
            if idx == self.spobj.begin or idx == (self.spobj.end-1):
                self.spobj = self.spobj.difference_inplace(SimpleSpan(idx))
            else:
                self.spobj = SimpleIndexSpan(self.spobj.iterindexes()).remove(idx)
        else:
            self.spobj.remove(idx)
        return self

    def difference(self, other):
        """Remove other from this span."""
        if other is None or len(other) == 0:
            return self
        assert self._sent is other._sent
        if isinstance(self.spobj, SimpleSpan):
            if isinstance(other.spobj, SimpleSpan):
                sp = self.spobj.difference(other.spobj)
                if isinstance(sp, tuple):
                    return Span(self._sent, sp[0]).union(Span(self._sent, sp[1]))
                else:
                    return Span(self._sent, sp)
            return Span(self._sent, SimpleIndexSpan(self.spobj.iterindexes()).difference_inplace(other.spobj))
        return Span(self._sent, self.spobj.difference(other.spobj))

    def intersection(self, other):
        """Find common span."""
        if other is None or len(other) == 0:
            return Span(self._sent)
        assert self._sent is other._sent
        if isinstance(self.spobj, SimpleSpan):
            if isinstance(other.spobj, SimpleSpan):
                return Span(self._sent, self.spobj.intersection(other.spobj))
            return Span(self._sent, other.spobj.intersection(self.spobj))
        return Span(self._sent, self.spobj.intersection(other.spobj))

    def subspan(self, required, excluded=0):
        """Refine the span with `required` and `excluded` criteria's.

        Args:
            required: A mask of RT_? bits.
            excluded: A mask of RT_? bits.

        Returns:
            A Span instance.
        """
        return Span(self._sent, filter(lambda i: 0 != (self._sent[i].mask & required) and \
                                                 0 == (self._sent[i].mask & excluded), self.iterindexes()))

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
        if len(self) <= 1:
            return self
        return Span(self._sent, SimpleSpan(self.spobj.begin, self.spobj.end))

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
        return drt.drs.DRS(refs, conds)

    def get_head_span(self, strict=False):
        """Get the head lexemes of the span.

        Args:
            strict: If true then heads must point to a lexeme within the span. If false then some
                head must point to a lexeme within the span.

        Returns:
            A span of Lexeme instances.
        """
        # Handle singular case
        if len(self) == 1:
            return self

        indexes = set(self.indexes())
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
                        wr = self._sent.safe_wikipage(t)
                        if wr is not None:
                            topics.append(wr)

                if len(topics) == 0:
                    # Get suggestions from wikipedia
                    query = wikipedia.suggest(txt)
                    if query is not None:
                        result = self._sent.safe_wikipage(query)
                        if result is not None:
                            return [result]
                    if google and (result is None or len(result) == 0):
                        # Try google search - hopefully will fix up spelling or ignore irrelevent words
                        scraper = kb.google_search.GoogleScraper(browser)
                        spell, urls = scraper.search(txt, 'wikipedia.com')
                        if spell is not None:
                            result = wikipedia.search(txt, results=max_results)
                            if result is not None and len(result) != 0:
                                for t in result:
                                    wr = self._sent.safe_wikipage(t)
                                    if wr is not None:
                                        topics.append(wr)

                            if len(topics) == 0:
                                # Get suggestions from wikipedia
                                query = wikipedia.suggest(txt)
                                if query is not None:
                                    result = self._sent.safe_wikipage(query)
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
                                    wr = self._sent.safe_wikipage(t.replace('_', ' '))
                                    if wr:
                                        topics.append(wr)
                                        if len(topics) >= max_results:
                                            break
                return topics if len(topics) != 0 else None
            except requests.exceptions.ConnectionError as e:
                attempts += 1
                retry = attempts <= 3
                if self._sent.msgid is not None:
                    _logger.exception('[msgid=%s] Span.search_wikipedia', self._sent.msgid, exc_info=e)
                else:
                    _logger.exception('Span.search_wikipedia', exc_info=e)
                time.sleep(0.25)
            except wikipedia.exceptions.DisambiguationError as e:
                # TODO: disambiguation
                retry = False
            except wikipedia.exceptions.HTTPTimeoutError as e:
                attempts += 1
                retry = attempts <= 3
                if self._sent.msgid is not None:
                    _logger.exception('[msgid=%s] Span.search_wikipedia', self._sent.msgid, exc_info=e)
                else:
                    _logger.exception('Span.search_wikipedia', exc_info=e)
                time.sleep(0.25)

        return None
