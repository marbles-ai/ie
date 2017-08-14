#! /usr/bin/env python
from __future__ import unicode_literals, print_function

import os
import re
import sys
from optparse import OptionParser

# Modify python path
projdir = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
pypath = os.path.join(projdir, 'src', 'python')
datapath = os.path.join(pypath, 'marbles', 'ie', 'drt')
sys.path.insert(0, pypath)

from marbles.ie import grpc
from marbles import safe_utf8_encode
from marbles.ie.semantics.ccg import process_ccg_pt, pt_to_ccg_derivation, _UNDEFINED_UNARY
from marbles.ie.core.constants import *
from marbles.ie.ccg import parse_ccg_derivation2 as parse_ccg_derivation
from marbles.ie.drt.common import SHOW_LINEAR
from marbles.ie.utils.text import preprocess_sentence
from marbles.ie.core.exception import UnaryRuleError

def die(s):
    print('Error: %s' %s)
    sys.exit(1)


def do_print(out_file, lines):
    if out_file is None or len(lines) == 0:
        return
    with open(out_file, 'w') as fd:
        for txt in lines:
            print(txt)
            fd.write(txt)
            fd.write('\n')


SVCLIST = ['neuralccg']

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

    try:
        allfiles = []
        autopath = os.path.join(projdir, 'data', 'ldc', 'ccgbank_1_1', 'data', 'AUTO')
        rawpath = os.path.join(projdir, 'data', 'ldc', 'ccgbank_1_1', 'data', 'RAW')
        mappath = os.path.join(projdir, 'data', 'ldc', 'mapping')
        outpath = os.path.join(projdir, 'data', 'ldc', 'compare')
        if not os.path.exists(outpath):
            os.makedirs(outpath)
        dirlist = sorted(os.listdir(rawpath))
        lastwsj_file = ''
        wsjd = {}

        # These allow us to start from a section 00-24 and line number in raw file.
        start_section = 0
        start_line = 897  # 1271

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
                    if total_err != 0:
                        do_print(out_file, lnout)
                    total_err = 0
                    out_file = os.path.join(projdir, 'data', 'ldc', 'compare', section, mm.split('.')[0] + '.txt')
                    with open(wsj_file, 'r') as fd:
                        derivations = fd.readlines()
                    for k, v in zip(derivations[0::2],derivations[1::2]):
                        #012
                        #ID=wsj_0001.1 PARSER=GOLD NUMPARSE=1
                        key = k[3:].split(' ')[0]
                        wsjd[key] = v

                lnout.append('-------')
                lnout.append('ID=%s' % mm)
                lnout.append('RAW_LN=%d' % idx)
                lc = len(lnout)
                lnout.append(ln.strip())

                if mm not in wsjd:
                    lnout.append('ERR: cannot find mapping to %s' % mm)
                    total_err += 1
                    continue
                gold_derivation = wsjd[mm]

                e_sentence = None
                n_sentence = None
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
                except UnaryRuleError as e:
                    lnout.append('ERR: %s' % e)
                    total_err += 1
                    continue
                except Exception as e:
                    lnout.append('ERR: %s' % e)
                    total_err += 1
                    do_print(out_file, lnout)
                    raise
                    continue

                if (e_sentence is not None and len(gold_sentence) != len(e_sentence)) or \
                        (n_sentence is not None and len(gold_sentence) != len(n_sentence)):
                    lnout.append('ERR: sentence len mismatch for %s' % mm)
                    continue

                lnout.append('GOLD: %s' % gold_sentence.get_drs().show(SHOW_LINEAR))
                if n_sentence is not None:
                    lnout.append('NCCG: %s' % n_sentence.get_drs().show(SHOW_LINEAR))
                if e_sentence is not None:
                    lnout.append('ESRL: %s' % e_sentence.get_drs().show(SHOW_LINEAR))
                errcount = 0
                if n_sentence is not None and e_sentence is not None:
                    for lxg,lxe,lxn in zip(gold_sentence.lexemes, e_sentence.lexemes, n_sentence.lexemes):
                        if lxe.drs is not None and lxn.drs is not None and lxg.drs is not None:
                            te = lxe.drs.show(SHOW_LINEAR)
                            tn = lxn.drs.show(SHOW_LINEAR)
                            tg = lxg.drs.show(SHOW_LINEAR)
                            if te != tg or tn != tg:
                                lnout.append('  Mismatch at word %s' % lxg.word)
                                lnout.append('    Expected  %s' % tg)
                            if te != tg:
                                errcount += 1
                                lnout.append('    Easysrl   %s' % te)
                            if tn != tg:
                                errcount += 1
                                lnout.append('    Neuralccg %s' % tn)
                elif n_sentence is not None:
                    for lxg,lxn in zip(gold_sentence.lexemes, n_sentence.lexemes):
                        if lxn.drs is not None and lxg.drs is not None:
                            tn = lxn.drs.show(SHOW_LINEAR)
                            tg = lxg.drs.show(SHOW_LINEAR)
                            if tn != tg:
                                lnout.append('  Mismatch at word %s' % lxg.word)
                                lnout.append('    Expected  %s' % tg)
                                lnout.append('    Neuralccg %s' % tn)
                                errcount += 1
                elif e_sentence is not None:
                    for lxg,lxe in zip(gold_sentence.lexemes, e_sentence.lexemes):
                        if lxe.drs is not None and lxg.drs is not None:
                            te = lxe.drs.show(SHOW_LINEAR)
                            tg = lxg.drs.show(SHOW_LINEAR)
                            if te != tg:
                                lnout.append('  Mismatch at word %s' % lxg.word)
                                lnout.append('    Expected  %s' % tg)
                                lnout.append('    Easysrl   %s' % te)
                                errcount += 1
                # Only want to see errors
                total_err += errcount
                if errcount == 0:
                    lnout = lnout[0:lc]
            if total_err != 0:
                do_print(out_file, lnout)
            out_file = None
            start_line = 0
            total_err = 0

    finally:
        if estub is not None:
            esvc.shutdown()
        if nstub is not None:
            nsvc.shutdown()

    if len(_UNDEFINED_UNARY) != 0:
        print('-----------------------------------------')
        print('The following unary rules were undefined.')
        for rule in _UNDEFINED_UNARY:
            print("  (r'%s', r'%s')" % rule)
