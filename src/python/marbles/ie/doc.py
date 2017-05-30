import drt
from ccg import Category, CAT_NP, CAT_PP, CAT_VP, CAT_VPdcl, CAT_VPb, CAT_VPto, CAT_AP, CAT_Sany, CAT_Sadj
from kb import google_search
import wikipedia
import re
import collections
import os


# Remove extra info from wikipedia topic
_WTOPIC = re.compile(r'http://.*/(?P<topic>[^/]+(\([^)]+\))?)')


class DocProp(object):
    @property
    def no_vn(self):
        return True

    @property
    def no_wn(self):
        return True


class Constituent(object):
    """A constituent is a sentence span with an category."""
    def __init__(self, category, span, vntype):
        self.span = span
        self.category = category
        self.vntype = vntype

    def __repr__(self):
        return self.vntype + '(' + ' '.join([x.word for x in self.span]) + ')'

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
        elif category != CAT_Sadj and category == CAT_Sany:
            return category.signature
        return None

    def get_head(self):
        """Get the head lexeme of the constituent."""
        indexes = set(self.span.get_indexes())
        hd = set(indexes)
        for lex in self.span:
            if lex.head != lex.idx and lex.head in indexes:
                hd.remove(lex.idx)
        assert len(hd) == 1
        return self.span.sentence[hd.pop()]

    def search_wikipedia(self, max_results=1):
        """Find a wikipedia topic from this span.

        Returns: A wikipedia topic.
        """
        txt = self.span.text
        result = wikipedia.search(txt, resuts=max_results)
        if result is None:
            # Get suggestions from wikipedia
            query = wikipedia.suggest(txt)
            if query is not None:
                result = wikipedia.search(query, results=max_results)
                if result is not None:
                    return result
            if result is None:
                # Try google search - hopefully will fix up spelling or ignore irrelevent words
                scraper = google_search.GoogleScraper()
                urls = scraper.search(txt, 'wikipedia.com')
                topics = []
                seen = set()
                for u in urls:
                    m = _WTOPIC.match(u)
                    if m is not None:
                        t = m.group('topic')
                        if t not in seen:
                            seen.add(t)
                            topics.append(wikipedia.search(t.replace('_', ' ')))
                # FIXME: need a more thorough method for handling ambiguous results.
                return wikipedia.search(topics[0], results=max_results) if len(topics) != 0 else None
        return result

class UnboundSentence(object):
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


class IndexSpan(object):
    """View of a discourse."""
    def __init__(self, sentence, indexes=None):
        if not isinstance(sentence, UnboundSentence):
            raise TypeError('IndexSpan constructor requires sentence type = UnboundSentence')
        self._sent = sentence
        if indexes is None:
            self._indexes = []
        else:
            self._indexes = sorted(set([x for x in indexes]))

    def __repr__(self):
        d = self.get_drs()
        return d.show(drt.common.SHOW_LINEAR).encode('utf-8')

    def __eq__(self, other):
        return len(self) == len(other) and len(set(self._indexes).intersection(other._indexes)) == len(self)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        for i, j in zip(self._indexes, other._indexes):
            if i == j:
                continue
            return i < j
        return len(self) < len(other)

    def __gt__(self, other):
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
        return self._sent.at(i)

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
        u = set(self._indexes)
        self._indexes = sorted(u.union(other._indexes))
        return self

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
        u = set(self._indexes)
        self._indexes = sorted(u.difference(other._indexes))
        return self

    def intersection(self, other):
        """Find common span."""
        if other is None or len(other) == 0:
            self._indexes = []
            return self
        u = set(self._indexes)
        self._indexes = sorted(u.intersection(other._indexes))
        return self

    def subspan(self, required, excluded=0):
        """Refine the span with `required` and `excluded` criteria's.

        Args:
            required: A mask of RT_? bits.
            excluded: A mask of RT_? bits.

        Returns:
            A IndexSpan instance.
        """
        return IndexSpan(self._sent, filter(lambda i: 0 != (self[i].mask & required) and 0 == (self[i].mask & excluded), self._indexes))

    def get_drs(self):
        """Get a DRS view of the span.

        Returns:
            A DRS instance.
        """
        conds = []
        refs = []
        for tok in self:
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

    def get_subspan_from_wiki_search(self, search_result, max_results=1):
        """Get a subspan from a wikpedia search result."""
        spans = {}
        # FIXME: rank using statistical model based on context
        for result in search_result:
            title = result.title.split(' ')
            idxs = []
            words = {}
            for lex in self:
                for nm in title:
                    nml = nm.lower()
                    p1 = os.path.commonprefix(lex.word.lower(), nml)
                    p2 = os.path.commonprefix(lex.stem.lower(), nml)
                    if (len(p1) - len(p2)) >= 0:
                        if len(p1) >= (len(nml)/2):
                            idxs.append(lex.idx)
                    elif len(p2) > len(p1) and len(p2) >= (len(nml)/2):
                        idxs.append(lex.idx)
            idxs = sorted(idxs)
            if len(idxs) >= 2:
                idxs = sorted(idxs)
                idxs = range(idxs[0], idxs[-1]+1)
            spans.setdefault(len(idxs), [])
            spans[len(idxs)].append(IndexSpan(self._sent, idxs))

        # Order by size
        ranked_spans = []
        for v in sorted(spans.iterkeys()):
            ranked_spans.extend(v)
        if len(ranked_spans) == 0:
            return None
        return ranked_spans[0] if max_results == 1 else ranked_spans[0:max_results]



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