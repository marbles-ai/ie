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
from marbles.ie.ccg import parse_ccg_derivation2 as parse_ccg_derivation
from marbles.ie.ccg.utils import sentence_from_pt
from marbles.ie.semantics.ccg import extract_lexicon_from_pt
from marbles.ie.ccg import Category
from marbles import safe_utf8_encode, safe_utf8_decode


def die(s):
    print('Error: %s' %s)
    sys.exit(1)


def print_progress(progress, tick=1, done=False):
    progress += 1
    if (progress / tick) > 79 or done:
        sys.stdout.write('.\n')
        sys.stdout.flush()
        return 0
    elif (progress % tick) == 0:
        sys.stdout.write('.')
        sys.stdout.flush()
    return progress


idsrch = re.compile(r'^.*ccg_derivation(?P<id>\d+)\.txt')


def make_lexicon(daemon):
    global pypath, projdir, datapath, idsrch
    allfiles = []
    projdir = os.path.dirname(os.path.dirname(__file__))

    easysrl_path = os.path.join(projdir, 'data', 'ldc', daemon, 'lexicon')
    mappath = os.path.join(projdir, 'data', 'ldc', 'mapping')
    if not os.path.exists(easysrl_path):
        os.makedirs(easysrl_path)
    if not os.path.exists(os.path.join(easysrl_path, 'rt')):
        os.makedirs(os.path.join(easysrl_path, 'rt'))
    if not os.path.exists(os.path.join(easysrl_path, 'az')):
        os.makedirs(os.path.join(easysrl_path, 'az'))

    # Get files
    ldcpath = os.path.join(projdir, 'data', 'ldc', daemon, 'ccgbank')
    dirlist1 = sorted(os.listdir(ldcpath))
    #dirlist1 = ['ccg_derivation00.txt']
    for fname in dirlist1:
        if 'ccg_derivation' not in fname:
            continue
        ldcpath1 = os.path.join(ldcpath, fname)
        if os.path.isfile(ldcpath1):
            allfiles.append(ldcpath1)

    failed_parse = 0
    failed_ccg_derivation = []
    start_line = 0
    progress = -1
    dictionary = None
    allfiles = sorted(allfiles)
    section_map = {}
    for fn in allfiles:
        section = idsrch.match(fn)
        if section is None:
            continue
        section = section.group('id')

        with open(fn, 'r') as fd:
            lines = fd.readlines()

        # Get mapping
        mapfile = os.path.join(mappath, 'ccg_map%s.txt' % section)
        with open(mapfile, 'r') as fd:
            mapping = fd.readlines()
        for i, mm in zip(range(len(lines)), mapping):
            uid = '%s-%04d' % (section, i)
            mm = mm.strip()
            section_map[uid] = mm

        # Process lines
        name, _ = os.path.splitext(os.path.basename(fn))
        for i in range(start_line, len(lines)):
            start_line = 0
            ccgbank = lines[i].strip()
            if len(ccgbank) == 0 or ccgbank[0] == '#':
                continue

            if progress < 0:
                print('%s-%04d' % (name, i))
            else:
                progress = print_progress(progress, 10)

            try:
                # CCG parser is Java so output is UTF-8.
                ccgbank = safe_utf8_decode(ccgbank)
                pt = parse_ccg_derivation(ccgbank)
                s = sentence_from_pt(pt).strip()
            except Exception:
                failed_parse += 1
                raise
                continue

            uid = '%s-%04d' % (section, i)
            try:
                #dictionary[0-25][stem][set([c]), set(uid)]
                dictionary = extract_lexicon_from_pt(pt, dictionary, uid=uid)
            except Exception as e:
                print(e)
                raise
                continue

    rtdict = {}
    for section in range(len(dictionary)):
        fname = unichr(section+0x40)
        filepath = os.path.join(easysrl_path, 'az', fname + '.txt')
        with open(filepath, 'w') as fd:
            d = dictionary[section]
            for k, v in d.iteritems():
                # k == stem, v = {c: set(uid)}
                fd.write(b'<predicate name=\"%s\">\n' % safe_utf8_encode(k))
                for x, w in v.iteritems():
                    nc = x.split(':')
                    if len(nc) == 2:
                        c = Category.from_cache(Category(nc[1].strip()).clean(True))
                        fd.write(b'<usage final_atom=\"%s\" predarg=\"%s\" category=\"%s\">\n' %
                                 (safe_utf8_encode(nc[0].strip()), safe_utf8_encode(nc[1].strip()),
                                  safe_utf8_encode(c.signature)))
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
                    else:
                        continue
                    for y in sorted(w):
                        fd.write(b'sentence-id: %s|%s' % (safe_utf8_encode(y), safe_utf8_encode(section_map[y])))
                        fd.write(b'\n')
                    fd.write(b'</usage>\n')
                fd.write(b'</predicate>\n\n')
            # Free up memory
            dictionary[section] = None
            d = None
    for rt, cdict in rtdict.iteritems():
        fname = rt.signature.replace('[', '_').replace(']', '')
        filepath = os.path.join(easysrl_path, 'rt', fname + '.txt')
        with open(filepath, 'w') as fd:
            for c, vs in cdict.iteritems():
                fd.write(b'<category signature=\'%s\'>\n' % safe_utf8_encode(c))
                for v in vs:
                    fd.write(v)
                    fd.write(b'\n')
                fd.write(b'</category>\n\n')


if __name__ == '__main__':
    make_lexicon('easysrl')
    #make_lexicon('neuralccg')





