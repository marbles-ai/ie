from marbles.ie.utils.vmap import VectorMap

DELAY_SPACY_IMPORT = True

TYPEOF_SUBJECT = 0x00000001
TYPEOF_OBJECT =  0x00000002
TYPEOF_CONJ =    0x00000004
TYPEOF_AMOD =    0x00000008
TYPEOF_ISA_END = 0x00000010
TYPEOF_APPOS   = 0x00000020
TYPEOF_AUX     = 0x00000040


def build_typeof_map(module):
    '''Allows O(1) test of part-of-speech or dependency-relation in [...].'''
    map = VectorMap(max(module.dep.DEP_UPPER_BOUND, module.pos.POS_UPPER_BOUND) + 1)
    map.insert_new(module.dep.NSUBJ, TYPEOF_SUBJECT)
    map.insert_new(module.dep.NSUBJPASS, TYPEOF_SUBJECT)

    map.insert_new(module.dep.DOBJ, TYPEOF_OBJECT)
    map.insert_new(module.dep.IOBJ, TYPEOF_OBJECT)
    map.insert_new(module.dep.ACOMP, TYPEOF_OBJECT)

    map.insert_new(module.dep.CC, TYPEOF_CONJ)
    map.insert_new(module.dep.CONJ, TYPEOF_CONJ)

    map.insert_new(module.dep.ADVMOD, TYPEOF_AMOD)
    map.insert_new(module.dep.QUANTMOD, TYPEOF_AMOD)

    map.insert_new(module.pos.PUNCT, TYPEOF_ISA_END)
    map.insert_new(module.pos.VERB, TYPEOF_ISA_END)
    map.insert_new(module.pos.ADV, TYPEOF_ISA_END)

    map.insert_new(module.dep.APPOS, TYPEOF_APPOS)

    map.insert_new(module.dep.AUX, TYPEOF_AUX)
    map.insert_new(module.dep.AUXPASS, TYPEOF_AUX)
    map.insert_new(module.dep.NEG, TYPEOF_AUX)

    map.set_default_lookup(0)
    return map


class IndexSpan(object):
    '''View of a document. The class has a similar interface to spacy.Span
    '''
    def __init__(self, doc, indexes=None):
        self._doc = doc
        if indexes is None:
            self._indexes = []
        else:
            self._indexes = indexes

    def __len__(self):
        return len(self._indexes)

    def __getitem__(self, i):
        return self._doc[i]

    def __iter__(self):
        for k in self._indexes:
            yield self._doc[k]

    def __repr__(self):
        return self.text

    def __eq__(self, other):
        return (len(other._indexes) == 0 and len(self._indexes) == 0) or \
               (len(self._indexes) != 0 and len(other._indexes) != 0 and \
                other._doc._hash == self._doc._hash and other._indexes[0] == self._indexes[0])

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        return self._doc._hash < other._doc._hash or (self._doc._hash == other._doc._hash and \
                ((len(self._indexes) == 0 and len(other._indexes) != 0) or \
                 (len(self._indexes) != 0 and len(other._indexes) != 0 and self._indexes[0] < other._indexes[0])))

    def __gt__(self, other):
        return self._doc._hash > other._doc._hash or (self._doc._hash == other._doc._hash and \
                ((len(self._indexes) != 0 and len(other._indexes) == 0) or \
                 (len(self._indexes) != 0 and len(other._indexes) != 0 and self._indexes[0] > other._indexes[0])))

    def __le__(self, other):
        return other.__gt__(self)

    def __ge__(self, other):
        return other.__lt__(self)

    def __hash__(self):
        return (self._idx << 5) ^ (self.idx >> 27) ^ self._doc._hash

    def union(self, other):
        '''Union two spans.'''
        if other is None or len(other) == 0: return
        self._indexes.extend(filter(lambda x: x not in self._indexes, other._indexes))
        self._indexes.sort()

    def complement(self, other):
        '''Remove other from this span.'''
        if other is None or len(other) == 0: return
        self._indexes = filter(lambda x: x not in other._indexes, self._indexes)

    def intersect(self, other):
        '''Find common span.'''
        if other is None or len(other) == 0:
            self._indexes = []
            return
        self._indexes = filter(lambda x: x in other._indexes, self._indexes)

    @property
    def text(self):
        if len(self._indexes) == 0:
            return ''
        txt = self._doc[self._indexes[0]].text
        for i in self._indexes[1:]:
            tok = self._doc[i]
            if tok.is_punct:
                txt += tok.text
            else:
                txt += ' ' + tok.text
        return txt

    @property
    def text_with_ws(self):
        return self.text


class SubtreeSpan(IndexSpan):
    '''View of a document. Specialization of IndexSpan.'''

    def __init__(self, doc, idx=None, removePunct=False, shallow=False, nofollow=None):
        '''Constructor.

        Args:
            idx: A token index or a Token instance.
            removePunct: If True punctuation is excluded from the span.
            shallow: If shallow is a boolean and True then don't add dependent
                tokens to span. If shallow isa list of token indexes these are
                used as the adjacency for the token a idx.
        '''
        if idx is not None and isinstance(idx, (int,long)):
            indexes = [idx]
        else:
            idx = doc.i
            doc = doc.doc
            indexes = [idx]

        stk = None
        if isinstance(shallow, list):
            if len(shallow) > 0:
                stk = shallow
            shallow = False

        if not shallow:
            if nofollow is not None and len(nofollow) != 0:
                if not isinstance(nofollow[0], int):
                    nofollow = [x.i for x in nofollow]
            else:
                nofollow = []
            tok = doc[idx]
            if stk is None:
                stk = filter(lambda x: x not in nofollow, [x.i for x in tok.children])
            indexes.extend(stk)
            while len(stk) != 0:
                tok = doc[stk.pop()]
                adj = filter(lambda x: x not in nofollow, [x.i for x in tok.children])
                stk.extend(adj)
                indexes.extend(adj)
            if removePunct:
                indexes = filter(lambda x: not doc[x].is_punct, indexes)
            indexes.sort()
        super(SubtreeSpan, self).__init__(doc, indexes)
        self._rootIdx = idx

    def __repr__(self):
        if len(self._indexes) == 0:
            return '(%i,\"\")' % self._rootIdx
        txt = '(%i,\"%s' % (self._rootIdx, self._doc[self._indexes[0]].text)
        for i in self._indexes[1:]:
            tok = self._doc[i]
            if tok.is_punct:
                txt += tok.text
            else:
                txt += ' ' + tok.text
        return txt + '\")'

    def repair(self):
        '''If the span no longer includes the root index due to complement or intersect
        operations then this ensures the root idx is included. Also sorts indexes.
        '''
        if self._rootIdx not in self._indexes:
            self._indexes.append(self._rootIdx)
        self._indexes.sort()

    @property
    def root(self):
        '''Return the root of the subtree span.

        Returns: A Token instance.
        '''
        return self._doc[self._rootIdx]

    @property
    def i(self):
        '''Return the root index of the subtree span.

        Returns: A index onto the Token array.
        '''
        return self._rootIdx


class SyntheticSpan(object):
    '''View of a document. The class has a similar interface to spacy.Span
    '''

    def __init__(self, text):
        self._text = text

    def __len__(self):
        return 0

    def __getitem__(self, i):
        raise NotImplemented

    def __iter__(self):
        pass

    def union(self, other):
        raise NotImplemented

    def complement(self, other):
        raise NotImplemented

    def intersect(self, other):
        raise NotImplemented

    @property
    def text(self):
        return '\"%s\"' % self._text

    @property
    def text_with_ws(self):
        return self.text


