#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import os
import re
import sys

# Modify python path
projdir = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
pypath = os.path.join(projdir, 'src', 'python')
sys.path.insert(0, pypath)


from marbles.ie.kb.spell import SymSpell


idsrch = re.compile(r'[^.]+\.(?P<id>\d+)\.raw')

if __name__ == '__main__':
    ldcpath = os.path.join(projdir, 'data', 'ldc', 'ccgbank_1_1', 'data', 'RAW')
    dirlist = os.listdir(ldcpath)
    spellchecker = SymSpell()

    stats = (0, 0)
    for fname in dirlist:
        print(fname)
        ldcpath1 = os.path.join(ldcpath, fname)

        m = idsrch.match(os.path.basename(ldcpath1))
        if m is None:
            continue

        stats = spellchecker.build_from_corpus(ldcpath1, stats)

    print("total words processed: %i" % stats[0])
    print("total unique words in corpus: %i" % stats[1])
    print("total items in dictionary (corpus words and deletions): %i" % len(spellchecker.dictionary))
    print("  edit distance for deletions: %i" % spellchecker.max_edit_distance)
    print("  length of longest word in corpus: %i" % spellchecker.longest_word_length)
    spellchecker.save(os.path.join(pypath, 'marbles', 'ie', 'kb', 'data', 'dictionary-en.dat'))


