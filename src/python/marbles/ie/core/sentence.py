from __future__ import unicode_literals, print_function

import collections
import itertools
import logging
import time

import requests
import wikipedia

import marbles.ie.drt
import marbles.ie.utils.cache
from marbles.ie.ccg import *
from marbles.ie.kb import google_search
from marbles.ie.core import constituent_types as ct
from marbles.ie.core.constants import *
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


class Constituent(object):
    """A constituent is a sentence span and a phrase type."""
    def __init__(self, span, vntype, chead=-1):
        if not isinstance(span, IndexSpan) or not isinstance(vntype, marbles.ie.utils.cache.ConstString):
            raise TypeError('Constituent.__init__() bad argument')
        self.span = span
        self.vntype = vntype
        self.chead = chead

    def get_json(self):
        result = {
            'span': self.span.get_indexes(),
            'vntype': self.vntype.signature,
            'chead': self.chead
        }
        return result

    @classmethod
    def from_json(self, data, sentence):
        c = Constituent(None, None)
        c.vntype = ct.Typeof[data['vntype']]
        c.span = IndexSpan(sentence, data['span'])
        c.chead = data['chead']

    def __unicode__(self):
        return self.vntype.signature + u'(' + u' '.join([safe_utf8_decode(x.word) for x in self.span]) + u')'

    def __str__(self):
        return safe_utf8_encode(self.__unicode__())

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(self.span)

    def __eq__(self, other):
        return self.vntype is other.vntype and self.span == other.span

    def __ne__(self, other):
        return self.vntype is other.vntype or self.span != other.span

    def __lt__(self, other):
        return self.span < other.span or (self.span == other.span and self.vntype < other.vntype)

    def __gt__(self, other):
        return self.span > other.span or (self.span == other.span and self.vntype > other.vntype)

    def __le__(self, other):
        return not self.__gt__()

    def __ge__(self, other):
        return not self.__lt__()

    def __contains__(self, item):
        return item.span in self.span

    @property
    def sentence(self):
        return self.span.sentence

    def clone(self):
        return Constituent(self.span.clone(), self.vntype, self.chead)

    def get_head(self, multihead=False):
        """Get the head lexeme of the constituent.

        Args:
            multihead: If True the return result is a list of heads. If false
                a consituent with multiple heads will cause a ValueError.

        Returns:
            A Lexeme instance or None if the constituent span is empty.

        Raises:
            ValueError
        """
        if self.span.isempty:
            return None
        hdspan = self.span.get_head_span()
        if len(hdspan) != 1 and not multihead:
            raise ValueError('multiple heads (%s) for constituent %s' %
                             (repr(hdspan.text), repr(self)))
        return hdspan[0] if not multihead else [lex for lex in hdspan]

    def get_chead(self):
        """Get the head constituent.

        Returns:
            A Constituent instance or None if the root constituent.
        """
        return self.span.sentence.constituents[self.chead]


class Sentence(collections.Sequence):
    """A sentence."""

    def __init__(self, lexemes=None, constituents=None, i2c=None, msgid=None):
        if lexemes is not None:
            self.lexemes = lexemes
            self.constituents = constituents or []
        else:
            self.lexemes = []
            self.constituents = []
            i2c = None
        self.i2c = i2c or {}
        self.msgid = msgid
        if i2c is None and self.constituents is not None:
            self.map_heads_to_constituents()

    def __len__(self):
        return len(self.lexemes)

    def __getitem__(self, slice_i_j):
        if isinstance(slice_i_j, slice):
            indexes = [i for i in range(len(self))]
            return IndexSpan(self, indexes[slice_i_j])
        return self.at(slice_i_j)

    def __iter__(self):
        for i in range(len(self)):
            yield self.at(i)

    def at(self, i):
        """Get the lexeme at index i."""
        return self.lexemes[i]

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

    def get_constituent_tree(self):
        """Get the constituent tree as an adjacency list of lists."""
        constituents = self.constituents
        if len(constituents) == 0:
            return []

        # Each node is a tuple (constituency index, [adjacency tuples])
        nodes = [(i, []) for i in range(len(constituents))] # create empty
        seen = [[] for i in range(len(constituents))]
        root = 0
        for i in range(len(constituents)):
            nd = constituents[i]
            if nd.chead != i:
                if i not in seen[nd.chead]:
                    nodes[nd.chead][1].append(nodes[i])
                    seen[nd.chead].append(i)
            else:
                root = nd.chead
        return nodes[root]

    def print_constituent_tree(self, ctree, level=0):
        """Print the constituent tree."""
        indent = '' if level == 0 else ' ' * level
        c = self.constituents[ctree[0]]
        print('%s%02d %s(%s)' % (indent, ctree[0], c.vntype.signature, c.span.text))
        for nd in ctree[1]:
            self.print_constituent_tree(nd, level+3)

    def _get_constituent_tree_as_string_helper(self, ctree, level, result):
        indent = '' if level == 0 else ' ' * level
        c = self.constituents[ctree[0]]
        result.append('%s%02d %s(%s)' % (indent, ctree[0], c.vntype.signature, c.span.text))
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
            nd = self.at(i)
            if nd.head != i:
                if i not in seen[nd.head]:
                    nodes[nd.head][1].append(nodes[i])
                    seen[nd.head].append(i)
            else:
                root = nd.head
        return nodes[root]

    def print_dependency_tree(self, dtree, level=0):
        """Print the constituent tree."""
        indent = '' if level == 0 else ' ' * level
        lex = self.at(dtree[0])
        print('%s%02d %-4s(%s)' % (indent, dtree[0], lex.pos, lex.word))
        for nd in dtree[1]:
            self.print_dependency_tree(nd, level+3)

    def _get_dependency_tree_as_string_helper(self, dtree, level, result):
        indent = '' if level == 0 else ' ' * level
        lex = self.at(dtree[0])
        result.append('%s%02d %-4s(%s)' % (indent, dtree[0], lex.pos, lex.word))
        for nd in dtree[1]:
            self._get_dependency_tree_as_string_helper(nd, level+3, result)
        return result

    def get_dependency_tree_as_string(self, ctree):
        """Get the dependency tree as a string."""
        result = self._get_dependency_tree_as_string_helper(ctree, 0, [])
        return '\n'.join(result)

    def map_heads_to_constituents(self):
        """Set constituent heads."""

        # Lexeme head index is always in constituent so use it to map between the two.
        i2c = {}
        for i in range(len(self.constituents)):
            c = self.constituents[i]
            lexhd = c.get_head()
            if lexhd.idx in i2c:
                pass
            assert lexhd.idx not in i2c
            i2c[lexhd.idx] = i

        for i in range(len(self.constituents)):
            c = self.constituents[i]
            lexhd = c.get_head()
            if lexhd.head in i2c:
                c.chead = i2c[lexhd.head]
            else:
                while lexhd.head not in i2c and lexhd.head != lexhd.idx:
                    lexhd = self.at(lexhd.head)
                if lexhd.head in i2c:
                    c.chead = i2c[lexhd.head]
        self.i2c = dict(map(lambda x: (x[0], self.constituents[x[1]]), i2c.iteritems()))

    def trim(self, to_remove):
        assert isinstance(to_remove, IndexSpan)
        if to_remove.isempty:
            return self, None
        # Python 2.x does not support nonlocal keyword for the closure
        class context:
            i = 0
        def counter(inc=1):
            idx = context.i
            context.i += inc
            return idx

        # Remove constituents and remap indexes.
        context.i = 0
        constituents = map(lambda c: Constituent(c.span.difference(to_remove), c.vntype, c.chead), self.constituents)
        idxs_to_del = set(filter(lambda i: constituents[i].span.isempty, range(len(constituents))))
        if len(idxs_to_del) != 0:
            idxmap = map(lambda x: -1 if x in idxs_to_del else counter(), range(len(constituents)))
            constituents = map(lambda y: constituents[y], filter(lambda x: idxmap[x] >= 0, range(len(idxmap))))
            for c in constituents:
                if c.chead >= 0:
                    c.chead = idxmap[c.chead]
                    assert c.chead >= 0

        # Remove lexemes and remap indexes.
        context.i = 0
        idxs_to_del = set(to_remove.get_indexes())

        # Find the sentence head
        sentence_head = 0
        while self[sentence_head].head != sentence_head:
            sentence_head = self[sentence_head].head

        # Only allow deletion if it has a single child, otherwise we get multiple sentence heads
        if sentence_head in idxs_to_del and len(filter(lambda lex: lex.head == sentence_head, self)) != 2:
            idxs_to_del.remove(sentence_head)

        # Reparent heads marked for deletion
        for lex in itertools.ifilter(lambda x: x.idx not in idxs_to_del, self):
            lasthead = -1
            while lex.head in idxs_to_del and lex.head != lasthead:
                lasthead = lex.head
                lex.head = self[lex.head].head
            if lex.head in idxs_to_del:
                # New head for sentence
                lex.head = lex.idx

        idxmap = map(lambda x: -1 if x in idxs_to_del else counter(), range(len(self)))
        for c in constituents:
            c.span = IndexSpan(self, map(lambda y: idxmap[y],
                                         filter(lambda x: idxmap[x] >= 0, c.span.get_indexes())))
        lexemes = map(lambda y: self[y], filter(lambda x: idxmap[x] >= 0, range(len(idxmap))))
        for i in range(len(lexemes)):
            lexeme = lexemes[i]
            lexeme.idx = i
            lexeme.head = idxmap[lexeme.head]
            assert lexeme.head >= 0

        return Sentence(lexemes, constituents), idxmap

    def trim_punctuation(self):
        to_remove = IndexSpan(self, filter(lambda i: self[i].ispunct, range(len(self))))
        sent, _ = self.trim(to_remove)
        return sent

    def get_verbnet_sentence(self):

        constituents = [c.clone() for c in self.constituents]

        # Build adjacency list
        adj = map(lambda x: list(), constituents)
        for i in range(len(constituents)):
            c = constituents[i]
            if c.chead != i:
                adj[c.chead].append(i)

        vps = []
        allspan = IndexSpan(self)
        for i in itertools.ifilter(lambda x: constituents[x].vntype in [ct.CONSTITUENT_VP, ct.CONSTITUENT_SDCL,
                                                                        ct.CONSTITUENT_SEM, ct.CONSTITUENT_SQ,
                                                                        ct.CONSTITUENT_S, ct.CONSTITUENT_SINF],
                                   range(len(constituents))):
            ci = constituents[i]
            span = IndexSpan(self)
            for j in adj[i]:
                span = span.union(constituents[j].span)

            span = span.union(allspan)
            idxs = ci.span.difference(span).get_indexes()
            if len(idxs) == 0:
                ci.vntype = None
                ci.span.clear()
                continue
            hds = dict([(hd.idx, Constituent(IndexSpan(self), ci.vntype))
                        for hd in IndexSpan(self, idxs).get_head_span()])
            for j in idxs:
                k = j
                while k not in hds and self[k].head != k:
                    k = self[k].head
                hds[k].span.add(j)

            # Check referents
            refs = {}
            spcjs = IndexSpan(self)
            for cj in hds.itervalues():
                refs[cj.get_head().refs[0]] = cj
                spcjs = spcjs.union(cj.span)
            nspcj = ci.span.difference(spcjs)
            for lex in nspcj:
                if len(lex.refs) != 0 and lex.refs[0] in refs:
                    cj = refs[lex.refs[0]]
                    if lex.head in cj.span and 0 != (lex.mask & (RT_EVENT | RT_EVENT_MODAL | RT_EVENT_ATTRIB)):
                        cj.span.add(lex.idx)

            for cj in hds.itervalues():
                allspan = allspan.union(cj.span)
            vps.extend(hds.itervalues())
            ci.vntype = None
            ci.span.clear()

        for c in vps:
            if c.vntype is ct.CONSTITUENT_SINF:
                if len(c.span) == 1 and c.span[0] == 'to':
                    c.vntype = ct.CONSTITUENT_TO
            else:
                c.vntype = ct.CONSTITUENT_VP

        # Split Noun phrases
        for i in itertools.ifilter(lambda x: constituents[x].vntype is not None and constituents[x].vntype in [ct.CONSTITUENT_NP, ct.CONSTITUENT_PP],
                                   range(len(constituents))):
            ci = constituents[i]
            span = IndexSpan(self)
            for j in adj[i]:
                span = span.union(constituents[j].span)

            ctmp = Constituent(ci.span.difference(span), ci.vntype)
            if ctmp.span == ci.span:
                continue

            hds = ctmp.get_head(multihead=True)
            if len(hds) == 1:
                ci.span = ctmp.span
        ##
        # Constituent adjacency incorrect after this call
        ##
        constituents = filter(lambda x: x.vntype is not None, constituents)
        constituents.extend(vps)

        # TODO: do we need to do the same for PP, ADVP?
        # Split adjacent NP, ADVP|ADJP
        cadvp = filter(lambda x: x.vntype in [ct.CONSTITUENT_ADVP, ct.CONSTITUENT_ADJP], reversed(constituents))
        cnp   = filter(lambda x: x.vntype is ct.CONSTITUENT_NP, reversed(constituents))
        while len(cnp) > 0 and len(cadvp) > 0:
            c1 = cnp.pop()
            c2 = cadvp.pop()
            hd1 = c1.get_head()
            hd2 = c2.get_head()
            if c2.span in c1.span:
                lex = c2.span[0]
                if lex.idx > 0 and self[lex.idx-1].ispunct and hd2.head in c1.span:
                    c1.span = c1.span.difference(c2.span)
                else:
                    for lx in c2.span:
                        lx.mask &= ~RT_ADJUNCT
            elif hd1.idx < hd2.idx:
                cadvp.append(c2)
            elif hd1.idx > hd2.idx:
                cnp.append(c1)

        constituents = sorted(constituents)
        return Sentence([lex for lex in self], constituents)


class IndexSpan(collections.Sequence):
    """View of a discourse."""
    def __init__(self, sentence, indexes=None):
        if not isinstance(sentence, Sentence):
            raise TypeError('IndexSpan constructor requires sentence type = Sentence')
        self._sent = sentence
        if indexes is None:
            self._indexes = []
        elif isinstance(indexes, set):
            self._indexes = sorted(indexes)
        else:
            self._indexes = sorted(set([x for x in indexes]))

    def __unicode__(self):
        return safe_utf8_decode(self.text)

    def __str__(self):
        return safe_utf8_encode(self.text)

    def __repr__(self):
        return self.text

    def __eq__(self, other):
        return other is not None and self.sentence is other.sentence and len(self) == len(other) \
               and len(set(self._indexes).intersection(other._indexes)) == len(self)

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
            return IndexSpan(self._sent, self._indexes[i])
        return self._sent.at(self._indexes[i])

    def __iter__(self):
        for k in self._indexes:
            yield self._sent.at(k)

    def __contains__(self, item):
        if isinstance(item, IndexSpan):
            return len(item) != 0 and len(set(item._indexes).difference(self._indexes)) == 0
        elif isinstance(item, int):
            return item in self._indexes
        # Must be a Lexeme
        # FIXME: raise exception if not isinstance Lexeme
        return item.idx in self._indexes

    @property
    def text(self):
        if len(self._indexes) == 0:
            return ''
        txt = [self._sent.at(self._indexes[0]).word]
        for i in self._indexes[1:]:
            tok = self._sent.at(i)
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

    def get_indexes(self):
        """Get the list of indexes in this span."""
        return [x for x in self._indexes]

    def clone(self):
        """Do a shallow copy and clone the span."""
        return IndexSpan(self._sent, self._indexes)

    def union(self, other):
        """Union two spans."""
        if other is None or len(other) == 0:
            return self
        return IndexSpan(self._sent, set(self._indexes).union(other._indexes))

    def add(self, idx):
        """Add an index to the span."""
        u = set(self._indexes)
        u.add(idx)
        self._indexes = sorted(u)
        return self

    def difference(self, other):
        """Remove other from this span."""
        if other is None or len(other) == 0:
            return self
        return IndexSpan(self._sent, set(self._indexes).difference(other._indexes))

    def intersection(self, other):
        """Find common span."""
        if other is None or len(other) == 0:
            return IndexSpan(self._sent)
        return IndexSpan(self._sent, set(self._indexes).intersection(other._indexes))

    def subspan(self, required, excluded=0):
        """Refine the span with `required` and `excluded` criteria's.

        Args:
            required: A mask of RT_? bits.
            excluded: A mask of RT_? bits.

        Returns:
            A IndexSpan instance.
        """
        return IndexSpan(self._sent, filter(lambda i: 0 != (self[i].mask & required) and 0 == (self[i].mask & excluded), self._indexes))

    def fullspan(self):
        """Return the span which is a superset of this span but where the indexes are contiguous.

        Returns:
            A IndexSpan instance.
        """
        if len(self._indexes) <= 1:
            return self
        return IndexSpan(self._sent, [x for x in range(self._indexes[0], self._indexes[-1]+1)])

    def get_drs(self):
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
        return IndexSpan(self._sent, hds)

    def search_wikipedia(self, max_results=1, google=True):
        """Find a wikipedia topic from this span.

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
                        scraper = google_search.GoogleScraper()
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
                    _logger.exception('[msgid=%s] IndexSpan.search_wikipedia', self.sentence.msgid, exc_info=e)
                else:
                    _logger.exception('IndexSpan.search_wikipedia', exc_info=e)
                time.sleep(0.25)
            except wikipedia.exceptions.DisambiguationError as e:
                # TODO: disambiguation
                retry = False
            except wikipedia.exceptions.HTTPTimeoutError as e:
                attempts += 1
                retry = attempts <= 3
                if self.sentence.msgid is not None:
                    _logger.exception('[msgid=%s] IndexSpan.search_wikipedia', self.sentence.msgid, exc_info=e)
                else:
                    _logger.exception('IndexSpan.search_wikipedia', exc_info=e)
                time.sleep(0.25)

        return None
