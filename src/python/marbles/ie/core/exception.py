# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function


class DrsComposeError(Exception):
    """Drs Composition Error."""
    pass


class UnaryRuleError(Exception):
    """Unary Rule Error."""
    pass


class TemplateRuleError(Exception):
    """Functor Template Rule Error"""
    pass


class CombinatorNotFoundError(Exception):
    """Combinator Rule Error"""
    pass


# Track missing rules
_UNDEFINED_UNARY = set()
_UNDEFINED_TEMPLATES = set()


def save_undefined_unary_rules(path):
    """Save missing unary rules to a file."""
    if len(_UNDEFINED_UNARY) == 0:
        return
    with open(path, 'w') as fp:
        for rule in _UNDEFINED_UNARY:
            fp.write('%s %s\n' % rule)


def save_undefined_template_rules(path):
    """Save missing unary rules to a file."""
    if len(_UNDEFINED_TEMPLATES) == 0:
        return
    with open(path, 'w') as fp:
        for rule in _UNDEFINED_TEMPLATES:
            fp.write('%s %s\n' % rule)




