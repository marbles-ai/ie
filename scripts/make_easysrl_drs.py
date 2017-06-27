#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import os
import re
import sys

# Modify python path
projdir = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
pypath = os.path.join(projdir, 'src', 'python')
datapath = os.path.join(pypath, 'marbles', 'ie', 'drt')
sys.path.insert(0, pypath)


#from marbles.ie.parse import parse_ccg_derivation
from marbles.ie.core.constants import *
from marbles.ie.ccg import parse_ccg_derivation2 as parse_ccg_derivation, sentence_from_pt
from marbles.ie.semantics.ccg import process_ccg_pt, pt_to_ccgbank
from marbles.ie.drt.common import SHOW_LINEAR
from marbles.ie.drt.drs import DRS
from marbles import safe_utf8_encode


def die(s):
    print('Error: %s' %s)
    sys.exit(1)


def print_progress(progress, tick=1, done=False):
    progress += 1
    if (progress / tick) >= 79 or done:
        sys.stdout.write('.\n')
        sys.stdout.flush()
        return 0
    elif (progress % tick) == 0:
        sys.stdout.write('.')
        sys.stdout.flush()
    return progress


idsrch = re.compile(r'^.*ccg_derivation(?P<id>\d+)\.txt')


if __name__ == '__main__':
    allfiles = []
    projdir = os.path.dirname(os.path.dirname(__file__))

    easysrl_path = os.path.join(projdir, 'data', 'ldc', 'easysrl', 'drs')
    if not os.path.exists(easysrl_path):
        os.makedirs(easysrl_path)

    # Get files
    ldcpath = os.path.join(projdir, 'data', 'ldc', 'easysrl', 'ccgbank')
    dirlist1 = os.listdir(ldcpath)
    for fname in dirlist1:
        if 'ccg_derivation' not in fname:
            continue
        ldcpath1 = os.path.join(ldcpath, fname)
        if os.path.isfile(ldcpath1):
            allfiles.append(ldcpath1)

    failed_parse = 0
    failed_ccg2drs = []
    start = 119
    progress = -1
    for fn in allfiles:
        idx = idsrch.match(fn)
        if idx is None:
            continue
        idx = idx.group('id')

        if not os.path.exists(os.path.join(easysrl_path, idx)):
            os.mkdir(os.path.join(easysrl_path, idx))

        with open(fn, 'r') as fd:
            lines = fd.readlines()

        name, _ = os.path.splitext(os.path.basename(fn))
        for i in range(start, len(lines)):
            start = 0
            ccgbank = lines[i].strip()
            if len(ccgbank) == 0 or ccgbank[0] == '#':
                continue

            if progress < 0:
                print('%s-%04d' % (name, i))
            else:
                progress = print_progress(progress, 10)

            try:
                # CCG parser is Java so output is UTF-8.
                pt = parse_ccg_derivation(ccgbank)
                s = sentence_from_pt(pt).strip()
                pccg = pt_to_ccgbank(pt)
            except Exception:
                failed_parse += 1
                raise
                continue

            try:
                d = process_ccg_pt(pt, CO_VERIFY_SIGNATURES | CO_ADD_STATE_PREDICATES).get_drs()
                assert d is not None
                assert isinstance(d, DRS)
                d = d.show(SHOW_LINEAR).strip()
            except Exception as e:
                print(e)
                failed_ccg2drs.append((name, i, ccgbank))
                raise
                continue

            with open(os.path.join(easysrl_path, idx, 'drs_%s_%04d.dat' % (idx, i)), 'w') as fd:
                fd.write(b'<sentence>\n')
                fd.write(safe_utf8_encode(s))
                fd.write(b'\n</sentence>\n<drs>\n')
                fd.write(safe_utf8_encode(d))
                fd.write(b'\n</drs>\n<predarg>\n')
                fd.write(safe_utf8_encode(pccg))
                fd.write(b'\n')
                fd.write(b'</predarg>\n')

    if failed_parse != 0:
        print('%d derivations failed to parse' % failed_parse)
    if len(failed_ccg2drs) != 0:
        print('%d derivations failed to convert to DRS' % len(failed_ccg2drs))
        for x in failed_ccg2drs:
            print('%s-%04d failed: {%s}' % x)



