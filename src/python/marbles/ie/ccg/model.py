# -*- coding: utf-8 -*-
"""CCG Model"""

import os
import pickle
import re

from marbles.ie.ccg.ccgcat import Category, CAT_Sadj, CAT_CONJ, CAT_Sany
from marbles.ie.drt.common import DRSVar
from marbles.ie.drt.compose import FunctorProduction, DrsProduction, PropProduction
from marbles.ie.drt.drs import DRS, DRSRef


class FunctorTemplateGeneration(object):
    """Template Generation Variables"""

    def __init__(self):
        self.ei = 0
        self.xi = 0
        self.tags = {}

    def next_ei(self):
        self.ei += 1
        return self.ei

    def next_xi(self):
        self.xi += 1
        return self.xi

    def istagged(self, key):
        return key in self.tags

    def get_tag(self, key):
        return self.tags[key]

    def tag(self, key, v):
        self.tags[key] = v


class FunctorTemplate(object):
    """Template for functor generation."""
    _names = ['f', 'g', 'h', 'm', 'n', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w']
    _PredArgIdx = re.compile(r'^.*_(?P<idx>\d+)$')

    def __init__(self, rule, category, finalRef, finalAtom):
        """Constructor.

        Args:
            rule: The production constructor rule.
            category: A predarg category.
            finalRef: The final referent result.
            finalAtom: The final atomic category result.
        """
        self._constructor_rule = rule
        self._category = category
        self._final_ref = finalRef
        self._final_atom = finalAtom

    @property
    def constructor_rule(self):
        """Read only access to constructor rule."""
        return self._constructor_rule

    def __repr__(self):
        """Return the model as a string."""
        return self.category.clean(True).signature + ':' + self.__str__()

    def __str__(self):
        """Return the model as a string."""
        line = []
        for i in range(len(self.constructor_rule)):
            fn = self.constructor_rule[i]
            if isinstance(fn[1], tuple):
                if fn[0] == PropProduction:
                    line.append(self._names[i].upper() + '(')
                else:
                    line.append(self._names[i] + '(')
                line.append(','.join([x.var.to_string() for x in fn[1]]))
                line.append(').')
            else:
                if fn[0] == PropProduction:
                    line.append(self._names[i].upper() + '(' + fn[1].var.to_string() + ').')
                else:
                    line.append(self._names[i] + '(' + fn[1].var.to_string() + ').')
        if self.final_ref is None:
            line.append('none')
        else:
            line.append(self.final_ref.var.to_string())
        return ''.join(line)

    @property
    def category(self):
        """Read only access to category."""
        return self._category

    @property
    def final_ref(self):
        """Read only access to final DRS referent."""
        return self._final_ref

    @property
    def final_atom(self):
        """Read only access to final atom category."""
        return self._final_atom

    @property
    def isfinalevent(self):
        """Test if the final return referent is an event."""
        return self._final_atom != CAT_Sadj and self._final_atom == CAT_Sany

    @classmethod
    def create_from_category(cls, predarg, final_atom=None, gen=None):
        """Create a functor template from a predicate-argument category.

        Args:
            predarg: The predicate-argument category.
            final_atom: for special rules where we override the unify scope.
            gen: Optional FunctorTemplateGeneration instance. Required for unary rule generation.

        Returns:
            A FunctorTemplate instance or None if predarg is an atomic category.
        """
        # Ignore atoms and conj rules. Conj rules are handled by CcgTypeMapper
        catclean = predarg.clean(True)  # strip all pred-arg tags
        if not catclean.isfunctor or catclean.result_category == CAT_CONJ or catclean.argument_category == CAT_CONJ:
            return None

        if gen is None:
            gen = FunctorTemplateGeneration()

        predarg, final_tag = predarg.trim_functor_tag()
        predarg = predarg.clean()       # strip functor tags
        predargOrig = predarg

        fn = []
        while predarg.isfunctor:
            atoms = predarg.argument_category.extract_unify_atoms(False)
            predarg = predarg.result_category
            refs = []
            for a in atoms:
                key = None
                m = cls._PredArgIdx.match(a.signature)
                if m is not None:
                    key = m.group('idx')
                if key is None or not gen.istagged(key):
                    acln = a.clean(True)
                    if (acln == CAT_Sany and acln != CAT_Sadj) or acln.signature[0] == 'Z':
                        r = DRSRef(DRSVar('e', gen.next_ei()))
                    else:
                        r = DRSRef(DRSVar('x', gen.next_xi()))
                    if key is not None:
                        gen.tag(key, r)
                else:
                    r = gen.get_tag(key)
                refs.append(r)

            if len(refs) == 1:
                fn.append((FunctorProduction, refs[0]))
            else:
                fn.append((FunctorProduction, tuple(refs)))

        # Handle return atom
        acln = predarg.clean(True)
        key = None
        m = cls._PredArgIdx.match(predarg.signature)
        if m is not None:
            key = m.group('idx')

        if key is None or not gen.istagged(key):
            if acln == CAT_Sany and acln != CAT_Sadj:
                r = DRSRef(DRSVar('e', gen.next_ei()))
            else:
                r = DRSRef(DRSVar('x', gen.next_xi()))
            if key is not None:
                gen.tag(key, r)
        else:
            r = gen.get_tag(key)

        # If the functor is tagged then modify the final_ref
        if final_tag is not None and gen.istagged(final_tag):
            r = gen.get_tag(final_tag)

        return FunctorTemplate(tuple(fn), predargOrig, r, acln if final_atom is None else final_atom)

    def create_empty_functor(self, dep=None):
        """Create a FunctorProduction with an empty inner DrsProduction

        Args:
            dep: Optional marbles.ie.drt.compose.Dependency instance.

        Returns:
            A FunctorProduction.
        """
        fn = DrsProduction(drs=DRS([], []), category=self.final_atom.remove_wildcards(), dep=dep)
        fn.set_lambda_refs([self.final_ref])
        category = self.category.clean(True).remove_wildcards()
        for c in self._constructor_rule:
            assert not category.isempty
            assert category.isfunctor
            fn = c[0](category, c[1], fn)
            category = category.result_category
        assert category.isatom
        return fn


class UnaryRule(object):
    """A unary rule."""

    def __init__(self, result, argument):
        """Constructor for unary rule `result <- argument`.

        Args:
            result: The result category.
            argument: The argument category.

        Remarks:
            Both categories must include predarg tags.
        """
        if not isinstance(result, Category):
            raise TypeError('UnaryRule expects a result Category')
        if not isinstance(argument, Category):
            raise TypeError('UnaryRule expects a argument Category')
        # We implement unary rules using backward application of the functor below
        self._template = FunctorTemplate.create_from_category(Category.combine(result.clean(), '\\', argument.clean(), False))

    @staticmethod
    def create_key(result, argument):
        """Create a rule key from result and argument categories.

        Args:
            result: The result category.
            argument: The argument category.

        Returns:
            A string.

        Remarks:
            Both categories must NOT include predarg tags. To remove tags do Category.clean(True).
        """
        if not isinstance(result, Category):
            raise TypeError('UnaryRule.create_key() expects a Category instance ')
        if not isinstance(argument, Category):
            raise TypeError('UnaryRule.create_key() expects a Category instance')
        return Category.combine(result, '\\', argument, False).signature

    def getkey(self):
        """Get the dictionary key for this rule.

        Returns:
            A string.
        """
        return self._template.category.clean(True).signature

    def get(self, dep=None):
        """Get a unary functor that can be applied using function application.

        Args:
            dep: Optional marbles.ie.drt.compose.Dependency instance.

        Returns:
            A FunctorProduction instance.
        """
        return self._template.create_empty_functor(dep=dep)


class Model(object):
    """CCG Model"""
    _Feature = re.compile(r'\[[a-z]+\]')

    def __init__(self, templates=None, unary_rules=None):
        """Constructor.

        Args:
            templates: A dictionary of FunctorTemplates keyed by category signature.
            unary_rules: A dictionary of UnaryRules keyed by category signature
        """
        if templates is None:
            templates = {}
        if unary_rules is None:
            unary_rules = {}
        self._TEMPLATES = templates
        self._UNARY = unary_rules

    @classmethod
    def load(cls, filepath):
        with open(filepath, 'rb') as fd:
            dict = pickle.load(fd)
        return Model(dict)

    def save(self, filepath):
        with open(filepath, 'wb') as fd:
            pickle.dump(self, fd)

    def add_template(self, cat, replace=False, final_atom=None):
        """Add a template to the model.

        Args:
            cat: A Category instance or a category signature string.
            replace: Optional flag to overwrite existing entry. Existing entry is preserved by default.
            final_atom: Optional final atom category for functor template.
        """
        if isinstance(cat, str):
            cat = Category(cat)
        elif not isinstance(cat, Category):
            raise TypeError('Model.add_template() expects signature or Category')
        ccat = Category(cat.clean(True))
        #ccat = Category.from_cache(cat.clean(True))
        key = ccat.signature
        if key not in self._TEMPLATES or replace:
            templ = FunctorTemplate.create_from_category(cat, final_atom)
            self._TEMPLATES[key] = templ
            return templ
        return

    def add_unary_rule(self, result, argument, replace=False):
        """Add a unary rule."""
        if isinstance(result, str):
            result = Category(result)
        elif not isinstance(result, Category):
            raise TypeError('Model.add_unary_rule() expects signature or Category result')
        if isinstance(argument, str):
            argument = Category(argument)
        elif not isinstance(argument, Category):
            raise TypeError('Model.add_unary_rule() expects signature or Category argument')

        rule = UnaryRule(result, argument)
        key = rule.getkey()
        if key not in self._UNARY or replace:
            self._UNARY[key] = rule
            # Force add to category cache
            #Category.from_cache(key)
            return rule
        return None

    def infer_unary(self, category):
        """Attempt to build a unary modifier from existing templates if possible."""
        if category.ismodifier:
            template = self.lookup(category.result_category)
            if template is not None:
                taggedcat = template.category.complete_tags()
                return self.add_unary_rule(Category.combine(taggedcat, category.slash, taggedcat),
                                           taggedcat, False)
        return None

    def infer_template(self, category):
        """Attempt to build a template from existing templates if possible."""
        if category.isfunctor and not self.issupported(category):
            catArg = category.argument_category
            catArgArg = catArg.argument_category
            catResult = category.result_category
            if category.istype_raised and (self.issupported(catResult) or catResult.isatom) \
                    and (self.issupported(catArgArg) or catArgArg.isatom):
                # If the catgeory is type raised then check if result type exists and build now.
                # TODO: This should be sent to a log
                print('Adding type-raised category %s to TEMPLATES' % category.signature)
                # Template categories contain predarg info so build new from these
                if catResult.isfunctor:
                    catResult = self.lookup(catResult).category.complete_tags()
                else:
                    catResult = Category(catResult.signature + '_999')  # synthesize pred-arg info
                if catArgArg.isfunctor:
                    # FIXME: Should really check predarg info does not overlap with catResult. Chances are low.
                    catArgArg = self.lookup(catArgArg).category.complete_tags()
                else:
                    catArgArg = Category(catArgArg.signature + '_998')  # synthesize pred-arg info
                newcat = Category.combine(catResult, category.slash,
                                          Category.combine(catResult, category.argument_category.slash, catArgArg, False))
                # FIXME: This is not thread safe. Should add to separate synchronized dictionary.
                return self.add_template(newcat.signature)
            elif category.ismodifier and self.issupported(catResult):
                # FIXME: This is not thread safe. Should add to separate synchronized dictionary.
                predarg = self.lookup(catResult).category.complete_tags()
                newcat = Category.combine(predarg, category.slash, predarg, False)
                return self.add_template(newcat.signature)

        return None

    def lookup_unary(self, result, argument):
        if isinstance(result, str):
            result = Category(result)
        elif not isinstance(result, Category):
            raise TypeError('Model.lookup_unary() expects signature or Category result')
        if isinstance(argument, str):
            argument = Category(argument)
        elif not isinstance(argument, Category):
            raise TypeError('Model.lookup_unary() expects signature or Category argument')
        key = UnaryRule.create_key(result, argument)
        if key in self._UNARY:
            return self._UNARY[key]
        # Perform wildcard replacements
        wc = self._Feature.sub('[X]', key)
        if wc in self._UNARY:
            return self._UNARY[wc]
        return None

    def lookup(self, category):
        """Lookup a FunctorTemplate with key=category."""
        # TODO: use two dictionaries, readonly and thread-safe.
        if category.signature in self._TEMPLATES:
            return self._TEMPLATES[category.signature]
        # Perform wildcard replacements
        if category.isfunctor:
            wc = self._Feature.sub('[X]', category.signature)
            if wc in self._TEMPLATES:
                return self._TEMPLATES[wc]
        return None

    def issupported(self, category):
        """Test a FunctorTemplate is in TEMPLATES with key=category."""
        if category.signature in self._TEMPLATES:
            return True
        # Perform wildcard replacements
        if category.isfunctor:
            wc = self._Feature.sub('[X]', category.signature)
            return wc in self._TEMPLATES
        return False


# Run scripts/make_functor_templates.py to create templates file
try:
    MODEL = Model.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'functor_templates.dat'))
    # Add missing categories
    MODEL.add_template(r'(NP_148\NP_148)/(NP_148\NP_148)', replace=True)
    # Use unique numeric tags above 1K so when building a template from existing ones we don't overlap
    MODEL.add_template(r'((S[adj]_2000\NP_1000)\NP_2000)_1000', replace=True)
    # Attach passive then infinitive to verb that follows
    MODEL.add_template(r'(S[pss]_2001\NP_1001)/(S[to]_2001\NP_1001)', replace=True)
    #MODEL.add_template(r'PP_1002/NP_1002', replace=True)
    MODEL.add_template(r'N_1003/PP_1003', replace=True)
    MODEL.add_template(r'NP_1004/PP_1004', replace=True)
    MODEL.add_template(r'NP_1007/N_2007')
    MODEL.add_template(r'NP_1005/(N_2005/PP_2005)')
    MODEL.add_template(r'((N_2006/N_2006)/(N_2006/N_2006))\(S[adj]_1006\NP_2006)', replace=True)

    MODEL.add_template(r'S[dcl]_1007/S[dcl]_2007')
    MODEL.add_template(r'S[dcl]_1008\S[dcl]_2008')
    MODEL.add_template(r'S_1009/(S_1009\NP)')
    MODEL.add_template(r'S_1010\(S_1010/NP)')
    MODEL.add_template(r'(S_2011\NP_1011)/((S_2011\NP_1011)\PP)')
    MODEL.add_template(r'(S_1012\NP_2012)\((S_1012\NP_2012)/PP)')
    MODEL.add_template(r'(N_1013\N_1013)/(S[dcl]\NP_1013)')
    MODEL.add_template(r'(S[dcl]_1014\NP_2014)/((S[dcl]_1014\NP_2014)\PP)')

    MODEL.add_template(r'S[X]_1015/S[X]_2015')
    MODEL.add_template(r'S[X]_1016\S[X]_2016')
    MODEL.add_template(r'((S[dcl]\NP_2017)/NP_1017)/PR')
    MODEL.add_template(r'(NP_1018\NP_1018)\(S[dcl]\NP_1018)')
    MODEL.add_template(r'(NP_1019/NP_1019)\(S[adj]\NP_1019)')
    MODEL.add_template(r'(NP_1020/N_2020)\NP_1020')

    MODEL.add_template(r'((N_1021\N_1021)/S[dcl])\((N_1021\N_1021)/NP)')

    # Add unary rules
    MODEL.add_unary_rule(r'NP_1', r'N_1')
    MODEL.add_unary_rule(r'NP_1\NP_1', r'NP_1')
    # Wildcards incur more string processing so cover main rules
    MODEL.add_unary_rule(r'N_1\N_1', r'S[pss]_2\NP_1')
    MODEL.add_unary_rule(r'N_1\N_1', r'S[adj]_2\NP_1')
    MODEL.add_unary_rule(r'N_1\N_1', r'S[dcl]_2\NP_1')
    MODEL.add_unary_rule(r'N_1\N_1', r'S[ng]_2\NP_1')
    MODEL.add_unary_rule(r'N_1\N_1', r'S_2\NP_1')
    MODEL.add_unary_rule(r'N_1\N_1', r'S[X]_2\NP_1')

    MODEL.add_unary_rule(r'S_1/S_1', r'S[pss]_1\NP')
    MODEL.add_unary_rule(r'S_1/S_1', r'S[to]_1\NP')
    MODEL.add_unary_rule(r'S_1/S_1', r'S[ng]_1\NP')
    MODEL.add_unary_rule(r'S_1/S_1', r'S[X]_1\NP')
    MODEL.add_unary_rule(r'S_1/S_1', r'S_1\NP')

    MODEL.add_unary_rule(r'S_1\S_1', r'S[X]_1\NP')
    MODEL.add_unary_rule(r'PP_1/PP_1', r'PP_1')
    MODEL.add_unary_rule(r'PP_1\PP_1', r'PP_1')
    MODEL.add_unary_rule(r'(N_1\N_1)\(N_1\N_1)', r'(N_1\N_1)')

    MODEL.add_unary_rule(r'(S[X]_1\NP_2)\(S[X]_1\NP_2)', 'S[X]_1\NP_2')
    MODEL.add_unary_rule(r'((S[X]_1\NP_2)/NP_3)\((S[X]_1\NP_2)/NP_3)', '(S[X]_1\NP_2)/NP_3')
    MODEL.add_unary_rule(r'((S[dcl]_3\NP_2)_3/((S_3\NP_2)_3\(S_3\NP_2)_3)_1)_3', r'(S[dcl]_3\NP_2)_3')
    MODEL.add_unary_rule(r'((S[pss]_3\NP_2)_3/((S_3\NP_2)_3\(S_3\NP_2)_3)_1)_3', r'(S[pss]_3\NP_2)_3')
    MODEL.add_unary_rule(r'((S[b]_3\NP_2)_3/((S_3\NP_2)_3\(S_3\NP_2)_3)_1)_3', r'(S[b]_3\NP_2)_3')
    MODEL.add_unary_rule(r'((S[ng]_3\NP_2)_3/((S_3\NP_2)_3\(S_3\NP_2)_3)_1)_3', r'(S[ng]_3\NP_2)_3')

    MODEL.add_unary_rule(r'((S_1\NP_2)\(S_1\NP_2))\((S_1\NP_2)\(S_1\NP_2))', '(S_1\NP_2)\(S_1\NP_1)')
    MODEL.add_unary_rule(r'((S[dcl]_1\NP_2)/(S[b]_1\NP_2))\((S[dcl]_1\NP_2)/(S[b]_1\NP_2))', '(S_1\NP_2)/(S_1\NP_2)')

    MODEL.add_unary_rule(r'(S[pss]_1\NP_1)\(S[pss]_1\NP_2)', 'S_1\NP_2')
    MODEL.add_unary_rule(r'(S[dcl]_1\NP_2)\(S[dcl]_1\NP_2)', 'S_1\NP_2')
    MODEL.add_unary_rule(r'(S[em]_1\NP_2)\(S[em]_1\NP_2)', 'S_1\NP_2')
    MODEL.add_unary_rule(r'(S_1\NP_2)\(S_1\NP_2)', 'S[ng]_1\NP_2')
    MODEL.add_unary_rule(r'(S[X]_1\NP_2)\(S[X]_1\NP_2)', 'S_1\NP_2')
    MODEL.add_unary_rule(r'(S_1\NP_1)\(S_1\NP_1)', 'S_1\NP_1')
    MODEL.add_unary_rule(r'(N_1/N_1)\(N_1/N_1)', 'N_1/N_1')
    MODEL.add_unary_rule(r'S[X]_1\S[X]_1', r'S[X]_1')
    MODEL.add_unary_rule(r'S[dcl]_1\S[dcl]_1', r'S_1')
    MODEL.add_unary_rule(r'S[X]_1\S[X]_1', r'S_1')
    MODEL.add_unary_rule(r'(S_1\NP_2)/(S_1\NP_2)', r'S[dcl]_1/S[dcl]_1')
    MODEL.add_unary_rule(r'S_1\S_1', 'S_1')
    MODEL.add_unary_rule(r'((S[dcl]_1\NP_2)/NP_3)\((S[dcl]_1\NP_2)/NP_3)', r'(S_1\NP_2)/NP_3')
    MODEL.add_unary_rule(r'((S[b]_1\NP_2)/NP_3)\((S[b]_1\NP_2)/NP_3)', r'(S_1\NP_2)/NP_3')
    MODEL.add_unary_rule(r'((S[X]_1\NP_2)/NP_3)\((S[X]_1\NP_2)/NP_3)', r'(S_1\NP_2)/NP_3')

    MODEL.add_unary_rule(r'(N_2/PP_1)\(N_2/PP_1)', r'N_2/PP_1')
    MODEL.add_unary_rule(r'(S_2/S_1)\(S_2/S_1)', r'S_2/S_1')
    MODEL.add_unary_rule(r'S_1/S_1', r'S[ng]_1\NP_2')

    MODEL.add_unary_rule(r'NP_1', r'S[ng]_1\NP_2')
    MODEL.add_unary_rule(r'NP_1', r'S_1\NP_2')
    MODEL.add_unary_rule(r'NP_1', r'S[X]_1\NP_2')

    MODEL.add_unary_rule(r'NP_1\NP_1', r'S[pss]_2\NP_1')
    MODEL.add_unary_rule(r'NP_1\NP_1', r'S[adj]_2\NP_1')
    MODEL.add_unary_rule(r'NP_1\NP_1', r'S[dcl]_2\NP_1')
    MODEL.add_unary_rule(r'NP_1\NP_1', r'S[ng]_2\NP_1')
    MODEL.add_unary_rule(r'NP_1\NP_1', r'S_2\NP_1')
    MODEL.add_unary_rule(r'NP_1\NP_1', r'S_2/NP_1')
    MODEL.add_unary_rule(r'NP_1\NP_1', r'S[X]_2\NP_1')
    MODEL.add_unary_rule(r'(S_1\NP_2)/(S_1\NP_2)', 'S[ng]_1\NP_2')
    MODEL.add_unary_rule(r'(S_1\NP_2)\(S_1\NP_2)', 'S[to]_1\NP_2')
    MODEL.add_unary_rule(r'(S_1\NP_2)\(S_1\NP_2)', 'S[X]_1\NP_2')
    MODEL.add_unary_rule(r'(S_1\NP_2)\(S_1\NP_2)', 'NP_2')
    MODEL.add_unary_rule(r'NP_1\NP_1', 'S[dcl]_1')

    MODEL.add_unary_rule(r'((S[dcl]_1\NP_3)/S[em]_2)\((S[dcl]_1\NP_3)/S[em]_2)', r'(S_1\NP_3)/S_2[em]')
    MODEL.add_unary_rule(r'((S[X]_1\NP_3)/S[X]_2)\((S[X]_1\NP_3)/S[X]_2)', r'(S_1\NP_3)/S_2[X]')
    MODEL.add_unary_rule(r'((S[dcl]_1\NP_2)/(S[b]_1\NP_2))\((S[dcl]_1\NP_2)/(S[b]_1\NP_2))', r'(S_1\NP_2)/(S[b]_1\NP_2)')
    MODEL.add_unary_rule(r'N_2\N_2', r'S[dcl]_1/NP_2')
    MODEL.add_unary_rule(r'N_2\N_2', r'S[X]_1/NP_2')
    MODEL.add_unary_rule(r'N_2\N_2', r'S_1/NP_2')
    MODEL.add_unary_rule(r'((S[dcl]_1\NP_2)/(S[adj]_3\NP_2))\((S[dcl]_1\NP_2)/(S[adj]_3\NP_2))', r'(S_1\NP_2)/(S[adj]_3\NP_2)')

    MODEL.add_unary_rule(r'((S[pss]_1\NP_2)/PP_3)\((S[pss]_1\NP_2)/PP_3)', r'(S_1\NP_2)/PP_3')
    MODEL.add_unary_rule(r'((S[b]_1\NP_2)/PP_3)\((S[b]_1\NP_2)/PP_3)', r'(S_1\NP_2)/PP_3')
    MODEL.add_unary_rule(r'((S[X]_1\NP_2)/PP_3)\((S[X]_1\NP_2)/PP_3)', r'(S_1\NP_2)/PP_3')
except Exception as e:
    print(e)
    # Allow module to load else we cannot create the dat file.
    MODEL = Model()

