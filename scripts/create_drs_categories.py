#! /usr/bin/env python

import sys
import os
from optparse import OptionParser

projectPath = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
pysrcPath = os.path.join(projectPath, 'src', 'python')
sys.path.append(pysrcPath)


from marbles.ie.drt import ccg2drs


def die(s):
    print('Error: %s' %s)
    sys.exit(1)


if __name__ == '__main__':
    usage = 'Converts CCG types to DRS types\nUsage: %prog [options] model-category-file(s)\n'
    parser = OptionParser(usage)
    parser.add_option('-f', '--file', type='string', action='store', dest='outfile', help='output file name, default is stdout')

    (options, args) = parser.parse_args()
    outfile = options.outfile or None

    if len(args) == 0:
        die('missing filename')

    lines = []
    for infile in args:
        with open(infile, 'r') as fd:
            lns = fd.readlines()
            lines.extend(lns)

    results = ccg2drs.CcgTypeMapper.convert_model_categories(lines)

    if outfile is None:
        for r in results:
            sys.stdout.write(r)
            sys.stdout.write('\n')
    else:
        with open(outfile, 'w') as fd:
            for r in results:
                fd.write(r)
                fd.write('\n')
