#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import os
import sys

# Modify python path
projdir = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
pypath = os.path.join(projdir, 'src', 'python')
datapath = os.path.join(pypath, 'marbles', 'ie', 'drt')
sys.path.insert(0, pypath)
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


if __name__ == '__main__':
    print('This will take about 1 minute...')
    allfiles = []
    ldcpath = os.path.join(projdir, 'data', 'ldc', 'ccgbank_1_1', 'data', 'AUTO')
    outpath = os.path.join(projdir, 'data', 'ldc', 'mapping')
    if not os.path.exists(outpath):
        os.makedirs(outpath)
    dirlist1 = os.listdir(ldcpath)
    for dir1 in dirlist1:
        ldcpath1 = os.path.join(ldcpath, dir1)
        if os.path.isdir(ldcpath1):
            dirlist2 = os.listdir(ldcpath1)
            mapping = []
            for dir2 in dirlist2:
                ldcpath2 = os.path.join(ldcpath1, dir2)
                wsjnm, _ = os.path.splitext(dir2)
                if os.path.isfile(ldcpath2):
                    id = 1
                    with open(ldcpath2, 'r') as fd:
                        lines = fd.readlines()
                        for hdr,ccgbank in zip(lines[0::2], lines[1::2]):
                            mapping.append(b'%s.%d' % (wsjnm, id))
                            id += 1
            with open(os.path.join(outpath, 'ccg_map%s.txt' % dir1), 'w') as fd:
                fd.write(b'\n'.join(mapping))
