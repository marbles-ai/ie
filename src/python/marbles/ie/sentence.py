from __future__ import unicode_literals, print_function
import drt
from kb import google_search
import wikipedia
import re
import collections
import os
import logging
import requests
import time
import constituent_types
import utils.cache
from marbles import safe_utf8_encode, safe_utf8_decode
from marbles.log import ExceptionRateLimitedLogAdaptor


_actual_logger = logging.getLogger(__name__)
_logger = ExceptionRateLimitedLogAdaptor(_actual_logger)


# Remove extra info from wikipedia topic
_WTOPIC = re.compile(r'http://.*/(?P<topic>[^/]+(\([^)]+\))?)')

# Rate limit wiki requests
wikipedia.set_rate_limiting(rate_limit=True)


class DocProp(object):
    @property
    def no_vn(self):
        return True

    @property
    def no_wn(self):
        return True


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


def safe_wikipage(query):
    global _logger
    try:
        return wikipedia.page(title=query)
    except wikipedia.PageError as e:
        _logger.warning('wikipedia.page(%s) - %s', query, str(e))

    return None


class Constituent(object):
    """A constituent is a sentence span with an category."""
    def __init__(self, span, vntype, chead=-1):
        if not isinstance(span, IndexSpan) or not isinstance(vntype, utils.cache.ConstString):
            raise TypeError('Constituent.__init__() bad argument')
        self.span = span
        self.vntype = vntype
        self.wiki_data = None
        self.chead = chead

    def get_json(self):
        result = {
            'span': self.span.get_indexes(),
            'vntype': self.vntype.signature,
            'chead': self.chead
        }
        if self.wiki_data:
            result['wiki'] = self.wiki_data.get_json()
        return result

    @classmethod
    def from_json(self, data, sentence):
        c = Constituent(None, None)
        c.vntype = constituent_types.Typeof[data['vntype']]
        c.span = IndexSpan(sentence, data['span'])
        c.chead = data['chead']
        if 'wiki' in data:
            c.wiki_data = Wikidata.from_json(data['wiki'])

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

    def get_head(self, multihead=False):
        """Get the head lexeme of the constituent.

        Returns:
            A Lexeme instance.
        """
        indexes = set(self.span.get_indexes())

        # Handle singular case
        if len(indexes) == 1:
            return self.span[0] if not multihead else [self.span[0]]

        hd = set(indexes)
        for lex in self.span:
            if lex.head != lex.idx and lex.head in indexes:
                hd.remove(lex.idx)
        if len(hd) == 0:
            return None
        # We don't support multiple heads
        if len(hd) != 1 and not multihead:
            raise ValueError('multiple heads (%s) for constituent %s' %
                             (repr(IndexSpan(self.span.sentence, hd).text), repr(self)))
        return self.span.sentence[hd.pop()] if not multihead else [self.span.sentence[i] for i in hd]

    def get_chead(self):
        """Get the head constituent.

        Returns:
            A Constituent instance or None if the root constituent.
        """
        return self.span.sentence.get_constituent_at(self.chead)

    def set_wiki_entry(self, page):
        self.wiki_data = Wikidata(page)

    def search_wikipedia(self, max_results=1, google=True):
        """Find a wikipedia topic from this span.

        Returns: A wikipedia topic.
        """
        global _logger
        retry = True
        attempts = 0
        while retry:
            try:
                txt = self.span.text
                topics = []
                result = wikipedia.search(txt, results=max_results)
                if result is not None and len(result) != 0:
                    for t in result:
                        wr = safe_wikipage(t)
                        if wr is not None:
                            topics.append(wr)

                if len(topics) == 0:
                    # Get suggestions from wikipedia
                    query = wikipedia.suggest(txt)
                    if query is not None:
                        result = safe_wikipage(query)
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
                                    wr = safe_wikipage(t)
                                    if wr is not None:
                                        topics.append(wr)

                            if len(topics) == 0:
                                # Get suggestions from wikipedia
                                query = wikipedia.suggest(txt)
                                if query is not None:
                                    result = safe_wikipage(query)
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
                                    wr = safe_wikipage(t.replace('_', ' '))
                                    if wr:
                                        topics.append(wr)
                                        if len(topics) >= max_results:
                                            break
                return topics if len(topics) != 0 else None
            except requests.exceptions.ConnectionError as e:
                attempts += 1
                retry = attempts <= 3
                _logger.exception('Constituent.search_wikipedia', exc_info=e)
                time.sleep(0.25)
            except wikipedia.exceptions.DisambiguationError as e:
                # TODO: disambiguation
                retry = False
            except wikipedia.exceptions.HTTPTimeoutError as e:
                attempts += 1
                retry = attempts <= 3
                _logger.exception('Constituent.search_wikipedia', exc_info=e)
                time.sleep(0.25)

        return None


class UnboundSentence(collections.Sequence):
    """A sentence with no bound to a discourse."""

    def __getitem__(self, slice_i_j):
        if isinstance(slice_i_j, slice):
            indexes = [i for i in range(len(self))]
            return IndexSpan(self, indexes[slice_i_j])
        return self.at(slice_i_j)

    def __iter__(self):
        for i in range(len(self)):
            yield self.at(i)

    def __len__(self):
        raise NotImplementedError

    def at(self, i):
        """Get the lexeme at index i."""
        raise NotImplementedError

    def get_constituents(self):
        """Get the list of constituents"""
        raise NotImplementedError

    def get_constituent_at(self, i):
        """Get the constituent at index i."""
        raise NotImplementedError

    def get_constituent_tree(self):
        """Get the constituent tree as an adjacency list of lists."""
        constituents = self.get_constituents()
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
        c = self.get_constituent_at(ctree[0])
        print('%s%02d %s(%s)' % (indent, ctree[0], c.vntype.signature, c.span.text))
        for nd in ctree[1]:
            self.print_constituent_tree(nd, level+3)

    def _get_constituent_tree_as_string_helper(self, ctree, level, result):
        indent = '' if level == 0 else ' ' * level
        c = self.get_constituent_at(ctree[0])
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



class IndexSpan(collections.Sequence):
    """View of a discourse."""
    def __init__(self, sentence, indexes=None):
        if not isinstance(sentence, UnboundSentence):
            raise TypeError('IndexSpan constructor requires sentence type = UnboundSentence')
        self._sent = sentence
        if indexes is None:
            self._indexes = []
        elif isinstance(indexes, set):
            self._indexes = sorted(indexes)
        else:
            self._indexes = sorted(set([x for x in indexes]))

    def __unicode__(self):
        return unicode(self.get_drs())

    def __str__(self):
        return str(self.get_drs())

    def __repr__(self):
        return str(self.get_drs())

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
        txt = self._sent.at(self._indexes[0]).word
        for i in self._indexes[1:]:
            tok = self._sent.at(i)
            if tok.ispunct:
                txt += tok.word
            else:
                txt += ' ' + tok.word
        return txt

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
        return drt.drs.DRS(refs, conds)

    def get_subspan_from_wiki_search(self, search_result, max_results=0):
        """Get a subspan from a wikpedia search result.

        Args:
            search_result: The result of a wikipedia.search().
            max_results: If zero return a IndexSpan, else return a list of IndexSpan.

        Returns:
            A IndexSpan instance or a list of IndexSpan instances.
        """
        spans = {}
        # FIXME: rank using statistical model based on context
        for result in search_result:
            title = result.title.split(' ')
            idxs = set()
            words = {}
            for lex in self:
                for nm in title:
                    nml = nm.lower()
                    p1 = os.path.commonprefix([lex.word.lower(), nml])
                    p2 = os.path.commonprefix([lex.stem.lower(), nml])
                    if (len(p1) - len(p2)) >= 0:
                        if len(p1) >= (len(nml)/2):
                            idxs.add(lex.idx)
                    elif len(p2) > len(p1) and len(p2) >= (len(nml)/2):
                        idxs.add(lex.idx)
            idxs = sorted(idxs)
            if len(idxs) >= 2:
                idxs = [x for x in range(idxs[0], idxs[-1]+1)]
            spans.setdefault(len(idxs), [])
            spans[len(idxs)].append(IndexSpan(self._sent, idxs))

        # Order by size
        ranked_spans = []
        for k in reversed(sorted(spans.iterkeys())):
            ranked_spans.extend(spans[k])
        if len(ranked_spans) == 0:
            return None
        return ranked_spans[0] if max_results == 0 else ranked_spans[0:max_results]


