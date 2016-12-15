# NOTE: pypeg2 is written in python 3. The future import will convert all strings
# to unicode.
from __future__ import unicode_literals, print_function
from pypeg2 import *
import re
from .drs import DRSRelation
from .pdrs import MAP, PDRS, LambdaPDRS, PDRSRef, PRef, LambdaPDRSRef
from .pdrs import PCond, PNeg, PRel, PProp, PImp, POr, PDiamond, PBox
from .drs import DRS, DRSRef,  LambdaDRS, LambdaDRSRef
from .drs import Neg, Rel, Prop, Imp, Or, Diamond, Box


###########################################################################
# Common to both parsers.
#
# The following names can be used for different operators (these are all
# case insensitive):
#
# * Negation operators: '!', 'not', 'neg'
# * Implication operators (infix): 'imp', '->', '=>', 'then'
# * Disjunction operators (infix): 'v', 'or'
# * Box operators: 'b', 'box', 'necessary'
# * Diamond operators: 'd', 'diamond', 'maybe'.
# * Proposition operator: ':'
#
# Syntax:
# * A DRS/PDRS is contained between '<' and '>'
# * A list is contained between '{' and '}'. List can have [0,inf] elements
# * A tuple is contained between '(' and ')'. Tuples have fixed cardinality.
# * Elements are separated by a comma


class NegateOp(Keyword):
    grammar = Enum(K('not'), K('neg'), K('!'))


class BinaryOp(Keyword):
    grammar = Enum(K('b'), K('box'), K('necessary'),
                   K('d'), K('diamond'), K('maybe'),
                   K('imp'), K('=>'), K('->'), K('then'),
                   K('or'), K('v'))


Predicate = re.compile(r'[a-zA-Z][_\w]*')
Number = re.compile(r'-?\d+')
PosInt = re.compile(r'\d+')

###########################################################################
# PDRS Parser


class Map(List):
    grammar = '(', Number, ',', Number, ')'

    def to_drs(self):
        return MAP(int(self[0]), int(self[1]))


class ProjRef(List):
    grammar = '(', PosInt, ',', Predicate, ')'

    def to_drs(self):
        return PRef(int(self[0]), PDRSRef(self[1].encode('utf-8')))


class PRelExpr(List):
    grammar = Predicate, '(', csl(Predicate), ')'

    def to_drs(self):
        refs = [PDRSRef(r) for r in self[1].encode('utf-8')]
        return PRel(DRSRelation(self[0].encode('utf-8')), refs)


class PdrsDecl(List):
    # Grammar is recursive so must declare with None
    grammar = None

    def to_drs(self):
        return PDRS(int(self[0]), self[3].to_drs(), self[1].to_drs(), self[2].to_drs())


class PPropExpr(List):
    grammar = Predicate, ':', PdrsDecl

    def to_drs(self):
        return PProp(PDRSRef(self[0].encode('utf-8')), self[2].to_drs())


class PNegExpr(List):
    grammar = NegateOp, PdrsDecl

    def to_drs(self):
        return PNeg(self[1].to_drs())


class PBinaryExpr(List):
    grammar = PdrsDecl, BinaryOp, PdrsDecl

    def to_drs(self):
        if self[1] in ['d', 'diamond', 'maybe']:
            return PDiamond(self[0].to_drs(), self[2].to_drs())
        elif self[1] in ['b', 'box', 'necessary']:
            return PBox(self[0].to_drs(), self[2].to_drs())
        elif self[1] in ['imp', '=>', '->', 'then']:
            return PImp(self[0].to_drs(), self[2].to_drs())
        else: # Must be or
            return POr(self[0].to_drs(), self[2].to_drs())


class PCondChoice(List):
    grammar = '(', PosInt, ',', [PNegExpr, PRelExpr, PBinaryExpr, PPropExpr], ')'

    def to_drs(self):
        return PCond(int(self[0]), self[1].to_drs())


class PCondDecl(List):
    grammar = optional(csl(PCondChoice))

    def to_drs(self):
        return [x.to_drs() for x in self]


class PRefDecl(List):
    grammar = optional(csl(ProjRef))

    def to_drs(self):
        return [x.to_drs() for x in self]


class MapDecl(List):
    grammar = optional(csl(Map))

    def to_drs(self):
        return [x.to_drs() for x in self]


PdrsDecl.grammar = '<', PosInt, ',', '{', PRefDecl, '}', ',', '{', PCondDecl, '}', ',', '{', MapDecl, '}', '>'

def parse_pdrs(s):
    """Convert linear notation into a DRS. All whitespace, including new lines
    are ignored. The parser uses pypeg2 which is written in python 3, therefore
    the input string must be unicode.

    The following names can be used for different operators (these are all
    case insensitive):
        - Negation operators: '!', 'not', 'neg'
        - Implication operators (infix): 'imp', '->', '=>', 'then'
        - Disjunction operators (infix): 'v', 'or'
        - Box operators: 'b', 'box', 'necessary'
        - Diamond operators: 'd', 'diamond', 'maybe'.
        - Proposition operator: ':'

    The following rules apply:
        - A PDRS is contained between '<' and '>'
        - A list is contained between '{' and '}'. List's can have [0,inf] elements
        - A tuple is contained between '(' and ')'. Tuples have fixed cardinality of 2.
        - Elements are separated by a comma.
        - An element can be: a PDRS, a list, a tuple, or an expression using the operators
          described above.

    For example, "The man is not happy" can be represented by
        "<1,{},{ (1,not <5,{(2,x)},{(2,man(x)),(5,happy(x))},{(5,2)}>) },{}>"

    Args:
        s: The unicode string to parse.

    Returns:
        A PDRS instance.

    See Also:
        parse_drs()
        marbles.ie.common.Showable.show()
    """
    # Remove all spaces in a string
    p = Parser()
    if isinstance(s, str):
        s = s.decode('utf-8')
    pt = p.parse(s, PdrsDecl)
    drs = pt[1].to_drs()
    return drs

###########################################################################
# DRS Parser


class RelExpr(List):
    grammar = Predicate, '(', csl(Predicate), ')'

    def to_drs(self):
        refs = [DRSRef(r) for r in self[1].encode('utf-8')]
        return Rel(DRSRelation(self[0].encode('utf-8')), refs)


class DrsDecl(List):
    # Grammar is recursive so must declare with None
    grammar = None

    def to_drs(self):
        return DRS(self[0].to_drs(), self[1].to_drs())


class PropExpr(List):
    grammar = Predicate, ':', DrsDecl

    def to_drs(self):
        return PProp(PDRSRef(self[0].encode('utf-8')), self[2].to_drs())


class NegExpr(List):
    grammar = NegateOp, DrsDecl

    def to_drs(self):
        return Neg(self[1].to_drs())


class BinaryExpr(List):
    grammar = DrsDecl, BinaryOp, DrsDecl

    def to_drs(self):
        if self[1] in ['d', 'diamond', 'maybe']:
            return Diamond(self[0].to_drs(), self[2].to_drs())
        elif self[1] in ['b', 'box', 'necessary']:
            return Box(self[0].to_drs(), self[2].to_drs())
        elif self[1] in ['imp', '=>', '->', 'then']:
            return Imp(self[0].to_drs(), self[2].to_drs())
        else:  # Must be or
            return Or(self[0].to_drs(), self[2].to_drs())


class CondChoice(List):
    grammar = [NegExpr, RelExpr, BinaryExpr, PropExpr]

    def to_drs(self):
        return self[0].to_drs()


class CondDecl(List):
    grammar = optional(csl(CondChoice))

    def to_drs(self):
        return [x.to_drs() for x in self]


class RefDecl(List):
    grammar = optional(csl(Predicate))

    def to_drs(self):
        return [DRSRef(x.encode('utf-8')) for x in self]


DrsDecl.grammar = '<', '{', RefDecl, '}', ',', '{', CondDecl, '}', '>'

def parse_drs(s):
    """Convert linear notation into a DRS. All whitespace, including new lines
    are ignored. The parser uses pypeg2 which is written in python 3, therefore
    the input string must be unicode.

    The following names can be used for different operators (these are all
    case insensitive):
        - Negation operators: '!', 'not', 'neg'
        - Implication operators (infix): 'imp', '->', '=>', 'then'
        - Disjunction operators (infix): 'v', 'or'
        - Box operators: 'b', 'box', 'necessary'
        - Diamond operators: 'd', 'diamond', 'maybe'.
        - Proposition operator: ':'

    The following rules apply:
        - A DRS is contained between '<' and '>'
        - A list is contained between '{' and '}'. List can have [0,inf] elements
        - A tuple is contained between '(' and ')'. Tuples have fixed cardinality.
        - Elements are separated by a comma.
        - An element can be: a DRS, a list, a tuple, or an expression using the operators
          described above.

    For example, "The man is not happy" can be represented by
        "<{x},{man(x), not <{},{happy(x)}>}>"

    Args:
        s: The unicode string to parse.

    Returns:
        A DRS instance.

    See Also:
        parse_pdrs()
        marbles.ie.common.Showable.show()
    """
    # Remove all spaces in a string
    p = Parser()
    if isinstance(s, str):
        s = s.decode('utf-8')
    pt = p.parse(s, DrsDecl)
    drs = pt[1].to_drs()
    return drs



