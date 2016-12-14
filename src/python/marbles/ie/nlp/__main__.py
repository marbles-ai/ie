from clausefinder import *
import sys, json
from optparse import OptionParser
from clausefinder.clause import preprocess


print('Clause Finder supports Google or spaCy NLP')

# Parse command line
usage = '%prog [options] [text]'
parser = OptionParser(usage)
parser.add_option('-j', '--json-in', type='string', dest='jsoninfile', help='Process a Google NLP response.')
parser.add_option('-o', '--json-out', type='string', dest='jsonoutfile', help='Save Google NLP response.')
parser.add_option('-f', '--file', type='string', dest='infile', help='Process a text file.')
parser.add_option('-k', '--hack', action='store_true', dest='hack', help='Add hack to fixup incorrect root token.')
parser.add_option('-c', '--compact', action='store_true', dest='compact', help='compact json output.')
parser.add_option('-p', '--parser', type='string', dest='parser', help='Parsers to invoke (google|spacy), default is google.')
options, args = parser.parse_args()

parser = options.parser or 'google'
if parser not in ['google', 'spacy']:
    print('Error: bad --parser=%s option' % parser)
    sys.exit(1)
if parser != 'google' and options.jsoninfile is not None:
    print('Warning --json-in only available for google parser')
if parser != 'google' and options.jsonoutfile is not None:
    print('Warning --json-out only available for google parser')

if parser == 'google':
    i = 1
    if options.jsoninfile is not None:
        # Always google in this case
        print('Processing json file %s' % options.jsoninfile)
        with open(options.jsoninfile, 'rt') as fd:
            doc = googlenlp.Doc(json.load(fd))
            i = 1
            cf = ClauseFinder(doc)
            for s in doc.sents:
                clauses = cf.find_clauses(s)
                for clause in clauses:
                    print('%i. %s: %s' % (i, clause.type, clause.text))
                i += 1

    if options.infile is not None:
        print('Processing text file %s' % options.infile)
        nlp = googlenlp.GoogleNLP()
        with open(options.infile, 'rt') as fd:
            lines = fd.readlines()
        cleanlines = filter(lambda x: len(x) != 0 and x[0] != '#', [x.strip() for x in lines])
        if options.hack:
            changeCount = 0
            nounCount = 0
            for i in range(len(cleanlines)):
                ln = cleanlines[i]
                result = nlp.parse(ln)
                doc = googlenlp.Doc(result)
                prep, changed, nroot = preprocess(doc)
                if changed:
                    changeCount += 1
                    assert len(prep) == 1
                    cleanlines[i] = prep[0]
                if nroot is not None:
                    nounCount += 1
            print('Preprocessed %i sentences. %i sentences had noun as root.' % (changeCount, nounCount))

        result = nlp.parse(' '.join(cleanlines))
        if options.jsonoutfile is not None:
            with open(options.jsonoutfile, 'w') as fd:
                if options.compact:
                    json.dump(result, fp=fd)
                else:
                    json.dump(result, fp=fd, indent=2)
        doc = googlenlp.Doc(result)
        cf = ClauseFinder(doc)
        for s in doc.sents:
            clauses = cf.find_clauses(s)
            for clause in clauses:
                print('%i. %s: %s' % (i, clause.type, clause.text))
            i += 1

    elif len(args) != 0:
        nlp = googlenlp.GoogleNLP()

    if args is not None and len(args) != 0:
        print('Processing command line text')
        result = nlp.parse(''.join(args))
        doc = googlenlp.Doc(result)
        cf = ClauseFinder(doc)
        for s in doc.sents:
            clauses = cf.find_clauses(s)
            for clause in clauses:
                print('%s: %s' % (clause.type, clause.text))
else:
    if DELAY_SPACY_IMPORT:
        import spacynlp
    i = 1
    if options.infile is not None:
        print('Processing text file %s' % options.infile)
        with open(options.infile, 'rt') as fd:
            lines = fd.readlines()
        cleanlines = filter(lambda x: len(x) != 0 and x[0] != '#', [x.strip() for x in lines])
        doc = spacynlp.parse(' '.join(cleanlines).decode('utf-8'))
        cf = ClauseFinder(doc)
        for s in doc.sents:
            clauses = cf.find_clauses(s)
            for clause in clauses:
                print('%i. %s: %s' % (i, clause.type, clause.text))
            i += 1

sys.exit(0)