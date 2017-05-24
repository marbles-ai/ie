#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import re
import sys

# Modify python path
projdir = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
pypath = os.path.join(projdir, 'src', 'python')
datapath = os.path.join(pypath, 'marbles', 'ie', 'drt')
sys.path.insert(0, pypath)


#from marbles.ie.parse import parse_ccg_derivation
from marbles.ie.ccg2drs import parse_ccg_derivation2 as parse_ccg_derivation
from marbles.ie.ccg2drs import sentence_from_pt, extract_lexicon_from_pt
from marbles.ie.ccg.cat import Category


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

    easysrl_path = os.path.join(projdir, 'data', 'ldc', 'easysrl', 'lexicon')
    if not os.path.exists(easysrl_path):
        os.makedirs(easysrl_path)
    if not os.path.exists(os.path.join(easysrl_path, 'rt')):
        os.makedirs(os.path.join(easysrl_path, 'rt'))
    if not os.path.exists(os.path.join(easysrl_path, 'az')):
        os.makedirs(os.path.join(easysrl_path, 'az'))

    # Get files
    ldcpath = os.path.join(projdir, 'data', 'ldc', 'easysrl', 'ccgbank')
    dirlist1 = sorted(os.listdir(ldcpath))
    for fname in dirlist1:
        if 'ccg_derivation' not in fname:
            continue
        ldcpath1 = os.path.join(ldcpath, fname)
        if os.path.isfile(ldcpath1):
            allfiles.append(ldcpath1)

    failed_parse = 0
    failed_ccg2drs = []
    start = 0
    progress = -1
    dictionary = None
    for fn in allfiles:
        idx = idsrch.match(fn)
        if idx is None:
            continue
        idx = idx.group('id')

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
            except Exception:
                failed_parse += 1
                continue

            uid = '%s-%04d' % (idx, i)
            try:
                dictionary = extract_lexicon_from_pt(pt, dictionary, uid=uid)
            except Exception as e:
                print(e)
                continue

    rtdict = {}
    for idx in range(len(dictionary)):
        fname = chr(idx+0x41)
        filepath = os.path.join(easysrl_path, 'az', fname + '.txt')
        with open(filepath, 'w') as fd:
            d = dictionary[idx]
            for k, v in d.iteritems():
                fd.write('<predicate name=\'%s\'>\n' % k)
                for x in v[0]:
                    fd.write(x)
                    fd.write('\n')
                    nc = x.split(':')
                    if len(nc) == 2:
                        c = Category.from_cache(Category(nc[1].strip()).clean(True))
                        # Return type atom
                        rt = c.extract_unify_atoms(False)[-1]
                        if rt in rtdict:
                            cdict = rtdict[rt]
                            if c in cdict:
                                cdict[c].append(nc[0])
                            else:
                                cdict[c] = [nc[0]]
                        else:
                            rtdict[rt] = {c: [nc[0]]}
                for x in v[1]:
                    fd.write('sentence id: ' + x)
                    fd.write('\n')
                fd.write('</predicate>\n')
            # Free up memory
            dictionary[idx] = None
            d = None
    for rt, cdict in rtdict.iteritems():
        fname = rt.signature.replace('[', '_').replace(']', '')
        filepath = os.path.join(easysrl_path, 'rt', fname + '.txt')
        with open(filepath, 'w') as fd:
            for c, vs in cdict.iteritems():
                fd.write('<category signature=\'%s\'>\n' % c.signature)
                for v in vs:
                    fd.write(v)
                    fd.write('\n')
                fd.write('</category>\n\n')








