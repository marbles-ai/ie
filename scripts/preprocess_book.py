import re, sys
from optparse import OptionParser


def die(s):
    print('Error: %s' %s)
    sys.exit(1)


def write_title(fd, title):
    pass


def write_line(fd, line):
    pass


def write_hdr(fd):
    pass


def write_footer(fd):
    pass


def openfile(outfile):
    if outfile == sys.stdout:
        return outfile
    return open(outfile, 'w')


def process_file(out, titleSrch, wordsep):
    for fn in args:
        line = ''
        write_hdr(out)
        with open(fn, 'r') as fd:
            while True:
                ln = fd.readline()
                if len(ln) == 0:
                    # end of file
                    write_footer(out)
                    break
                ln = ln.strip()
                if len(ln) == 0: continue
                ln = line + ln

                m = titleSrch.match(ln)
                if m is not None:
                    write_title(out, ln)
                    continue
                else:
                    sentences = ln.split('.')
                    for s in sentences[:-1]:
                        write_line(out, s)
                    if sentences[-1][-1] == wordsep:
                        line = sentences[-1][:-1]


if __name__ == '__main__':
    usage = 'Usage: %prog [options] input-file(s)'
    parser = OptionParser(usage)
    parser.add_option('-s', '--wordsep', type='string', action='append', dest='wordsep', help='word separator, defaults to hyphen')
    parser.add_option('-t', '--title', type='string', action='append', dest='title', help='title regex, defaults to \'\s*[A-Z][-A-Z\s\.]*$\'')
    parser.add_option('-f', '--file', type='string', action='append', dest='outfile', help='output file name')

    (options, args) = parser.parse_args()
    titleRe = options.title or r'^\s*[A-Z][-A-Z\s\.]*$'
    wordsep = options.wordsep or '-'
    outfile = options.outfile or None

    if len(args) == 0:
        die('missing filename')

    titleSrch = re.compile(titleRe)
    if outfile is None:
        process_file(sys.stdout, titleSrch, wordsep)
    else:
        with openfile(outfile) as out:
            process_file(sys.stdout, titleSrch, wordsep)

