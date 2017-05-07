from marbles.ie.utils.cache import Cache, Freezable


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
        return self._tag

    def __repr__(self):
        return self._tag

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


# Initialize POS cache
_tags = [
    'CC', 'CD', 'DT', 'EX', 'FW', 'IN', 'JJ', 'JJR', 'JJS', 'LS', 'MD', 'NN', 'NNS', 'NNP', 'NNPS',
    'PDT', 'POS', 'PRP', 'PRP$', 'RB', 'RBR', 'RBS', 'RP', 'SYM', 'TO', 'UH', 'VB', 'VBD', 'VBG', 'VBN',
    'VBP', 'VBZ', 'WDT', 'WP', 'WP$', 'WRB', 'UNKNOWN', ',', '.', ':', ';', '?'
]
for _t in _tags:
    POS._cache.addinit((_t, POS(_t)))
for _t in _tags:
    POS.from_cache(_t).freeze()


# Useful tags
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


