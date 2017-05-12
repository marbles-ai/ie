class VectorMap(object):
    '''Helper for dispatchers. Should be faster than a dictionary, especially
    for large documents, since clear, insert and lookup are done in O(1) time.
    '''

    def __init__(self, size):
        '''Constructor

        Args:
            size: The maximum size of the map.
        '''
        self._tokMap = [0] * size
        self._tokLimit = 0
        self._default = None
        self._map = []

    def set_default_lookup(self, default):
        '''Sets the default returned by lookup when it fails. If not set
        None is returned.

        Args:
            default: The default lookup value.
        '''
        self._default = default

    def insert_new(self, key, value):
        '''Insert value at key if the key is not mapped else do nothing.

        Args:
            key: An integer or Token
            value: The value associated with key.

        Returns:
            True if the inserted, false if not.
        '''
        if not isinstance(key, int): key = key.i
        if key >= len(self._tokMap):
            raise KeyError
        if (self._tokMap[key] >= self._tokLimit or self._map[self._tokMap[key]][0] != key):
            self._tokMap[key] = self._tokLimit
            if self._tokLimit < len(self._map):
                self._map[self._tokLimit] = (key, value)
            else:
                assert self._tokLimit == len(self._map)
                self._map.append((key, value))
            self._tokLimit += 1
            return True
        return False

    def clear(self, deep=True):
        '''Clears the map to an empty state.

        Args:
            deep: If true do a deep reset in O(N) time, else do a shallow reset
                in O(1) time.
        '''
        # Once fully debugged we can set default deep=False.
        if deep:
            for i in range(self._tokLimit):
                self._map[i] = None
        self._tokLimit = 0

    def append(self, key, value):
        '''Append an item to the value list associated with key.

        Args:
            key: The key. If the key does not exists value is added at key. if
                the key does exist value is appended to the value list at key.
            value: An instance of Token.
        '''
        if not isinstance(key, int): key = key.i
        if not self.insert_new(key, [value]):
            self._map[self._tokMap[key]][1].append(value)

    def extend(self, key, value):
        '''Extend the value list associated with key.

        Args:
            key: The key. If the key does not exists value is added at key. if
                the key does exist value is appended to the value list at key.
            value: An instance of Token or a list of Token instances.
        '''
        if not isinstance(key, int): key = key.i
        if not self.insert_new(key, [value]):
            self._map[self._tokMap[key]][1].extend(value)

    def lookup(self, key, nodefault=False):
        '''Get the value at key.

        Args:
            key: An integer or Token.
            nodefault: Don't return default value, i.e. return None if not found.

        Returns:
             The value at key. If not found then the default value is returned.

        See Also:
            set_default_lookup()
        '''
        if not isinstance(key, int): key = key.i
        if key < len(self._tokMap):
            if self._tokMap[key] < self._tokLimit and self._map[self._tokMap[key]][0] == key:
                return self._map[self._tokMap[key]][1]
        if nodefault:
            return None
        return self._default

    def replace(self, key, value):
        '''Replace the current value at key with a new value.

        Args:
            key: An integer or Token
            value: The new value.
        '''
        if not isinstance(key, int): key = key.i
        if key >= len(self._tokMap): raise KeyError
        if self._tokMap[key] < self._tokLimit and self._map[self._tokMap[key]][0] == key:
            # map items are a tuple so keep list reference
            L = self._map[self._tokMap[key]][1]
            if isinstance(L, list):
                del L[0:len(L)]
                L.extend(value)
            else:
                # Remove and add new
                self.remove(key)
                self.insert_new(key, value)

    def remove(self, key):
        '''Remove a key from the map

        Args:
            key: An integer or Token
            value: The new value.
        '''
        if not isinstance(key, int): key = key.i
        if self._tokMap[key] < self._tokLimit and self._map[self._tokMap[key]][0] == key:
            idx = self._tokMap[key]
            self._tokMap[key] = 0 # don't really need to do this
            if (self._tokMap[key]+1) < self._tokLimit:
                # Swap with back
                self._map[idx] = self._map[self._tokLimit-1][1]
                self._tokMap[self._map[self._tokLimit-1][0]] = idx
                self._map[self._tokLimit - 1] = None
            else:
                self._map[idx] = None
            self._tokLimit -= 1

    def __len__(self):
        # Iterable override
        return self._tokLimit

    def __getitem__(self, slice_i_j):
        # Iterable override
        if isinstance(slice_i_j, slice):
            return self._map(range(slice_i_j))
        return self._map[slice_i_j]

    def __iter__(self):
        # Iterable override
        for i in range(self._tokLimit):
            yield self._map[i]