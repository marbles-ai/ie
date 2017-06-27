from __future__ import unicode_literals, print_function
from marbles import future_string
from marbles.ie.ccg import Category, CAT_CONJ


## @ingroup gfn
def extract_predarg_categories_from_pt(pt, lst=None):
    """Extract the predicate-argument categories from a CCG parse tree.

    Args:
        pt: The parse tree returned from marbles.ie.ccg.parse_ccg_derivation2().
        lst: An optional list of existing predicate categories.
    Returns:
        A list of Category instances.
    """
    global _PredArgIdx
    if future_string != unicode:
        pt = pt_to_utf8(pt)
    if lst is None:
        lst = []

    stk = [pt]
    while len(stk) != 0:
        pt = stk.pop()
        if pt[-1] == 'T':
            stk.extend(pt[1:-1])
        else:
            # Leaf nodes contains six fields:
            # <L CCGcat mod_POS-tag orig_POS-tag word PredArgCat>
            # PredArgCat example: (S[dcl]\NP_3)/(S[pt]_4\NP_3:B)_4>
            catkey = Category(pt[0])

            # Ignore atoms and conj rules.
            if not catkey.isfunctor or catkey.result_category() == CAT_CONJ or catkey.argument_category() == CAT_CONJ:
                continue

            predarg = Category(pt[4])
            assert catkey == predarg.clean(True)
            lst.append(predarg)
    return lst


## @ingroup gfn
def pt_to_utf8(pt, force=False):
    """Convert a parse tree to utf-8. The conversion is done in-place.

    Args:
        pt: The parse tree returned from marbles.ie.drt.parse.parse_ccg_derivation().

    Returns:
        A utf-8 parse tree
    """
    if force or isinstance(pt[0][0], unicode):  # isinstance(pt[-1], unicode)
        # Convert to utf-8
        stk = [pt]
        while len(stk) != 0:
            lst = stk.pop()
            for i in range(len(lst)):
                x = lst[i]
                if isinstance(x, list):
                    stk.append(x)
                elif isinstance(x, unicode):
                    lst[i] = x.encode('utf-8')
    return pt


## @ingroup gfn
def sentence_from_pt(pt):
    """Get the sentence from a CCG parse tree.

    Args:
        pt: The parse tree returned from marbles.ie.drt.parse.parse_ccg_derivation().

    Returns:
        A string
    """
    s = []
    stk = [pt]
    while len(stk) != 0:
        pt = stk.pop()
        if pt[-1] == 'T':
            stk.extend(reversed(pt[1:-1]))
        else:
            s.append(pt[1])
    return ' '.join(s).replace(' ,', ',').replace(' .', '.')