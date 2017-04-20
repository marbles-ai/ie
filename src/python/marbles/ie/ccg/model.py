# -*- coding: utf-8 -*-
"""CCG Model"""

import os
import re

from marbles.ie.ccg.ccgcat import Category, CAT_Sadj, CAT_CONJ, CAT_Sany
from marbles.ie.drt.common import DRSVar
from marbles.ie.drt.compose import FunctorProduction, DrsProduction, PropProduction
from marbles.ie.drt.drs import DRS, DRSRef
from marbles.ie.utils.cache import Cache


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

    def __init__(self, rule, category, finalRef, finalAtom, construct_empty=False):
        """Constructor.

        Args:
            rule: The production constructor rule.
            category: A predarg category.
            finalRef: The final referent result.
            finalAtom: The final atomic category result.
            construct_empty: If true the functor should be constructed with an empty DrsProduction as the final atom.
        """
        self._constructor_rule = rule
        self._category = category
        self._cleancategory = Category.from_cache(category.clean(True))
        self._final_ref = finalRef
        self._final_atom = finalAtom
        self._construct_empty = construct_empty

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
    def constructor_rule(self):
        """Read only access to constructor rule."""
        return self._constructor_rule

    @property
    def construct_empty(self):
        """If true the functor should be constructed with an empty DrsProduction as the final_atom."""
        return self._construct_empty

    @property
    def category(self):
        """Read only access to category."""
        return self._category

    @property
    def clean_category(self):
        """Read only access to cleaned category."""
        return self._cleancategory

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
    def create_from_category(cls, predarg, final_atom=None, gen=None, construct_empty=False):
        """Create a functor template from a predicate-argument category.

        Args:
            predarg: The predicate-argument category.
            final_atom: for special rules where we override the unify scope.
            gen: Optional FunctorTemplateGeneration instance. Required for unary rule generation.
            construct_empty: If true the functor should be constructed with an empty DrsProduction as the final atom.

        Returns:
            A FunctorTemplate instance or None if predarg is an atomic category.
        """
        # Ignore atoms and conj rules. Conj rules are handled by CcgTypeMapper
        catclean = predarg.clean(True)  # strip all pred-arg tags
        if not catclean.isfunctor or catclean.result_category() == CAT_CONJ or catclean.argument_category() == CAT_CONJ:
            return None

        if gen is None:
            gen = FunctorTemplateGeneration()

        predarg, final_tag = predarg.trim_functor_tag()
        predarg = predarg.clean()       # strip functor tags
        predargOrig = predarg

        fn = []
        while predarg.isfunctor:
            atoms = predarg.argument_category(False).extract_unify_atoms(False)
            predarg = predarg.result_category(False)
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

        return FunctorTemplate(tuple(fn), predargOrig, r, acln if final_atom is None else final_atom,
                               construct_empty=construct_empty)

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
            category = category.result_category()
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

    @property
    def template(self):
        """Read only access to template."""
        return self._template

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
            templates: A cache of FunctorTemplates keyed by category signature.
            unary_rules: A cache of UnaryRules keyed by category signature
        """
        if templates is None:
            templates = Cache()
        elif not isinstance(templates, Cache):
            raise TypeError('Model constructor expects a Cache instance for templates argument.')
        if unary_rules is None:
            unary_rules = Cache()
        elif not isinstance(unary_rules, Cache):
            raise TypeError('Model constructor expects a Cache instance for unary_rules argument.')

        self._TEMPLATES = templates
        self._UNARY = unary_rules

    @classmethod
    def load_templates(cls, filepath):
        """Load the model from a file.

        Args:
            filepath: The filename and path.

        Returns:
            A Cache instance.
        """
        with open(filepath, 'rb') as fd:
            templates = fd.readlines()
        dict = {}
        for line in templates:
            ln = line.strip()
            if len(ln) == 0 or ln[0] == '#':
                continue
            predarg = ln.split(',')
            if len(predarg) == 1:
                key, templ = cls.build_template(predarg[0])
                dict[key] = templ
            elif len(predarg) == 2:
                key, templ = cls.build_template(predarg[0].strip(), final_atom=predarg[1].strip())
                dict[key] = templ
            else:
                # Ignore this
                print('Warning: ignoring badly formatted functor template \"%s\"' % ln)
        cache = Cache()
        cache.initialize(dict.iteritems())
        return cache

    def save_templates(self, filepath):
        """Save the model to a file.

        Args:
            filepath: The filename and path:
        """
        with open(filepath, 'wb') as fd:
            for k, v in self._TEMPLATES:
                final_atom = v.final_atom
                if final_atom != Category(k).extract_unify_atoms(False)[-1]:
                    fd.write('%s,  %s\n' % (v.category.signature, v.final_atom))
                else:
                    fd.write('%s\n' % v.category)

    @classmethod
    def build_template(cls, cat, final_atom=None, construct_empty=False):
        """Build a template.

        Args:
            cat: A Category instance or a category signature string.
            final_atom: Optional final atom category for functor template.
            construct_empty: If true the functor should be constructed with an empty DrsProduction as the final atom.

        Returns:
            A tuple of key string and a FunctorTemplate instance.

        Remarks:
            Used to load templates from a file.
        """
        if isinstance(cat, str):
            cat = Category(cat)
        elif not isinstance(cat, Category):
            raise TypeError('Model.build_template() expects signature or Category')
        key = Category(cat.clean(True)).signature
        return key, FunctorTemplate.create_from_category(cat, final_atom, construct_empty=construct_empty)

    def add_template(self, cat, final_atom=None):
        """Add a template to the model.

        Args:
            cat: A Category instance or a category signature string.
            final_atom: Optional final atom category for functor template.
        """
        key, templ = self.build_template(cat, final_atom)
        if key not in self._TEMPLATES:
            self._TEMPLATES[key] = templ
            return templ
        return

    @staticmethod
    def build_unary_rule(result, argument):
        """Build a unary rule.

        Args:
            result: The result Category.
            argument: The argument category.

        Returns:
            A tuple of key string and a UnaryRule instance.

        Remarks:
            Used to load unary rules from a file.
        """
        if isinstance(result, str):
            result = Category(result)
        elif not isinstance(result, Category):
            raise TypeError('Model.build_unary_rule() expects signature or Category result')
        if isinstance(argument, str):
            argument = Category(argument)
        elif not isinstance(argument, Category):
            raise TypeError('Model.build_unary_rule() expects signature or Category argument')

        rule = UnaryRule(result, argument)
        key = rule.getkey()
        return key, rule

    def add_unary_rule(self, result, argument):
        """Add a unary rule.

        Args:
            result: The result Category.
            argument: The argument category.
        """
        key, rule = self.build_unary_rule(result, argument)
        if key not in self._UNARY:
            self._UNARY[key] = rule
            # Force add to category cache
            #Category.from_cache(key)
            return rule
        return None

    def infer_unary(self, category):
        """Attempt to build a unary modifier from existing templates if possible."""
        if category.ismodifier:
            template = self.lookup(category.result_category())
            if template is not None:
                taggedcat = template.category.complete_tags()
                return self.add_unary_rule(Category.combine(taggedcat, category.slash, taggedcat),
                                           taggedcat)
        return None

    def infer_template(self, category):
        """Attempt to build a template from existing templates if possible."""
        if category.isfunctor and not self.issupported(category):
            catArg = category.argument_category()
            catArgArg = catArg.argument_category()
            catResult = category.result_category()
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
                                          Category.combine(catResult, category.argument_category().slash, catArgArg, False))
                return self.add_template(newcat.signature)
            elif category.ismodifier and self.issupported(catResult):
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

## @cond
# Run scripts/make_functor_templates.py to create templates file
try:
    _tcache = Model.load_templates(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'functor_templates.dat'))
    # Add missing categories
    _tcache.addinit(Model.build_template(r'(NP_148\NP_148)/(NP_148\NP_148)'), replace=True)
    # Use unique numeric tags above 1K so when building a template from existing ones we don't overlap
    _tcache.addinit(Model.build_template(r'((S[adj]_2000\NP_1000)\NP_2000)_1000'), replace=True)
    # Attach passive then infinitive to verb that follows
    _tcache.addinit(Model.build_template(r'(S[pss]_2001\NP_1001)/(S[to]_2001\NP_1001)'), replace=True)
    _tcache.addinit(Model.build_template(r'PP_1002/NP_2002'), replace=True)
    _tcache.addinit(Model.build_template(r'N_1003/PP_1003'), replace=True)
    _tcache.addinit(Model.build_template(r'NP_1004/PP_1004'), replace=True)
    _tcache.addinit(Model.build_template(r'NP_1007/N_2007'))
    _tcache.addinit(Model.build_template(r'NP_1005/(N_2005/PP_2005)'))
    _tcache.addinit(Model.build_template(r'((N_2006/N_2006)/(N_2006/N_2006))\(S[adj]_1006\NP_2006)'), replace=True)

    _tcache.addinit(Model.build_template(r'S[dcl]_1007/S[dcl]_2007'))
    _tcache.addinit(Model.build_template(r'S[dcl]_1008\S[dcl]_2008'))
    _tcache.addinit(Model.build_template(r'S_1009/(S_1009\NP)'))
    _tcache.addinit(Model.build_template(r'S_1010\(S_1010/NP)'))
    _tcache.addinit(Model.build_template(r'(S_2011\NP_1011)/((S_2011\NP_1011)\PP)'))
    _tcache.addinit(Model.build_template(r'(S_1012\NP_2012)\((S_1012\NP_2012)/PP)'))
    _tcache.addinit(Model.build_template(r'(N_1013\N_1013)/(S[dcl]\NP_1013)'))
    _tcache.addinit(Model.build_template(r'(S[dcl]_1014\NP_2014)/((S[dcl]_1014\NP_2014)\PP)'))

    _tcache.addinit(Model.build_template(r'S[X]_1015/S[X]_2015'))
    _tcache.addinit(Model.build_template(r'S[X]_1016\S[X]_2016'))
    _tcache.addinit(Model.build_template(r'((S[dcl]\NP_2017)/NP_1017)/PR'))
    _tcache.addinit(Model.build_template(r'(NP_1018\NP_1018)\(S[dcl]\NP_1018)'))
    _tcache.addinit(Model.build_template(r'(NP_1019/NP_1019)\(S[adj]\NP_1019)'))
    _tcache.addinit(Model.build_template(r'(NP_1020/N_2020)\NP_1020'))

    _tcache.addinit(Model.build_template(r'((N_1021\N_1021)/S[dcl])\((N_1021\N_1021)/NP)'))

    _tcache.addinit(Model.build_template(r'S[X]_1022/NP_2022'))
    _tcache.addinit(Model.build_template(r'S[X]_1023\NP_2023'))

    # Add unary rules
    _rcache = Cache()
    _rcache.addinit(Model.build_unary_rule(r'(S_1024\NP_2024)/(S_1024\NP_2024)', 'S_1024/S[dcl]_1024'))
    _rcache.addinit(Model.build_unary_rule(r'(S[adj]_1025\NP_2025)\(S[adj]_1025\NP_2025)', 'S_1025/S[dcl]_1025'))
    _rcache.addinit(Model.build_unary_rule(r'(S[X]_1026\NP_2026)\(S[X]_1026\NP_2026)', 'S_1026/S[dcl]_1026'))
    _rcache.addinit(Model.build_unary_rule(r'NP_1027', r'N_1027'))
    _rcache.addinit(Model.build_unary_rule(r'NP_1028\NP_1028', r'NP_1028'))
    # Wildcards incur more string processing so cover main rules
    _rcache.addinit(Model.build_unary_rule(r'N_1030\N_1030', r'S[pss]_2030\NP_1030'))
    _rcache.addinit(Model.build_unary_rule(r'N_1031\N_1031', r'S[adj]_2031\NP_1031'))
    _rcache.addinit(Model.build_unary_rule(r'N_1032\N_1032', r'S[dcl]_2032\NP_1032'))
    _rcache.addinit(Model.build_unary_rule(r'N_1033\N_1033', r'S[ng]_2033\NP_1033'))
    _rcache.addinit(Model.build_unary_rule(r'N_1034\N_1034', r'S_2034\NP_1034'))
    _rcache.addinit(Model.build_unary_rule(r'N_1035\N_1035', r'S[X]_2035\NP_1035'))
    _rcache.addinit(Model.build_unary_rule(r'S_1036/S_2036', r'S[ng]_1036\NP_3036'))
    _rcache.addinit(Model.build_unary_rule(r'S_1037/S_1037', r'S[pss]_1037\NP'))
    _rcache.addinit(Model.build_unary_rule(r'S_1038/S_1038', r'S[to]_1038\NP'))
    _rcache.addinit(Model.build_unary_rule(r'S_1039/S_1039', r'S[X]_1039\NP'))
    _rcache.addinit(Model.build_unary_rule(r'S_1040/S_1040', r'S_1040\NP'))
    _rcache.addinit(Model.build_unary_rule(r'S_1041\S_1041', r'S[X]_1041\NP'))
    _rcache.addinit(Model.build_unary_rule(r'PP_1042/PP_1042', r'PP_1042'))
    _rcache.addinit(Model.build_unary_rule(r'PP_1043\PP_1043', r'PP_1043'))
    _rcache.addinit(Model.build_unary_rule(r'(N_1044\N_1044)\(N_1044\N_1044)', r'(N_1044\N_1044)'))
    _rcache.addinit(Model.build_unary_rule(r'(S[X]_1045\NP_2045)\(S[X]_1045\NP_2045)', 'S[X]_1045\NP_2045'))
    _rcache.addinit(Model.build_unary_rule(r'((S[X]_1046\NP_2046)/NP_3046)\((S[X]_1046\NP_2046)/NP_3046)', '(S[X]_1046\NP_2046)/NP_3046'))
    _rcache.addinit(Model.build_unary_rule(r'((S[dcl]_3047\NP_2047)_3047/((S_3047\NP_2047)_3047\(S_3047\NP_2047)_3047)_1047)_3047', r'(S[dcl]_3047\NP_2047)_3047'))
    _rcache.addinit(Model.build_unary_rule(r'((S[pss]_3048\NP_2048)_3048/((S_3048\NP_2048)_3048\(S_3048\NP_2048)_3048)_1048)_3048', r'(S[pss]_3048\NP_2048)_3048'))
    _rcache.addinit(Model.build_unary_rule(r'((S[b]_3049\NP_2049)_3049/((S_3049\NP_2049)_3049\(S_3049\NP_2049)_3049)_1049)_3049', r'(S[b]_3049\NP_2049)_3049'))
    _rcache.addinit(Model.build_unary_rule(r'((S[ng]_3050\NP_2050)_3050/((S_3050\NP_2050)_3050\(S_3050\NP_2050)_3050)_1050)_3050', r'(S[ng]_3050\NP_2050)_3050'))
    _rcache.addinit(Model.build_unary_rule(r'((S_1051\NP_2051)\(S_1051\NP_2051))\((S_1051\NP_2051)\(S_1051\NP_2051))', '(S_1051\NP_2051)\(S_1051\NP_1051)'))
    _rcache.addinit(Model.build_unary_rule(r'((S[dcl]_1052\NP_2052)/(S[b]_1052\NP_2052))\((S[dcl]_1052\NP_2052)/(S[b]_1052\NP_2052))', '(S_1052\NP_2052)/(S_1052\NP_2052)'))
    _rcache.addinit(Model.build_unary_rule(r'(S[pss]_1053\NP_1053)\(S[pss]_1053\NP_2053)', 'S_1053\NP_2053'))
    _rcache.addinit(Model.build_unary_rule(r'(S[dcl]_1054\NP_2054)\(S[dcl]_1054\NP_2054)', 'S_1054\NP_2054'))
    _rcache.addinit(Model.build_unary_rule(r'(S[em]_1055\NP_2055)\(S[em]_1055\NP_2055)', 'S_1055\NP_2055'))
    _rcache.addinit(Model.build_unary_rule(r'(S_1056\NP_2056)\(S_1056\NP_2056)', 'S[ng]_1056\NP_2056'))
    _rcache.addinit(Model.build_unary_rule(r'(S[X]_1057\NP_2057)\(S[X]_1057\NP_2057)', 'S_1057\NP_2057'))
    _rcache.addinit(Model.build_unary_rule(r'(S_1058\NP_1058)\(S_1058\NP_1058)', 'S_1058\NP_1058'))
    _rcache.addinit(Model.build_unary_rule(r'(N_1059/N_1059)\(N_1059/N_1059)', 'N_1059/N_1059'))
    _rcache.addinit(Model.build_unary_rule(r'S[X]_1060\S[X]_1060', r'S[X]_1060'))
    _rcache.addinit(Model.build_unary_rule(r'S[dcl]_1061\S[dcl]_1061', r'S_1061'))
    _rcache.addinit(Model.build_unary_rule(r'S[X]_1062\S[X]_1062', r'S_1062'))
    _rcache.addinit(Model.build_unary_rule(r'(S_1\NP_2063)/(S_1\NP_2063)', r'S[dcl]_1063/S[dcl]_1063'))
    _rcache.addinit(Model.build_unary_rule(r'S_1064\S_1064', 'S_1064'))
    _rcache.addinit(Model.build_unary_rule(r'((S[dcl]_1065\NP_2065)/NP_3065)\((S[dcl]_1065\NP_2065)/NP_3065)', r'(S_1065\NP_2065)/NP_3065'))
    _rcache.addinit(Model.build_unary_rule(r'((S[b]_1066\NP_2066)/NP_3066)\((S[b]_1066\NP_2066)/NP_3066)', r'(S_1066\NP_2066)/NP_3066'))
    _rcache.addinit(Model.build_unary_rule(r'((S[X]_1067\NP_2067)/NP_3067)\((S[X]_1067\NP_2067)/NP_3067)', r'(S_1067\NP_2067)/NP_3067'))
    _rcache.addinit(Model.build_unary_rule(r'(N_2068/PP_1068)\(N_2068/PP_1068)', r'N_2068/PP_1068'))
    _rcache.addinit(Model.build_unary_rule(r'(S_2069/S_1069)\(S_2069/S_1069)', r'S_2069/S_1069'))
    _rcache.addinit(Model.build_unary_rule(r'NP_1070', r'S[ng]_1070\NP_2070'))
    _rcache.addinit(Model.build_unary_rule(r'NP_1071', r'S_1071\NP_2071'))
    _rcache.addinit(Model.build_unary_rule(r'NP_1072', r'S[X]_1072\NP_2072'))
    _rcache.addinit(Model.build_unary_rule(r'NP_1073\NP_1073', r'S[pss]_2073\NP_1073'))
    _rcache.addinit(Model.build_unary_rule(r'NP_1074\NP_1074', r'S[adj]_2074\NP_1074'))
    _rcache.addinit(Model.build_unary_rule(r'NP_1075\NP_1075', r'S[dcl]_2075\NP_1075'))
    _rcache.addinit(Model.build_unary_rule(r'NP_1076\NP_1076', r'S[ng]_2076\NP_1076'))
    _rcache.addinit(Model.build_unary_rule(r'NP_1077\NP_1077', r'S_2077\NP_1077'))
    _rcache.addinit(Model.build_unary_rule(r'NP_1078\NP_1078', r'S_2078/NP_1078'))
    _rcache.addinit(Model.build_unary_rule(r'NP_1079\NP_1079', r'S[X]_2079\NP_1079'))
    _rcache.addinit(Model.build_unary_rule(r'(S_1080\NP_2080)/(S_1080\NP_2080)', 'S[ng]_1080\NP_2080'))
    _rcache.addinit(Model.build_unary_rule(r'(S_1081\NP_2081)\(S_1081\NP_2081)', 'S[to]_1081\NP_2081'))
    _rcache.addinit(Model.build_unary_rule(r'(S_1082\NP_2082)\(S_1082\NP_2082)', 'S[X]_1082\NP_2082'))
    _rcache.addinit(Model.build_unary_rule(r'(S_1083\NP_2083)\(S_1083\NP_2083)', 'NP_2083'))
    _rcache.addinit(Model.build_unary_rule(r'NP_1084\NP_1084', 'S[dcl]_1084'))
    _rcache.addinit(Model.build_unary_rule(r'((S[dcl]_1085\NP_3085)/S[em]_2085)\((S[dcl]_1085\NP_3085)/S[em]_2085)', r'(S_1085\NP_3085)/S[em]_2085'))
    _rcache.addinit(Model.build_unary_rule(r'((S[X]_1086\NP_3086)/S[X]_2086)\((S[X]_1086\NP_3086)/S[X]_2086)', r'(S_1086\NP_3086)/S[X]_2086'))
    _rcache.addinit(Model.build_unary_rule(r'((S[dcl]_1087\NP_2087)/(S[b]_1087\NP_2087))\((S[dcl]_1087\NP_2087)/(S[b]_1087\NP_2087))', r'(S_1087\NP_2087)/(S[b]_1087\NP_2087)'))
    _rcache.addinit(Model.build_unary_rule(r'N_2088\N_2088', r'S[dcl]_1088/NP_2088'))
    _rcache.addinit(Model.build_unary_rule(r'N_2089\N_2089', r'S[X]_1089/NP_2089'))
    _rcache.addinit(Model.build_unary_rule(r'N_2090\N_2090', r'S_1090/NP_2090'))
    _rcache.addinit(Model.build_unary_rule(r'((S[dcl]_1091\NP_2091)/(S[adj]_3091\NP_2091))\((S[dcl]_1091\NP_2091)/(S[adj]_3091\NP_2091))', r'(S_1091\NP_2091)/(S[adj]_3091\NP_2091)'))
    _rcache.addinit(Model.build_unary_rule(r'((S[pss]_1092\NP_2092)/PP_3092)\((S[pss]_1092\NP_2)/PP_3092)', r'(S_1092\NP_2092)/PP_3092'))
    _rcache.addinit(Model.build_unary_rule(r'((S[b]_1093\NP_2093)/PP_3093)\((S[b]_1093\NP_2093)/PP_3093)', r'(S_1093\NP_2093)/PP_3093'))
    _rcache.addinit(Model.build_unary_rule(r'((S[X]_1094\NP_2094)/PP_3094)\((S[X]_1094\NP_2094)/PP_3094)', r'(S_1094\NP_2094)/PP_3094'))
    MODEL = Model(templates=_tcache, unary_rules=_rcache)
except Exception as e:
    print(e)
    # Allow module to load else we cannot create the dat file.
    MODEL = Model()
## @endcond
