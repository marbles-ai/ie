"""A thread safe cache."""

from __future__ import unicode_literals, print_function
from collections import MutableMapping
from threading import Lock
import pickle
from marbles import safe_utf8_encode, safe_utf8_decode, future_string, native_string


class Freezable(object):
    """Frozen objects require strict equality based on instance id."""
    def __init__(self):
        self._freeze = False

    @property
    def isfrozen(self):
        """Test if a cache entry is frozen."""
        return self._freeze

    def freeze(self, frozen=True):
        """Freeze a cache entry so equality requires same object id."""
        self._freeze = frozen


class ConstString(Freezable):
    """String which is shared as a key and value part of a cache."""
    def __init__(self, s=None):
        super(ConstString, self).__init__()
        self._s = future_string(s) if s is not None else ''
        self._h = hash(self._s)

    def __str__(self):
        return safe_utf8_encode(self._s)

    def __unicode__(self):
        return safe_utf8_decode(self._s)

    def __repr__(self):
        return native_string(self._s)

    def __hash__(self):
        return self._h

    def __eq__(self, other):
        return self is other if self.isfrozen and other.isfrozen else other._s == self._s

    def __ne__(self, other):
        return self is not other if self.isfrozen and other.isfrozen else other._s != self._s

    def __lt__(self, other):
        return self._s < other._s

    def __le__(self, other):
        return self._s <= other._s

    def __gt__(self, other):
        return self._s > other._s

    def __ge__(self, other):
        return self._s >= other._s

    @property
    def signature(self):
        return self._s


class Cache(MutableMapping):
    """A cache object for managing types."""
    def __init__(self):
        self._ro_dict = {}
        self._rw_dict = {}
        self._lock = Lock()

    def __getitem__(self, key):
        try:
            v = self._ro_dict[key]
            return v
        except KeyError:
            with self._lock:
                v = self._rw_dict[key]
            return v

    def __setitem__(self, key, value):
        with self._lock:
            self._rw_dict[key] = value

    def __delitem__(self, key):
        with self._lock:
            del self._rw_dict[key]

    def __len__(self):
        # Must do this thread safe. Typically never called for caches.
        with self._lock:
            return len(self._rw_dict) + len(self._ro_dict)

    def __iter__(self):
        for x in self._ro_dict.iteritems():
            yield x
        # To avoid potential dead lock we must copy the rw part
        with self._lock:
            rw = [x for x in self._rw_dict.iteritems()]
        for x in rw:
            yield x

    def initialize(self, kv_pairs):
        """Initialize the read only part of the cache.

        Args:
            kv_pairs: Key-value pairs

        Returns:
            self.

        Remarks:
            Not thread safe. Do once before using cache.
        """
        for k, v in kv_pairs:
            if k not in self._ro_dict:
                self._ro_dict[k] = v
        return self

    def addinit(self, kv_pair, replace=False):
        """Add to the read only part of the cache.

        Args:
            kv_pair: A Key-value pair
            replace: If True replace the existing entry.

        Returns:
            self.

        Remarks:
            Not thread safe. Do all addinit()'s before using cache.
        """
        k, v = kv_pair
        if k not in self._ro_dict or replace:
            self._ro_dict[k] = v
        return self

    def save(self, filename):
        """Save the cache to a file.

        Args:
            filename: The file name and path.

        Remarks:
            Is threadsafe.
        """
        if len(self) == 0:
            return
        d = {}
        for k, v in self._ro_dict.iteritems():
            d[k] = v
        with self._lock:
            for k, v in self._rw_dict.iteritems():
                d[k] = v

        with open(filename, 'wb') as fd:
            pickle.dump(d, fd)

    def load(self, filename):
        """Load the cache from a file.

        Args:
            filename: The file name and path.

        Remarks:
            Not threadsafe.
        """
        with open(filename, 'rb') as fd:
            self._ro_dict = pickle.load(fd)





