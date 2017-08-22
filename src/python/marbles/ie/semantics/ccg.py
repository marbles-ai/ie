# -*- coding: utf-8 -*-
"""CCG to DRS Production Generator"""

from __future__ import unicode_literals, print_function

import collections
import itertools
import numpy as np

from marbles import isdebugging
from marbles.ie.ccg import *
from marbles.ie.ccg.model import MODEL, UCONJ, UnaryRule
from marbles.ie.ccg.utils import pt_to_utf8
from marbles.ie.core import constituent_types as ct
from marbles.ie.core.constants import *
from marbles.ie.core.exception import UnaryRuleError, CombinatorNotFoundError, _UNDEFINED_UNARY
from marbles.ie.core.sentence import AbstractSentence, Sentence, Span
from marbles.ie.drt.common import DRSVar
from marbles.ie.drt.drs import DRS, DRSRef, Rel, DRSRelation
from marbles.ie.drt.utils import remove_dups
from marbles.ie.semantics.compose import ProductionList, FunctorProduction, DrsProduction, identity_functor
from marbles.ie.semantics.lexeme import Lexeme, EventPredicates
from marbles.ie.semantics.syntaxtree import STreeNode, STreeLeafNode
from marbles.ie.utils.vmap import VectorMap, dispatchmethod, default_dispatchmethod
from marbles.log import ExceptionRateLimitedLogAdaptor

_actual_logger = logging.getLogger(__name__)
_logger = ExceptionRateLimitedLogAdaptor(_actual_logger)


# The sentential features are as follows:
#   S[dcl: for declarative sentences
#   S[wq]: for wh-questions
#   S[q]: for yes-no questions (Does he leave?)
#   S[qem]: for embedded questions (worry [whether he left])
#   S[em]: for embedded declaratives (he says [that he left])
#   S[bem]: for embedded sentences in subjunctive mood (I demand [that he leave])
#   S[b]: for sentences in subjunctive mood (I demand (that) [he leave])
#   S[frg]: for sentence fragments (derived from the Treebank label     )
#   S[for]:for small clauses headed by for ([for X to do sth])
#   S[intj]: for interjections
#   S[inv]: for elliptical inversion ((as) [does President Bush])

# These are the verb phrase features:
#   S[b]\NP: for bare infinitives, subjunctives and imperatives
#   S[to]\NP: for to-infinitives
#   S[pss]: for past participles in passive mode
#   S[pt]: for past participles used in active mode
#   S[ng]: for present participles


# Copular verbs
_COPULAR = [
    'act', 'appear', 'be', 'become', 'bleed', 'come', 'come out', 'constitute', 'end up', 'die', 'get', 'go', 'grow',
    'fall', 'feel', 'freeze', 'keep', 'look', 'prove', 'remain', 'run', 'seem', 'shine', 'smell', 'sound', 'stay',
    'taste', 'turn', 'turn up', 'wax'
]

# To indicate time order
_TIME_ORDER = [
    'in the past', 'before', 'earlier', 'previously', 'formerly', 'yesterday', 'recently', 'not long ago',
    'at present', 'presently', 'currently', 'now', 'by now', 'until', 'today', 'immediately', 'simultaneously',
    'at the same time', 'during', 'all the while', 'in the future', 'tomorrow', 'henceforth', 'after',
    'after a short time', 'after a while', 'soon', 'later', 'later on', 'following'
]

# To indicate how or when something occurs in time
_TIME_OCCURRENCE = [
    'suddenly', 'all at once', 'instantly', 'immediately', 'quickly', 'directly', 'soon', 'as soon as', 'just then',
    'when', 'sometimes', 'some of the time', 'in the meantime', 'occasionally', 'rarely', 'seldom', 'infrequently',
    'temporarily', 'periodically', 'gradually', 'eventually', 'little by little', 'slowly', 'while', 'meanwhile',
    'always', 'all of the time', 'without exception', 'at the same time', 'repeatedly', 'often', 'frequently',
    'generally', 'usually', 'as long as', 'never', 'not at all'
]

# To indicate sequence
_SEQUENCE = [
    'first', 'in the first place', 'at first', 'once', 'once upon time', 'to begin with', 'at the beginning',
    'starting with', 'initially', 'from this point', 'earlier', 'second', 'secondly', 'in the second place', 'next',
    'the next time', 'the following week', 'then', 'after that', 'following that', 'subsequently',
    'on the next occasion', 'so far', 'later on', 'third', 'in the third place', 'last', 'last of all', 'at last',
    'at the end', 'in the end', 'final finally', 'to finish', 'to conclude', 'in conclusion', 'consequently'
]

# To repeat
_REPEAT = [
    'all in all', 'altogether', 'in brief', 'in short', 'in fact', 'in particular', 'that is', 'in simpler terms',
    'to put it differently', 'in other words', 'again', 'once more', 'again and again', 'over and over', 'to repeat',
    'as stated', 'that is to say', 'to retell', 'to review', 'to rephrase', 'to paraphrase', 'to reconsider',
    'to clarify', 'to explain', 'to outline', 'to summarize'
]

# To provide an example
_EXAMPLE = [
    'for example', 'as an example', 'for instance', 'in this case', 'to illustrate', 'to show', 'to demonstrate',
    'to explain', 'suppose that', 'specifically', 'to be exact', 'in particular', 'such as', 'namely', 'for one thing',
    'indeed', 'in other words', 'to put it in another way', 'thus'
]

# To concede
_CONCEDE = [
    'of course', 'after all', 'no doubt', 'naturally', 'unfortunately', 'while it is true', 'although this may be true',
    'although', 'to admit', 'to confess', 'to agree'
]

# To conclude or to summarize
_SUMMARIZE = [
    'to conclude', 'in conclusion', 'to close', 'last of all', 'finally', 'to end', 'to complete', 'to bring to an end',
    'thus', 'hence', 'therefore', 'as a consequence of', 'as a result', 'in short', 'to sum up', 'to summarize',
    'to recapitulate'
]

# To add a point
_POINT = [
    'also', 'too', 'as well as', 'besides', 'equally important', 'first of all', 'furthermore', 'in addition (to)',
    'moreover', 'likewise', 'above all', 'most of all', 'least of all', 'and', 'either…or', 'neither…nor', 'however',
    'yet', 'but', 'nevertheless', 'still', 'to continue'
]

# To compare
_COMPARE = [
    'As', 'as well as', 'like', 'in much the same way', 'resembling', 'parallel to', 'same as', 'identically',
    'of little difference', 'equally', 'matching', 'also', 'exactly', 'similarly', 'similar to',
    'in comparison', 'in relation to'
]

# To contrast
_CONTRAST = [
    'though', 'although', 'and yet', 'but', 'despite', 'despite this fact', 'in spite of', 'even so', 'for all that',
    'however', 'in contrast', 'by contrast', 'on one hand', 'on the other hand', 'on the contrary', 'in one way',
    'in another way', 'although this may be true', 'nevertheless', 'nonetheless', 'still', 'yet', 'to differ from',
    'a striking difference', 'another distinction', 'otherwise', 'after all', 'instead', 'unlike', 'opposite',
    'to oppose', 'in opposition to', 'versus', 'against'
]

# To emphasise or to intensify
_EMPHASIZE = [
    'above all', 'after all', 'indeed', 'as a matter of fact', 'chiefly', 'especially', 'actually',
    'more important', 'more importantly', 'most important of all', 'most of all', 'moreover', 'furthermore',
    'significantly', 'the most significant', 'more and more', 'of major interest', 'the chief characteristic',
    'the major point', 'the main problem (issue)', 'the most necessary', 'extremely', 'to emphasize', 'to highlight',
    'to stress', 'by all means', 'undoubtedly', 'without a doubt', 'certainly', 'to be sure', 'surely', 'absolutely',
    'obviously', 'to culminate', 'in truth', 'the climax of', 'to add to that', 'without question', 'unquestionably',
    'as a result'
]

# To generalize
_GENERALIZE = [
    'On the whole', 'in general', 'as a rule', 'in most cases', 'broadly speaking', 'to some extent', 'mostly'
]

# Showing our attitude to what we are saying
_ATTITUDE = [
    'Frankly', 'honestly', 'I think', 'I suppose', 'after all', 'no doubt', 'I’m afraid', 'actually',
    'as a matter of fact', 'to tell the truth', 'unfortunately'
]

## @ingroup gfn
def safe_create_empty_functor(category):
    """Lookup model templates and create an empty functor. If the template
    does not exits attempt to infer from existing templates.

    Args:
        category: The functor category.

    Returns:
        A functor or None.
    """
    templ = MODEL.lookup(category, infer=False)
    if templ is None:
        if category.isfunctor:
            if category != CAT_CONJ_CONJ and category != CAT_CONJCONJ \
                    and (category.result_category().isfunctor or category.argument_category().isfunctor):
                templ = MODEL.infer_template(category)
                if templ is not None:
                    return templ.create_empty_functor()
            elif category.result_category().can_unify(category.argument_category()):
                return identity_functor(category)
            else:
                return identity_functor(category, [DRSRef('X2'), DRSRef('X1')])
    else:
        return templ.create_empty_functor()
    return None


def ndtype_from_category(category):
    if category == CAT_NP:
        return ct.CONSTITUENT_NP
    elif category == CAT_PP:
        return ct.CONSTITUENT_PP
    elif category in [CAT_VPdcl, CAT_VP]:
        return ct.CONSTITUENT_VP
    elif category in [CAT_VPb, CAT_VPto]:
        return ct.CONSTITUENT_SINF
    elif category == CAT_AP:
        return ct.CONSTITUENT_ADJP
    elif category.isatom and category == CAT_Sany:
        if category.has_any_features(FEATURE_DCL):
            return ct.CONSTITUENT_SDCL
        elif category.has_any_features(FEATURE_EM | FEATURE_BEM):
            return ct.CONSTITUENT_SEM
        elif category.has_any_features(FEATURE_QEM | FEATURE_Q):
            return ct.CONSTITUENT_SQ
        elif category.has_any_features(FEATURE_WQ):
            return ct.CONSTITUENT_SWQ
        else:
            return ct.CONSTITUENT_S
    return None


CcgArgSep = re.compile(r'/|\\')
TType = re.compile(r'((?:[()/\\]|(?:(?:S|NP|N)(?:\[[Xa-z]+\])?)|conj|[A-Z]+\$?|-[A-Z]+-)*)')
LPosType = re.compile(r'([A-Z$:-]+|[.,:;])(?=\s+[^>\s]+\s+[^>\s]+(?:\s|[>]))')
LWord = re.compile(r'[^>\s]+(?=\s)')
CcgComplexTypeBegin = re.compile(r'([()/\\]|(?:(?:S|NP|N)(?:\[[Xa-z]+\])?)|conj|[A-Z]+|[.,:;])+(?=\s)')
CcgComplexTypeEnd = re.compile(r'([()/\\]|(?:(?:S|NP|N)(?:\[[Xa-z]+\])?)|conj|[A-Z]+|[.,:;]|_\d+)+(?=[>])')
PosInt = re.compile(r'\d+')
POS_NOUN_CHECK1 = [POS_POSSESSIVE, POS_PROPER_NOUN, POS_PROPER_NOUN_S]
POS_NOUN_CHECK2 = [POS_NOUN, POS_NOUN_S]
NPP_Appos_S = re.compile(r"-'[sS]")


class Ccg2Drs(AbstractSentence):
    """CCG to DRS Converter"""
    dispatchmap = VectorMap(Rule.rule_count())
    debugcount = 0

    def __init__(self, options=0, msgid=None):
        """Constructor

        Args:
            options: compose options
            msgid: optional message id string tobe used when logging
        """
        super(Ccg2Drs, self).__init__(msgid=msgid)
        self.xid = 10
        self.eid = 10
        self.limit = 10
        self.options = options or 0
        self.stree_nodes = []
        self.lexemes = []
        self.depth = -1
        self.final_prod = None
        self.drs_extra = []
        self.conjoins = []
        self.unary_seen = set()

    def __len__(self):
        # Required by AbstractSentence
        return len(self.lexemes)

    def __getitem__(self, slice_i_j):
        # Required by AbstractSentence
        if isinstance(slice_i_j, slice):
            indexes = [i for i in range(len(self))]
            return Span(self, indexes[slice_i_j])
        return self.lexemes[slice_i_j]

    def __iter__(self):
        # Required by AbstractSentence
        for i in range(len(self)):
            yield self.lexemes[i]

    def constituent_at(self, idx):
        """Required by AbstractSentence."""
        return self.stree_nodes[idx]

    def iterconstituents(self):
        for nd in self.stree_nodes:
            if nd.ndtype != ct.CONSTITUENT_NODE:
                yield nd.constituent(self)

    @dispatchmethod(dispatchmap, RL_TCL_UNARY)
    def _dispatch_lunary(self, nd, stk):
        if len(nd.children) == 2:
            assert len(stk) >= 2
            unary = MODEL.lookup_unary(nd.category, nd.children[0].category)
            if unary is None:
                _UNDEFINED_UNARY.add((nd.category, nd.children[0].category))
            if unary is None:
                # DEBUG HELPER
                if isdebugging():
                    unary = MODEL.lookup_unary(nd.category, nd.children[0].category)
                raise UnaryRuleError('Missing unary rule for %s' % UnaryRule.create_key(nd.category, nd.children[0].category))

            self.unary_seen.add(unary.getkey())
            fn = self.rename_vars(unary.get())
            ucat = fn.category
            fn.set_options(self.options)
            d2 = stk.pop()
            stk.append(fn)
            self._dispatch_ba(nd, stk)

            nlst = ProductionList()
            nlst.set_options(self.options)
            nlst.set_category(nd.category)
            nlst.push_right(stk.pop())
            nlst.push_right(d2)
            stk.append(nlst.flatten().unify())
        else:
            unary = MODEL.lookup_unary(nd.category, nd.children[0].category)
            if unary is None:
                _UNDEFINED_UNARY.add((nd.category, nd.children[0].category))
            if unary is None:
                # DEBUG HELPER
                if isdebugging():
                    unary = MODEL.lookup_unary(nd.category, nd.children[0].category)
                raise UnaryRuleError('Missing unary rule for %s' % UnaryRule.create_key(nd.category, nd.children[0].category))

            self.unary_seen.add(unary.getkey())
            fn = self.rename_vars(unary.get())
            ucat = fn.category
            fn.set_options(self.options)
            stk.append(fn)
            self._dispatch_ba(nd, stk)
        self._mark_if_adjunct(nd, ucat, stk[-1])

    def _can_use_conjoin_rules(self, nd):
        # Conjoins are built right to left. The right child should be a binary
        # node with a left conjoin child, or a partially built conjoin
        if not nd.isbinary or not nd.children[1].isbinary \
                or not isinstance(nd.children[1].children[0], STreeLeafNode) \
                or not (nd.children[1].children[0].category == CAT_CONJ \
                            or (nd.children[1].children[0].category.ispunct and nd.children[1].children[1].conjoin)):
            return False

        # Check nodes
        nds = [nd.children[0], nd.children[1].children[1]]
        return nds[0].category.can_unify(nds[1].category)

    @dispatchmethod(dispatchmap, RL_TCR_UNARY)
    def _dispatch_runary(self, nd, stk):
        assert len(nd.children) == 2
        assert len(stk) >= 2
        unary = None
        if nd.children[0].category == CAT_CONJ and isinstance(nd.children[0], STreeLeafNode) and \
                nd.children[1].category is not CAT_CONJ_CONJ and self._can_use_conjoin_rules(nd):
            # Conj has different unification rules
            unary = UCONJ.lookup_unary(nd.category, nd.children[1].category, infer=False)
            nd.conjoin = True
        elif nd.children[0].category == CAT_COMMA and isinstance(nd.children[0], STreeLeafNode):
            # TODO: Check if this is a conj rule
            nd.conjoin = self._can_use_conjoin_rules(nd)

        if unary is None:
            unary = MODEL.lookup_unary(nd.category, nd.children[1].category)
        if unary is None:
            _UNDEFINED_UNARY.add((nd.category, nd.children[1].category))
            if unary is None:
                # DEBUG HELPER
                if isdebugging():
                    unary = MODEL.lookup_unary(nd.category, nd.children[1].category)
                raise UnaryRuleError('Missing unary rule for %s' % UnaryRule.create_key(nd.category, nd.children[1].category))

        self.unary_seen.add(unary.getkey())
        fn = self.rename_vars(unary.get())
        ucat = fn.category
        fn.set_options(self.options)
        stk.append(fn)
        self._dispatch_ba(nd, stk)

        nlst = ProductionList()
        nlst.set_options(self.options)

        d1 = stk.pop()
        d2 = stk.pop()
        markadjunct = True
        if d2.category == CAT_CONJ:
            if ucat.test_returns_entity_modifier():
                nlst.set_category(nd.category.add_conj_feature())
            else:
                nlst.set_category(nd.category)

            if d1.category.test_returns_entity_modifier():
                # FIXME: this is a hack to get proper nouns separated by 'and' merged
                d2.rename_vars(zip(d2.lambda_refs, reversed(d1.lambda_refs)))
            elif nd.category.ismodifier and nd.category.simplify().test_return(CAT_S_NP) and \
                    (nd.category.test_return(d1.category) or nd.category.test_return(d2.category)):
                markadjunct = False
        elif d2.category == CAT_COMMA and ucat.test_returns_entity_modifier():
            nlst.set_category(nd.category.add_conj_feature())
        else:
            nlst.set_category(nd.category)

        nlst.push_right(d1)
        nlst.push_right(d2)
        stk.append(nlst.flatten().unify())
        if markadjunct:
            self._mark_if_adjunct(nd, ucat, stk[-1])

    @dispatchmethod(dispatchmap, RL_TC_CONJ)
    def _dispatch_tcconj(self, nd, stk):
        # Special type change rules. See section 3.7-3.8 of LDC 2005T13 manual.
        if len(nd.children) == 2:
            self._dispatch_runary(nd, stk)
            return
            fn = self.rename_vars(safe_create_empty_functor(nd.category))
            self.unary_seen.add(fn.category)
            if nd.children[0].category == CAT_CONJ:
                vp_or_np = stk.pop()
                d = stk.pop()
            else:
                d = stk.pop()
                vp_or_np = stk.pop()

            nlst = ProductionList()
            nlst.push_right(fn.type_change_np_snp(vp_or_np))
            nlst.push_right(d)
            nlst.set_options(self.options)
            nlst.set_category(nd.category)
            stk.append(nlst.flatten().unify())
        else:
            fn = self.rename_vars(safe_create_empty_functor(nd.category))
            self.unary_seen.add(fn.category)
            vp_or_np = stk.pop()
            stk.append(fn.type_change_np_snp(vp_or_np))

    @dispatchmethod(dispatchmap, RL_TC_ATOM)
    def _dispatch_tcatom(self, nd, stk):
        # Special rule to change atomic type
        fn = self.rename_vars(identity_functor(Category.combine(nd.category, '\\', stk[-1].category)))
        self.unary_seen.add(fn.category)
        fn.set_options(self.options)
        stk.append(fn)
        self._dispatch_ba(nd, stk)  # backward application
        if len(nd.children) == 2:
            if nd.children[0].category == CAT_CONJ and isinstance(nd.children[0], STreeLeafNode):
                nd.conjoin = True
            d2 = stk.pop()
            d1 = stk.pop()
            stk.append(d2)

    @dispatchmethod(dispatchmap, RL_TYPE_RAISE)
    def _dispatch_type_raise(self, nd, stk):
        ## Forward   X:g => T/(T\X): λxf.f(g)
        ## Backward  X:g => T\(T/X): λxf.f(g)
        assert len(nd.children) == 1
        f = self.rename_vars(safe_create_empty_functor(nd.category))
        g = stk.pop()
        stk.append(f.type_raise(g))

    def _update_conjoins(self, nd):
        # Assumes conjoins are built right to left
        if nd.isbinary and nd.children[1].conjoin:
            nd.conjoin = True
            if len(self.conjoins) != 0:
                ndsp = nd.span(self)
                lastsp = self.conjoins[-1].span(self)
                if lastsp in ndsp:
                    self.conjoins.pop()

            self.conjoins.append(nd)

    @dispatchmethod(dispatchmap, RL_FA)
    def _dispatch_fa(self, nd, stk):
        # Forward application.
        d = stk.pop()   # arg1
        fn = stk.pop()  # arg0
        prevcat = fn.category
        # Track spans of like items
        stk.append(self._update_constituents(nd, fn.apply(d), prevcat))
        self._update_conjoins(nd)

    @dispatchmethod(dispatchmap, RL_BA)
    def _dispatch_ba(self, nd, stk):
        # Backward application.
        fn = stk.pop()   # arg1
        d = stk.pop()    # arg0
        prevcat = fn.category
        stk.append(self._update_constituents(nd, fn.apply(d), prevcat))
        self._update_conjoins(nd)

    @dispatchmethod(dispatchmap, RL_FC, RL_FX)
    def _dispatch_fc(self, nd, stk):
        # CALL[X/Y](Y|Z)
        # Forward Composition           X/Y:f Y/Z:g => X/Z: λx􏰓.f(g(x))
        # Forward Crossing Composition  X/Y:f Y\Z:g => X\Z: λx􏰓.f(g(x))
        g = stk.pop()   # arg1
        f = stk.pop()   # arg0
        stk.append(f.compose(g))

    @dispatchmethod(dispatchmap, RL_GFC, RL_GFX)
    def _dispatch_gfc(self, nd, stk):
        # CALL[X/Y](Y|Z)$
        # Generalized Forward Composition           X/Y:f (Y/Z)/$ => (X/Z)/$
        # Generalized Forward Crossing Composition  X/Y:f (Y\Z)$: => (X\Z)$
        g = stk.pop()   # arg1
        f = stk.pop()   # arg0
        stk.append(f.generalized_compose(g))

    @dispatchmethod(dispatchmap, RL_BC, RL_BX)
    def _dispatch_bc(self, nd, stk):
        # CALL[X\Y](Y|Z)
        # Backward Composition          Y\Z:g X\Y:f => X\Z: λx􏰓.f(g(x))
        # Backward Crossing Composition Y/Z:g X\Y:f => X/Z: λx􏰓.f(g(x))
        f = stk.pop()
        g = stk.pop()
        stk.append(f.compose(g))

    @dispatchmethod(dispatchmap, RL_GBC, RL_GBX)
    def _dispatch_gbc(self, nd, stk):
        # CALL[X\Y](Y|Z)$
        # Generalized Backward Composition          (Y\Z)$  X\Y:f => (X\Z)$
        # Generalized Backward Crossing Composition (Y/Z)/$ X\Y:f => (X/Z)/$
        f = stk.pop()
        g = stk.pop()
        stk.append(f.generalized_compose(g))

    @dispatchmethod(dispatchmap, RL_FS, RL_FXS)
    def _dispatch_fs(self, nd, stk):
        # CALL[(X/Y)|Z](Y|Z)
        # Forward Substitution          (X/Y)/Z:f Y/Z:g => X/Z: λx􏰓.fx􏰨(g􏰨(x􏰩􏰩))
        # Forward Crossing Substitution (X/Y)\Z:f Y\Z:g => X\Z: λx􏰓.fx􏰨(g􏰨(x􏰩􏰩))
        g = stk.pop()   # arg1
        f = stk.pop()   # arg0
        stk.append(f.substitute(g))

    @dispatchmethod(dispatchmap, RL_BS, RL_BXS)
    def _dispatch_bs(self, nd, stk):
        # CALL[(X\Y)|Z](Y|Z)
        # Backward Substitution             Y\Z:g (X\Y)\Z:f => X/Z: λx􏰓.fx􏰨(g􏰨(x􏰩􏰩))
        # Backward Crossing Substitution    Y/Z:g (X\Y)/Z:f => X/Z: λx􏰓.fx􏰨(g􏰨(x􏰩􏰩))
        f = stk.pop()   # arg1
        g = stk.pop()   # arg0
        stk.append(f.substitute(g))

    @dispatchmethod(dispatchmap, RL_LCONJ, RL_RCONJ)
    def _dispatch_conj(self, nd, stk):
        # Conjoin of like types.
        g = stk.pop()
        f = stk.pop()
        if f.isfunctor:
            d = f.conjoin(g, False)
        elif g.isfunctor:
            d = g.conjoin(f, True)
        else:
            d = ProductionList(f)
            d.push_right(g)
            d = d.unify()
            d.set_category(f.category)
        stk.append(self._update_constituents(nd, d, d.category))
        self._update_conjoins(nd)

    @dispatchmethod(dispatchmap, RL_LP, RL_RP, RL_RNUM)
    def _dispatch_pass(self, nd, stk):
        d = ProductionList()
        d.set_options(self.options)
        d.set_category(nd.category)
        nd.conjoin = nd.children[0].category in [CAT_CONJ, CAT_COMMA] and isinstance(nd.children[0],
                                                                                        STreeLeafNode) and \
                     self._can_use_conjoin_rules(nd)
        for i in range(len(nd.children)):
            d.push_left(stk.pop())
        if d.contains_functor:
            # Bit of a hack, flatten() gets rid of empty productions
            stk.append(self._update_constituents(nd, d.flatten().unify(), d.category))
        else:
            stk.append(self._update_constituents(nd, d.unify(), d.category))

    @default_dispatchmethod(dispatchmap)
    def _dispatch_default(self, nd, stk):
        # All rules must have a handler
        assert False

    def _dispatch(self, nd, stk):
        """Dispatch a rule.

        Args:
            nd: The STreeNode. The dispatch is based on nd.rule.
            stk. The execution stack.
        """
        method = self.dispatchmap.lookup(nd.rule)
        method(self, nd, stk)

    def _mark_if_adjunct(self, nd, ucat, d):
        # ucat is the unary type change catgory
        # d is the result of the type change
        c = nd.constituent(self, ct.CONSTITUENT_ADJP if ucat.argument_category() == CAT_AP else ct.CONSTITUENT_ADVP)
        # Cannot have a proper noun as head of an adverbial or adjectival phrase
        if not c.head().isproper_noun:
            nd.ndtype = c.ndtype

    def _update_constituents(self, nd, d, cat_before_rule):
        ndtype = None
        if isinstance(d, (FunctorProduction, DrsProduction)):
            if d.category == CAT_NP:
                ndtype = ct.CONSTITUENT_NP
            elif cat_before_rule == CAT_ESRL_PP:
                if nd.constituent(self).head().pos == POS_PREPOSITION:
                    ndtype = ct.CONSTITUENT_PP
            elif cat_before_rule == CAT_PP_ADVP and d.category == CAT_VP_MOD and not d.span.isempty:
                hd = nd.constituent(self)
                if hd.pos == POS_PREPOSITION and hd.stem in ['for']:
                    ndtype = ct.CONSTITUENT_ADVP
            else:
                ndtype = ndtype_from_category(d.category)
                if ndtype is None and cat_before_rule.argument_category().remove_features() == CAT_N \
                        and (cat_before_rule.test_return(CAT_VPMODX) or cat_before_rule.test_return(CAT_VP_MODX)):
                    # (S\NP)/(S\NP)/N[X]
                    ndtype = ct.CONSTITUENT_NP
                elif ndtype is None and cat_before_rule.argument_category() in [CAT_VPb, CAT_VPto] and \
                        cat_before_rule.result_category().ismodifier and \
                        cat_before_rule.result_category().test_return(CAT_S_NP):
                    # Handle categories like ((S\NP)\(S\NP))/(S[b]\NP) for TO in 'has done more than its share to popularize'
                    ndtype = ct.CONSTITUENT_SINF

            if ndtype is not None:
                nd.ndtype = ndtype
        return d

    def _unary_np_map(self):
        nps = {}
        for np in itertools.ifilter(lambda x: 0 != (x.mask & (RT_ENTITY|RT_PROPERNAME)), self.lexemes):
            lst = nps.setdefault(np.refs[0], [])
            lst.append(np)
        for lx in itertools.ifilter(lambda x: 0 == (x.mask & (RT_ENTITY|RT_PROPERNAME)), self.lexemes):
            for r in lx.refs:
                if r in nps:
                    del nps[r]
                    break
        return nps

    def _refine_constituents(self):
        # Merge adjacent phrases
        # TODO: only iterate once from leaves
        merge = True
        while merge:
            merge = False
            for nd in itertools.ifilter(lambda nd: nd.isunary and nd.ndtype == ct.CONSTITUENT_NODE \
                                                and nd.children[0].ndtype != ct.CONSTITUENT_NODE, self.stree_nodes):
                nd.ndtype = nd.children[0].ndtype
                merge = True
            for nd in itertools.ifilter(lambda nd: nd.isbinary and nd.ndtype == ct.CONSTITUENT_NODE \
                                            and nd.children[0].ndtype != ct.CONSTITUENT_NODE \
                                            and nd.children[0].ndtype == nd.children[1].ndtype, self.stree_nodes):
                nd.ndtype = nd.children[0].ndtype
                merge = True

        # Ensure phrases have a constituent
        nps = dict(self.get_np_nominals())
        vps = dict(self.get_vp_nominals())
        for ps, ndtype in [(nps, ct.CONSTITUENT_NP), (vps, ct.CONSTITUENT_VP)]:
            leaves = filter(lambda x: x.isleaf and x.ndtype is ndtype, self.stree_nodes)
            for nd in leaves:
                refs = nd.lexeme.refs
                if refs[0] in ps:
                    p = ps[refs[0]].fullspan()
                    lastnd = None
                    while nd is not lastnd:
                        spnd = nd.span(self)
                        if p in spnd:
                            if p == spnd:
                                nd.ndtype = ndtype
                                # clear NP types below
                                for ndx in nd.iternodes():
                                    if not ndx.isleaf:
                                        ndx.ndtype = ct.CONSTITUENT_NODE
                            elif nd.isbinary:
                                i = 0 if nd.children[0] == lastnd else 1
                                assert lastnd == nd.children[i]

                                spi = nd.children[i].span(self)
                                if p in spi:
                                    # will catch in another leaf-root traversal
                                    pass
                                else:
                                    # Not sure this is required
                                    spk = nd.children[1-i].span(self)
                                    pk = spk.intersection(p)
                                    pi = spi.intersection(p)
                                    ck = spk.difference(pi)
                                    ci = spi.intersection(pk)
                                    args = [self.msgid]
                                    args.extend(sorted([spnd, ci, ck, p]))
                                    _logger.warning('[msgid=%s], cannot split phrase /%s/ -> /%s/%s/%s/' % tuple(args))
                            break
                        else:
                            lastnd = nd
                            nd = self.stree_nodes[nd.parent]

    def fixup_possessives(self):
        # Map possessives syntax tree nodes
        leaves = filter(lambda x: x.isleaf and x.lexeme.pos is POS_POSSESSIVE
                                  and x.category in [CAT_POSSESSIVE_PRONOUN, CAT_POSSESSIVE_ARGUMENT], self.stree_nodes)

        nps = dict(self.get_np_nominals())

        # Ensure there is a constituent containing the possessive and its owner NP
        for nd in leaves:
            refs = nd.lexeme.refs
            if len(refs) != 2 or refs[0] not in nps:
                continue
            np = nps[refs[0]].fullspan()
            poss = nd.span(self)
            lastnd = None
            while nd is not lastnd:
                spnd = nd.span(self)
                if np in spnd:
                    if (len(spnd) - len(np)) == 1:
                        # possessive and np in same phrase - make parent an NP
                        nd = self.stree_nodes[nd.parent]
                    if nd.ndtype == ct.CONSTITUENT_NODE:
                        nd.ndtype = ct.CONSTITUENT_NP
                    break
                else:
                    lastnd = nd
                    nd = self.stree_nodes[nd.parent]

    def post_create_fixup(self):
        # Special post create rules

        # clear existing
        self.drs_extra = filter(lambda x: not isinstance(x, Rel) or x.relation != DRSRelation('_ORPHANED'), self.drs_extra)
        for lx in self.lexemes:
            lx.mask &= ~RT_ORPHANED

        # Handle NP conjoins to VP
        orphaned_nps = self.select_phrases(RT_ENTITY | RT_ANAPHORA | RT_PROPERNAME | RT_ATTRIBUTE | RT_DATE | RT_NUMBER | RT_EMPTY_DRS,
                                           lambda x: True)
        vps = self.select_phrases(lambda x: 0 != (x.mask & RT_EVENT))
        refs = []
        for r, v in vps.iteritems():
            refs.extend(v[0].refs[1:])

        # TODO: find conjoins with orphaned nps
        for nd in self.conjoins:
            # For correctly built conjoins the head of the span is the attachment point.
            phrases = []
            cj = nd.span(self)

        # CCGBank does not specify appositives so attempt to find here
        r2c = {}
        for leaf in itertools.ifilter(lambda x: x.isleaf and x.ndtype in [ct.CONSTITUENT_NP], self.stree_nodes):
            lastnd = None
            lst = r2c.setdefault(leaf.lexeme.refs[0], set())
            while nd is not lastnd:
                lst.add(nd)
                lastnd = nd
                nd = self.stree_nodes[nd.parent]
        akas = set()

        # Look for patterns:
        #   Name-of-thing, a NP
        #   Name-of-thing, possessive NP
        # where graph connecting Name-of-thing is disjoint with NP

        disjoint_spans = self.get_disjoint_drs_spans()

        if len(disjoint_spans) > 1:
            orphaned = reduce(lambda x, y: x.union(y), disjoint_spans, set())

            # Look for patterns:
            #   Name-of-thing, a NP
            #   Name-of-thing, possessive NP
            # where graph connecting Name-of-thing is disjoint with NP
            #nps = self.select_phrases(RT_ENTITY | RT_PROPERNAME | RT_ATTRIBUTE | RT_EMPTY_DRS)
            # Look for patterns:
            #   a NP, Name-of-thing
            #   possessive NP, Name-of-thing
            # where graph connecting Name-of-thing is disjoint with NP
            nps = self.select_phrases(RT_ENTITY | RT_ANAPHORA | RT_PROPERNAME | RT_ATTRIBUTE |
                                                  RT_DATE | RT_NUMBER | RT_EMPTY_DRS)

            #for nd in itertools.ifilter(lambda x: x.isbinary and x.rule is RL_LP and not x.conjoin, self.stree_nodes):
            for nd in itertools.ifilter(lambda x: x.isbinary and x.rule in [RL_LP, RL_TCR_UNARY] and not x.conjoin
                                and x.children[0].category == CAT_COMMA, self.stree_nodes):

                parent = self.stree_nodes[nd.parent]
                if parent == nd or not parent.isbinary:
                    continue
                i = 0 if parent.children[0] == nd else 1
                if i == 0:
                    continue
                if nd.children[1].ndtype != ct.CONSTITUENT_NP or parent.children[1-i].ndtype != ct.CONSTITUENT_NP:
                    continue

                cnpR = nd.children[1].constituent(self)
                cnpL = parent.children[0].constituent(self)
                npR = cnpR.span
                npL = cnpL.span

                orphanedL = orphaned.intersection(npL)
                orphanedR = orphaned.intersection(npR)
                if (len(orphanedL) == 0 and len(orphanedR) == 0) or (len(orphanedL) != 0 and len(orphanedR) != 0):
                    continue

                i = 0 if len(orphanedL) == 0 else 1
                cnpX = [cnpL, cnpR]

                if npR[0].stem in ['a', 'an', 'the'] and cnpL.head().refs[0] in nps:
                    sp = nps[cnpL.head().refs[0]]
                    if sp in npL:
                        # OK this looks like an appositive
                        akas.add((cnpX[1-i].head().refs[0], cnpX[i].head().refs[0]))
                elif cnpR.head().refs[0] in nps:
                    sp = nps[cnpR.head().refs[0]]
                    if sp in npR:
                        # OK this looks like an appositive
                        akas.add((cnpX[1-i].head().refs[0], cnpX[i].head().refs[0]))
                # FIXME: LDC RAW 897, AUTO wsj_0048.24

        # Add aliases
        for x, y in akas:
            self.drs_extra.append(Rel('_AKA', [x, y]))

        # Find orphaned and add to extra's
        orphaned_nps = self.select_phrases(RT_ENTITY | RT_ANAPHORA | RT_PROPERNAME | RT_ATTRIBUTE | RT_DATE | RT_NUMBER | RT_EMPTY_DRS,
                                           lambda x: True)
        for x, y in akas:
            if x in orphaned_nps:
                del orphaned_nps[x]
            if y in orphaned_nps:
                del orphaned_nps[y]

        for r, np in orphaned_nps.iteritems():
            for lx in np:
                lx.mask |= RT_ORPHANED
            self.drs_extra.append(Rel('_ORPHANED', [r]))

    def create_drs(self):
        """Create a DRS from the execution queue. Must call build_execution_sequence() first."""
        assert self.stree_nodes[-1].parent == (len(self.stree_nodes)-1)  # check root is at end
        # First create all productions up front
        prods = [None] * len(self.lexemes)
        for i in range(len(self.lexemes)):
            lexeme = self.lexemes[i]
            if lexeme.category.ispunct:
                prod = DrsProduction([], [], category=lexeme.category, span=Span(self))
                prod.set_lambda_refs([DRSRef(DRSVar('X', self.xid+1))])
                self.xid += 1
                prod.set_options(self.options)
            elif lexeme.category in [CAT_LRB, CAT_RRB, CAT_LQU, CAT_RQU]:
                prod = DrsProduction([], [], category=CAT_EMPTY, span=Span(self))
                prod.set_lambda_refs([DRSRef(DRSVar('X', self.xid+1))])
                self.xid += 1
            else:
                prod = self.rename_vars(lexeme.get_production(self, self.options))
            prod.set_options(self.options)
            prods[i] = prod

            # Useful for select_phrases
            if lexeme.drs is None or lexeme.drs.isempty:
                lexeme.mask |= RT_EMPTY_DRS
        # TODO: Defer special handling of proper nouns

        # Process exec queue
        stk = []
        for nd in self.stree_nodes:
            if isinstance(nd, STreeLeafNode):
                # Set leaf constituent types
                if 0 != (nd.lexeme.mask & (RT_EVENT|RT_EVENT_ATTRIB|RT_EVENT_MODAL)):
                    nd.ndtype = ct.CONSTITUENT_VP
                elif 0 != (nd.lexeme.mask & (RT_ENTITY|RT_PROPERNAME)):
                    nd.ndtype = ct.CONSTITUENT_NP
                elif nd.lexeme.pos == POS_PREPOSITION:
                    nd.ndtype = ct.CONSTITUENT_PP
                stk.append(prods[nd.lexeme.idx])
            else:
                # STreeNode dispatch based on rule
                self._dispatch(nd, stk)

            if not (stk[-1].verify() and stk[-1].category.can_unify(nd.category)):
                stk[-1].verify()
                stk[-1].category.can_unify(nd.category)
                pass
            assert stk[-1].verify() and stk[-1].category.can_unify(nd.category)
            assert nd.category.get_scope_count() == stk[-1].get_scope_count(), "result-category=%s, prod=%s" % \
                                                                               (nd.category, stk[-1])
        # Get final DrsProduction
        assert len(stk) == 1
        d = stk[0]
        if d.isfunctor and d.isarg_left and d.category.argument_category().isatom:
            d = d.apply_null_left().unify()
            oldroot = self.stree_nodes[-1]
            oldroot.parent = len(self.stree_nodes)
            newroot = STreeNode(len(self.stree_nodes), [oldroot], oldroot.head_idx, CAT_S, RL_NOP, oldroot.lex_range, 0)
            newroot.ndtype = ct.CONSTITUENT_S
            self.stree_nodes.append(newroot)
        self.final_prod = d

        # TODO: update universe and freerefs to match DRS

        # Now check prepositions that are orphaned - He waited for them to arrive
        #   he(x1) wait(e1) arg0(e1, x1) arg1(e1, x2) for(x2, e2) them(x3) arrive(e2) arg0(e2, x3)
        # becomes:
        #   he(x1) wait(e1) arg0(e1, x1) arg1(e1, e2) for(e1, e2) them(x3) arrive(e2) arg0(e2, x3)
        all_vars = set()
        preps = set()
        prep_args = set()
        evt_args = set()
        for lex in self.lexemes:
            if lex.ispreposition:
                preps.add(lex.refs[0])
                prep_args = prep_args.union(filter(lambda x: x != lex.refs[0], lex.refs[1:]))
            elif 0 != (lex.mask & RT_EVENT):
                all_vars.add(lex.refs[0])
                evt_args = evt_args.union(lex.refs[1:])
            else:
                all_vars = all_vars.union(lex.refs)
        orphaned_preps = preps.difference(all_vars.union(prep_args)).intersection(evt_args)
        orphaned_prep_args = prep_args.difference(all_vars.union(preps)).intersection(evt_args)

        if len(orphaned_preps) != 0:
            eargs = {}
            for lex in itertools.ifilter(lambda x: 0 != (x.mask & RT_EVENT), self.lexemes):
                for r in lex.refs[1:]:
                    es = eargs.setdefault(r, set())
                    es.add(lex.idx)
            for lex in itertools.ifilter(lambda x: len(x.refs) > 1 and x.refs[0] in orphaned_preps, self.lexemes):
                if lex.refs[0] in eargs:
                    if len(lex.refs) == 2:
                        if lex.refs[1] not in orphaned_prep_args:
                            # left arg is orphaned
                            es = eargs[lex.refs[0]]
                            if len(es) == 1:
                                d.rename_vars([(lex.refs[0], lex.refs[1])])
                                e = self.lexemes[sorted(es)[0]]
                                lex.refs = [e.refs[0], lex.refs[1]]
                                lex.drs = DRS([], [Rel(lex.stem, lex.refs)])
                                # TODO: remove _ARG? from event drs
                        else:
                            # left and right are orphaned
                            # TODO: handle these later
                            pass
                            #d.rename_vars([(lex.refs[0], lex.refs[1])])
                            #lex.refs = [lex.refs[0]]
                            #lex.drs = DRS([], [Rel(lex.stem, lex.refs)])
                elif len(lex.refs) > 1:
                    d.rename_vars([(lex.refs[0], lex.refs[1])])
                    lex.refs = lex.refs[1:]
                    lex.drs = DRS([], [Rel(lex.stem, lex.refs)])

        # Fixup conjoins - must have at least one CAT_CONJ
        self.conjoins = filter(lambda sp: any([x.category == CAT_CONJ for x in sp]), self.conjoins)
        # Refine constituents and we are done
        self._refine_constituents()

    def select_phrases(self, select_fn, exclude_fn=None, contiguous=True):
        """Get a map of the phrases match the selection/exclusion criteria.

        Args:
            select_fn: The lexeme selection function. If an integer mask is passed then select function
                is set to lambda x: 0 != (x.mask & select_fn)
            exclude_fn: Exclusion function applied to unselected lexemes. Default is no exclusion. If
                lexemes in the exclusion set have a n-ary predicate connected to the selected set then the
                selected entry is excluded from the result. If an integer mask is passed then exclusion
                function is set to lambda x: 0 != (x.mask & exclude_fn)
            contiguous: If True (default) then only allow contiguous spans.

        Returns:
            A dictionary of referent(key):Span(value) instances.
        """
        if isinstance(select_fn, (long, int)):
            mask = select_fn
            select_fn = (lambda x: 0 != (x.mask & mask))

        nps = {}
        for np in itertools.ifilter(lambda x: len(x.refs) != 0 and select_fn(x), self.lexemes):
            lst = nps.setdefault(np.refs[0], Span(self))
            lst.add(np)

        # Trim leading and trailing conjoins
        for r, np in nps.iteritems():
            while len(np) != 0 and np[0].category in [CAT_COMMA, CAT_CONJ]:
                np.remove(np[0])
            while len(np) != 0 and np[-1].category in [CAT_COMMA, CAT_CONJ]:
                np.remove(np[-1])

        if exclude_fn is not None:
            if isinstance(exclude_fn, (long, int)):
                emask = exclude_fn
                exclude_fn = (lambda x: 0 != (x.mask & emask))
            for lx in itertools.ifilter(lambda x: len(x.refs) != 0 and not select_fn(x) and exclude_fn(x), self.lexemes):
                refs = [] if lx.drs is None or lx.drs.isempty else lx.drs.variables
                if len(refs) < 2:
                    continue
                for r in refs:
                    if r in nps:
                        del nps[r]

        # Remove solo empty entries
        for lx in itertools.ifilter(lambda x: 0 != (x.mask & RT_EMPTY_DRS) and len(x.refs) != 0, self.lexemes):
            if lx.refs[0] in nps:
                np = nps[lx.refs[0]]
                if len(np) == 0 or (len(np) == 1 and 0 != (np[0].mask & RT_EMPTY_DRS)):
                    del nps[lx.refs[0]]

        if contiguous:
            # Contiguous when we allow lexemes with no drs
            del_marked = []
            for r, np in nps.iteritems():
                fnp = np.fullspan()
                dnp = fnp.difference(np)
                # This happends because we assign a variable to conjoins so we
                # can see it in functor phrases - RT_EMPTY_DRS
                while len(dnp) != 0 and np[-1].stem in ['or', 'and', 'neither', 'nor', '-LRB-', '-RRB-', '-LQU-', '-RQU-']:
                    np.remove(np[-1].idx)
                    fnp = np.fullspan()
                    dnp = fnp.difference(np)
                if len(dnp) != 0 and not all([x.drs is None or x.drs.isempty for x in dnp]):
                    del_marked.append(r)
            for r in del_marked:
                del nps[r]

        return nps

    def get_np_nominals(self):
        """Get noun phrases consisting of logical And of functions in the same referent.

        Remarks:
            This uses the logical model not the constituent model.
        """
        nps = self.select_phrases(lambda x: 0 != (x.mask & (RT_ENTITY | RT_PROPERNAME | RT_ATTRIBUTE | RT_DATE | RT_NUMBER | RT_EMPTY_DRS)))
        return nps.items()

    def get_vp_nominals(self):
        """Get verb phrases consisting of logical And of functions in the same referent.

        Remarks:
            This uses the logical model not the constituent model.
        """
        vps = self.select_phrases(lambda x: 0 != (x.mask & (RT_EVENT_ATTRIB | RT_EVENT_MODAL | RT_EVENT)))
        return vps.items()

    def get_orphaned_np_nominals(self):
        """Identify orphaned noun phrases and anaphora. This can happen when comma's are inserted incorrectly.

        Remarks:
            Uses select_phrases(lambda x: 0 != (x.mask & RT_ORPHANED)) for results.
        """
        nps = self.select_phrases(lambda x: 0 != (x.mask & RT_ORPHANED))
        return None if len(nps) == 0 else nps.items()

    def resolve_proper_names(self):
        """Merge proper names."""

        # Sort NP syntax tree nodes by their span
        constituents = sorted(filter(lambda np: np.ndtype == ct.CONSTITUENT_NP, self.stree_nodes), key=lambda np: np.span(self))

        to_remove = Span(self)
        for nd in constituents:
            c = nd.constituent(self)
            cspan = c.span.difference(to_remove)
            if cspan.isempty:
                continue

            spans = []
            lastref = DRSRef('$$$$')
            startIdx = -1
            endIdx = -1
            for i in range(len(c.span)):
                lexeme = c.span[i]
                if lexeme.refs is None or len(lexeme.refs) == 0:
                    ref = DRSRef('$$$$')
                else:
                    ref = lexeme.refs[0]

                if startIdx >= 0:
                    if ref == lastref and (lexeme.isproper_noun or lexeme.category == CAT_N):
                        endIdx = i
                        continue
                    elif ref == lastref and lexeme.word in ['&', 'and', 'for', 'of'] and (i+1) < len(c.span) \
                            and c.span[i+1].isproper_noun:
                        continue
                    else:
                        if startIdx != endIdx:
                            spans.append((startIdx, endIdx))
                        startIdx = -1

                if lexeme.isproper_noun:
                    startIdx = i
                    endIdx = i
                    lastref = ref

            if startIdx >= 0 and startIdx != endIdx:
                spans.append((startIdx, endIdx))

            for s, e in spans:
                # Handle cases like  "according to Donoghue 's ." and "go to Paul 's"
                if c.span[e].word == "'s":
                    if e == (s+1):
                        continue
                    e -= 1

                spfound = Span(self, s, e+1)
                if spfound in to_remove:
                    continue

                # Preserve heads
                lexeme = c.head()
                if lexeme.idx not in spfound:
                    # TODO: log this
                    continue

                ref = lexeme.refs[0]
                word = '-'.join([c.span[i].word for i in range(s, e+1)])
                stem = '-'.join([c.span[i].stem for i in range(s, e+1)])
                fca = lexeme.drs.find_condition(Rel(lexeme.stem, [ref]))
                if fca is None:
                    continue
                fca.cond.relation.rename(stem)
                lexeme.stem = stem
                lexeme.word = word
                spfound.remove(lexeme.idx)
                to_remove = to_remove.union(spfound)

        if not to_remove.isempty:
            # Python 2.x does not support nonlocal keyword for the closure
            class context:
                i = 0
            def counter(inc=1):
                idx = context.i
                context.i += inc
                return idx

            # Remove constituents and remap indexes.
            #
            inodes = []
            for nd in itertools.ifilter(lambda nd: nd.isleaf and nd.lexeme.idx in to_remove, self.stree_nodes):
                lastnd = None
                # Trace path back to root and mark nodes for deletion
                inodes.append(nd.idx)
                while nd.idx != 0:
                    if nd.isbinary:
                        i = 0 if nd.children[0] == lastnd else 1
                        assert nd.children[i].span(self) in to_remove
                        inodes.append(nd.children[i].idx)
                        # Make node unary, if another path from a leaf includes this node
                        # then it will be marked for deletion
                        nd.remove_child(i)
                        nd.rule = RL_NOP
                        break
                    else:
                        # Should never delete root
                        assert nd.idx != 0
                        inodes.append(nd.idx)
                    lastnd = nd
                    nd = self.stree_nodes[nd.parent]

            # Remove nodes and remap tree indexes
            inodes = set(inodes)
            context.i = 0
            idxmap = map(lambda x: -1 if x in inodes else counter(), range(len(self.stree_nodes)))
            newsize = len(self.stree_nodes) - len(inodes)
            self.conjoins = filter(lambda nd: nd.idx not in inodes, self.conjoins)
            self.stree_nodes = filter(lambda nd: nd.idx not in inodes, self.stree_nodes)
            idxmap = dict([(x[0].idx, x[1]) for x in zip(self.stree_nodes, range(len(self.stree_nodes)))])
            assert newsize == len(self.stree_nodes)
            for i in xrange(len(self.stree_nodes)):
                nd = self.stree_nodes[i]
                nd.idx = i
                nd.parent = idxmap[nd.parent]

            # Remove lexemes and remap indexes.
            idxs_to_del = set(to_remove.indexes())

            # Reparent heads marked for deletion
            for lex in itertools.ifilter(lambda x: x.idx not in idxs_to_del, self.lexemes):
                lasthead = -1
                while lex.head in idxs_to_del and lex.head != lasthead:
                    lasthead = lex.head
                    lex.head = self.lexemes[lex.head].head
                if lex.head in idxs_to_del:
                    # New head for sentence
                    lex.head = lex.idx

            context.i = 0
            idxmap = map(lambda x: -1 if x in idxs_to_del else counter(), range(len(self.lexemes)))

            self.lexemes = map(lambda y: self.lexemes[y], filter(lambda x: idxmap[x] >= 0, range(len(idxmap))))
            for i in range(len(self.lexemes)):
                lexeme = self.lexemes[i]
                lexeme.idx = i
                lexeme.head = idxmap[lexeme.head]
                assert lexeme.head >= 0

            # Set lexical heads for tree nodes
            for nd in self.stree_nodes:
                nd.set_head(idxmap[nd.head_idx])

            # Last is root
            self.stree_nodes[-1].recalc_span()

            if self.final_prod is not None:
                pspan = Span(self, map(lambda y: idxmap[y],
                                       filter(lambda x: idxmap[x] >= 0, self.final_prod.span.indexes())))
                self.final_prod.span = pspan

            if isdebugging():
                # Check the sentence head
                for lex in self.lexemes:
                    sentence_head = lex.idx
                    while self.lexemes[sentence_head].head != sentence_head:
                        sentence_head = self.lexemes[sentence_head].head
                    assert sentence_head == self.stree_nodes[-1].head_idx


    def get_drs(self, nodups=False):
        refs = []
        conds = []
        for w in self.lexemes:
            if w.drs:
                refs.extend(w.drs.universe)
                conds.extend(w.drs.conditions)
        conds.extend(self.drs_extra)
        if not nodups:
            return DRS(refs, conds)
        cs = set(conds)
        rs = set(refs)
        # Remove dups but keep ordering. Ordering is not necessary but makes it easier to read.
        nrefs = []
        nconds = []
        for r in refs:
            if r in rs:
                rs.remove(r)
                nrefs.append(r)
        for c in conds:
            if c in cs:
                cs.remove(c)
                nconds.append(c)
        return DRS(nrefs, nconds)

    def final_rename(self):
        """Rename to ensure:
            - indexes progress is 1,2,...
            - events are tagged e, others x
        """
        use_word_idx = 0 != (self.options & CO_VARNAMES_MATCH_WORD_INDEX)
        vx = set(filter(lambda x: not x.isconst, self.final_prod.variables))
        ors = filter(lambda x: x.var.idx < len(vx), vx)
        if len(ors) != 0:
            # Move names to > len(vx)
            mx = 1 + max([x.var.idx for x in vx])
            idx = [i+mx for i in range(len(ors))]
            rs = map(lambda x: (x[0], DRSRef(DRSVar(x[0].var.name, x[1]))), zip(ors, idx))
            self.final_prod.rename_vars(rs)
            vx = set(filter(lambda x: not x.isconst, self.final_prod.variables))

        if use_word_idx:
            # This rename method help comparison with Gold parse
            vm = {}
            idunused = len(self.lexemes)
            for lx in self.lexemes:
                if 0 != (lx.mask & (RT_EVENT|RT_ANAPHORA|RT_ENTITY|RT_PROPERNAME)) and lx.refs[0] not in vm:
                    vm[lx.refs[0]] = lx.idx
            for lx in self.lexemes:
                if len(lx.refs) != 0 and lx.refs[0] not in vm:
                    vm[lx.refs[0]] = lx.idx
            for lx in self.lexemes:
                for r in lx.refs:
                    if r not in vm:
                        vm[r] = idunused
                        idunused += 1
            rs = []
            for r, i in vm.iteritems():
                if i < len(self.lexemes) and 0 != (self.lexemes[i].mask & RT_EVENT):
                    # ensure events are prefixed 'E'
                    rs.append((r, DRSRef(DRSVar('E', i+1))))
                else:
                    rs.append((r, DRSRef(DRSVar('X', i+1))))

            self.final_prod.rename_vars(rs)

            # For NP's we sometimes get the head wrong. This changes the dependency
            # tree but the DRS is the same. Align left so we can compare easily.
            nps = self.get_np_nominals()
            rs = []
            for r, np in nps:
                idx = r.var.idx
                if len(np) > 1 and idx != (np[0].idx+1):
                    # Align left
                    rs.append((r, DRSRef(DRSVar('X', np[0].idx+1))))

            self.final_prod.rename_vars(rs)

            # Save verbs for next 2 steps
            vps = filter(lambda x: 0 != (x.mask & RT_EVENT), self.lexemes)

            # For conjoins head is on left or right. Force event _ARGn variables aligned left.
            # We choose left because we want to skip prepositional phrases in conjoin.
            # For example: "the President and every member of Congress"
            for ndconj in self.conjoins:
                ndc = ndconj
                while ndc.parent != ndc.idx and ndc.ndtype != ct.CONSTITUENT_NODE:
                    ndc = self.stree_nodes[ndc.parent]
                if ndc.ndtype != ct.CONSTITUENT_NODE:
                    conj = ndconj.span(self)
                    rconj = set(map(lambda x: x.refs[0], filter(lambda x: not x.drs.isempty, conj)))
                    rl = conj[0].refs[0]
                    rr = conj[-1].refs[0]
                    rconj.discard(rl)
                    if rl != rr:
                        # Change verb arguments
                        for vp in vps:
                            for i in range(1, len(vp.refs)):
                                if vp.refs[i] in rconj:
                                    if i >= len(EventPredicates):
                                        pass
                                        assert False
                                    fc = vp.drs.find_condition(Rel(EventPredicates[i-1], [vp.refs[0], vp.refs[i]]))
                                    if fc is not None:
                                        vp.refs[i] = rl
                                        fc.cond.set_referents([vp.refs[0], rl])
                        # Change prep immediately to left if it exists
                        if conj[0].idx > 0:
                            lex = self.lexemes[conj[0].idx-1]
                            if lex.pos == POS_PREPOSITION and len(lex.refs) == 2 and lex.refs[1] in rconj:
                                lex.refs[1] = rl
                                lex.drs = DRS([], [Rel(lex.stem, lex.refs)])

            # Remove orphaned verb arguments
            all_vpargs = dict(map(lambda x: (x, 0), reduce(lambda x, y: x.union(y.refs[1:]), vps, set())))
            for lex in self.lexemes:
                for r in itertools.ifilter(lambda x: x in all_vpargs, lex.refs):
                    all_vpargs[r] += 1  # usage count
            for r, _ in itertools.ifilter(lambda x: x[1] == 1, all_vpargs.items()):
                for vp in vps:
                    idel = []
                    for i in range(1, len(vp.refs)):
                        if r == vp.refs[i]:
                            fc = vp.drs.find_condition(Rel(EventPredicates[i-1], [vp.refs[0], r]))
                            if fc is not None:
                                # TODO: enable this
                                pass
                                #idel.append(i)
                                #vp.drs.remove_condition(fc)
                    for i in idel:
                        del vp.refs[i]

        else:
            # Attempt to order by first occurence
            v = []
            for t in self.lexemes:
                if t.drs:
                    v.extend(t.drs.universe)

            v = remove_dups(v)
            if len(vx) != len(v):
                f = set(vx).difference(v)
                v.extend(f)

            # Map variables to type
            vtype = dict(map(lambda y: (y.refs[0], y.mask), filter(lambda x: x.drs and len(x.drs.universe) != 0, self.lexemes)))

            # Move names to 1:...
            idx = [i+1 for i in range(len(v))]
            #rs = map(lambda x: (x[0], DRSRef(DRSVar(x[0].var.name, x[1]))), zip(v, idx))
            rs = []
            for u, i in zip(v, idx):
                mask = vtype.setdefault(u, 0)
                if 0 != (mask & RT_EVENT):
                    # ensure events are prefixed 'E'
                    rs.append((u, DRSRef(DRSVar('E', i))))
                else:
                    rs.append((u, DRSRef(DRSVar('X', i))))

            self.final_prod.rename_vars(rs)

        self.xid = self.limit
        self.eid = self.limit

    def rename_vars(self, d):
        """Rename to ensure variable names are disjoint. This should be called immediately after
        creating a production.

        Args:
            d: A DrsProduction instance.

        Returns:
            A renamed DrsProduction instance.
        """
        if d is None:
            raise ValueError
        assert len(filter(lambda x: x.isconst, d.variables)) == 0
        v = set(filter(lambda x: not x.isconst, d.variables))
        xlimit = 0
        elimit = 0
        for i in range(10):
            if DRSRef(DRSVar('X', 1+i)) in v:
                xlimit = 1 + i
                if DRSRef(DRSVar('E', 1+i)) in v:
                    elimit = 1 + i
            elif DRSRef(DRSVar('E', 1+i)) in v:
                elimit = 1 + i
            else:
                break
        rs = []
        if self.xid == 0:
            self.xid = xlimit
        else:
            for i in range(xlimit):
                rs.append((DRSRef(DRSVar('X', 1+i)), DRSRef(DRSVar('X', 1+i+self.xid))))
            self.xid += xlimit
        if self.eid == 0:
            self.eid = elimit
        else:
            for i in range(elimit):
                rs.append((DRSRef(DRSVar('E', 1+i)), DRSRef(DRSVar('E', 1+i+self.eid))))
            self.eid += elimit
        if len(rs) != 0:
            rs.reverse()
            d.rename_vars(rs)
        return d

    def build_execution_sequence(self, pt, keep_predarg=False):
        """Build the execution sequence from a ccg derivation's parse tree.

        Args:
            pt: The parse tree for a ccg derivation.
            keep_predarg: If true the keep predarg categories. Default is false.
        """
        # FIXME: Remove recursion from this function
        self.depth += 1
        if pt[-1] == 'T':
            head = int(pt[0][1])
            count = int(pt[0][2])
            assert head == 1 or head == 0, 'ccgbank T node head=%d, count=%d' % (head, count)
            result = Category.from_cache(pt[0][0])

            idxs = []
            lex_begin = len(self.lexemes)
            nd_begin = len(self.stree_nodes)
            nd_end = []
            for nd in pt[1:-1]:
                idxs.append(self.build_execution_sequence(nd))
                nd_end.append(len(self.stree_nodes)-1)

            assert count == len(idxs)
            # Ranges allow us to schedule work to a thread pool
            op_range = (nd_begin, len(self.stree_nodes))
            lex_range = (lex_begin, len(self.lexemes))

            if count == 2:
                childs = [self.stree_nodes[nd_end[0]], self.stree_nodes[-1]]
                #cats = map(lambda x: CAT_EMPTY if x.category in [CAT_LRB, CAT_RRB, CAT_LQU, CAT_RQU] else x.category,
                #           childs)
                cats = [x.category for x in childs]
                rule = get_rule(cats[0], cats[1], result)
                if rule is None:
                    rule = get_rule(cats[0].simplify(), cats[1].simplify(), result)
                    if rule is None:
                        raise CombinatorNotFoundError('cannot discover combinator for %s <- %s <?> %s' % (result, cats[0], cats[1]))

                # Head resolved to lexemes indexes
                assert idxs[1-head] in range(lex_range[0], lex_range[1])
                assert idxs[head] in range(lex_range[0], lex_range[1])
                self.lexemes[idxs[1-head]].head = idxs[head]
                childs[0].parent = len(self.stree_nodes)
                childs[1].parent = len(self.stree_nodes)
                self.stree_nodes.append(
                    STreeNode(len(self.stree_nodes), childs, idxs[head], result, rule, lex_range, self.depth))
                self.depth -= 1
                return idxs[head]
            else:
                assert count == 1
                childs = [self.stree_nodes[-1]]
                childs[0].parent = len(self.stree_nodes)
                #cats = map(lambda x: CAT_EMPTY if x.category in [CAT_LRB, CAT_RRB, CAT_LQU, CAT_RQU] else x.category,
                #           childs)
                cats = [x.category for x in childs]
                rule = get_rule(cats[0], CAT_EMPTY, result)
                if rule is None:
                    rule = get_rule(cats[0].simplify(), CAT_EMPTY, result)
                    assert rule is not None

                # No need to set head, Lexeme defaults to self is head
                self.stree_nodes.append(
                    STreeNode(len(self.stree_nodes), childs, idxs[head], result, rule, lex_range, self.depth))
                self.depth -= 1
                return idxs[head]
        else:
            lexeme = Lexeme(Category.from_cache(pt[0]), pt[1], pt[2:4], len(self.lexemes))
            self.lexemes.append(lexeme)
            self.stree_nodes.append(
                STreeLeafNode(lexeme, len(self.stree_nodes), self.depth, Category(pt[4]) if keep_predarg else None))
            self.depth -= 1
            return lexeme.idx

    def get_predarg_ccgbank(self, pretty=False):
        """Return a ccgbank representation with predicate-argument tagged categories. See LDC 2005T13 for details.

        Args:
            pretty: Pretty format, else one line string.

        Returns:
            A ccgbank string.
        """
        assert len(self.stree_nodes) != 0 and len(self.lexemes) != 0
        assert isinstance(self.stree_nodes[0], STreeLeafNode)

        # Process exec queue
        stk = collections.deque()
        sep = '\n' if pretty else ' '
        for nd in self.stree_nodes:
            indent = '  ' * nd.depth if pretty else ''
            if isinstance(nd, STreeLeafNode):
                # Leaf nodes contain 5 fields:
                # <L CCGcat mod_POS-tag orig_POS-tag word PredArgCat>
                if nd.lexeme.category in [CAT_LRB, CAT_RRB, CAT_LQU, CAT_RQU]:
                    stk.append('%s(<L %s %s %s %s %s>)' % (indent, nd.lexeme.category, nd.lexeme.pos, nd.lexeme.pos,
                                                           nd.lexeme.word, nd.lexeme.category))
                else:
                    template = nd.lexeme.get_template()
                    if template is None:
                        stk.append('%s(<L %s %s %s %s %s>)' % (indent, nd.lexeme.category, nd.lexeme.pos, nd.lexeme.pos,
                                                               nd.lexeme.word, nd.lexeme.category))
                    else:
                        stk.append('%s(<L %s %s %s %s %s>)' % (indent, nd.lexeme.category, nd.lexeme.pos, nd.lexeme.pos,
                                                               nd.lexeme.word, template.predarg_category))
            elif len(nd.children) == 2:
                assert len(stk) >= 2
                if nd.rule == RL_TCL_UNARY:
                    unary = MODEL.lookup_unary(nd.category, nd.children[0].category)

                    nlst = collections.deque()
                    # reverse order
                    nlst.append('%s(<T %s %d %d>' % (indent, nd.category, 1, 2))
                    nlst.append(stk.pop())
                    if unary is None:
                        _UNDEFINED_UNARY.add((nd.category, nd.children[0].category))
                        unary = Category.combine(nd.category, '\\', nd.children[0].category, cacheable=False)
                        nlst.append('%s  (<L %s %s %s %s %s>)' % (indent, unary, '?UNARY?', '?UNARY?',
                                                                  '?UNARY?', unary))
                    else:
                        template = unary.template
                        nlst.append('%s  (<L %s %s %s %s %s>)' % (indent, template.clean_category, 'UNARY', 'UNARY',
                                                                  'UNARY', template.predarg_category))
                    nlst.append('%s)' % indent)
                    stk.append(sep.join(nlst))
                elif nd.rule == RL_TCR_UNARY:
                    unary = MODEL.lookup_unary(nd.category, nd.children[1].category)
                    nlst = collections.deque()
                    nlst.append('%s(<T %s %d %d>' % (indent, nd.category, 1, 2))
                    b = stk.pop()
                    a = stk.pop()
                    nlst.append(a)
                    nlst.append(b)
                    if unary is None:
                        _UNDEFINED_UNARY.add((nd.category, nd.children[1].category))
                        unary = Category.combine(nd.category, '\\', nd.children[1].category, cacheable=False)
                        nlst.append('%s  (<L %s %s %s %s %s>)' % (indent, unary, '?UNARY?', '?UNARY?',
                                                                  '?UNARY?', unary))
                    else:
                        template = unary.template
                        nlst.append('%s  (<L %s %s %s %s %s>)' % (indent, template.clean_category, 'UNARY', 'UNARY',
                                                                  'UNARY', template.predarg_category.signature))
                    nlst.append('%s)' % indent)
                    stk.append(sep.join(nlst))
                else:
                    nlst = collections.deque()
                    nlst.appendleft(stk.pop())  # arg1
                    nlst.appendleft(stk.pop())  # arg0
                    nlst.appendleft('%s(<T %s %d %d>' % (indent, nd.category, 0 if nd.head_idx == nd.children[0].head_idx else 1, 2))
                    nlst.append('%s)' % indent)
                    stk.append(sep.join(nlst))
            elif nd.rule == RL_TCL_UNARY:
                unary = MODEL.lookup_unary(nd.category, nd.children[0].category)
                template = unary.template
                nlst = collections.deque()
                # reverse order
                nlst.append('%s(<T %s %d %d>' % (indent, nd.category, 0, 2))
                nlst.append(stk.pop())
                if unary is None:
                    _UNDEFINED_UNARY.add((nd.category, nd.children[0].category))
                    unary = Category.combine(nd.category, '\\', nd.children[0].category, cacheable=False)
                    nlst.append('%s  (<L %s %s %s %s %s>)' % (indent, unary, '?UNARY?', '?UNARY?',
                                                              '?UNARY?', unary))
                else:
                    nlst.append('%s  (<L %s %s %s %s %s>)' % (indent, template.clean_category, 'UNARY', 'UNARY',
                                                              'UNARY', template.predarg_category))
                nlst.append('%s)' % indent)
                stk.append(sep.join(nlst))
            else:
                nlst = collections.deque()
                nlst.appendleft(stk.pop())  # arg0
                nlst.appendleft('%s(<T %s %d %d>' % (indent, nd.category, 0, 1))
                nlst.append('%s)' % indent)
                stk.append(sep.join(nlst))

        assert len(stk) == 1
        return stk[0]

    def get_disjoint_drs_spans(self):
        """Get the list of spans such that the drs for each span are disjoint."""
        r2i = {}
        for lx in self.lexemes:
            if lx.drs is None or len(lx.refs) == 0:
                continue
            elif lx.drs.isempty:
                vs = [lx.refs[0]]
            else:
                vs = lx.drs.variables
            for v in vs:
                lst = r2i.setdefault(v, [])
                lst.append(lx.idx)

        spans = []
        seen = set()
        for r in r2i.iterkeys():
            if r in seen:
                continue
            stk = [r]
            closure = []
            while len(stk) != 0:
                r = stk.pop()
                if r in seen:
                    continue
                seen.add(r)
                idxs = r2i[r]
                closure.extend(idxs)
                for i in idxs:
                    lx = self.lexemes[i]
                    if lx.drs is None or len(lx.refs) == 0:
                        continue
                    elif lx.drs.isempty:
                        stk.append(lx.refs[0])
                    else:
                        stk.extend(lx.drs.variables)
            if len(closure) != 0:
                spans.append(Span(self, closure))

        return sorted(spans)

    def get_span(self):
        """Get a span of the entire sentence.

        Returns:
            A Span instance.
        """
        # TODO: support span with start and length
        return Span(self, range(len(self.lexemes)))

    def get_subspan_from_wiki_search(self, query_span, search_result, threshold=0.7, title_only=True):
        """Get a subspan from a wikpedia search result.

        Args:
            query_span: The span of the query.
            search_result: The result of a wikipedia.search().
            threshold: A ratio (< 1) of match quality.
            title_only: If True then search title words else search page content.

        Returns:
            A tuple containing an Span instance and the wiki-page.
        """
        # TODO: search page content
        if not title_only:
            return None, None
        best_score = np.float32(0)
        best_result = None
        best_span = None
        iwords = []
        threshold = np.float32(threshold)

        for lex in query_span:
            # Proper nouns get hypenated
            iwords.extend([(w, lex.idx) for w in lex.word.replace('-', ' ').lower().split(' ')])

        for result in search_result:
            title = result.title.lower().split(' ')
            score = np.zeros(shape=(len(iwords), len(title)), dtype=np.float32)
            for k in range(len(iwords)):
                wi = iwords[k]
                score[k,:] = [float(len(os.path.commonprefix([wi[0], nm])))/float(len(wi[0])) for nm in title]
            d0 = np.max(score, axis=1)
            score = np.mean(d0)
            if score >= threshold and score > best_score:
                pos = (d0 > threshold/2) * np.arange(1, len(iwords)+1, dtype=np.int32)
                idxs = set()
                for k in np.nditer(pos):
                    if k > 0:
                        idxs.add(iwords[int(k)-1][1])
                best_score = score
                best_result = result
                idxs = sorted(idxs)
                if len(idxs) >= 2:
                    idxs = [x for x in range(idxs[0], idxs[-1]+1)]
                best_span = Span(self, idxs)
        return best_span, best_result

    def add_wikipedia_links(self, browser):
        """Call after resolved proper nouns."""
        '''
        NNP = filter(lambda x: x.isproper_noun, self.lexemes)
        found = []
        skip_to = -1
        for i in range(len(NNP)):
            if i < skip_to:
                continue
            skip_to = -1
            lex = NNP[i]
            todo = [Span(self, [lex.idx])]
            j = i+1
            k = lex.idx + 1
            while j < len(NNP) and self.lexemes[k].word in ['for', 'and', 'of'] and NNP[j].idx == k+1:
                todo.append(Span(self, [x for x in range(lex.idx, k + 2)]))
                j += 1
                k += 2
            retry = True
            allresults = []
            while skip_to < 0 and (retry or len(allresults) != 0):
                allresults.reverse()
                while len(todo):
                    c = todo.pop()
                    if retry:
                        result = c.search_wikipedia(browser=browser)
                        allresults.append(result)
                    else:
                        result = allresults.pop()
                    if result is not None:
                        subspan, bresult = self.get_subspan_from_wiki_search(c, result, title_only=retry)
                        if subspan is not None:
                            # Only checking first result
                            found.append((c, bresult))
                            if len(c) > 1 and c[-1].idx in subspan.indexes():
                                skip_to = j+1
                            break
                if not retry:
                    break
                retry = False

        recalc_nnps = False
        for f in itertools.ifilter(lambda x: len(x[0]) > 1, found):
            # Proper nouns separated by for|of|and
            nspan = f[0]
            hds = nspan.get_head_span()
            if len(hds) != 1:
                nspan.clear()
                _logger.info('Multi-headed proper noun discarded (%s), hds=(%s)', nspan.text, hds.text)
                continue
            if not hds[0].idx in self.i2c:
                c = Constituent(nspan, ct.CONSTITUENT_NP)
                self.i2c[hds[0]] = c
                self.constituents.append(c)
            ref = nspan[0].refs[0]
            for lex in nspan[1::2]:
                lex.refs = [ref]
                lex.drs = DRS([], [])
            rs = []
            for lex in nspan[2::2]:
                assert lex.isproper_noun
                rs.append((lex.refs[0], ref))
            self.final_prod.rename_vars(rs)
            recalc_nnps = True

        # Attach wiki pages
        for f in found:
            # We clear multiheaded entries
            if len(f[0]) > 0:
                f[0][0].set_wiki_entry(f[1])

        if recalc_nnps:
            self.constituents = sorted(set(self.constituents))
            self.map_heads_to_constituents()
            self.resolve_proper_names()

        # TODO: Add wiki entry to local search engine - like indri from lemur project
        '''

## @ingroup gfn
def process_ccg_pt(pt, options=0, browser=None):
    """Process the CCG parse tree.

    Args:
        pt: The parse tree returned from marbles.ie.drt.parse.parse_ccg_derivation().
        options: None or marbles.ie.drt.compose.CO_REMOVE_UNARY_PROPS to simplify propositions.
        browser: Headless browser used for scraping.

    Returns:
        A Ccg2Drs instance. Call Ccg2Drs.get_drs() to obtain the DRS.

    See Also:
        marbles.ie.drt.parse.parse_ccg_derivation()
    """
    if pt is None:
        return None
    ccg = Ccg2Drs(options | CO_FAST_RENAME)
    if future_string != unicode:
        pt = pt_to_utf8(pt)
    ccg.build_execution_sequence(pt)
    ccg.create_drs()
    ccg.resolve_proper_names()
    ccg.fixup_possessives()
    ccg.post_create_fixup()
    if 0 == (options & CO_NO_WIKI_SEARCH):
        ccg.add_wikipedia_links(browser)
    ccg.final_rename()
    # TODO: resolve anaphora
    return ccg


## @ingroup gfn
def pt_to_ccg_derivation(pt, fmt=True):
    """Process the CCG parse tree, add predicate argument tags, and return the ccgbank string.

    Args:
        pt: The parse tree returned from marbles.ie.drt.parse.parse_ccg_derivation().
        fmt: If True format for pretty print.
    Returns:
        A string
    """
    if future_string != unicode:
        pt = pt_to_utf8(pt)
    ccg = Ccg2Drs()
    ccg.build_execution_sequence(pt)
    s = ccg.get_predarg_ccgbank(fmt)
    return s


## @ingroup gfn
def extract_lexicon_from_pt(pt, dictionary=None, uid=None):
    """Extract the lexicon and templates from a CCG parse tree.

    Args:
        pt: The parse tree returned from marbles.ie.drt.parse.parse_ccg_derivation().
        dictionary: An optional dictionary of a existing lexicon.
        uid: A unique identifier string for the sentence.
    Returns:
        A dictionary of functor instances.
    """

    if future_string != unicode:
        pt = pt_to_utf8(pt)
    if dictionary is None:
        dictionary = map(lambda x: {}, [None]*27)
    if uid is None:
        uid = ''

    stk = [pt]
    while len(stk) != 0:
        pt = stk.pop()
        if pt[-1] == 'T':
            stk.extend(pt[1:-1])
        else:
            # Lexeme will infer template if it does not exist in MODEL
            lexeme = Lexeme(category=pt[0], word=pt[1], pos_tags=pt[2:4])
            if len(lexeme.stem) == 0 or lexeme.category.isatom or lexeme.category in [CAT_LRB, CAT_RRB, CAT_LQU, CAT_RQU]:
                continue

            if lexeme.category.ismodifier and len(set(lexeme.category.extract_unify_atoms(False))) == 1:
                continue

            N = lexeme.stem[0].upper()
            if N not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                N = '@'

            idx = ord(N) - 0x40
            template = lexeme.get_template()
            if template is None:
                continue
            fn = lexeme.get_production(Sentence([lexeme],[]), options=CO_NO_VERBNET)
            if lexeme.drs is None or lexeme.drs.isempty or len(fn.lambda_refs) == 0:
                continue

            atoms = template.predarg_category.extract_unify_atoms(False)
            refs = fn.get_unify_scopes(False)
            # This will rename lexeme.drs
            fn.rename_vars(zip(refs, map(lambda x: DRSRef(x.signature), atoms)))
            rel = DRSRelation(lexeme.stem)
            c = filter(lambda x: isinstance(x, Rel) and x.relation == rel, lexeme.drs.conditions)
            if len(c) == 1:
                c = future_string(c[0]) + ': ' + template.predarg_category.signature
                di = dictionary[idx].setdefault(lexeme.stem, {})
                si = di.setdefault(c, set())
                si.add(uid)

    return dictionary

