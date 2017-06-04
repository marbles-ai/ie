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
from marbles.ie import grpc
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


idsrch = re.compile(r'[^.]+\.(?P<id>\d+)\.raw')

if __name__ == '__main__':
    allfiles = []
    esrlpath = os.path.join(projdir, 'data', 'ldc', 'easysrl', 'ccgbank')
    if not os.path.exists(esrlpath):
        os.makedirs(esrlpath)

    progress = 0
    svc = grpc.CcgParserService('easysrl')
    stub = svc.open_client()

    failed_total = 0
    ldcpath = os.path.join(projdir, 'data', 'ldc', 'ccgbank_1_1', 'data', 'RAW')
    dirlist = os.listdir(ldcpath)

    try:
        for fname in dirlist:
            ldcpath1 = os.path.join(ldcpath, fname)
            with open(ldcpath1, 'r') as fd:
                lines = fd.readlines()

            m = idsrch.match(os.path.basename(ldcpath1))
            if m is None:
                continue

            derivations = []
            failed_parse = []
            for ln in lines:
                # Parse with EasySRL via gRPC
                try:
                    ccg = grpc.ccg_parse(stub, ln)
                    derivations.append(safe_utf8_encode(ccg.replace('\n', '')))
                except Exception as e:
                    failed_parse.append(safe_utf8_encode(ln.strip()))
                    # Add comment so line numbers match id's
                    derivations.append(safe_utf8_encode('# FAILED: ' + ln.strip()))
                progress = print_progress(progress, 10)
            id = m.group('id')
            if len(derivations) != 0:
                with open(os.path.join(esrlpath, 'ccg_derivation%s.txt' % id), 'w') as fd:
                    fd.write(b'\n'.join(derivations))

            failed_total += len(failed_parse)
            if len(failed_parse) != 0:
                with open(os.path.join(esrlpath, 'ccg_failed%s.txt' % id), 'w') as fd:
                    fd.write(b'\n'.join(failed_parse))
    finally:
        progress = print_progress(progress, 10, done=True)
        svc.shutdown()

    if failed_total != 0:
        print('THERE WERE %d PARSE FAILURES' % failed_total)


