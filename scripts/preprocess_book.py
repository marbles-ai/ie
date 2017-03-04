#! /usr/bin/env python
import re
import sys
import os
import imp
import grpc
from optparse import OptionParser


projectPath = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
grpcSrvc = os.path.join(projectPath, 'build', 'grpc', 'python', 'marbles_service_pb2.py')
sessionPrefix, _ = os.path.splitext(os.path.basename(__file__))


def die(s):
    print('Error: %s' %s)
    sys.exit(1)


if not os.path.exists(grpcSrvc):
    die('gRPC service "%s" does not exist, run gradle build' % grpcSrvc)
marbles_svc = imp.load_source("lucida_service", grpcSrvc)


def create_query_input(typename, data):
    query_input = marbles_svc.QueryInput()
    query_input.type = typename
    query_input.data.append(str(data))
    return query_input


def create_query_spec(name, query_input_list):
    query_spec = marbles_svc.QuerySpec()
    query_spec.name = name
    query_spec.content.extend(query_input_list)
    return query_spec


def get_client_transport(host, port):
    channel = grpc.insecure_channel('%s:%u' % (host, port))
    stub = marbles_svc.LucidaServiceStub(channel)
    return stub, channel


def create_session(client, outputFormat):
    query_input = create_query_input('text', outputFormat.upper())
    request = marbles_svc.Request()
    request.LUCID = sessionPrefix.upper() + '-' + outputFormat
    request.spec.name = 'create'
    request.spec.content.extend([query_input])
    # Call create asynchronously
    create_future = client.create.future(request, 60)
    notused = create_future.result()
    #client.create(request)
    return sessionPrefix.upper() + '-' + outputFormat


def ccg_parse(client, sentence, sessionId):
    query_input = create_query_input('text', sentence)
    request = marbles_svc.Request()
    request.LUCID = sessionId
    request.spec.name = 'infer'
    request.spec.content.extend([query_input])
    response = client.infer(request)
    return response.msg


def write_title(fd, id, title, ccg):
    fd.write('TITLE:%d:%s\n' % (id, title))
    fd.write('CCG:%d:%s\n' % (id, ccg))


def write_line(fd, id, line, ccg):
    fd.write('SENTENCE:%d:%s\n' % (id, line))
    fd.write('CCG:%d:%s\n' % (id, ccg))


def write_hdr(fd):
    pass


def write_footer(fd):
    pass


def process_file(stub, out, args, titleSrch, wordsep, sessionId):
    id = 0
    for fn in args:
        line = ''
        write_hdr(out)
        line_number = 0
        try:
            with open(fn, 'r') as fd:
                while True:
                    ln = fd.readline()
                    line_number += 1
                    if len(ln) == 0:
                        # end of file
                        write_footer(out)
                        break
                    ln = ln.strip()
                    if len(ln) == 0:
                        line = ''
                        continue

                    m = titleSrch.match(ln)
                    if m is not None:
                        line = ''
                        ccg = ccg_parse(stub, ln, sessionId)
                        write_title(out, id, ln, ccg)
                        continue
                    else:
                        ln = line + ln
                        sentences = ln.split('.')
                        for s in sentences[:-1]:
                            x = s.strip()
                            if len(x) == 0: continue
                            id += 1
                            ccg = ccg_parse(stub, x, sessionId)
                            write_line(out, id, x, ccg)

                        if len(sentences) != 0:
                            s = sentences[-1].strip()
                            if len(s) != 0:
                                if sentences[-1][-1] == wordsep:
                                    line = sentences[-1][0:-1]
                                else:
                                    line = sentences[-1] + ' '
        except:
            print('Exception while processing file "%s" at line %d' % (fn, line_number))
            raise


if __name__ == '__main__':
    usage = 'Usage: %prog [options] input-file(s)'
    parser = OptionParser(usage)
    parser.add_option('-s', '--wordsep', type='string', action='store', dest='wordsep', help='word separator, defaults to hyphen')
    parser.add_option('-t', '--title', type='string', action='store', dest='title', help='title regex, defaults to \'\s*[A-Z][-A-Z\s\.]*$\'')
    parser.add_option('-f', '--file', type='string', action='store', dest='outfile', help='output file name')
    parser.add_option('-o', '--output-format', type='string', action='store', dest='ofmt', help='output format')
    parser.add_option('-D', '--direct', action='store_true', dest='direct', default=False, help='direct input from command line args')

    (options, args) = parser.parse_args()
    titleRe = options.title or r'^\s*[A-Z][-A-Z\s\.]*$'
    wordsep = options.wordsep or '-'
    outfile = options.outfile or None
    direct = options.direct or False

    sessionId = 'default'
    stub, _ = get_client_transport('localhost', 8084)
    if options.ofmt is not None:
        if options.ofmt.lower() not in ['ccgbank', 'html', 'logic', 'extended']:
            die('bad output format %s, must be ccgbank|html|logic|extended' % options.ofmt)
        # Create a session to match output format
        sessionId = create_session(stub, options.ofmt.upper())

    if len(args) == 0:
        die('missing filename')

    titleSrch = re.compile(titleRe)
    if direct:
        line = ' '.join(args)
        ccg = ccg_parse(stub, line, sessionId)
        if outfile is None:
            sys.stdout.write(ccg)
        else:
            with open(outfile, 'w') as fd:
                fd.write(ccg)
    elif outfile is None:
        process_file(stub, sys.stdout, args, titleSrch, wordsep, sessionId)
    else:
        with open(outfile, 'w') as fd:
            process_file(stub, fd, args, titleSrch, wordsep, sessionId)

