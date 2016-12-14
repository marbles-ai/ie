from utils import iterable_type_check
from common import Showable
from common import SHOW_BOX


class FOLConversionError(Exception):
    """For conversion errors"""
    pass


FOLVar = str
FOLPred = str


class FOLForm(Showable):
    """Abstract FOLForm"""

    ## remarks Original code in FOL/Show.hs
    def show(self):
        raise NotImplementedError

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __repr__(self):
        return self.__str__()

    def show(self, notation):
        if notation == SHOW_BOX:
            return u'\n' + unicode(self) + u'\n'
        return unicode(self)


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