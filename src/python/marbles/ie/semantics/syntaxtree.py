# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import weakref
from marbles import safe_utf8_encode, isdebugging
from marbles.ie.core.sentence import Span, AbstractConstituentNode, Constituent, ConstituentNode
from marbles.ie.core import constituent_types as ct


class AbstractSTreeNode(AbstractConstituentNode):
    """Syntax tree node. Can be a leaf, unary, or binary node."""
    def __init__(self, idx, depth):
        super(AbstractSTreeNode, self).__init__(ct.CONSTITUENT_NODE)
        self.idx = idx
        self.parent = idx
        self.depth = depth
        self.conjoin = False    # Set during construction

    @property
    def category(self):
        """Get the category assigned to the node."""
        raise NotImplementedError

    @property
    def isleaf(self):
        """Return true if a leaf node.

        Remarks:
            Required by AbstractConstituentNode.
        """
        return False

    @property
    def isbinary(self):
        """Return true if a binary node."""
        return False

    @property
    def isunary(self):
        """Return true if a unary node."""
        return not self.isbinary and not self.isleaf

    @property
    def adjunct(self):
        """Return true if an adjunct node."""
        return self.ndtype in [ct.CONSTITUENT_ADJP, ct.CONSTITUENT_ADVP]

    @property
    def parent_idx(self):
        """Return the index of the parent node.

        Remarks:
            Required by AbstractConstituentNode.
        """
        return self.parent

    def contains_adjunct(self):
        """Return true if the node or an children are tags as adjuncts"""
        return self.adjunct

    def clear_adjunct(self):
        """Clear the adjunct type for this node and all children"""
        raise NotImplementedError

    def contains_span(self, sp):
        """Test if the node contains span `sp`."""
        spnd = self.span(sp.sentence)
        return sp in spnd

    def union_span(self, sp):
        """Union the node span with `sp`."""
        return sp.union(self.span(sp.sentence))

    def span(self, sentence):
        """Build a span from this node and `sentence`."""
        rng = self.lex_range
        return Span(sentence, rng[0], rng[1])

    def constituent(self, sentence, ndtype=None):
        """Build a constituent from this node and `sentence`."""
        if isdebugging():
            sp = self.span(sentence)
            hds = sp.get_head_span()
            assert len(hds) == 1
            assert hds[0].idx == self.head_idx
        return Constituent(sentence, self)

    def set_head(self, new_idx):
        pass


class STreeNode(AbstractSTreeNode):
    """A syntax tree node. This includes unary and binary nodes."""
    def __init__(self, idx, child_nodes, head, result_category, rule, lex_range, depth):
        super(STreeNode, self).__init__(idx, depth)
        self.rule = rule
        self._result_category = result_category
        self._child_nodes = child_nodes
        self._head = head
        self._lex_range = lex_range

    def __repr__(self):
        return b'<STreeNode>:(%d, %s %s)' % (len(self._child_nodes), self.rule, self.category)

    @property
    def category(self):
        """Get the category assigned to the node."""
        return self._result_category

    @property
    def lex_range(self):
        """Return the lexical range (span).

        Remarks:
            Required by AbstractConstituentNode.
        """
        return self._lex_range

    @property
    def children(self):
        """Get a list of the child nodes."""
        return self._child_nodes

    @property
    def isbinary(self):
        return len(self._child_nodes) == 2

    @property
    def head_idx(self):
        """Return the lexical head of the phrase.

        Remarks:
            Required by AbstractConstituentNode.
        """
        return self._head

    def clear_adjunct(self):
        """Clear the adjuct tag for this node and all children"""
        if self.adjunct:
            self.ndtype = ct.CONSTITUENT_NODE
        for c in self._child_nodes:
            c.clear_adjunct()

    def contains_adjunct(self):
        """Return true if the node or an children are tags as adjuncts"""
        return self.adjunct or any([c.contains_adjunct() for c in self._child_nodes])

    def remove_child(self, i):
        del self._child_nodes[i]

    def trim_span(self, limit):
        size = self._lex_range[1] - self._lex_range[0]
        if size > 0:
            if limit >= 0:
                self._lex_range[0] = min(limit, size-1)
            else:
                self._lex_range[1] -= min(-limit, size)

    def recalc_span(self):
        leaves = sorted(filter(lambda x: x.isleaf, self.iternodes()), key=lambda x: x.lexeme.idx)
        nds = dict(map(lambda x: (x.idx, x), self.iternodes()))
        # reset all
        for nd in self.iternodes():
            if not nd.isleaf:
                nd._lex_range = []

        # Set this one
        self._lex_range = [leaves[0].lexeme.idx, leaves[-1].lexeme.idx]
        # Set the rest
        for nd in leaves:
            idx = nd.lexeme.idx
            nd = nds[nd.parent]
            while nd is not self:
                nd._lex_range.append(idx)
                nd = nds[nd.parent]
        # Trim
        for nd in self.iternodes():
            if not nd.isleaf:
                assert len(nd._lex_range) != 0
                nd._lex_range = [nd._lex_range[0], nd._lex_range[-1]+1]

        if (self._lex_range[1] - self._lex_range[0]) != len(leaves):
            raise ValueError('lex range %s does not match leaf count [%d]' % (repr(self._lex_range), len(leaves)))

    def set_head(self, new_idx):
        self._head = new_idx


class STreeLeafNode(AbstractSTreeNode):

    def __init__(self, lexeme, idx, depth, predarg=None):
        super(STreeLeafNode, self).__init__(idx, depth)
        self._lexeme = weakref.ref(lexeme)
        self.predarg = predarg # Use when building functor templates

    def __repr__(self):
        return b'<STreeLeafNode>:(%s, %s, %s)' % (safe_utf8_encode(self.lexeme.stem), self.lexeme.category, self.lexeme.pos)

    @property
    def lexeme(self):
        return self._lexeme()

    @property
    def category(self):
        """Get the category assigned to the node."""
        return self.lexeme.category

    @property
    def lex_range(self):
        """Return the lexical range (span).

        Remarks:
            Required by AbstractConstituentNode.
        """
        return [self.lexeme.idx, self.lexeme.idx+1]

    @property
    def isleaf(self):
        return True

    @property
    def head_idx(self):
        """Return the head of the phrase"""
        return self.lexeme.idx

    def clear_adjunct_tag(self):
        """Clear the adjunct for this node"""
        if self.adjunct:
            self.ndtype = ct.CONSTITUENT_NODE
