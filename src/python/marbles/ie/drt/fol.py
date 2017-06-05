from __future__ import unicode_literals, print_function
from utils import iterable_type_check
from common import Showable
from common import SHOW_BOX
from pysmt import shortcuts as sc
#import Solver, get_model
#from pysmt.shortcuts import Symbol, Bool, Implies, And, Not, Equals
#from pysmt.shortcuts import ForAll, Exists, Implies, Iff, TRUE, FALSE
from pysmt.logics import AUTO, QF_LRA, QF_UFLRA, QF_UFIDL
from pysmt.typing import REAL, FunctionType
from pysmt.exceptions import SolverReturnedUnknownResultError
from pysmt.environment import get_env
import os
from marbles import future_string, safe_utf8_encode


z3name = "z3"
if os.path.exists(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', 'src')):
    # Path to the solver in devel tree
    z3path = [os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', '..', 'scripts'))]
else:
    # Path to the solver in install tree
    z3path = [os.path.abspath(os.path.join(os.path.dirname(__file__), 'solvers'))]

logics = [QF_UFLRA, QF_UFIDL] # Some of the supported logics

env = sc.get_env()

# Add the solver to the environment
env.factory.add_generic_solver(z3name, z3path, logics)



class FOLConversionError(Exception):
    """For conversion errors"""
    pass


FOLVar = future_string
FOLPred = future_string


class FOLForm(Showable):
    """Abstract FOLForm"""

    ## remarks Original code in FOL/Show.hs
    def show(self):
        raise NotImplementedError

    def __str__(self):
        return unicode(self).encode('utf-8')

    def show(self, notation):
        if notation == SHOW_BOX:
            return u'\n' + unicode(self) + u'\n'
        return unicode(self)

    def to_smt(self):
        raise NotImplementedError


class Exists(FOLForm):
    """An existential quantification"""
    def __init__(self, folVar, folForm):
        if not isinstance(folVar, FOLVar) or not isinstance(folForm, FOLForm):
            raise TypeError
        self._var = folVar.decode('utf-8')
        self._fol = folForm

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self._var == other._var and self._fol == other._fol

    def __ne__(self, other):
        return self.__class__ != other.__class__ or self._var != other._var or self._fol != other._fol

    def __unicode__(self):
        return u'\u2203%s%s' % (self._var, self._fol)

    def to_smt(self):
        return sc.Exists(sc.Symbol(self._var), self._fol.to_smt())


class ForAll(FOLForm):
    """A universal quantification"""
    def __init__(self, folVar, folForm):
        if not isinstance(folVar, FOLVar) or not isinstance(folForm, FOLForm):
            raise TypeError
        self._var = folVar.decode('utf-8')
        self._fol = folForm

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self._var == other._var and self._fol == other._fol

    def __ne__(self, other):
        return self.__class__ != other.__class__ or self._var != other._var or self._fol != other._fol

    def __unicode__(self):
        return u'\u2200%s%s' % (self._var, self._fol)

    def to_smt(self):
        return sc.ForAll(sc.Symbol(self._var), self.to_smt())


class And(FOLForm):
    """A conjunction"""
    def __init__(self, folForm1, folForm2):
        if not isinstance(folForm1, FOLForm) or not isinstance(folForm2, FOLForm):
            raise TypeError
        self._folA = folForm1
        self._folB = folForm2

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self._folA == other._folA and self._folB == other._folB

    def __ne__(self, other):
        return self.__class__ != other.__class__ or self._folA != other._folA or self._folB != other._folB

    def __unicode__(self):
        return u'(%s \u2227 %s)' % (self._folA, self._folB)

    def to_smt(self):
        return sc.And(self._folA.to_smt(), self._folB.to_smt())


class Or(FOLForm):
    """A disjunction"""
    def __init__(self, folForm1, folForm2):
        if not isinstance(folForm1, FOLForm) or not isinstance(folForm2, FOLForm):
            raise TypeError
        self._folA = folForm1
        self._folB = folForm2

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self._folA == other._folA and self._folB == other._folB

    def __ne__(self, other):
        return self.__class__ != other.__class__ or self._folA != other._folA or self._folB != other._folB

    def __unicode__(self):
        return u'(%s \u2228 %s)' % (self._folA, self._folB)

    def to_smt(self):
        return sc.Or(self._folA.to_smt(), self._folB.to_smt())


class Imp(FOLForm):
    """An implication"""
    def __init__(self, folForm1, folForm2):
        if not isinstance(folForm1, FOLForm) or not isinstance(folForm2, FOLForm):
            raise TypeError
        self._folA = folForm1
        self._folB = folForm2

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self._folA == other._folA and self._folB == other._folB

    def __ne__(self, other):
        return self.__class__ != other.__class__ or self._folA != other._folA or self._folB != other._folB

    def __unicode__(self):
        return u'(%s) \u2192 (%s)' % (self._folA, self._folB)

    def to_smt(self):
        return sc.Implies(self._folA.to_smt(), self._folB.to_smt())


class Neg(FOLForm):
    """A negation"""
    def __init__(self, folForm):
        if not isinstance(folForm, FOLForm):
            raise TypeError
        self._fol = folForm

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self._fol == other._fol

    def __ne__(self, other):
        return self.__class__ != other.__class__ or self._fol != other._fol

    def __unicode__(self):
        return u'\u00AC%s' % self._fol

    def to_smt(self):
        return sc.Neg(self._fol.to_smt())


class Rel(FOLForm):
    """A relation"""
    def __init__(self, folPred, folVars):
        if not isinstance(folPred, FOLVar) or not iterable_type_check(folVars, FOLVar):
            raise TypeError
        self._pred = folPred.decode('utf-8')
        self._vars = [v.decode('utf-8') for v in folVars]

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self._pred == other._pred and self._vars == other._vars

    def __ne__(self, other):
        return self.__class__ != other.__class__ or self._pred != other._pred or self._vars != other._vars

    def __unicode__(self):
        return u'%s(%s)' % (self._pred, u','.join(self._vars))

    def to_smt(self):
        return sc.Function(sc.Symbol(self._pred), [sc.Symbol(x) for x in self._vars])


class Acc(FOLForm):
    """Acc relation"""
    def __init__(self, folVars):
        if not iterable_type_check(folVars, FOLVar):
            raise TypeError
        self._vars = [v.decode('utf-8') for v in folVars]

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self._vars == other._vars

    def __ne__(self, other):
        return self.__class__ != other.__class__ or self._vars != other._vars

    def __unicode__(self):
        return u'Acc(%s)' % u','.join(self._vars)

    def to_smt(self):
        return sc.Function(sc.Function(u'Acc'), [sc.Symbol(x) for x in self._vars])


class Top(FOLForm):
    """True constant"""

    def __eq__(self, other):
        return self.__class__ == other.__class__

    def __ne__(self, other):
        return self.__class__ != other.__class__

    def __neg__(self):
        return Bottom()

    def __unicode__(self):
        return u'\u22A4'

    def to_smt(self):
        return sc.TRUE


class Bottom(FOLForm):
    """False constant"""

    def __eq__(self, other):
        return self.__class__ == other.__class__

    def __ne__(self, other):
        return self.__class__ != other.__class__

    def __neg__(self):
        return Top()

    def __unicode__(self):
        return u'\u22A5'

    def to_smt(self):
        return sc.FALSE