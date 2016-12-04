
class AbstractDRSVar(object):
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
    def __init__(self, name):
        self._name = name
        self._idx = None

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        if self._idx is None: return self._name
        return '%s@%i' % (self._name, self._idx)

    def __eq__(self, other):
        return self._name == other._name and (self._idx or -1) == (other._idx or -1)

    def __ne__(self, other):
        return self._name != other._name or (self._idx or -1) != (other._idx or -1)

    def __hash__(self):
        return hash(self._idx or 0) ^ hash(self._name)

    def __lt__(self, other):
        return self.idx < other.idx or (self.idx == other.idx and self._name < other._name)

    def __le__(self, other):
        return self.idx < other.idx or (self.idx == other.idx and self._name <= other._name)

    def __gt__(self, other):
        return not self.__le__(other)

    def __ge__(self, other):
        return not self.__lt__(other)

    def increase_new(self):
        if self._idx is None:
            return DRSVar(self._name, 1)
        return DRSVar(self._name, self._idx + 1)

    @property
    def idx(self):
        return self._idx or 0

    @property
    def name(self):
        return self._name


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
        return '(%s, %s)' % (self._var, self._set)

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
        return LambdaDRSVar(self._name, self._var.idx + 1)


