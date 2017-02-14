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


def union(a, *args):
    '''Union two lists.'''
    y = []
    y.extend(a)
    for b in args:
        y.extend(filter(lambda x: x not in a, b))
    return y


def union_inplace(a, *args):
    for b in args:
        for x in b:
            if x not in a: a.append(x)
    return a


def complement(a, b, sorted=False):
    '''Remove b from a.'''
    if sorted:
        # optimize for sorted lists
        pass
    return filter(lambda x: x not in b, a)


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


def rename_var(v, rs):
    """Renames a variable v, iff v occurs in a variable conversion list. Otherwise, v is returned unmodified"""
    for r,s in rs:
        if v == r: return s
    return v


def remove_dups(orig):
    """Remove duplicates from a list but maintain ordering"""
    uniq = set(orig)
    r = []
    for o in orig:
        if o in uniq:
            r.append(o)
            uniq.discard(o)
    return r


def compare_lists_eq(l1, l2):
    if len(l1) != len(l2):
        return False
    s1 = set(l1)
    s2 = set(l2)
    return len(s1.intersection(s2)) == len(s2)

