from __future__ import unicode_literals, print_function
import drt
from ccg import Category, CAT_NP, CAT_PP, CAT_VP, CAT_VPdcl, CAT_VPb, CAT_VPto, CAT_AP, CAT_Sany, CAT_Sadj
from kb import google_search
import wikipedia
import re
import collections
import os
import logging
import requests
import time
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
    def __init__(self, category, span, vntype):
        self.span = span
        self.category = category
        self.vntype = safe_utf8_decode(vntype) if vntype is not None else None
        self.wiki_data = None

    def get_json(self):
        result = {
            'span': self.span.get_indexes(),
            'category': self.category.signature,
            'vntype': self.vntype
        }
        if self.wiki_data:
            result['wiki'] = self.wiki_data.get_json()
        return result

    @classmethod
    def from_json(self, data, sentence):
        c = Constituent(None, None, None)
        c.category = Category.from_cache(data['category'])
        c.vntype = data['vntype']
        c.span = IndexSpan(sentence, data['span'])
        if 'wiki' in data:
            c.wiki_data = Wikidata.from_json(data['wiki'])

    def __unicode__(self):
        return self.vntype + u'(' + u' '.join([safe_utf8_decode(x.word) for x in self.span]) + u')'

    def __str__(self):
        return safe_utf8_encode(self.__unicode__())

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(self.span)

    def __eq__(self, other):
        return self.span == other.span

    def __ne__(self, other):
        return self.span != other.span

    def __lt__(self, other):
        return self.span < other.span

    def __gt__(self, other):
        return self.span > other.span

    def __le__(self, other):
        return self.span <= other.span

    def __ge__(self, other):
        return self.span >= other.span

    def __contains__(self, item):
        return item.span in self.span

    @classmethod
    def vntype_from_category(cls, category):
        if category in [CAT_PP, CAT_NP]:
            return category.signature
        elif category == CAT_VPdcl and not category.simplify().ismodifier:
            return 'VP'
        elif category == CAT_VPb:
            return 'S_INF'
        elif category == CAT_VPto:
            return 'TO'
        elif category == CAT_AP:
            return 'ADJP'
        #elif category != CAT_Sadj and category == CAT_Sany:
        #    return category.signature
        return None

    def get_head(self):
        """Get the head lexeme of the constituent."""
        indexes = set(self.span.get_indexes())

        # Handle singular case
        if len(indexes) == 1:
            return self.span[0]

        hd = set(indexes)
        for lex in self.span:
            if lex.head != lex.idx and lex.head in indexes:
                hd.remove(lex.idx)
        if len(hd) == 0:
            return None
        # We don't support multiple heads
        assert len(hd) == 1
        return self.span.sentence[hd.pop()]

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
            return IndexSpan(self, [i for i in range(slice_i_j)])
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
        return len(self) < len(other)

    def __gt__(self, other):
        if self.sentence is not other.sentence:
            return id(self.sentence) > id(other.sentence)
        for i, j in zip(self._indexes, other._indexes):
            if i == j:
                continue
            return i > j
        return len(self) > len(other)

    def __le__(self, other):
        return not self.__gt__(other)

    def __ge__(self, other):
        return not self.__lt__(other)

    def __len__(self):
        return len(self._indexes)

    def __getitem__(self, i):
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

    def get_constituents(self, category_filter=None, heads_only=True):
        """Get the constituents of the span. These are only potential constituents.

        Args:
            category_filter: A Category or RegexCategoryClass instance or a list of these types (None == any == default).
            heads_only: Only return constituents where the head is in this span (default == True).

        Returns:
            An array of Constituent instances.
        """
        idxs = set(self._indexes)
        if category_filter:
            if isinstance(category_filter, collections.Iterable):
                if heads_only:
                    return filter(lambda x: x.category in category_filter and x.get_head().idx in idxs,
                                  self._sent.get_constituents())
                return filter(lambda x: x.category in category_filter and len(idxs.intersection(x.span.get_indexes())) != 0,
                              self._sent.get_constituents())
            if heads_only:
                return filter(lambda x: x.category == category_filter and x.get_head().idx in idxs,
                              self._sent.get_constituents())
            return filter(lambda x: x.category == category_filter and len(idxs.intersection(x.span.get_indexes())) != 0,
                          self._sent.get_constituents())
        # Any category
        if heads_only:
            return filter(lambda x: x.get_head().idx in idxs, self._sent.get_constituents())
        return filter(lambda x: len(idxs.intersection(x.span.get_indexes())) != 0, self._sent.get_constituents())

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


class Document(DocProp):
    """A sentence."""
    def __init__(self):
        self.sents = []

    @property
    def no_vn(self):
        return True

    @property
    def no_wn(self):
        return True
