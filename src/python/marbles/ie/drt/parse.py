# NOTE: pypeg2 is written in python 3. The future import will convert all strings
# to unicode.
from __future__ import unicode_literals, print_function
from pypeg2 import *
import re
from .drs import DRSRelation
from .pdrs import MAP, PDRS, PDRSRef, PRef
from .pdrs import PCond, PNeg, PRel, PProp, PImp, POr, PDiamond, PBox
from .drs import DRS, DRSRef
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
# Set notation syntax:
# * A DRS/PDRS is contained between '<' and '>'
# * A list is contained between '{' and '}'. List can have [0,inf] elements
# * A tuple is contained between '(' and ')'. Tuples have fixed cardinality.
# * Elements are separated by a comma


## @cond
NegateOp = re.compile(r'not|neg|!')
BinaryOp = re.compile(r'box|b|necessary|diamond|d|maybe|imp|=>|->|then|or|v')
Predicate = re.compile(r'[a-zA-Z][_\w.$-]*')
Number = re.compile(r'-?\d+')
PosInt = re.compile(r'\d+')
## @endcond

###########################################################################
# PDRS Set Notation Grammar
## @cond


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
        refs = [PDRSRef(r.encode('utf-8')) for r in self[1:]]
        return PRel(DRSRelation(self[0].encode('utf-8')), refs)


class PdrsDecl(List):
    # Grammar is recursive so must declare with None
    grammar = None

    def to_drs(self):
        return PDRS(int(self[0]), self[3].to_drs(), self[1].to_drs(), self[2].to_drs())


class PPropExpr(List):
    grammar = Predicate, ':', PdrsDecl

    def to_drs(self):
        return PProp(PDRSRef(self[0].encode('utf-8')), self[1].to_drs())


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
## @endcond

def parse_pdrs(s):
    """Convert set notation into a PDRS. All whitespace, including new lines
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
        - A tuple is contained between '(' and ')'. Tuples have fixed cardinality of 2, where the first item is an
          integer
        - A list is contained between '{' and '}'. List's can have [0,inf] tuples.
        - A n-ary relation R is defined as R(x1,x2,...,xn)
        - Elements are separated by a comma.
        - An element can be: a PDRS, a relation, a tuple, or an expression using the operators
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
# DRS Set Grammar
## @cond


class RelExpr(List):
    grammar = Predicate, '(', csl(Predicate), ')'

    def to_drs(self):
        refs = [DRSRef(r.encode('utf-8')) for r in self[1:]]
        return Rel(DRSRelation(self[0].encode('utf-8')), refs)


class DrsDecl(List):
    # Grammar is recursive so must declare with None
    grammar = None

    def to_drs(self):
        return DRS(self[0].to_drs(), self[1].to_drs())


class PropExpr(List):
    grammar = Predicate, ':', DrsDecl

    def to_drs(self):
        return Prop(DRSRef(self[0].encode('utf-8')), self[1].to_drs())


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


DrsDecl.grammar  = '<', '{', RefDecl, '}', ',', '{', CondDecl, '}', '>'
## @endcond

###########################################################################
# DRS NLTK Grammar
## @cond


class NltkDecl(List):
    # Grammar is recursive so must declare with None
    grammar = None

    def to_drs(self):
        return DRS(self[0].to_drs(), self[1].to_drs())


class NltkPropExpr(List):
    grammar = Predicate, ':', NltkDecl

    def to_drs(self):
        return Prop(DRSRef(self[0].encode('utf-8')), self[1].to_drs())


class NltkNegExpr(List):
    grammar = NegateOp, NltkDecl

    def to_drs(self):
        return Neg(self[1].to_drs())


class NltkBinaryExpr(List):
    grammar = NltkDecl, BinaryOp, NltkDecl

    def to_drs(self):
        if self[1] in ['d', 'diamond', 'maybe']:
            return Diamond(self[0].to_drs(), self[2].to_drs())
        elif self[1] in ['b', 'box', 'necessary']:
            return Box(self[0].to_drs(), self[2].to_drs())
        elif self[1] in ['imp', '=>', '->', 'then']:
            return Imp(self[0].to_drs(), self[2].to_drs())
        else:  # Must be or
            return Or(self[0].to_drs(), self[2].to_drs())


class NltkCondChoice(List):
    grammar = [NltkNegExpr, RelExpr, NltkBinaryExpr, NltkPropExpr]

    def to_drs(self):
        return self[0].to_drs()


class NltkBracketedCondExpr(List):
    grammar = None

    def to_drs(self):
        return self[0].to_drs()


class NltkBracketedCondChoice(List):
    grammar = [NltkCondChoice, NltkBracketedCondExpr]

    def to_drs(self):
        return self[0].to_drs()


NltkBracketedCondExpr.grammar = '(', NltkBracketedCondChoice, ')'


class NltkCondDecl(List):
    #grammar = optional(csl(NltkCondChoice))
    grammar = optional(csl(NltkBracketedCondChoice))

    def to_drs(self):
        return [x.to_drs() for x in self]


class NltkRefDecl(List):
    grammar = optional(csl(Predicate))

    def to_drs(self):
        return [DRSRef(x.encode('utf-8')) for x in self]


NltkDecl.grammar = '(', '[', NltkRefDecl, ']', ',', '[', NltkCondDecl, ']', ')'
## @endcond

def parse_drs(s, grammar=None):
    """Convert set notation into a DRS. All whitespace, including new lines
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

    The following rules apply apply to set notation:
        - A DRS is contained between '<' and '>'.
        - A list is contained between '{' and '}'. List can have [0,inf] elements
        - A n-ary relation R is defined as R(x1,x2,...,xn).
        - Elements are separated by a comma.
        - An element can be: a DRS, a list, a relation, or an expression using the operators
          described above.

    For example, "The man is not happy" can be represented by
        "<{x},{man(x), not <{},{happy(x)}>}>"

    Args:
        s: The unicode string to parse.
        grammar: Either 'set' or 'nltk', default is 'set'. Use 'nltk' format to parse. See
            <a href="http://www.nltk.org/howto/drt.html">nltk drt</a>.

    Returns:
        A DRS instance.

    See Also:
        parse_pdrs()
        marbles.ie.common.Showable.show()
    """
    # Remove all spaces in a string
    if grammar is None:
        grammar = 'set'

    p = Parser()
    if isinstance(s, str):
        s = s.decode('utf-8')
    if grammar == 'set':
        pt = p.parse(s, DrsDecl)
    elif grammar == 'nltk':
        pt = p.parse(s, NltkDecl)
    else:
        raise SyntaxError('grammar not in ["set", "nltk"]')
    drs = pt[1].to_drs()
    return drs


###########################################################################
# EasySRL Grammar
## @cond

# (<T S[dcl] 1 2>
#   (<T NP 0 2>
#       (<L NP/N DT DT The NP/N>)
#       (<T N 1 2>
#           (<L N/N NN NN school N/N>)
#           (<L N NN NN bus N>)
#       )
#   )
#   (<T S[dcl]\NP 0 2>
#       (<L (S[dcl]\NP)/PP VBZ VBZ wheezes (S[dcl]\NP)/PP>)
#       (<T PP 0 2>
#           (<L PP/NP TO TO to PP/NP>)
#           (<T NP 0 2>
#               (<L NP/N PRP$ PRP$ my NP/N>)
#               (<L N NN NN corner. N>)
#           )
#       )
#   )
# )

CcgArgSep = re.compile(r'/|\\')

TType = re.compile(r'((?:[()/\\]|(?:(?:S|NP|N)(?:\[[a-z]+\])?)|conj|[A-Z]+\$?|-[A-Z]+-)*)')

LPosType = re.compile(r'([A-Z$:-]+|[.,:;])(?=\s+[^>\s]+\s+[^>\s]+(?:\s|[>]))')
LWord = re.compile(r'[^>\s]+(?=\s)')
CcgComplexTypeBegin = re.compile(r'([()/\\]|(?:(?:S|NP|N)(?:\[[a-z]+\])?)|conj|[A-Z]+|[.,:;])+(?=\s)')
CcgComplexTypeEnd = re.compile(r'([()/\\]|(?:(?:S|NP|N)(?:\[[a-z]+\])?)|conj|[A-Z]+|[.,:;]|_\d+)+(?=[>])')


class EsrlCcgTypeBegin(List):
    grammar = (CcgComplexTypeBegin)

    def to_list(self):
        # DRS is the only type in our model
        return self[0]


class EsrlCcgTypeEnd(List):
    grammar = (CcgComplexTypeEnd)

    def to_list(self):
        return [self[0]]


class EsrlLTypeExpr(List):
    grammar = some(LPosType), LWord

    def to_list(self):
        r = [self[-1]]
        r.extend(self[0:-1])
        return r


class EsrlLTypeDecl(List):
    grammar = '<', 'L', EsrlCcgTypeBegin, EsrlLTypeExpr, EsrlCcgTypeEnd, '>'

    def to_list(self):
        r = [self[0].to_list()]
        for x in self[1:]:
            r.extend(x.to_list())
        #r.extend([x.to_list() for x in self[1:-1]])
        return r


class EsrlTTypeExpr(List):
    grammar = '<', 'T', TType, PosInt, PosInt, '>'

    def to_list(self):
        return [self[0], int(self[1]), int(self[2])]


class EsrlTTypeDecl(List):
    # Grammar is recursive so must declare with None
    grammar = None

    def to_list(self):
        return [x.to_list() for x in self]


class EsrlChoice(List):
    grammar = [EsrlTTypeDecl, EsrlLTypeDecl]

    def to_list(self):
        if isinstance(self[0], EsrlTTypeDecl):
            r = self[0].to_list()
            r.append('T')
            return r
        else:
            r = self[0].to_list()
            r.append('L')
            return r


class EsrlDecl(List):
    grammar = '(', EsrlChoice, ')'

    def to_list(self):
        return self[0].to_list()


EsrlTTypeDecl.grammar = EsrlTTypeExpr, some(EsrlDecl)
## @endcond


def parse_ccg_derivation(s):
    """Parse the CCG syntactic derivation for a sentence.

    The syntactic derivation is the same format as used by LDC 200T13. See
    files data/ldc/2005T13/ccgbank_1_1/data/AUTO. EasySRL outputs this format
    when running as a gRPC daemon, or from the command line using the --ccgbank
    option.

    Args:
        s: The CCG syntactic derivation.

    Returns:
        A parse tree for the syntactic derivation. This should be passed to
        marbles.ie.drt.ccg2drs.process_ccg_pt to convert to a DRS.
    """
    p = Parser()
    if isinstance(s, str):
        s = s.decode('utf-8')
    pt = p.parse(s, EsrlDecl)
    return pt[1].to_list()

###########################################################################
# CCG/DRS Category Parser

## @cond
# Include DRS categories T,Z
CcgBaseType = re.compile(r'(?:(?:S|NP|N)(?:\[[a-z]+\])?)|PP|conj|PR|RQU|RRB|LQU|LRB|Z|T|[,\.:;]')


class CCGType(List):
    grammar = CcgBaseType

    def to_list(self):
        return self[0]


class CCGSimpleFunc(List):
    grammar = CcgBaseType, CcgArgSep, CcgBaseType

    def to_list(self):
        return [x for x in self]


class CCGFunc(List):
    grammar = None

    def to_list(self):
        return self[0].to_list()


class CCGHigherOrderFunc1(List):
    grammar = '(', CCGFunc, ')', CcgArgSep, CCGType

    def to_list(self):
        return [self[0].to_list(), self[1], self[2].to_list()]


class CCGHigherOrderFunc2(List):
    grammar = '(', CCGFunc, ')', CcgArgSep, '(', CCGFunc, ')'

    def to_list(self):
        return [self[0].to_list(), self[1], self[2].to_list()]


class CCGHigherOrderFunc3(List):
    grammar = CCGType, CcgArgSep, '(', CCGFunc, ')'

    def to_list(self):
        return [self[0].to_list(), self[1], self[2].to_list()]


class CCGHigherOrderFunc(List):
    grammar = [CCGHigherOrderFunc2, CCGHigherOrderFunc1, CCGHigherOrderFunc3]

    def to_list(self):
        return self[0].to_list()


CCGFunc.grammar = [CCGSimpleFunc, CCGHigherOrderFunc]


class CCGCategory(List):
    grammar = [CCGHigherOrderFunc, CCGSimpleFunc, CCGType]

    def to_list(self):
        return self[0].to_list()


## @endcond

def parse_ccgtype(s):
    """Parse a CCG category type.

    Args:
        s: A ccg type string, for example `'(S[dcl]/NP)/NP'`

    Returns:
        A parse tree.

    Remarks:
        Used by marbles.ie.drt.ccg2drs.CcgTypeMapper.
    """
    p = Parser()
    if isinstance(s, str):
        s = s.decode('utf-8')
    pt = p.parse(s, CCGCategory)
    pt = pt[1].to_list()
    if not isinstance(pt, list):
        return [pt]
    return pt
