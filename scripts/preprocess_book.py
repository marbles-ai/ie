#! /usr/bin/env python
import re
import sys
import os
import time
from subprocess import call
from optparse import OptionParser

# Modify python path
projdir = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
pypath = os.path.join(projdir, 'src', 'python')
datapath = os.path.join(pypath, 'marbles', 'ie', 'drt')
sys.path.insert(0, pypath)
from marbles.ie import grpc


def die(s):
    print('Error: %s' %s)
    sys.exit(1)


sessionPrefix, _ = os.path.splitext(os.path.basename(__file__))


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
                        ccg = grpc.ccg_parse(stub, ln, sessionId)
                        write_title(out, id, ln, ccg)
                        continue
                    else:
                        ln = line + ln
                        sentences = ln.split('.')
                        for s in sentences[:-1]:
                            x = s.strip()
                            if len(x) == 0: continue
                            id += 1
                            ccg = grpc.ccg_parse(stub, x, sessionId)
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

    if len(args) == 0:
        die('missing filename')

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

    try:
        sessionId = grpc.DEFAULT_SESSION
        if options.ofmt is not None:
            if options.ofmt.lower() not in ['ccgbank', 'html', 'logic', 'extended']:
                die('bad output format %s, must be ccgbank|html|logic|extended' % options.ofmt)
            # Create a session to match output format, default is CCGBANK
            if options.ofmt.lower() != 'ccgbank':
                sessionId = grpc.create_session(stub, options.ofmt.upper())

        titleSrch = re.compile(titleRe)
        if direct:
            line = ' '.join(args)
            ccg = grpc.ccg_parse(stub, line, sessionId)
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
    finally:
        if svc_cmd is not None:
            # Stop service
            stub = None
            call([svc_cmd, 'easysrl'])
