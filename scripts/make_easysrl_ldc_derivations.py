#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import re
import sys
import imp
import grpc

# Modify python path
projdir = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
pypath = os.path.join(projdir, 'src', 'python')
datapath = os.path.join(pypath, 'marbles', 'ie', 'drt')
sys.path.insert(0, pypath)


def die(s):
    print('Error: %s' %s)
    sys.exit(1)


grpcSrvc = os.path.join(projdir, 'build', 'grpc', 'python', 'marbles_service_pb2.py')
sessionPrefix, _ = os.path.splitext(os.path.basename(__file__))
if not os.path.exists(grpcSrvc):
    die('gRPC service "%s" does not exist, run gradle build' % grpcSrvc)
marbles_svc = imp.load_source("lucida_service", grpcSrvc)


def create_query_input(typename, data):
    query_input = marbles_svc.QueryInput()
    query_input.type = typename
    query_input.data.append(str(data))
    return query_input


def get_client_transport(host, port):
    channel = grpc.insecure_channel('%s:%u' % (host, port))
    stub = marbles_svc.LucidaServiceStub(channel)
    return stub, channel


def ccg_parse(client, sentence, sessionId):
    query_input = create_query_input('text', sentence)
    request = marbles_svc.Request()
    request.LUCID = sessionId
    request.spec.name = 'infer'
    request.spec.content.extend([query_input])
    response = client.infer(request)
    return response.msg


idsrch = re.compile(r'[^.]+\.(?P<id>\d+)\.raw')

if __name__ == '__main__':
    allfiles = []
    esrlpath = os.path.join(projdir, 'data', 'ldc', 'easysrl')
    if not os.path.exists(esrlpath):
        os.mkdir(esrlpath)

    sessionId = 'default'
    stub, _ = get_client_transport('localhost', 8084)

    failed_total = 0
    ldcpath = os.path.join(projdir, 'data', 'ldc', 'ccgbank_1_1', 'data', 'RAW')
    dirlist = os.listdir(ldcpath)

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
                ccg = ccg_parse(stub, ln, sessionId)
                derivations.append(ccg.replace('\n', ''))
            except Exception as e:
                failed_parse.append(ln.strip())
        id = m.group('id')
        if len(derivations) != 0:
            with open(os.path.join(esrlpath, 'ccg_derivation%s.txt' % id), 'w') as fd:
                fd.write('\n'.join(derivations))

        failed_total += len(failed_parse)
        if len(failed_parse) != 0:
            with open(os.path.join(esrlpath, 'ccg_failed%s.txt' % id), 'w') as fd:
                fd.write('\n'.join(failed_parse))

    if failed_total != 0:
        print('THERE WERE %d PARSE FAILURES' % failed_total)


