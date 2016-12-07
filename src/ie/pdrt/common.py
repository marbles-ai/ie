from utils import iterable_type_check


# Show notations
SHOW_BOX = 0
SHOW_LINEAR = 1
SHOW_SET = 2
SHOW_DEBUG = 3


class Showable(object):
    """Like haskell show"""

    # Symbols
    opNeg = u"\u00AC"
    opImp = u"\u21D2"
    opOr = u"\u2228"
    opDiamond = u"\u25C7"
    opBox = u"\u25FB"
    opLambda = u"\u03BB"
    opMerge = u"\u002B"

    # Box
    boxTopLeft = u'\u250C'
    boxTopRight = u'\u2510'
    boxBottomLeft = u'\u2514'
    boxBottomRight = u'\u2518'
    boxMiddleLeft = u'\u251C'
    boxMiddleRight = u'\u2524'
    boxHorLine = u'-'
    boxVerLine = u'|'

    def show(self, notation):
        """Display for screen.

        Args:
            notation: An integer notation.

        Returns:
            A unicode string.
        """
        raise NotImplementedError

    @classmethod
    def show_concat(cls, ss1, ss2):
        """Shows the line by line concatenation of two lists of Strings.

        Args:
            ss1: A unicode string
            ss2: A unicode string

        Returns:
            A unicode string
        """
        ls1 = ss1.split(u'\n')
        ls2 = ss2.split(u'\n')
        if len(ss2) == 0:
            return u'\n'.join([x + u' ' for x in ls1])
        elif len(ss1) == 0:
            return u'\n'.join([u' ' + x for x in ls2])

        result = []
        n2 = len(ls2[0])
        for s1,s2 in zip(ls1,ls2):
            result.append(s1 + s2)

        if len(ls1) < len(ls2):
            n = len(ls1[0]) + 1
            for s2 in ls2[len(ls1):]:
                result.append(u' ' * n + s2)
        elif len(ls2) < len(ls1):
            n = len(ls2[0]) + 1
            for s1 in ls1[len(ls2):]:
                result.append(s2 + (u' ' * n))
        return u'\n'.join(result)

    @classmethod
    def show_content(cls, n, s):
        """Shows the content of a DRS box surrounded by vertical bars.

        Args:
            n: An integer
            s: a unicode string

        Returns:
            A unicode string
        """
        ls = s.split(u'\n')
        return u'\n'.join(map(lambda x: cls.boxVerLine + u' ' + x + (u' ' * (n - 4 - len(x))) + u' ' + cls.boxVerLine, ls))

    @classmethod
    def show_horz_line(cls, n, lc, rc):
        """Shows a horizontal line of length n with left corner symbol ls and
        right corner symbol rc.

        Args:
            n: An integer.
            lc: A unicode string.
            rc: A unicode string.

        Returns:
            A unicode string
        """
        return lc + (cls.boxHorLine * (n - 2)) + rc + u'\n'

    @classmethod
    def show_modifier(cls, m, p, s):
        """Shows a modifier m at line number p in front of String s

        Args:
            m: A modifier string.
            p: An integer.
            s: A unicode string.

        Returns:
            A unicode string.
        """
        if len(m) == 0: return s
        lns = s.split(u'\n')
        k = len(m)
        if len(lns) <= p:
            return cls.show_concat(u' ' * k, s)
        ws = u' ' * (k+1)
        for i in range(p):
            lns[i] = ws + lns[i]
        lns[p] = m + u' ' + lns[p]
        for i in range(p+1,len(lns)):
            lns[i] = ws + lns[i]
        return u'\n'.join(lns)

    @classmethod
    def show_padding(cls, s):
        n = len(s) - 1
        return (u' ' * n) + u'\n' + (u' ' * n) + u'\n' + s


class AbstractDRSVar(Showable):
    """Abstract DRS Variable"""
    def increase_new(self):
        raise NotImplementedError
    def idx(self):
        raise NotImplementedError
    @property
    def name(self):
        raise NotImplementedError


# DRS variable
class DRSVar(AbstractDRSVar):
    def __init__(self, name, idx=0):
        self._name = name
        self._idx = idx

    def __repr__(self):
        return 'DRSVar(%s)' % self.__str__()

    def __str__(self):
        if self._idx  == 0: return self._name
        return '%s%i' % (self._name, self._idx)

    def __unicode__(self):
        if self._idx == 0: return self._name.decode('utf-8')
        return u'%s%i' % (self._name, self._idx)

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self._name == other._name and self._idx == other._idx

    def __ne__(self, other):
        return self.__class__ == other.__class__ or self._name != other._name or self._idx != other._idx

    def __hash__(self):
        return hash(self._idx) ^ hash(self._name)

    def __lt__(self, other):
        return self.__class__ == other.__class__ and (self.idx < other.idx or (self._idx == other._idx and self._name < other._name))

    def __le__(self, other):
        return self.__class__ == other.__class__ and (self.idx < other.idx or (self._idx == other._idx and self._name <= other._name))

    def __gt__(self, other):
        return not self.__le__(other)

    def __ge__(self, other):
        return not self.__lt__(other)

    def increase_new(self):
        return DRSVar(self._name, self._idx + 1)

    @property
    def idx(self):
        return self._idx

    @property
    def name(self):
        return self._name

    def show(self, notation):
        """Display for screen.

        Args:
            notation: An integer notation.

        Returns:
            A unicode string.
        """
        return unicode(self)


class LambdaDRSVar(AbstractDRSVar):
    def __init__(self, drsVar, drsVarSet):
        """A lambda DRS.

        Args:
            drsVar: A variable.
            drsVarSet: The set of referents to be applied to the DRS.
        """
        if not isinstance(drsVar, DRSVar) or not iterable_type_check(drsVarSet, DRSVar):
            raise TypeError
        self._var = drsVar
        self._set = drsVarSet

    def __ne__(self, other):
        return other._var != self._var or other._set != self._set

    def __eq__(self, other):
        return other._var == self._var and other._set == self._set

    def __repr__(self):
        return 'LambdaDRSVar(%s,%s)' % (self._var, self._set)

    def __str__(self):
        return str(self._var)

    def __unicode__(self):
        return unicode(self._var)

    def __hash__(self):
        return hash(self._var) ^ hash(self._set)

    def __lt__(self, other):
        return self._var < other._var

    def __le__(self, other):
        return self._var <= other._var

    def __gt__(self, other):
        return not self.__le__(other)

    def __ge__(self, other):
        return not self.__lt__(other)

    # @remarks Original code in `/pdrt-sandbox/src/Data/DRS/Show.hs:showDRSLambdas`
    def _show_lambdas(self):
        return self.opLambda + unicode(self._var) + u'.'

    @property
    def var(self):
        return self._var

    @property
    def referents(self):
        return self._set

    @property
    def idx(self):
        return self._var.idx

    @property
    def name(self):
        return self._var.name

    def increase_new(self):
        # TODO: check implementation
        return LambdaDRSVar(self._var.increase_new(), self._set)

    def show(self, notation):
        """Display for screen.

        Args:
            notation: An integer notation.

        Returns:
            A unicode string.
        """
        if len(self._set) == 0:
            return unicode(self)
        return unicode(self) + u'(' + u','.join([unicode(x) for x in self._set]) + u')'

