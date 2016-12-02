# Generic tag class used for a part-of-speech or a dependency-relation

class ConstantTag(object):
    '''Constant Tag class'''
    def __init__(self, idx, name):
        self._idx = idx
        self._name = name

    def __eq__(self, other):
        return isinstance(other, ConstantTag) and other._idx == self._idx

    def __ne__(self, other):
        return not isinstance(other, ConstantTag) or other._idx != self._idx

    def __lt__(self, other):
        return other._idx < self._idx

    def __gt__(self, other):
        return other._idx > self._idx

    def __le__(self, other):
        return other._idx <= self._idx

    def __ge__(self, other):
        return other._idx >= self._idx

    def __hash__(self):
        return (self._idx << 5) ^ (self._idx >> 27)

    def __repr__(self):
        return self._name

    @property
    def i(self):
        return self._idx

    @property
    def text(self):
        return self._name


