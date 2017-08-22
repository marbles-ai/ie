#! /usr/bin/env python
from __future__ import unicode_literals, print_function

import sys
import os
import re

# Modify python path
projdir = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
pypath = os.path.join(projdir, 'src', 'python')
datapath = os.path.join(pypath, 'marbles', 'ie', 'drt')
sys.path.insert(0, pypath)

from marbles.ie import grpc
from marbles import safe_utf8_encode, isdebugging
from marbles.ie.semantics.ccg import process_ccg_pt, pt_to_ccg_derivation
from marbles.ie.core.constants import *
from marbles.ie.ccg import parse_ccg_derivation2 as parse_ccg_derivation
from marbles.ie.drt.common import SHOW_LINEAR
from marbles.ie.utils.text import preprocess_sentence
from marbles.ie.core.exception import *
from marbles.ie.core.exception import _UNDEFINED_UNARY, _UNDEFINED_TEMPLATES

ISDEBUG = isdebugging()


def die(s):
    print('Error: %s' %s)
    sys.exit(1)


def dbg_print(lines):
    for txt in lines:
        print(txt)


def finalize_output(out_file, lines):
    global ISDEBUG
    if ISDEBUG:
        # prints are executed immediately when debugging
        return
    if out_file is None or len(lines) == 0:
        return
    with open(out_file, 'w') as fd:
        for txt in lines:
            print(txt)
            fd.write(txt)
            fd.write('\n')


def output_unary(sentence, name, lines):
    global ISDEBUG
    if sentence is None:
        return
    lns = []
    if len(sentence.unary_seen) != 0:
        lns.append('%s: seen unary rules' % name)
        for x in sentence.unary_seen:
            lns.append('  %s' % x)
        lns.append('')
    if ISDEBUG:
        dbg_print(lns)
    else:
        lines.extend(lns)


def output_drs(sentence, name, lines):
    global ISDEBUG
    if sentence is None:
        return
    lns = []
    lns.append('%s: %s' % (name, sentence.get_drs().show(SHOW_LINEAR)))
    if ISDEBUG:
        dbg_print(lns)
    else:
        lines.extend(lns)


def output_derivation(sentence, derivation, name, lines):
    global ISDEBUG
    if sentence is None:
        return
    lns = []
    lns.append('%s: %s' % (name, derivation))
    if ISDEBUG:
        dbg_print(lns)
    else:
        lines.extend(lns)


def output_text(txt, lines):
    global ISDEBUG
    if ISDEBUG:
        dbg_print([txt])
    else:
        lines.append(txt)



SVCLIST = ['easysrl']

if __name__ == '__main__':
    idsrch = re.compile(r'[^.]+\.(?P<id>\d+)\.raw')
    estub = None
    nstub = None

    if 'easysrl' in SVCLIST:
        esvc = grpc.CcgParserService('easysrl')
        estub = esvc.open_client()
    if 'neuralccg' in SVCLIST:
        nsvc = grpc.CcgParserService('neuralccg')
        nstub = nsvc.open_client()

    cmpdir = 'compare'

    try:
        allfiles = []
        autopath = os.path.join(projdir, 'data', 'ldc', 'ccgbank_1_1', 'data', 'AUTO')
        rawpath = os.path.join(projdir, 'data', 'ldc', 'ccgbank_1_1', 'data', 'RAW')
        mappath = os.path.join(projdir, 'data', 'ldc', 'mapping')
        outpath = os.path.join(projdir, 'data', 'ldc', cmpdir)
        if not os.path.exists(outpath):
            os.makedirs(outpath)
        dirlist = sorted(os.listdir(rawpath))
        lastwsj_file = ''
        wsjd = {}

        # BUG IN NCCG section 1, raw 327 - never finishes

        # These allow us to start from a section 00-24 and line number in raw file.
        start_section = 0
        start_line = 186
        exceptions = []

        for fname in dirlist[start_section:]:
            ldcfile = os.path.join(rawpath, fname)
            with open(ldcfile, 'r') as fd:
                lines = fd.readlines()

            m = idsrch.match(os.path.basename(ldcfile))
            if m is None:
                continue
            section = m.group('id')
            mapfile = os.path.join(mappath, 'ccg_map%s.txt' % section)

            if not os.path.exists(os.path.join(outpath,section)):
                os.makedirs(os.path.join(outpath,section))

            with open(mapfile, 'r') as fd:
                mapping = fd.readlines()

            out_file = None
            lnout = []
            total_err = 0
            for ln, mm, idx in zip(lines[start_line:], mapping[start_line:], range(start_line, len(lines))):
                mm = mm.strip()
                fm = mm.split('.')[0] + '.auto'
                wsj_file = os.path.join(projdir, 'data', 'ldc', 'ccgbank_1_1', 'data', 'AUTO', section, fm)
                if wsj_file != lastwsj_file:
                    lastwsj_file = wsj_file
                    wsjd = {}
                    finalize_output(out_file, lnout)
                    lnout = []
                    total_err = 0
                    out_file = os.path.join(projdir, 'data', 'ldc', cmpdir, section, mm.split('.')[0] + '.txt')
                    with open(wsj_file, 'r') as fd:
                        derivations = fd.readlines()
                    for k, v in zip(derivations[0::2],derivations[1::2]):
                        #012
                        #ID=wsj_0001.1 PARSER=GOLD NUMPARSE=1
                        key = k[3:].split(' ')[0]
                        wsjd[key] = v

                output_text('-------', lnout)
                output_text('ID=%s' % mm, lnout)
                output_text('RAW_LN=%d\n' % idx, lnout)
                lc = len(lnout)
                output_text(ln.strip(), lnout)

                if mm not in wsjd:
                    output_text('ERR: cannot find mapping to %s' % mm, lnout)
                    total_err += 1
                    continue
                gold_derivation = wsjd[mm]

                e_sentence = None
                n_sentence = None
                gold_sentence = None
                ed = None
                nd = None

                options = CO_NO_VERBNET | CO_NO_WIKI_SEARCH | CO_VARNAMES_MATCH_WORD_INDEX
                try:
                    if estub is not None:
                        ed = grpc.ccg_parse(estub, ln)
                        ept = parse_ccg_derivation(ed)
                        e_sentence = process_ccg_pt(ept, options)

                    if nstub is not None:
                        nd = grpc.ccg_parse(nstub, ln)
                        npt = parse_ccg_derivation(nd)
                        n_sentence = process_ccg_pt(npt, options)

                    gpt = parse_ccg_derivation(gold_derivation)
                    gold_sentence = process_ccg_pt(gpt, options)

                except (UnaryRuleError, TemplateRuleError, CombinatorNotFoundError) as e:
                    output_unary(gold_sentence, 'GOLD', lnout)
                    output_unary(n_sentence, 'NCCG', lnout)
                    output_unary(e_sentence, 'ESRL', lnout)
                    output_text('ERR: %s' % e, lnout)
                    total_err += 1
                    continue
                except Exception as e:
                    output_unary(gold_sentence, 'GOLD', lnout)
                    output_unary(n_sentence, 'NCCG', lnout)
                    output_unary(e_sentence, 'ESRL', lnout)
                    output_text('ERR: %s' % e, lnout)
                    total_err += 1
                    exceptions.append((e, idx, mm))
                    if ISDEBUG:
                        raise
                    continue

                output_unary(gold_sentence, 'GOLD', lnout)
                output_unary(n_sentence, 'NCCG', lnout)
                output_unary(e_sentence, 'ESRL', lnout)

                if (e_sentence is not None and len(gold_sentence) != len(e_sentence)) or \
                        (n_sentence is not None and len(gold_sentence) != len(n_sentence)):
                    output_text('ERR: sentence len mismatch for %s' % mm, lnout)
                    total_err += 1
                    continue

                output_drs(gold_sentence, 'GOLD', lnout)
                output_drs(n_sentence, 'NCCG', lnout)
                output_drs(e_sentence, 'ESRL', lnout)
                output_text('', lnout)

                errcount = 0
                if n_sentence is not None and e_sentence is not None:
                    for lxg,lxe,lxn in zip(gold_sentence.lexemes, e_sentence.lexemes, n_sentence.lexemes):
                        if lxe.drs is not None and lxn.drs is not None and lxg.drs is not None:
                            te = lxe.drs.show(SHOW_LINEAR)
                            tn = lxn.drs.show(SHOW_LINEAR)
                            tg = lxg.drs.show(SHOW_LINEAR)
                            if te != tg or tn != tg:
                                output_text('  Mismatch at word %s' % lxg.word, lnout)
                                output_text('    Expected  %s' % tg, lnout)
                            if te != tg:
                                errcount += 1
                                output_text('    Easysrl   %s' % te, lnout)
                            if tn != tg:
                                errcount += 1
                                output_text('    Neuralccg %s' % tn, lnout)
                elif n_sentence is not None:
                    for lxg,lxn in zip(gold_sentence.lexemes, n_sentence.lexemes):
                        if lxn.drs is not None and lxg.drs is not None:
                            tn = lxn.drs.show(SHOW_LINEAR)
                            tg = lxg.drs.show(SHOW_LINEAR)
                            if tn != tg:
                                output_text('  Mismatch at word %s' % lxg.word, lnout)
                                output_text('    Expected  %s' % tg, lnout)
                                output_text('    Neuralccg %s' % tn, lnout)
                                errcount += 1
                elif e_sentence is not None:
                    for lxg,lxe in zip(gold_sentence.lexemes, e_sentence.lexemes):
                        if lxe.drs is not None and lxg.drs is not None:
                            te = lxe.drs.show(SHOW_LINEAR)
                            tg = lxg.drs.show(SHOW_LINEAR)
                            if te != tg:
                                output_text('  Mismatch at word %s' % lxg.word, lnout)
                                output_text('    Expected  %s' % tg, lnout)
                                output_text('    Easysrl   %s' % te, lnout)
                                errcount += 1

                output_text('', lnout)
                output_derivation(gold_sentence, gold_derivation, 'GOLD', lnout)
                output_derivation(n_sentence, nd, 'NCCG', lnout)
                output_derivation(e_sentence, ed, 'ESRL', lnout)

                # Only want to see errors
                total_err += errcount
                if errcount == 0 and not ISDEBUG:
                    lnout = lnout[0:lc]

            finalize_output(out_file, lnout)
            lnout = []
            out_file = None
            start_line = 0
            total_err = 0

    finally:
        if estub is not None:
            esvc.shutdown()
        if nstub is not None:
            nsvc.shutdown()

        if len(_UNDEFINED_UNARY) != 0 or len(_UNDEFINED_TEMPLATES) != 0:
            print('-----------------------------------------')

        if len(_UNDEFINED_UNARY) != 0:
            print('The following unary rules were undefined.')
            for rule in _UNDEFINED_UNARY:
                print("  (r'%s', r'%s')" % rule)

        if len(_UNDEFINED_TEMPLATES) != 0:
            print('The following templates were undefined.')
            for cat in _UNDEFINED_TEMPLATES:
                print("  r'%s'" % cat)

        if len(exceptions) != 0:
            print('---------------------------------')
            print('The following exceptions occured.')
            for e, idx, mm in exceptions:
                print('ID=%s, RAW_LN=%d' % (mm, idx))
                print('  %s' % e)

