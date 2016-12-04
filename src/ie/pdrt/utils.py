import collections


def iterable_type_check(theList, type_info, emptyOK=True):
    if not isinstance(theList, collections.Iterable):
        return False
    if not emptyOK and len(theList) == 0:
        return False
    for i in theList:
        if not isinstance(i,type_info):
            return False
    return True


def union(a, b, sorted=False):
    '''Union two lists.'''
    if sorted:
        # optimize for sorted lists
        pass
    y = []
    y.extend(a)
    y.extend(filter(lambda x: x not in a, b))
    return y


def union_inplace(a, b, sorted=False):
    for x in b:
        if x not in a: a.append(x)
    return a


def complement(a, b, sorted=False):
    '''Remove b from a.'''
    if sorted:
        # optimize for sorted lists
        pass
    return filter(lambda x: x not in a, b)


def intersect(a, b, sorted=False):
    '''Find common elements.'''
    if sorted:
        # optimize for sorted lists
        pass
    return filter(lambda x: x in a, b) if len(a)<len(b) else filter(lambda x: x in b, a)


def partition(predicate, a):
    x = []
    y = []
    for k in a:
        if predicate(k):
            x.append(k)
        else:
            y.append(k)
    return (x,y)