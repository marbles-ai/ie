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
from marbles.ie.parse import parse_ccg_derivation
from marbles.ie.ccg.ccg2drs import process_ccg_pt, pt_to_ccgbank
from marbles.ie.drt.compose import CO_VERIFY_SIGNATURES, CO_ADD_STATE_PREDICATES
from marbles.ie.drt.common import SHOW_LINEAR


def die(s):
    print('Error: %s' %s)
    sys.exit(1)


sessionPrefix, _ = os.path.splitext(os.path.basename(__file__))


def write_title(fd, id, title, ccg):
    sentence = u'TITLE:%d:%s\n' % (id, title.strip().decode('utf-8'))
    ccgbank  = u'CCG:%d:%s\n' % (id, ccg.strip())
    fd.write(sentence.encode('utf-8'))
    fd.write(ccgbank.encode('utf-8'))


def write_line(fd, id, line, ccg):
    sentence = u'SENTENCE:%d:%s\n' % (id, line.strip().decode('utf-8'))
    ccgbank  = u'CCG:%d:%s\n' % (id, ccg.strip())
    fd.write(sentence.encode('utf-8'))
    fd.write(ccgbank.encode('utf-8'))


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
    parser.add_option('-f', '--file', type='string', action='store', dest='outfile', help='output file name')
    parser.add_option('-o', '--output-format', type='string', action='store', dest='ofmt', help='output format')
    parser.add_option('-d', '--daemon', type='string', action='store', dest='daemon', help='CCG daemon name, [easysrl (default),easyccg]')
    parser.add_option('-B', '--book', action='store_true', dest='book', default=False, help='book mode, default is input from command line args')
    parser.add_option('-s', '--wordsep', type='string', action='store', dest='wordsep', help='book mode word separator, defaults to hyphen')
    parser.add_option('-t', '--title', type='string', action='store', dest='title', help='book mode title regex, defaults to \'\s*[A-Z][-A-Z\s\.]*$\'')

    (options, args) = parser.parse_args()
    titleRe = options.title or r'^\s*[A-Z][-A-Z\s\.]*$'
    wordsep = options.wordsep or '-'
    outfile = options.outfile or None
    daemon = options.daemon or 'easysrl'
    daemon_port = grpc.EASYSRL_PORT if daemon == 'easysrl' else grpc.EASYCCG_PORT

    if len(args) == 0:
        die('missing filename')

    if daemon not in ['easysrl', 'easyccg']:
        die('daemon must be easysrl or easyccg')

    svc_cmd = None
    progress = 0
    try:
        # Check if service has started. If not start it.
        stub, _ = grpc.get_client_transport('localhost', daemon_port)
        ccg = grpc.ccg_parse(stub, '')
    except Exception:
        # Not started
        call([os.path.join(projdir, 'scripts', 'start_server.sh'), daemon])
        time.sleep(4)   # Give it some time to lock session access
        stub, _ = grpc.get_client_transport('localhost', daemon_port)
        # Call asynchronously - will wait until default session is created
        ccg = grpc.ccg_parse(stub, '', timeout=120)
        svc_cmd = os.path.join(projdir, 'scripts', 'stop_server.sh')

    try:
        sessionId = grpc.DEFAULT_SESSION
        if options.ofmt is not None:
            if options.ofmt not in ['ccgbank', 'html', 'logic', 'extended', 'drs']:
                die('bad output format %s, must be ccgbank|html|logic|extended' % options.ofmt)
            # Create a session to match output format, default is CCGBANK
            if options.ofmt != 'ccgbank' and options.ofmt != 'drs':
                sessionId = grpc.create_session(stub, options.ofmt)

        titleSrch = re.compile(titleRe)
        if not options.book:
            line = ' '.join(args)
            html = None
            # FIXME: Convert to python 3. Unicode is default.
            ccg = grpc.ccg_parse(stub, line, sessionId)
            if options.ofmt == 'html':
                html = ccg
                ccg = None
            drs = None
            pccg = None

            if options.ofmt == 'drs':
                try:
                    pt = parse_ccg_derivation(ccg)
                    pccg = pt_to_ccgbank(pt)
                except Exception as e:
                    print('Error: failed to parse ccgbank - %s' % str(e))
                    raise

                try:
                    d = process_ccg_pt(pt, CO_VERIFY_SIGNATURES | CO_ADD_STATE_PREDICATES)
                    d = d.unify()
                    d = d.drs.show(SHOW_LINEAR).encode('utf-8').strip()
                    drs = d
                except Exception as e:
                    print('Error: failed to compose DRS - %s' % str(e))
                    raise

            if outfile is None:
                if html:
                    sys.stdout.write(html)
                    sys.stdout.write('\n')
                if ccg:
                    sys.stdout.write('<ccg>\n')
                    sys.stdout.write(ccg.strip())
                    sys.stdout.write('\n')
                    sys.stdout.write('</ccg>\n')
                if pccg:
                    sys.stdout.write('<predarg>\n')
                    sys.stdout.write(pccg)
                    sys.stdout.write('\n')
                    sys.stdout.write('</predarg>\n')
                if drs:
                    sys.stdout.write('<drs>\n')
                    sys.stdout.write(drs)
                    sys.stdout.write('\n')
                    sys.stdout.write('</drs>\n')
            else:
                with open(outfile, 'w') as fd:
                    if html:
                        fd.write(html.encode('utf-8'))
                        fd.write('\n')
                    if ccg:
                        fd.write('<ccg>\n')
                        fd.write(ccg.strip().encode('utf-8'))
                        fd.write('\n')
                        fd.write('</ccg>\n')
                    if pccg:
                        fd.write('<predarg>\n')
                        fd.write(pccg)
                        fd.write('\n')
                        fd.write('</predarg>\n')
                    if drs:
                        fd.write('<drs>\n')
                        fd.write(drs)
                        fd.write('\n')
                        fd.write('</drs>\n')

        elif outfile is None:
            process_file(stub, sys.stdout, args, titleSrch, wordsep, sessionId)
        else:
            with open(outfile, 'w') as fd:
                process_file(stub, fd, args, titleSrch, wordsep, sessionId)
    finally:
        if svc_cmd is not None:
            # Stop service
            stub = None
            call([svc_cmd, daemon])
