# -*- coding: utf-8 -*-
"""CCG to DRS Production Generator"""

from __future__ import unicode_literals, print_function

import collections
import itertools
import logging

import numpy as np

from marbles.ie.ccg import *
from marbles.ie.ccg.model import MODEL
from marbles.ie.ccg.utils import pt_to_utf8
from marbles.ie.core import constituent_types as ct
from marbles.ie.core.constants import *
from marbles.ie.core.sentence import Sentence, Span, Constituent
from marbles.ie.drt.common import DRSVar
from marbles.ie.drt.drs import DRS, DRSRef, Rel, DRSRelation
from marbles.ie.drt.utils import remove_dups
from marbles.ie.semantics.compose import ProductionList, FunctorProduction, DrsProduction, identity_functor
from marbles.ie.semantics.lexeme import Lexeme
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
    templ = MODEL.lookup(category)
    if templ is None:
        if category.isfunctor:
            if category != CAT_CONJ_CONJ and category != CAT_CONJCONJ \
                    and not category.result_category().isatom and not category.argument_category().isatom:
                templ = MODEL.infer_template(category)
                if templ is not None:
                    return templ.create_empty_functor()
            elif category.result_category().can_unify(category.argument_category()):
                return identity_functor(category)
            else:
                return identity_functor(category, [DRSRef('x2'), DRSRef('x1')])
    else:
        return templ.create_empty_functor()
    return None


def vntype_from_category(category):
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
        elif category.has_any_features(FEATURE_QEM | FEATURE_Q | FEATURE_WQ):
            return ct.CONSTITUENT_SQ
        else:
            return ct.CONSTITUENT_S
    return None


class AbstractOperand(object):

    def __init__(self, idx, depth):
        self.idx = idx
        self.depth = depth

    @property
    def category(self):
        raise NotImplementedError


class PushOp(AbstractOperand):

    def __init__(self, lexeme, idx, depth):
        super(PushOp, self).__init__(idx, depth)
        self.lexeme = lexeme

    def __repr__(self):
        return b'<PushOp>:(%s, %s, %s)' % (safe_utf8_encode(self.lexeme.stem), self.lexeme.category, self.lexeme.pos)

    @property
    def category(self):
        return self.lexeme.category


class ExecOp(AbstractOperand):

    def __init__(self, idx, sub_ops, head, result_category, rule, lex_range, op_range, depth):
        super(ExecOp, self).__init__(idx, depth)
        self.rule = rule
        self.result_category = result_category
        self.sub_ops = sub_ops
        self.head = head
        self.lex_range = lex_range
        self.op_range = op_range

    def __repr__(self):
        return b'<ExecOp>:(%d, %s %s)' % (len(self.sub_ops), self.rule, self.category)

    @property
    def category(self):
        return self.result_category


CcgArgSep = re.compile(r'/|\\')
TType = re.compile(r'((?:[()/\\]|(?:(?:S|NP|N)(?:\[[Xa-z]+\])?)|conj|[A-Z]+\$?|-[A-Z]+-)*)')
LPosType = re.compile(r'([A-Z$:-]+|[.,:;])(?=\s+[^>\s]+\s+[^>\s]+(?:\s|[>]))')
LWord = re.compile(r'[^>\s]+(?=\s)')
CcgComplexTypeBegin = re.compile(r'([()/\\]|(?:(?:S|NP|N)(?:\[[Xa-z]+\])?)|conj|[A-Z]+|[.,:;])+(?=\s)')
CcgComplexTypeEnd = re.compile(r'([()/\\]|(?:(?:S|NP|N)(?:\[[Xa-z]+\])?)|conj|[A-Z]+|[.,:;]|_\d+)+(?=[>])')
PosInt = re.compile(r'\d+')


class Ccg2Drs(Sentence):
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
        self.exeque = []
        self.depth = -1
        self.final_prod = None

    @dispatchmethod(dispatchmap, RL_TCL_UNARY)
    def _dispatch_lunary(self, op, stk):
        if len(op.sub_ops) == 2:
            assert len(stk) >= 2
            unary = MODEL.lookup_unary(op.category, op.sub_ops[0].category)
            if unary is None and op.category.ismodifier and op.category.result_category() == op.sub_ops[0].category:
                unary = MODEL.infer_unary(op.category)
            assert unary is not None
            fn = self.rename_vars(unary.get())
            ucat = fn.category
            fn.set_options(self.options)
            d2 = stk.pop()
            d1 = stk.pop()
            stk.append(d1)
            self._dispatch_ba(op, stk)

            nlst = ProductionList()
            nlst.set_options(self.options)
            nlst.set_category(op.category)
            nlst.push_right(stk.pop())
            nlst.push_right(d2)
            stk.append(nlst.flatten().unify())
        else:
            unary = MODEL.lookup_unary(op.category, op.sub_ops[0].category)
            if unary is None and op.category.ismodifier and op.category.result_category() == op.sub_ops[0].category:
                unary = MODEL.infer_unary(op.category)
            assert unary is not None
            fn = self.rename_vars(unary.get())
            ucat = fn.category
            fn.set_options(self.options)
            stk.append(fn)
            self._dispatch_ba(op, stk)
        self._mark_if_adjunct(ucat, stk[-1])

    @dispatchmethod(dispatchmap, RL_TCR_UNARY)
    def _dispatch_runary(self, op, stk):
        assert len(op.sub_ops) == 2
        assert len(stk) >= 2
        unary = MODEL.lookup_unary(op.category, op.sub_ops[1].category)
        if unary is None and op.category.ismodifier and op.category.result_category() == op.sub_ops[1].category:
            unary = MODEL.infer_unary(op.category)
        assert unary is not None
        fn = self.rename_vars(unary.get())
        ucat = fn.category
        fn.set_options(self.options)
        stk.append(fn)
        self._dispatch_ba(op, stk)

        nlst = ProductionList()
        nlst.set_options(self.options)
        nlst.set_category(op.category)

        d1 = stk.pop()
        d2 = stk.pop()
        markadjunct = True
        if d2.category is CAT_CONJ:
            if d1.category.test_returns_entity_modifier():
                # FIXME: this is a hack to get proper nouns separated by 'and' merged
                d2.rename_vars(zip(d2.lambda_refs, reversed(d1.lambda_refs)))
            elif op.category.ismodifier and op.category.simplify().test_return(CAT_S_NP) and \
                    (op.category.test_return(d1.category) or op.category.test_return(d2.category)):
                markadjunct = False


        nlst.push_right(d1)
        nlst.push_right(d2)
        stk.append(nlst.flatten().unify())
        if markadjunct:
            self._mark_if_adjunct(ucat, stk[-1])

    @dispatchmethod(dispatchmap, RL_TC_CONJ)
    def _dispatch_tcconj(self, op, stk):
        # Special type change rules. See section 3.7-3.8 of LDC 2005T13 manual.
        if len(op.sub_ops) == 2:
            fn = self.rename_vars(safe_create_empty_functor(op.category))
            if op.sub_ops[0].category == CAT_CONJ:
                vp_or_np = stk.pop()
                d = stk.pop()
            else:
                d = stk.pop()
                vp_or_np = stk.pop()

            nlst = ProductionList()
            nlst.push_right(fn.type_change_np_snp(vp_or_np))
            nlst.push_right(d)
            nlst.set_options(self.options)
            nlst.set_category(op.category)
            stk.append(nlst.flatten().unify())
        else:
            fn = self.rename_vars(safe_create_empty_functor(op.category))
            vp_or_np = stk.pop()
            stk.append(fn.type_change_np_snp(vp_or_np))

    @dispatchmethod(dispatchmap, RL_TC_ATOM)
    def _dispatch_tcatom(self, op, stk):
        assert len(op.sub_ops) == 1
        # Special rule to change atomic type
        fn = self.rename_vars(identity_functor(Category.combine(op.category, '\\', stk[-1].category)))
        fn.set_options(self.options)
        stk.append(fn)
        self._dispatch_ba(op, stk)  # backward application

    @dispatchmethod(dispatchmap, RL_TYPE_RAISE)
    def _dispatch_type_raise(self, op, stk):
        ## Forward   X:g => T/(T\X): λxf.f(g)
        ## Backward  X:g => T\(T/X): λxf.f(g)
        assert len(op.sub_ops) == 1
        f = self.rename_vars(safe_create_empty_functor(op.category))
        g = stk.pop()
        stk.append(f.type_raise(g))

    @dispatchmethod(dispatchmap, RL_FA)
    def _dispatch_fa(self, op, stk):
        # Forward application.
        d = stk.pop()   # arg1
        fn = stk.pop()  # arg0
        prevcat = fn.category
        stk.append(self._update_constituents(fn.apply(d), prevcat))

    @dispatchmethod(dispatchmap, RL_BA)
    def _dispatch_ba(self, op, stk):
        # Backward application.
        fn = stk.pop()   # arg1
        d = stk.pop()    # arg0
        prevcat = fn.category
        stk.append(self._update_constituents(fn.apply(d), prevcat))

    @dispatchmethod(dispatchmap, RL_FC, RL_FX)
    def _dispatch_fc(self, op, stk):
        # CALL[X/Y](Y|Z)
        # Forward Composition           X/Y:f Y/Z:g => X/Z: λx􏰓.f(g(x))
        # Forward Crossing Composition  X/Y:f Y\Z:g => X\Z: λx􏰓.f(g(x))
        g = stk.pop()   # arg1
        f = stk.pop()   # arg0
        stk.append(f.compose(g))

    @dispatchmethod(dispatchmap, RL_GFC, RL_GFX)
    def _dispatch_gfc(self, op, stk):
        # CALL[X/Y](Y|Z)$
        # Generalized Forward Composition           X/Y:f (Y/Z)/$ => (X/Z)/$
        # Generalized Forward Crossing Composition  X/Y:f (Y\Z)$: => (X\Z)$
        g = stk.pop()   # arg1
        f = stk.pop()   # arg0
        stk.append(f.generalized_compose(g))

    @dispatchmethod(dispatchmap, RL_BC, RL_BX)
    def _dispatch_bc(self, op, stk):
        # CALL[X\Y](Y|Z)
        # Backward Composition          Y\Z:g X\Y:f => X\Z: λx􏰓.f(g(x))
        # Backward Crossing Composition Y/Z:g X\Y:f => X/Z: λx􏰓.f(g(x))
        f = stk.pop()
        g = stk.pop()
        stk.append(f.compose(g))

    @dispatchmethod(dispatchmap, RL_GBC, RL_GBX)
    def _dispatch_gbc(self, op, stk):
        # CALL[X\Y](Y|Z)$
        # Generalized Backward Composition          (Y\Z)$  X\Y:f => (X\Z)$
        # Generalized Backward Crossing Composition (Y/Z)/$ X\Y:f => (X/Z)/$
        f = stk.pop()
        g = stk.pop()
        stk.append(f.generalized_compose(g))

    @dispatchmethod(dispatchmap, RL_FS, RL_FXS)
    def _dispatch_fs(self, op, stk):
        # CALL[(X/Y)|Z](Y|Z)
        # Forward Substitution          (X/Y)/Z:f Y/Z:g => X/Z: λx􏰓.fx􏰨(g􏰨(x􏰩􏰩))
        # Forward Crossing Substitution (X/Y)\Z:f Y\Z:g => X\Z: λx􏰓.fx􏰨(g􏰨(x􏰩􏰩))
        g = stk.pop()   # arg1
        f = stk.pop()   # arg0
        stk.append(f.substitute(g))

    @dispatchmethod(dispatchmap, RL_BS, RL_BXS)
    def _dispatch_bs(self, op, stk):
        # CALL[(X\Y)|Z](Y|Z)
        # Backward Substitution             Y\Z:g (X\Y)\Z:g => X/Z: λx􏰓.fx􏰨(g􏰨(x􏰩􏰩))
        # Backward Crossing Substitution    Y/Z:g (X\Y)/Z:f => X/Z: λx􏰓.fx􏰨(g􏰨(x􏰩􏰩))
        f = stk.pop()   # arg1
        g = stk.pop()   # arg0
        stk.append(f.substitute(g))

    @dispatchmethod(dispatchmap, RL_LCONJ, RL_RCONJ)
    def _dispatch_conj(self, op, stk):
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
        stk.append(self._update_constituents(d, d.category))

    @dispatchmethod(dispatchmap, RL_RPASS, RL_LPASS, RL_RNUM)
    def _dispatch_pass(self, op, stk):
        d = ProductionList()
        d.set_options(self.options)
        d.set_category(op.category)
        for i in range(len(op.sub_ops)):
            d.push_left(stk.pop())
        if d.contains_functor:
            # Bit of a hack, flatten() gets rid of empty productions
            stk.append(self._update_constituents(d.flatten().unify(), d.category))
        else:
            stk.append(self._update_constituents(d.unify(), d.category))

    @default_dispatchmethod(dispatchmap)
    def _dispatch_default(self, op, stk):
        # All rules must have a handler
        assert False

    def _dispatch(self, op, stk):
        """Dispatch a rule.

        Args:
            op: The ExecOp. The dispatch is based on op.rule.
            stk. The execution stack.
        """
        method = self.dispatchmap.lookup(op.rule)
        method(self, op, stk)

    def _add_constituent(self, c):
        hd = c.get_head().idx
        if hd in self.i2c:
            cdel = self.i2c[hd]
            if cdel.vntype is not ct.CONSTITUENT_ADJP or c.vntype is not ct.CONSTITUENT_ADVP \
                    or c.span != cdel.span:
                self.constituents = filter(lambda x: x is not cdel, self.constituents)
            # else keep ADJP
        self.i2c[hd] = c
        self.constituents.append(c)

    def _pop_constituent(self):
        c = self.constituents.pop()
        del self.i2c[c.get_head().idx]
        return c

    def _mark_if_adjunct(self, ucat, d):
        # ucat is the unary type change catgory
        # d is the result of the type change
        for lex in d.span:
            lex.mask |= RT_ADJUNCT
        c = Constituent(d.span.clone(), ct.CONSTITUENT_ADJP if ucat.argument_category() == CAT_AP else ct.CONSTITUENT_ADVP)
        # Cannot have a proper noun as head of an adverbial phrase
        if not c.get_head().isproper_noun:
            self._add_constituent(c)

    def _update_constituents(self, d, cat_before_rule):
        vntype = None

        if isinstance(d, (FunctorProduction, DrsProduction)):
            if d.category == CAT_NP and 0 == (self.options & CO_NO_VERBNET):
                refs = set()
                for lex in d.span:
                    # Adverbial phrases are removed from NP's at a later point
                    if 0 == (lex.mask & (RT_ADJUNCT | RT_PP)):
                        refs = refs.union(lex.refs)
                vntype = ct.CONSTITUENT_NP if len(refs) == 1 else None
            elif cat_before_rule is CAT_ESRL_PP:
                vntype = ct.CONSTITUENT_PP
                if Constituent(d.span, vntype).get_head().pos != POS_PREPOSITION:
                    vntype = None
            elif cat_before_rule is CAT_PP_ADVP and d.category is CAT_VP_MOD and not d.span.isempty:
                hd = Constituent(d.span, ct.CONSTITUENT_ADVP).get_head()
                if hd.pos == POS_PREPOSITION and hd.stem in ['for']:
                    vntype = ct.CONSTITUENT_ADVP
            else:
                vntype = vntype_from_category(d.category)
                if vntype is None and cat_before_rule.argument_category().remove_features() == CAT_N \
                        and (cat_before_rule.test_return(CAT_VPMODX) or cat_before_rule.test_return(CAT_VP_MODX)):
                    # (S\NP)/(S\NP)/N[X]
                    vntype = ct.CONSTITUENT_NP
                elif vntype is None and cat_before_rule.argument_category() in [CAT_VPb, CAT_VPto] and \
                        cat_before_rule.result_category().ismodifier and \
                        cat_before_rule.result_category().test_return(CAT_S_NP):
                    # Handle categories like ((S\NP)\(S\NP))/(S[b]\NP) for TO in 'has done more than its share to popularize'
                    vntype = ct.CONSTITUENT_SINF

            if vntype is not None \
                    and ((0 == (self.options & CO_NO_VERBNET) \
                                  and vntype not in [ct.CONSTITUENT_VP, ct.CONSTITUENT_S,
                                                     ct.CONSTITUENT_SEM, ct.CONSTITUENT_SDCL,
                                                     ct.CONSTITUENT_SQ]) \
                     or vntype is not ct.CONSTITUENT_TO):
                c = Constituent(d.span, vntype)
                #if vntype is ct.CONSTITUENT_NP:
                    #for lex in d.span:
                    #    lex.mask |= RT_PP

                if 0 == (self.options & CO_NO_VERBNET):
                    while len(self.constituents) != 0 and self.constituents[-1].vntype is c.vntype \
                            and self.constituents[-1] in c:
                        cc = self._pop_constituent()
                        if cc.span == c.span and c.vntype == ct.CONSTITUENT_VP and cc.vntype in \
                                [ct.CONSTITUENT_SINF, ct.CONSTITUENT_SDCL, ct.CONSTITUENT_SEM,
                                 ct.CONSTITUENT_SQ, ct.CONSTITUENT_S]:
                            c = cc
                            break
                elif c.vntype == ct.CONSTITUENT_VP and len(self.constituents) != 0:
                    cc = self.constituents[-1]
                    if cc.span == c.span and cc.vntype in \
                            [ct.CONSTITUENT_SINF, ct.CONSTITUENT_SDCL, ct.CONSTITUENT_SEM,
                             ct.CONSTITUENT_SQ, ct.CONSTITUENT_S]:
                        # Keep vntype
                        return
                self._add_constituent(c)
            elif vntype is ct.CONSTITUENT_TO and len(self.constituents) != 0:
                c = self._pop_constituent()
                if c.vntype is ct.CONSTITUENT_SINF and c.span in d.span and len(c.span) == len(d.span) - 1:
                    c.span = d.span
                self._add_constituent(c)
        return d

    def _refine_constituents(self):

        # Constituents ordering (see span) for sentence AB, AB < A < B
        constituents = sorted(self.constituents)

        # Merge adjacent adjuncts
        cadvp = filter(lambda x: x.vntype is ct.CONSTITUENT_ADVP, reversed(constituents))
        while len(cadvp) > 1:
            c1 = cadvp.pop()
            c2 = cadvp.pop()
            hd1 = c1.get_head()
            hd2 = c1.get_head()
            if (c1.span[-1].idx + 1) == c2.span[0].idx and (hd1.head in c2.span or hd2.head in c1.span):
                c1.span = c1.span.union(c2.span)
                c2.span.clear()
                c2.vntype = None
                cadvp.append(c1)
            elif (c1.span[-1].idx + 1) == c2.span[0].idx and hd1.head == hd2.head:
                ctmp = Constituent(c1.span.union(c2.span), ct.CONSTITUENT_ADVP)
                if len(ctmp.get_head(multihead=True)) == 1:
                    c1.span = ctmp.span
                    c2.span.clear()
                    c2.vntype = None
                    cadvp.append(c1)
                else:
                    cadvp.append(c2)

            else:
                cadvp.append(c2)

        # Merge adjacent adjuncts
        cadvp = filter(lambda x: x.vntype is ct.CONSTITUENT_ADJP, reversed(constituents))
        while len(cadvp) > 1:
            c1 = cadvp.pop()
            c2 = cadvp.pop()
            hd1 = c1.get_head()
            hd2 = c1.get_head()
            if (c1.span[-1].idx + 1) == c2.span[0].idx and (hd1.head in c2.span or hd2.head in c1.span):
                c1.span = c1.span.union(c2.span)
                c2.span.clear()
                c2.vntype = None
                cadvp.append(c1)
            elif (c1.span[-1].idx + 1) == c2.span[0].idx and hd1.head == hd2.head:
                ctmp = Constituent(c1.span.union(c2.span), ct.CONSTITUENT_ADJP)
                if len(ctmp.get_head(multihead=True)) == 1:
                    c1.span = ctmp.span
                    c2.span.clear()
                    c2.vntype = None
                    cadvp.append(c1)
                else:
                    cadvp.append(c2)

            else:
                cadvp.append(c2)

        for c in itertools.ifilter(lambda x: x.vntype is ct.CONSTITUENT_ADVP, constituents):
            mask = reduce(lambda x, y: x | y, itertools.imap(lambda z: z.mask, c.span))
            if 0 == (mask & RT_EVENT):
                for x in c.span:
                    x.mask &= ~RT_ADJUNCT
                c.vntype = ct.CONSTITUENT_NP
            elif len(c.span) == 1:
                c.vntype = None
                for x in c.span:
                    x.mask &= ~RT_ADJUNCT
                c.span.clear()

        constituents = filter(lambda x: x.vntype is not None, constituents)
        self.i2c = {}

        # Finalize NP constituents, split VP's
        to_remove = set()
        constituents = sorted(set(constituents))

        allspan = Span(self)
        lastwiki_result = None
        lastwiki_idx = 0
        for i in range(len(constituents)):
            c = constituents[i]
            allspan = allspan.union(c.span)
            # FIXME: rank wikipedia search results
            if all(map(lambda x: x.category in [CAT_DETERMINER, CAT_POSSESSIVE_PRONOUN, CAT_PREPOSITION] or
                            x.pos in POS_LIST_PERSON_PRONOUN or x.pos in POS_LIST_PUNCT or
                            x.pos in [POS_PREPOSITION, POS_DETERMINER], c.span)) or c.span.isempty:
                to_remove.add(i)
                continue
            elif c.vntype is not ct.CONSTITUENT_NP:
                continue

            if 0 != (self.options & CO_NO_WIKI_SEARCH):
                continue

        # Remove irrelevent entries
        if len(to_remove) != 0:
            filtered_constituents = [constituents[i] for i in
                                     filter(lambda k: k not in to_remove, range(len(constituents)))]
            constituents = filtered_constituents

        # And finally remove any constituent that contains only punctuation
        constituents = filter(lambda x: len(x.span) != 1 or not x.span[0].ispunct, constituents)

        # If a constituent head and its category is N/N or a noun modifier and it is an RT_ATTRIBUTE
        # then all direct descendents are also attributes
        for c in constituents:
            hd = c.get_head()
            if 0 != (hd.mask & RT_ATTRIBUTE) and (hd.category in [CAT_ADJECTIVE, CAT_AP]
                                                  or hd.category.test_returns_entity_modifier()):
                for lex in c.span:
                    lex.mask |= RT_ATTRIBUTE

        # And finally make sure each constituent has one head. Trim if necessary
        # Lexeme head index is always in constituent so use it map between the two.
        i2c = {}
        stk = [i for i in reversed(range(len(constituents)))]
        resort = False
        while len(stk) != 0:
            i = stk.pop()
            ci = constituents[i]
            lexhd = ci.get_head()
            if lexhd is None:
                continue    # empty
            if lexhd.idx in i2c:
                resort = True
                j = i2c[lexhd.idx]
                cj = constituents[j]
                if ci.span == cj.span:
                    if ci.vntype in [ct.CONSTITUENT_PP, ct.CONSTITUENT_NP] \
                            and cj.vntype not in [ct.CONSTITUENT_PP, ct.CONSTITUENT_NP]:
                        # discard ci
                        ci.span.clear()
                    elif (cj.vntype in [ct.CONSTITUENT_PP, ct.CONSTITUENT_NP]
                            and ci.vntype not in [ct.CONSTITUENT_PP, ct.CONSTITUENT_NP]) \
                            or (ci.vntype == ct.CONSTITUENT_PP
                                and cj.vntype == ct.CONSTITUENT_NP) \
                            or (ci.vntype == ct.CONSTITUENT_ADVP
                                and ci.vntype in [ct.CONSTITUENT_VP,
                                                  ct.CONSTITUENT_SINF,
                                                  ct.CONSTITUENT_TO]):
                        # discard cj
                        cj.span.clear()
                        i2c[lexhd.idx] = i
                    else:
                        # discard ci
                        ci.span.clear()
                    continue
                elif ci.span in cj.span:
                    tmpcj = Constituent(cj.span.difference(ci.span), cj.vntype)
                    tmphds = tmpcj.get_head(multihead=True)
                    if len(tmphds) == 1:
                        cj.span = tmpcj.span
                    else:
                        ci.span.clear()
                elif cj.span in ci.span:
                    tmpci = Constituent(ci.span.difference(cj.span),cj.vntype)
                    tmphds = tmpci.get_head(multihead=True)
                    if len(tmphds) == 1:
                        ci.span = tmpci.span
                    else:
                        cj.span.clear()
                else:
                    assert False
                del i2c[lexhd.idx]
                stk.append(i)
                stk.append(j)
            else:
                i2c[lexhd.idx] = i

        if resort:
            constituents = sorted(set(filter(lambda c: not c.span.isempty, constituents)))

        # And finally set constituent heads and map lexeme heads to constituents
        self.constituents = constituents
        self.map_heads_to_constituents()

    def create_drs(self):
        """Create a DRS from the execution queue. Must call build_execution_sequence() first."""
        # First create all productions up front
        prods = [None] * len(self.lexemes)
        for i in range(len(self.lexemes)):
            lexeme = self.lexemes[i]
            if lexeme.category.ispunct:
                prod = DrsProduction([], [], category=lexeme.category, span=Span(self))
                prod.set_lambda_refs([DRSRef(DRSVar('x', self.xid+1))])
                self.xid += 1
                prod.set_options(self.options)
            elif lexeme.category in [CAT_LRB, CAT_RRB, CAT_LQU, CAT_RQU]:
                prod = DrsProduction([], [], category=CAT_EMPTY, span=Span(self))
                prod.set_lambda_refs([DRSRef(DRSVar('x', self.xid+1))])
                self.xid += 1
            else:
                prod = self.rename_vars(lexeme.get_production(self, self.options))
            prod.set_options(self.options)
            prods[i] = prod
        # TODO: Defer special handling of proper nouns

        # Process exec queue
        stk = []
        for op in self.exeque:
            if isinstance(op, PushOp):
                stk.append(prods[op.lexeme.idx])
            else:
                # ExecOp dispatch based on rule
                self._dispatch(op, stk)

            if not (stk[-1].verify() and stk[-1].category.can_unify(op.category)):
                pass

            assert stk[-1].verify() and stk[-1].category.can_unify(op.category)
            assert op.category.get_scope_count() == stk[-1].get_scope_count(), "result-category=%s, prod=%s" % \
                                                                               (op.category, stk[-1])
        # Get final DrsProduction
        assert len(stk) == 1
        d = stk[0]
        if d.isfunctor and d.isarg_left and d.category.argument_category().isatom:
            d = d.apply_null_left().unify()
        self.final_prod = d

        # Refine constituents and we are done
        self._refine_constituents()

    def get_vn_frames(self):
        i2c = {}
        attribs = set()
        # find head of the constituents
        for c in self.constituents:
            hd = c.get_head()
            i2c[hd.idx] = c
            if 0 != (hd.mask & RT_ATTRIBUTE):
                attribs.add(hd.idx)
        # If a head is an RT_ATTRIBUTE then all direct NP descendents are also attributes

    def resolve_proper_names(self):
        """Merge proper names."""

        to_remove = Span(self)
        for c in self.constituents:
            c.span = c.span.difference(to_remove)
            if c.span.isempty:
                continue
            if c.vntype is ct.CONSTITUENT_NP:
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
                    # Preserve heads
                    hdspan = c.span[s:e+1].get_head_span()
                    if len(hdspan) > 1:
                        global _logger
                        # Check if we can find a common head
                        sptmp = c.span[s:e+1]
                        hd = hdspan[0]
                        sptmp.add(hd.head)
                        while len(sptmp.get_head_span()) > 1 and not hd.isroot:
                            hd = self.lexemes[hd.head]
                            sptmp.add(hd.head)
                        if len(sptmp.get_head_span()) > 1:
                            dtree = self.get_dependency_tree()
                            _logger.info('resolve_proper_name (%s) in constituent %s(%s) multi headed\nsentence: %s\n%s',
                                         hdspan.text, c.vntype.signature, c.span.text, self.get_span().text,
                                         self.get_dependency_tree_as_string(dtree))
                            continue
                    lexeme = hdspan[0]
                    ref = lexeme.refs[0]
                    word = '-'.join([c.span[i].word for i in range(s, e+1)])
                    stem = '-'.join([c.span[i].stem for i in range(s, e+1)])
                    fca = lexeme.drs.find_condition(Rel(lexeme.stem, [ref]))
                    if fca is None:
                        continue
                    fca.cond.relation.rename(stem)
                    lexeme.stem = stem
                    lexeme.word = word
                    to_remove = to_remove.union(Span(self, filter(lambda y: y != lexeme.idx, [x.idx for x in c.span[s:e + 1]])))

        if not to_remove.isempty:
            # Python 2.x does not support nonlocal keyword for the closure
            class context:
                i = 0
            def counter(inc=1):
                idx = context.i
                context.i += inc
                return idx

            # Remove constituents and remap indexes.
            context.i = 0
            self.constituents = map(lambda c: Constituent(c.span.difference(to_remove), c.vntype, c.chead),
                                    self.constituents)
            idxs_to_del = set(filter(lambda i: self.constituents[i].span.isempty, range(len(self.constituents))))
            if len(idxs_to_del) != 0:
                idxmap = map(lambda x: -1 if x in idxs_to_del else counter(), range(len(self.constituents)))
                self.constituents = map(lambda y: self.constituents[y], filter(lambda x: idxmap[x] >= 0,
                                                                               range(len(idxmap))))
                for c in self.constituents:
                    if c.chead >= 0:
                        c.chead = idxmap[c.chead]
                        assert c.chead >= 0

            # Remove lexemes and remap indexes.
            context.i = 0
            idxs_to_del = set(to_remove.get_indexes())

            # Find the sentence head
            sentence_head = 0
            while self.lexemes[sentence_head].head != sentence_head:
                sentence_head = self.lexemes[sentence_head].head

            # Only allow deletion if it has a single child, otherwise we get multiple sentence heads
            if sentence_head in idxs_to_del and len(filter(lambda lex: lex.head == sentence_head, self.lexemes)) != 2:
                idxs_to_del.remove(sentence_head)

            # Reparent heads marked for deletion
            for lex in itertools.ifilter(lambda x: x.idx not in idxs_to_del, self.lexemes):
                lasthead = -1
                while lex.head in idxs_to_del and lex.head != lasthead:
                    lasthead = lex.head
                    lex.head = self.lexemes[lex.head].head
                if lex.head in idxs_to_del:
                    # New head for sentence
                    lex.head = lex.idx

            idxmap = map(lambda x: -1 if x in idxs_to_del else counter(), range(len(self.lexemes)))
            for c in self.constituents:
                c.span = Span(self, map(lambda y: idxmap[y],
                                        filter(lambda x: idxmap[x] >= 0, c.span.get_indexes())))
            self.lexemes = map(lambda y: self.lexemes[y], filter(lambda x: idxmap[x] >= 0, range(len(idxmap))))
            for i in range(len(self.lexemes)):
                lexeme = self.lexemes[i]
                lexeme.idx = i
                lexeme.head = idxmap[lexeme.head]
                assert lexeme.head >= 0

            if self.final_prod is not None:
                pspan = Span(self, map(lambda y: idxmap[y],
                                       filter(lambda x: idxmap[x] >= 0, self.final_prod.span.get_indexes())))
                self.final_prod.span = pspan

            self.map_heads_to_constituents()

    def get_drs(self):
        refs = []
        conds = []
        for w in self.lexemes:
            if w.drs:
                refs.extend(w.drs.universe)
                conds.extend(w.drs.conditions)

        return DRS(refs, conds)

    def final_rename(self):
        """Rename to ensure:
            - indexes progress is 1,2,...
            - events are tagged e, others x
        """
        vx = set(filter(lambda x: not x.isconst, self.final_prod.variables))
        ors = filter(lambda x: x.var.idx < len(vx), vx)
        if len(ors) != 0:
            # Move names to > len(vx)
            mx = 1 + max([x.var.idx for x in vx])
            idx = [i+mx for i in range(len(ors))]
            rs = map(lambda x: (x[0], DRSRef(DRSVar(x[0].var.name, x[1]))), zip(ors, idx))
            self.final_prod.rename_vars(rs)
            vx = set(filter(lambda x: not x.isconst, self.final_prod.variables))

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
                # ensure events are prefixed 'e'
                rs.append((u, DRSRef(DRSVar('e', i))))
            else:
                rs.append((u, DRSRef(DRSVar('x', i))))

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
        if len(filter(lambda x: x.isconst, d.variables)) != 0:
            pass
        assert len(filter(lambda x: x.isconst, d.variables)) == 0
        v = set(filter(lambda x: not x.isconst, d.variables))
        xlimit = 0
        elimit = 0
        for i in range(10):
            if DRSRef(DRSVar('x', 1+i)) in v:
                xlimit = 1 + i
                if DRSRef(DRSVar('e', 1+i)) in v:
                    elimit = 1 + i
            elif DRSRef(DRSVar('e', 1+i)) in v:
                elimit = 1 + i
            else:
                break
        rs = []
        if self.xid == 0:
            self.xid = xlimit
        else:
            for i in range(xlimit):
                rs.append((DRSRef(DRSVar('x', 1+i)), DRSRef(DRSVar('x', 1+i+self.xid))))
            self.xid += xlimit
        if self.eid == 0:
            self.eid = elimit
        else:
            for i in range(elimit):
                rs.append((DRSRef(DRSVar('e', 1+i)), DRSRef(DRSVar('e', 1+i+self.eid))))
            self.eid += elimit
        if len(rs) != 0:
            rs.reverse()
            d.rename_vars(rs)
        return d

    def build_execution_sequence(self, pt):
        """Build the execution sequence from a ccg derivation's parse tree.

        Args:
            pt: The parse tree for a ccg derivation.
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
            op_begin = len(self.exeque)
            op_end = []
            for nd in pt[1:-1]:
                idxs.append(self.build_execution_sequence(nd))
                op_end.append(len(self.exeque)-1)

            assert count == len(idxs)
            # Ranges allow us to schedule work to a thread pool
            op_range = (op_begin, len(self.exeque))
            lex_range = (lex_begin, len(self.lexemes))

            if count == 2:
                subops = [self.exeque[op_end[0]], self.exeque[-1]]
                cats = map(lambda x: CAT_EMPTY if x.category in [CAT_LRB, CAT_RRB, CAT_LQU, CAT_RQU] else x.category,
                           subops)
                rule = get_rule(cats[0], cats[1], result)
                if rule is None:
                    rule = get_rule(cats[0].simplify(), cats[1].simplify(), result)
                    assert rule is not None

                # Head resolved to lexemes indexes
                self.lexemes[idxs[1-head]].head = idxs[head]
                self.exeque.append(ExecOp(len(self.exeque), subops, head, result, rule, lex_range, op_range,
                                          self.depth))
                self.depth -= 1
                return idxs[head]
            else:
                assert count == 1
                subops = [self.exeque[-1]]
                cats = map(lambda x: CAT_EMPTY if x.category in [CAT_LRB, CAT_RRB, CAT_LQU, CAT_RQU] else x.category,
                           subops)
                rule = get_rule(cats[0], CAT_EMPTY, result)
                if rule is None:
                    rule = get_rule(cats[0].simplify(), CAT_EMPTY, result)
                    assert rule is not None

                # No need to set head, Lexeme defaults to self is head
                self.exeque.append(ExecOp(len(self.exeque), subops, head, result, rule, lex_range, op_range,
                                          self.depth))
                self.depth -= 1
                return idxs[head]
        else:
            lexeme = Lexeme(Category.from_cache(pt[0]), pt[1], pt[2:4], len(self.lexemes))
            self.lexemes.append(lexeme)
            self.exeque.append(PushOp(lexeme, len(self.exeque), self.depth))
            self.depth -= 1
            return lexeme.idx

    def get_predarg_ccgbank(self, pretty):
        """Return a ccgbank representation with predicate-argument tagged categories. See LDC 2005T13 for details.

        Args:
            pretty: Pretty format, else one line string.

        Returns:
            A ccgbank string.
        """
        assert len(self.exeque) != 0 and len(self.lexemes) != 0
        assert isinstance(self.exeque[0], PushOp)

        # Process exec queue
        stk = collections.deque()
        sep = '\n' if pretty else ' '
        for op in self.exeque:
            indent = '  ' * op.depth if pretty else ''
            if isinstance(op, PushOp):
                # Leaf nodes contain 5 fields:
                # <L CCGcat mod_POS-tag orig_POS-tag word PredArgCat>
                if op.lexeme.category in [CAT_LRB, CAT_RRB, CAT_LQU, CAT_RQU]:
                    stk.append('%s(<L %s %s %s %s %s>)' % (indent, op.lexeme.category, op.lexeme.pos, op.lexeme.pos,
                                                           op.lexeme.word, op.lexeme.category))
                else:
                    template = op.lexeme.get_template()
                    if template is None:
                        stk.append('%s(<L %s %s %s %s %s>)' % (indent, op.lexeme.category, op.lexeme.pos, op.lexeme.pos,
                                                               op.lexeme.word, op.lexeme.category))
                    else:
                        stk.append('%s(<L %s %s %s %s %s>)' % (indent, op.lexeme.category, op.lexeme.pos, op.lexeme.pos,
                                                               op.lexeme.word, template.predarg_category))
            elif len(op.sub_ops) == 2:
                assert len(stk) >= 2
                if op.rule == RL_TCL_UNARY:
                    unary = MODEL.lookup_unary(op.category, op.sub_ops[0].category)
                    if unary is None and op.category.ismodifier and op.category.result_category() == op.sub_ops[0].category:
                        unary = MODEL.infer_unary(op.category)
                    assert unary is not None
                    template = unary.template
                    nlst = collections.deque()
                    # reverse order
                    nlst.append('%s(<T %s %d %d>' % (indent, op.category, 1, 2))
                    nlst.append(stk.pop())
                    nlst.append('%s  (<L %s %s %s %s %s>)' % (indent, template.clean_category, 'UNARY', 'UNARY',
                                                              '.UNARY', template.predarg_category))
                    nlst.append('%s)')
                    stk.append(sep.join(nlst))
                elif op.rule == RL_TCR_UNARY:
                    unary = MODEL.lookup_unary(op.category, op.sub_ops[1].category)
                    if unary is None and op.category.ismodifier and op.category.result_category() == op.sub_ops[1].category:
                        unary = MODEL.infer_unary(op.category)
                    assert unary is not None
                    template = unary.template
                    nlst = collections.deque()
                    nlst.append('%s(<T %s %d %d>' % (indent, op.category, 1, 2))
                    b = stk.pop()
                    a = stk.pop()
                    nlst.append(a)
                    nlst.append(b)
                    nlst.append('%s  (<L %s %s %s %s %s>)' % (indent, template.clean_category, 'UNARY', 'UNARY',
                                                              '.UNARY', template.predarg_category.signature))
                    nlst.append('%s)' % indent)
                    stk.append(sep.join(nlst))
                else:
                    nlst = collections.deque()
                    nlst.appendleft(stk.pop())  # arg1
                    nlst.appendleft(stk.pop())  # arg0
                    nlst.appendleft('%s(<T %s %d %d>' % (indent, op.category, op.head, 2))
                    nlst.append('%s)' % indent)
                    stk.append(sep.join(nlst))
            elif op.rule == RL_TCL_UNARY:
                unary = MODEL.lookup_unary(op.category, op.sub_ops[0].category)
                if unary is None and op.category.ismodifier and op.category.result_category() == op.sub_ops[0].category:
                    unary = MODEL.infer_unary(op.category)
                assert unary is not None
                template = unary.template
                nlst = collections.deque()
                # reverse order
                nlst.append('%s(<T %s %d %d>' % (indent, op.category, 0, 2))
                nlst.append(stk.pop())
                nlst.append('%s  (<L %s %s %s %s %s>)' % (indent, template.clean_category, 'UNARY', 'UNARY',
                                                          '.UNARY', template.predarg_category))
                nlst.append('%s)' % indent)
                stk.append(sep.join(nlst))
            else:
                nlst = collections.deque()
                nlst.appendleft(stk.pop())  # arg0
                nlst.appendleft('%s(<T %s %d %d>' % (indent, op.category, 0, 1))
                nlst.append('%s)' % indent)
                stk.append(sep.join(nlst))

        assert len(stk) == 1
        return stk[0]

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

    def add_wikipedia_links(self):
        """Call after resolved proper nouns."""
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
                        result = c.search_wikipedia()
                        allresults.append(result)
                    else:
                        result = allresults.pop()
                    if result is not None:
                        subspan, bresult = self.get_subspan_from_wiki_search(c, result, title_only=retry)
                        if subspan is not None:
                            # Only checking first result
                            found.append((c, bresult))
                            if len(c) > 1 and c[-1].idx in subspan.get_indexes():
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


## @ingroup gfn
def process_ccg_pt(pt, options=0):
    """Process the CCG parse tree.

    Args:
        pt: The parse tree returned from marbles.ie.drt.parse.parse_ccg_derivation().
        options: None or marbles.ie.drt.compose.CO_REMOVE_UNARY_PROPS to simplify propositions.

    Returns:
        A Ccg2Drs instance. Call Ccg2Drs.get_drs() to obtain the DRS.

    See Also:
        marbles.ie.drt.parse.parse_ccg_derivation()
    """
    ccg = Ccg2Drs(options | CO_FAST_RENAME)
    if future_string != unicode:
        pt = pt_to_utf8(pt)
    ccg.build_execution_sequence(pt)
    ccg.create_drs()
    ccg.resolve_proper_names()
    if 0 == (options & CO_NO_WIKI_SEARCH):
        ccg.add_wikipedia_links()
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


class TestSentence(Sentence):
    def __init__(self, lst):
        super(TestSentence, self).__init__(lexemes=lst)


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
        dictionary = map(lambda x: {}, [None]*26)
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
                continue

            idx = ord(N) - 0x41
            template = lexeme.get_template()
            if template is None:
                continue
            fn = lexeme.get_production(TestSentence([lexeme]), options=CO_NO_VERBNET)
            if lexeme.drs is None or len(fn.lambda_refs) == 1:
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

