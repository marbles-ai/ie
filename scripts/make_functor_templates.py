#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import pickle
import sys

# Modify python path
projdir = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
pypath = os.path.join(projdir, 'src', 'python')
datapath = os.path.join(pypath, 'marbles', 'ie', 'drt')
sys.path.insert(0, pypath)

from marbles.ie.drt.ccg2drs import extract_predarg_categories_from_pt, FunctorTemplate
from marbles.ie.drt.parse import parse_ccg_derivation

if __name__ == "__main__":
    allfiles = []
    ldcpath = os.path.join(projdir, 'data', 'ldc', 'ccgbank_1_1', 'data', 'AUTO')
    dirlist1 = os.listdir(ldcpath)
    for dir1 in dirlist1:
        ldcpath1 = os.path.join(ldcpath, dir1)
        if os.path.isdir(ldcpath1):
            dirlist2 = os.listdir(ldcpath1)
            for dir2 in dirlist2:
                ldcpath2 = os.path.join(ldcpath1, dir2)
                if os.path.isfile(ldcpath2):
                    allfiles.append(ldcpath2)

    dict = {}
    failed_parse = []
    failed_rules = []
    rules = []
    for fn in allfiles:
        with open(fn, 'r') as fd:
            lines = fd.readlines()
        for hdr,ccgbank in zip(lines[0:2:], lines[1:2:]):
            try:
                pt = parse_ccg_derivation(ccgbank)
                extract_predarg_categories_from_pt(pt, rules)
            except Exception as e:
                failed_parse.append((ccgbank, str(e)))

    dict = {}
    for predarg in rules:
        try:
            catkey = predarg.clean(True)
            template = FunctorTemplate.create_from_category(predarg)
            if template is None:
                continue
            if catkey.ccg_signature not in dict:
                dict[catkey.ccg_signature] = template
            else:
                # verify
                t1 = str(dict[catkey.ccg_signature])
                t2 = str(template)
                assert t1 == t2
        except Exception as e:
            failed_rules.append((predarg, str(e)))
            # DEBUG ?
            if True:
                try:
                    FunctorTemplate.create_from_category(predarg)
                except Exception:
                    pass

    if len(failed_parse) != 0:
        print('THERE ARE %d PARSE FAILURES' % len(failed_parse))
        with open(os.path.join(datapath, 'test', 'parse_ccg_derivation_failed.dat'), 'w') as fd:
            pickle.dump(failed_parse, fd)
        if False:
            for x, m in failed_parse:
                print(m)
                print(x.strip())

    if len(failed_rules) != 0:
        print('THERE ARE %d RULE FAILURES' % len(failed_rules))
        with open(os.path.join(datapath, 'functor_templates_failed.dat'), 'w') as fd:
            pickle.dump(failed_rules, fd)
        if False:
            for x, m in failed_rules:
                print(m)
                print(x.ccg_category)

    print('THE FOLLOWING WERE PROCESSED WITHOUT ERROR')
    for k, v in dict.iteritems():
        print('%s: %s' % (k, str(v)))

    with open(os.path.join(datapath, 'functor_templates.dat'), 'wb') as fd:
        pickle.dump(dict, fd)

