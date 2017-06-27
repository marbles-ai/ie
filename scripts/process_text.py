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
    parser.add_option('-N', '--no-vn', action='store_true', dest='no_vn', default=False, help='disable verbnet, default is enabled')
    parser.add_option('-I', '--no-wp', action='store_true', dest='no_wp', default=False, help='disable wikipedia, default is enabled')
    parser.add_option('-W', '--word-vars', action='store_true', dest='wordvars', default=False, help='Use word names for variables, default is disabled')
    parser.add_option('-s', '--wordsep', type='string', action='store', dest='wordsep', help='book mode word separator, defaults to hyphen')
    parser.add_option('-t', '--title', type='string', action='store', dest='title', help='book mode title regex, defaults to \'\s*[A-Z][-A-Z\s\.]*$\'')

    (options, args) = parser.parse_args()

    # Delay imports so help text can be dislayed without loading model
    from marbles.ie.semantics.ccg import process_ccg_pt, pt_to_ccgbank
    from marbles.ie.semantics.compose import CO_ADD_STATE_PREDICATES, CO_NO_VERBNET, CO_BUILD_STATES, CO_NO_WIKI_SEARCH
    from marbles.ie.ccg import parse_ccg_derivation2 as parse_ccg_derivation
    #from marbles.ie.parse import parse_ccg_derivation
    from marbles.ie.drt.common import SHOW_LINEAR

    titleRe = options.title or r'^\s*[A-Z][-A-Z\s\.]*$'
    wordsep = options.wordsep or '-'
    outfile = options.outfile or None
    daemon = options.daemon or 'easysrl'

    if len(args) == 0:
        die('missing filename')

    if daemon not in ['easysrl', 'easyccg']:
        die('daemon must be easysrl or easyccg')

    svc = grpc.CcgParserService(daemon)
    stub = svc.open_client()

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
            fol = None
            constituents = None

            if options.ofmt == 'drs':
                try:
                    pt = parse_ccg_derivation(ccg)
                    pccg = pt_to_ccgbank(pt)
                except Exception as e:
                    print('Error: failed to parse ccgbank - %s' % str(e))
                    raise

                ops = CO_BUILD_STATES if options.wordvars else CO_ADD_STATE_PREDICATES
                ops |= CO_NO_VERBNET if options.no_vn else 0
                ops |= CO_NO_WIKI_SEARCH if options.no_wp else 0

                try:
                    sentence = process_ccg_pt(pt, ops)
                    d = sentence.get_drs()
                    fol, _ = d.to_fol()
                    fol = unicode(fol)
                    drs = d.show(SHOW_LINEAR)
                    constituents = []
                    for c in sentence.get_constituents():
                        constituents.append(c.vntype.signature + '(' + c.span.text + ')')
                    constituents = ' '.join(constituents)
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
                    sys.stdout.write('\n</ccg>\n')
                if pccg:
                    sys.stdout.write('<predarg>\n')
                    sys.stdout.write(pccg)
                    sys.stdout.write('\n</predarg>\n')
                if drs:
                    sys.stdout.write('<drs>\n')
                    sys.stdout.write(drs)
                    sys.stdout.write('\n</drs>\n')
                if fol:
                    sys.stdout.write('<fol>\n')
                    sys.stdout.write(fol)
                    sys.stdout.write('\n</fol>\n')
                if constituents:
                    sys.stdout.write('<constituents>\n')
                    sys.stdout.write(constituents)
                    sys.stdout.write('\n</constituents>\n')
            else:
                with open(outfile, 'w') as fd:
                    if html:
                        fd.write(safe_utf8_encode(html))
                        fd.write(b'\n')
                    if ccg:
                        fd.write(b'<ccg>\n')
                        fd.write(safe_utf8_encode(ccg.strip()))
                        fd.write(b'\n</ccg>\n')
                    if pccg:
                        fd.write(b'<predarg>\n')
                        fd.write(safe_utf8_encode(pccg))
                        fd.write(b'\n</predarg>\n')
                    if drs:
                        fd.write(b'<drs>\n')
                        fd.write(drs)
                        fd.write(b'\n</drs>\n')
                    if fol:
                        fd.write(b'<fol>\n')
                        fd.write(safe_utf8_encode(fol))
                        fd.write(b'\n</fol>\n')
                    if constituents:
                        fd.write(b'<constituents>\n')
                        fd.write(safe_utf8_encode(constituents))
                        fd.write(b'\n</constituents>\n')

        elif outfile is None:
            process_file(stub, sys.stdout, args, titleSrch, wordsep, sessionId)
        else:
            with open(outfile, 'w') as fd:
                process_file(stub, fd, args, titleSrch, wordsep, sessionId)
    finally:
        svc.shutdown()
