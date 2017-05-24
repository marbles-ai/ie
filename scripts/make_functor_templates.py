#!/usr/bin/env python
# -*- coding: utf-8 -*-
import datetime
import os
import sys
from optparse import OptionParser

# Modify python path
projdir = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
pypath = os.path.join(projdir, 'src', 'python')
datapath = os.path.join(pypath, 'marbles', 'ie', 'ccg', 'data')
sys.path.insert(0, pypath)

from marbles.ie.ccg2drs import extract_predarg_categories_from_pt
from marbles.ie.ccg.model import FunctorTemplate, Model
from marbles.ie.ccg.cat import Category
from marbles.ie.utils.cache import Cache
from marbles.ie.ccg2drs import parse_ccg_derivation2 as parse_ccg_derivation
#from marbles.ie.parse import parse_ccg_derivation


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


def build_from_ldc_ccgbank(dict, outdir, verbose=False, verify=True):
    print('Building function templates from LDC ccgbank...')

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

    failed_parse = []
    failed_rules = []
    rules = []
    progress = 0
    for fn in allfiles:
        progress = print_progress(progress, 10)
        with open(fn, 'r') as fd:
            lines = fd.readlines()
        for hdr,ccgbank in zip(lines[0::2], lines[1::2]):
            try:
                pt = parse_ccg_derivation(ccgbank)
                extract_predarg_categories_from_pt(pt, rules)
            except Exception as e:
                failed_parse.append('CCGBANK: ' + ccgbank.strip())
                failed_parse.append('Error: ' + str(e))

    progress = (progress / 10) * 1000
    for predarg in rules:
        progress = print_progress(progress, 1000)
        try:
            catkey = predarg.clean(True)
            template = FunctorTemplate.create_from_category(predarg)
            if template is None:
                continue
            if catkey.signature not in dict:
                dict[catkey.signature] = template
            elif verify:
                f1 = dict[catkey.signature]
                t1 = str(f1)
                t2 = str(template)
                assert t1 == t2, 'verify failed\n  t1=%s\n  t2=%s\n  f1=%s\n  f2=%s' % (t1, t2, f1.predarg_category, predarg)
        except Exception as e:
            failed_rules.append(str(predarg) + ': ' + str(e))
            # DEBUG ?
            if False:
                try:
                    FunctorTemplate.create_from_category(predarg)
                except Exception:
                    pass

    print_progress(progress, done=True)

    if len(failed_parse) != 0:
        print('Warning: ldc - %d parses failed' % (len(failed_parse)/2))
        with open(os.path.join(outdir, 'parse_ccg_derivation_failed.dat'), 'w') as fd:
            fd.write('\n'.join(failed_parse))
        if verbose:
            for x, m in failed_parse:
                print(m)

    if len(failed_rules) != 0:
        print('Warning: ldc - %d rules failed' % len(failed_rules))
        with open(os.path.join(outdir, 'functor_ldc_templates_failed.dat'), 'w') as fd:
            fd.write('\n'.join(failed_rules))
        if verbose:
            for m in failed_rules:
                print(m)

    return dict


def build_from_easysrl(dict, outdir, modelPath, verbose=False, verify=True):
    print('Building function templates from EasySRL model folder...')
    fname = os.path.join(modelPath, 'markedup')
    if not os.path.exists(fname) or not os.path.isfile(fname):
        print('Error: easysrl - %s does not exist or is not a file' % fname)

    with open(fname, 'r') as fd:
        signatures = fd.readlines()

    failed_rules = []
    progress = 0
    for sig in signatures:
        predarg = Category(sig.strip())
        progress = print_progress(progress, 1000)
        try:
            catkey = predarg.clean(True)
            template = FunctorTemplate.create_from_category(predarg)
            if template is None:
                continue

            if verify:
                f = template.create_empty_functor()
                U1 = f.get_unify_scopes(False)
                U2 = f.category.extract_unify_atoms(False)
                if len(U1) != len(U2):
                    assert False
                C1 = f.category
                C2 = template.predarg_category.clean(True)
                if not C1.can_unify(C2):
                    assert False

            if catkey.signature not in dict:
                dict[catkey.signature] = template
            elif verify:
                f1 = dict[catkey.signature]
                t1 = str(f1)
                t2 = str(template)
                assert t1 == t2, 'verify failed\n  t1=%s\n  t2=%s\n  f1=%s\n  f2=%s' % (t1, t2, f1.predarg_category, predarg)
        except Exception as e:
            failed_rules.append(str(predarg) + ': ' + str(e))
            # DEBUG ?
            if False:
                try:
                    FunctorTemplate.create_from_category(predarg)
                except Exception:
                    pass

    print_progress(progress, done=True)

    if len(failed_rules) != 0:
        print('Warning: easysrl - %d rules failed' % len(failed_rules))
        with open(os.path.join(outdir, 'functor_easysrl_templates_failed.dat'), 'w') as fd:
            fd.write('\n'.join(failed_rules))
        if verbose:
            for m in failed_rules:
                print(m)

    return dict


if __name__ == "__main__":
    usage = 'Usage: %prog [options] templates-to-merge'
    parser = OptionParser(usage)
    parser.add_option('-o', '--outdir', type='string', action='store', dest='outdir', help='output directory')
    parser.add_option('-m', '--easysrl-model', type='string', action='store', dest='esrl', help='output format')
    parser.add_option('-L', '--ldc', action='store_true', dest='ldc', default=False, help='Use LDC to generate template.')
    parser.add_option('-M', '--merge', action='store_true', dest='merge', default=False, help='Merge old cached categories.')
    parser.add_option('-v', '--verbose', action='store_true', dest='verbose', default=False, help='Verbose output.')

    (options, args) = parser.parse_args()
    dict = {}
    outdir = options.outdir or datapath

    if not os.path.exists(outdir):
        print('path does not exist - %s' % outdir)
        sys.exit(1)

    if not os.path.isdir(outdir):
        print('path is not a directory - %s' % outdir)
        sys.exit(1)

    tstart = datetime.datetime.now()
    # Clear category cache
    merge = Category.copy_cache() if options.merge else []
    Category.clear_cache()

    if options.esrl is not None:
        build_from_easysrl(dict, outdir, options.esrl, options.verbose)

    if options.ldc:
        build_from_ldc_ccgbank(dict, outdir, options.verbose)

    elapsed = datetime.datetime.now() - tstart
    print('Processing time = %d seconds' % elapsed.total_seconds())

    if options.verbose:
        print('The following %d categories were processed correctly...' % len(dict))
        for k, v in dict.iteritems():
            print('%s: %s' % (k, str(v)))

    if len(dict) != 0:
        Category.initialize_cache([Category(k) for k, v in dict.iteritems()])
        Category.initialize_cache([v for k, v in merge])
        Category.save_cache(os.path.join(outdir, 'categories.dat'))

        cache = Cache()
        cache.initialize([(Category(k), v) for k, v in dict.iteritems()])
        model = Model(templates=cache)
        model.save_templates(os.path.join(outdir, 'functor_templates.dat'))
    else:
        print('no templates generated')
