#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import re
import sys
import time
from subprocess import call

# Modify python path
projdir = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
pypath = os.path.join(projdir, 'src', 'python')
datapath = os.path.join(pypath, 'marbles', 'ie', 'drt')
sys.path.insert(0, pypath)
from marbles.ie import grpc


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

    svc_cmd = None
    progress = 0
    try:
        # Check if service has started. If not start it.
        stub, _ = grpc.get_client_transport('localhost', grpc.EASYSRL_PORT)
        ccg = grpc.ccg_parse(stub, '')
    except Exception:
        # Not started
        call([os.path.join(projdir, 'scripts', 'start_server.sh'), 'easysrl'])
        time.sleep(4)   # Give it some time to lock session access
        stub, _ = grpc.get_client_transport('localhost', grpc.EASYSRL_PORT)
        # Call asynchronously - will wait until default session is created
        ccg = grpc.ccg_parse(stub, '', timeout=120)
        svc_cmd = os.path.join(projdir, 'scripts', 'stop_server.sh')

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
                    derivations.append(ccg.replace('\n', ''))
                except Exception as e:
                    failed_parse.append(ln.strip())
                progress = print_progress(progress, 10)
            id = m.group('id')
            if len(derivations) != 0:
                with open(os.path.join(esrlpath, 'ccg_derivation%s.txt' % id), 'w') as fd:
                    fd.write('\n'.join(derivations))

            failed_total += len(failed_parse)
            if len(failed_parse) != 0:
                with open(os.path.join(esrlpath, 'ccg_failed%s.txt' % id), 'w') as fd:
                    fd.write('\n'.join(failed_parse))
    finally:
        progress = print_progress(progress, 10, done=True)
        if svc_cmd is not None:
            # Stop service
            stub = None
            call([svc_cmd, 'easysrl'])

    if failed_total != 0:
        print('THERE WERE %d PARSE FAILURES' % failed_total)


