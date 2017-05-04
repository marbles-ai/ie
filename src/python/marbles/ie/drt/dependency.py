import weakref
from marbles.ie.drt.drs import DRSRef


class Dependency(object):
    def __init__(self, drsref, word, typeid, idx=0):
        """Constructor.

        Args:
            drsref: Key for dictionary.
            word: Noun or Proper Name.
            typeid: An integer type id.
            idx: position in sentence
        """
        if isinstance(drsref, str):
            drsref = DRSRef(drsref)
        self._ref = drsref
        self._word = word
        self._mask = typeid
        self._head = None
        self._children = set()

    def _repr_heads(self, s):
        if self._ref is None:
            s = '[()<=(%s)]' % s
        else:
            s = '[(%s,%s)<=(%s)]' % (self._ref.var.to_string(), self._word, s)
        if self.head is None:
            return s
        return self.head._repr_heads(s)

    def _repr_children(self):
        if self._children is not None:
            nds = ','.join([x._repr_children() for x in self._children])
        else:
            nds = ''
        if self._ref is None:
            return '[()<-(%s)]' % nds
        else:
            return '[(%s,%s)<-(%s)]' % (self._ref, self._word, nds)

    def __repr__(self):
        s = self._repr_children()
        if self.head is not None:
            return self.head._repr_heads(s)
        return s

    @property
    def head(self):
        return self._head() if self._head is not None else None

    @property
    def children(self):
        return sorted(self._children)

    @property
    def descendants(self):
        u = set()
        u = u.union(self._children)
        for c in self._children:
            u = u.union(c.descendants)
        return sorted(u)

    @property
    def root(self):
        r = self
        while r.head is not None:
            r = r.head
        return r

    def set_head(self, head):
        if head != self.head:
            self._head = weakref.ref(head)
        head._children.add(self)
        return head

    def _update_referent(self, oldref, newref):
        if oldref == self._ref:
            self._ref = newref
        for c in self._children:
            c._update_referent(oldref, newref)

    def update_referent(self, oldref, newref):
        """Update a referent in the dependency tree.

        Args:
            oldref: Old referent name.
            newref: New referent name.
        """
        if isinstance(oldref, str):
            drsref = DRSRef(oldref)
        if isinstance(newref, str):
            drsref = DRSRef(newref)

        if oldref != newref:
            self.root._update_referent(oldref, newref)

    def _update_mapping(self, drsref, word, typeid):
        if drsref == self._ref:
            if word is not None:
                self._word = word
            self._mask |= typeid
            return True
        else:
            for c in self._children:
                if c._update_mapping(drsref, word, typeid):
                    return True
        return False

    def update_mapping(self, drsref, word, typeid=0):
        """Update a referents mapping in the dependency tree.

        Args:
            drsref: Key for dictionary.
            word: Noun or Proper Name.
            typeid: An optional integer type id.
        """
        if isinstance(drsref, str):
            drsref = DRSRef(drsref)
        if drsref == self._ref:
            if word is not None:
                self._word = word
            self._mask |= typeid
        else:
            self.root._update_mapping(drsref, word, typeid)

    def _get_mapping(self, drsref):
        if drsref == self._ref:
            return (self._word, self._mask)
        else:
            for c in self._children:
                result = c._get_mapping(drsref)
                if result is not None:
                    return result
        return None

    def get_mapping(self, drsref):
        """Get the referent mapping."""
        if drsref == self._ref:
            return self._get_mapping(drsref)
        return self.root._get_mapping(drsref)

    def get(self):
        """Get the referent mapping."""
        return self._ref, self._word, self._mask

    def _remove_ref(self, drsref):
        if drsref == self._ref:
            hd = self.head
            if hd is None:
                self._ref = DRSRef('ROOT')
                self._word = ''
                self._mask = 0
            else:
                hd._children = hd._children.difference([self])
                for c in self._children:
                    c.set_head(hd)
                self._children = None
                self._head = None
            return True
        else:
            for c in self._children:
                if c._remove_ref(drsref):
                    return True
        return False

    def remove_ref(self, drsref):
        if drsref == self._ref:
            self._remove_ref(drsref)
        else:
            self.root._remove_ref(drsref)


