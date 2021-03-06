from __future__ import unicode_literals, print_function
from utils import iterable_type_check, compare_lists_eq
import re
from marbles import safe_utf8_decode, safe_utf8_encode, future_string


## @defgroup showtypes Show notation
## @ingroup gconst
## @see Showable
## @{

## Display in box format
SHOW_BOX = 0

## Display in linear format
SHOW_LINEAR = 1

## Display in set format
SHOW_SET = 2

## Display in debug format
SHOW_DEBUG = 3
## @}

class Showable(object):
    """Like haskell show"""

    ## @cond

    # Symbols
    opNeg = u"\u00AC"
    opImp = u"\u21D2"
    opOr = u"\u2228"
    opDiamond = u"\u25C7"
    opBox = u"\u25FB"
    opLambda = u"\u03BB"
    opMerge = u"\u002B"

    opAMerge = u"\u002B"
    opPMerge = u"\u002A"
    modPointer = u"\u2190"
    modEquals = u"\u003D"
    modWeakSubord = u"\u2264"
    modStrictSubord = u"\u003C"

    # Box
    boxTopLeft = u'\u250C'
    boxTopRight = u'\u2510'
    boxBottomLeft = u'\u2514'
    boxBottomRight = u'\u2518'
    boxMiddleLeft = u'\u251C'
    boxMiddleRight = u'\u2524'
    boxHorLine = u'-'
    boxVerLine = u'|'

    ## @endcond

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
    def show_title_line(cls, n, title, lc, rc):
        """Shows a horizontal line of length n with left corner symbol ls and
        right corner symbol rc.

        Args:
            n: An integer.
            title: A unicode string
            lc: A unicode string.
            rc: A unicode string.

        Returns:
            A unicode string
        """
        k = len(title)
        if k >= (n - 2):
            return lc + title[0:n-2] + rc + u'\n'
        lm = (n - 2 - k) / 2
        rm = (n - 2 - k) - (n - 2 - k) / 2
        return lc + (cls.boxHorLine * lm) + title + (cls.boxHorLine * rm) + rc + u'\n'

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
        if len(m) == 0:
            return s
        lns = s.split(u'\n')
        k = len(m)
        if len(lns) <= p:
            return cls.show_concat(u' ' * k, s)
        ws = u' ' * (k+1)
        for i in range(p):
            lns[i] = ws + lns[i]
        lns[p] = m + u' ' + lns[p]
        for i in range(p+1, len(lns)-1):
            lns[i] = ws + lns[i]
        if len(lns[-1]) != 0:
            lns[-1] = ws + lns[-1]
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

    ## @property name
    @property
    def name(self):
        raise NotImplementedError

    def to_string(self):
        raise NotImplementedError


class DRSVar(AbstractDRSVar):
    """DRS variable"""
    _NumSuffix = re.compile(r'^([A-Za-z$@._-]+)(\d*)$')

    def __init__(self, name, idx=0):
        if isinstance(name, DRSVar):
            name = future_string(name)
        m = self._NumSuffix.match(name)
        if m is None:
            self._name = name
            self._idx = idx
        else:
            self._name = m.group(1)
            self._idx = idx if len(m.group(2)) == 0 or idx != 0 else int(m.group(2))

    def __str__(self):
        return safe_utf8_encode(self.to_string())

    def __unicode__(self):
        return safe_utf8_decode(self.to_string())

    def __eq__(self, other):
        return type(self) == type(other) and self.to_string() == other.to_string()

    def __ne__(self, other):
        return type(self) != type(other) or self.to_string() != other.to_string()

    def __hash__(self):
        return hash(self._idx) ^ hash(self._name)

    def __lt__(self, other):
        return type(self) == type(other) and self.to_string() < other.to_string()

    def __le__(self, other):
        return type(self) == type(other) and self.to_string() < other.to_string()

    def __gt__(self, other):
        return not self.__le__(other)

    def __ge__(self, other):
        return not self.__lt__(other)

    def increase_new(self):
        return DRSVar(self._name, self._idx + 1)

    ## @property idx
    @property
    def idx(self):
        return self._idx

    ## @property name
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

    def to_string(self):
        if self._idx  == 0: return self._name
        return '%s%i' % (self._name, self._idx)


class DRSConst(DRSVar):
    """DRS Constant. Refer to Muskens, 1996."""
    def __init__(self, *args, **kwargs):
        super(DRSConst, self).__init__(*args, **kwargs)

    def increase_new(self):
        return DRSConst(self._name, self._idx)
