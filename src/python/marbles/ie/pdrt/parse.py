from __future__ import unicode_literals, print_function
from pypeg2 import *
import re
from .drs import DRSRelation
from .pdrs import MAP, PDRS, PDRSRef, PRef
from .pdrs import PCond, PNeg, PRel, PProp, PImp, POr, PDiamond, PBox

# Besides directly defining a PDRS using the PDRS syntax, it is also
# possible to use a set-theoretical string input format directly.
#
# The following names can be used for different operators (these are all
# case insensitive):
#
# * Negation operators: !, not, neg
# * Implication operators (infix): imp, ->, =>, then
# * Disjuction operators (infix): v, or
# * Box operators: b, box, necessary
# * Diamond operators: d, diamond, maybe.
#
# "The man is not happy."
# "<1,{},{ (1,not <5,{(2,x)},{(2,man(x)),(5,happy(x))},{(5,2)}>) },{}>"


class NegateOp(Keyword):
    grammar = Enum(K('not'), K('neg'), K('!'))


class BinaryOp(Keyword):
    grammar = Enum(K('b'), K('box'), K('necessary'), K('d'), K('diamond'), K('maybe'))


Predicate = re.compile(r'[a-zA-Z][_\w]*')
Number = re.compile(ur'-?\d+')
PosInt = re.compile(ur'\d+')


class Map(List):
    grammar = '(', Number, ',', Number, ')'
    def to_drs(self):
        return MAP(int(self[0]), int(self[1]))


class ProjRef(List):
    grammar = '(', PosInt, ',', Predicate, ')'
    def to_drs(self):
        return PRef(int(self[0]), PDRSRef(self[1].encode('utf-8')))


class RelExpr(List):
    grammar = Predicate, '(', csl(Predicate), ')'
    def to_drs(self):
        refs = [PDRSRef(r) for r in self[1].encode('utf-8')]
        return PRel(DRSRelation(self[0].encode('utf-8')), refs)


class PdrsDecl(List):
    # Grammar is recursive so must declare with None
    grammar = None
    def to_drs(self):
        return PDRS(int(self[0]), self[3].to_drs(), self[1].to_drs(), self[2].to_drs())


class NegExpr(List):
    grammar = NegateOp, PdrsDecl
    def to_drs(self):
        return PNeg(self[1].to_drs())


class BinaryExpr(List):
    grammar = PdrsDecl, BinaryOp, PdrsDecl
    def to_drs(self):
        if self[1] in ['d', 'diamond','maybe']:
            return PDiamond(self[0].to_drs(), self[2].to_drs())
        else:
            return PBox(self[0].to_drs(), self[2].to_drs())


class CondChoice(List):
    grammar = '(', PosInt, ',', [NegExpr, RelExpr, BinaryExpr], ')'
    def to_drs(self):
        return PCond(int(self[0]), self[1].to_drs())


class CondDecl(List):
    grammar = optional(csl(CondChoice))
    def to_drs(self):
        return [x.to_drs() for x in self]


class RefDecl(List):
    grammar = optional(csl(ProjRef))
    def to_drs(self):
        return [x.to_drs() for x in self]


class MapDecl(List):
    grammar = optional(csl(Map))
    def to_drs(self):
        return [x.to_drs() for x in self]


PdrsDecl.grammar = '<', PosInt, ',', '{', RefDecl, '}', ',', '{', CondDecl, '}', ',', '{', MapDecl, '}', '>'


def parse_pdrs(s):
    """Convert linear notation into a PDRS.

    See Also:
        marbles.ie.common.Showable.show()
    """
    # Remove all spaces in a string
    p = Parser()
    if isinstance(s, str):
        s = s.decode('utf-8')
    pt = p.parse(s, PdrsDecl)
    drs = pt[1].to_drs()
    return drs