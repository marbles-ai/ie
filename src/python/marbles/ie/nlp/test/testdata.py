import json, os
from clausefinder.clause import preprocess
from clausefinder.googlenlp import Doc


PROBLEMS = [
    {
        "sentence": "He says that you like to swim.",
        "clauses": [
            {"type": "SVVCz", "text": "(He) (says) (you like to swim)"},
            {"type": "SVCzVCx", "text": "(you) (like) (to swim)"}
        ],
    } ,
    # CCOMP
    #
    # Google produces this:
    # IDX   0   1       2     3    4     5    6     7       8
    # HEAD
    # DEP   det nsubj   root  mark nsubj aux  neg   auxpass ccomp
    # SENT  The problem is    that this  has  never been    tried
    #                   be               have       be      try
    #       DET NOUN    VERB  ADP  DET   VERB ADV   VERB    VERB
    #
    # Stanford parser is similar except: "this" is a DEP nsubjpass.
    #
    # EXPECTED: (The problem) (is) (that this has never been tried)
    #           (this) (has never been tried)
    {
        "sentence": "The problem is that this has never been tried",
        "clauses": [
            {"type": "SVVCz", "text": "(The problem) (is) (this has never been tried)"},
            {"type": "SVCz", "text": "(this) (has never been tried)"}
        ],
    } ,
    {
        "sentence": "The important thing is to keep calm",
        "clauses": [
            {"type": "SVVCx", "text": "(The important thing) (is) (to keep calm)"}
        ],
    } ,
    {
        "sentence": "We started digging",
        "clauses": [
            {"type": "SVVCx", "text": "(We) (started) (digging)"}
        ],
    } ,
    {
        "sentence": "He says you like to swim.",
        "clauses": [
            {"type": "SVVCz", "text": "(He) (says) (you like to swim)"},
            {"type": "SVCzA", "text": "(you like) (to swim)"}
        ],
    }
    , {
        "sentence": "Sue asked George to respond to her offer",
        "clauses": [
            {"type": "SV", "text": "(Sue) (asked) (George) (to respond to her offer)"}
        ],
    } ,
    {
        "sentence": "The guy, John said, left early in the morning.",
        "clauses": [
            {"type": "SV", "text": "(John said) (The guy) (left) (early in the morning)"},
            {"type": "SV", "text": "(The guy) (left) (early in the morning)"}
        ],
    } ,
    # S1: SV
    #
    # Google and Stanford produce this:
    # IDX   0      1        2
    # HEAD  1      2        2
    # DEP   nn     nsubj    root
    # SENT  Albert Einstein Died
    #                       die
    #       NOUN   NOUN     VERB
    {
        "sentence": "Albert Einstein died",
        "clauses": [
            {"type": "SV", "text": "(Albert Einstein) (died)"}
        ],
    } ,
    # S2: SVeA SVA
    #
    # Google and Stanford produce this:
    # IDX   0      1        2        3    4
    # HEAD  1      2        2        2    3
    # DEP   nn     nsubj    root     prep pobj
    # SENT  Albert Einstein remained in   Princeton
    #                       remain
    #       NOUN   NOUN     VERB     ADP  NOUN
    {
        "sentence": "Albert Einstein remained in Princeton",
        "clauses": [
            {"type": "SVA", "text": "(Albert Einstein) (remained) (in Princeton)"}
        ],
    } ,
    # S3: SVcC SVC
    #
    # Google produced this:
    # IDX   0      1        2     3
    # HEAD  1      2        2     2
    # DEP   nn     nsubj    root  acomp
    # SENT  Albert Einstein is    smart
    #                       be
    #       NOUN   NOUN     VERB  ADJ
    #
    # ClausIE/Stanford produce this:
    # IDX   0      1        2     3
    # HEAD  1      3        3     3
    # DEP   nn     nsubj    cop   root
    # SENT  Albert Einstein is    smart
    #                       be
    #       NOUN   NOUN     VERB  ADJ
    {
        "sentence": "Albert Einstein is smart",
        "clauses": [
            {"type": "SVC", "text": "(Albert Einstein) (is) (smart)"}
        ],
    } ,
    # S4: SVmtO SVO
    #
    # Google and Stanford produce this:
    # IDX   0      1        2     3    4    5      6
    # HEAD  1      3        3     3    6    6      3
    # DEP   nn     nsubj    aux   root det  nn     dobj
    # SENT  Albert Einstein has   won  the  Nobel  Prize
    #                       be
    #       NOUN   NOUN     VERB  VERB DET  NOUN   NOUN
    {
        "sentence": "Albert Einstein has won the Nobel Prize",
        "clauses": [
            {"type": "SVO", "text": "(Albert Einstein) (has won) (the Nobel Prize)"}
        ],
    } ,
    # S5: SVdtOiO SVOO
    #
    # Google and Stanford produce this:
    # IDX   0     1     2      3        4    5      6
    # HEAD  1     1     3      2        6    6      1
    # DEP   nsubj root  nn     iobj     det  nn     dobj
    # SENT  RSAS  gave  Albert Einstein the  Nobel  Prize
    #             give
    #       NOUN  VERB  NOUN   NOUN     DET  NOUN   NOUN
    {
        "sentence": "RSAS gave Albert Einstein the Nobel Prize",
        "clauses": [
            {"type": "SVOiO", "text": "(RSAS) (gave) (Albert Einstein) (the Nobel Prize)"}
        ],
    } ,
    # S6: SVctOA SVOA (The doorman, showed, Albert Einstein, to his office)
    #
    # Google and Stanford produce this:
    # IDX   0     1       2      3      4        5    6    7
    # HEAD  1     2       2      4      2        2    7    5
    # DEP   det   nsubj   root   nn     dobj     prep poss pobj
    # SENT  The   doorman showed Albert Einstein to   his  office
    #                     show
    #       DET   NOUN    VERB   NOUN   NOUN     ADP  PRON NOUN
    {
        "sentence": "The doorman showed Albert Einstein to his office",
        "clauses": [
            {"type": "SVOA", "text": "(The doorman) (showed) (Albert Einstein) (to his office)"}
        ],
    } ,
    # S7: SVctOC SVOC
    #
    # Google produces this:
    # IDX   0      1        2        3    4       5
    # HEAD  1      2        2        4    5       2
    # DEP   nn     nsubj    root     det  nsubj   acomp
    # SENT  Albert Einstein declared the  meeting open
    #                       declare
    #       NOUN   NOUN     VERB     DET  NOUN    ADJ
    #
    # ClausIE/Stanford mark open as xcomp, otherwise they are the same.
    #
    # ClausIE: SVO (Albert Einstein) (declared) (the meeting open)
    #          SV  (the meeting) (open)
    #          We don't include the SV case because there is no verb.
    {
        "sentence": "Albert Einstein declared the meeting open",
        "clauses": [
            {"type": "SVC", "text": "(Albert Einstein) (declared) (the meeting open)"}
        ],
    } ,
    # Some extended patterns
    # S8: SViAA SV
    #
    # Google and Stanford produce this:
    # IDX   0      1        2     3     4          5     6
    # HEAD  1      2        2     2     3          2     5
    # DEP   nn     nsubj    root  prep  pobj       prep  pobj
    # SENT  Albert Einstein died  in    Princeton  in    1955
    #                       die
    #       NOUN   NOUN     VERB  ADP   NOUN       ADP   NUM
    #
    # Note: Stanford recognizes 1955 as a calendar date
    #
    # EXPECTED: (Albert Einstein) (died)
    #     (Albert Einstein) (died) (in Princeton)
    #     (Albert Einstein) (died) (in 1955)
    {
        "sentence": "Albert Einstein died in Princeton in 1955",
        "clauses": [
            {"type": "SVAA", "text": "(Albert Einstein) (died) (in Princeton) (in 1955)"},
            # FIXME: should get three clauses
            # {"type": "SV", "text": "(Albert Einstein) (died)"},
            # {"type": "SVA", "text": "(Albert Einstein) (died) (in Princeton)"},
            # {"type": "SVA", "text": "(Albert Einstein) (died) (in 1955)"},
        ],
    } ,
    # S9
    {
        "sentence": "Albert Einstein remained in Princeton until his death",
        "clauses": [
            # FIXME: should get two clauses
            #{"type": "SVA", "text": "(Albert Einstein) (remained) (in Princeton)"},
            {"type": "SVAA", "text": "(Albert Einstein) (remained) (in Princeton) (until his death)"},
        ],
    } ,
    # S10: SVcCA SVC
    #
    # Google produces this:
    # IDX   0      1        2     3    4          5     6    7     8
    # HEAD  1      2        2     4    2          4     8    8     5
    # DEP   nn     nsubj    root  det  attr       prep  det  amod  pobj
    # SENT  Albert Einstein is    a    scientist  of    the  20th  century
    #                       die
    #       NOUN   NOUN     VERB  DET  NOUN       ADP   DET  ADJ   NOUN
    #
    # Stanfors produces this:
    # IDX   0      1        2     3    4          5     6    7     8
    # HEAD  1      4        4     4    4          4     8    8     5
    # DEP   nn     nsubj    cop   det  root       prep  det  amod  pobj
    # SENT  Albert Einstein is    a    scientist  of    the  20th  century
    #                       die
    #       NOUN   NOUN     VERB  DET  NOUN       ADP   DET  ADJ   NOUN
    #
    # EXPECTED (Albert Einstein) (is) (a scientist)
    #     (Albert Einstein) (is a scientist) (of the 20th century)
    {
        "sentence": "Albert Einstein is a scientist of the 20th century",
        "clauses": [
            {"type": "SVcA", "text": "(Albert Einstein) (is) (a scientist) (of the 20th century)"}
        ],
    } ,
    {
        "sentence": "Albert Einstein has won the Nobel Prize in 1921",
        "clauses": [
            {"type": "SVOA", "text": "(Albert Einstein) (has won) (the Nobel Prize) (in 1921)"}
        ],
    } ,
    {
        "sentence": "In 1921, Albert Einstein has won the Nobel Prize",
        "clauses": [
            {"type": "SVAO", "text": "(Albert Einstein) (has won) (In 1921) (the Nobel Prize)"}
        ],
    } ,
    # A bunch of complicated sentences with APPOS and CONJ.  One problem we find is
    # when a proper noun|entity is the root of the tree. This typically is wrong
    # because it is most likely a subject or object.
    #
    # FIXME: One hack I have found with google is to preprocess and modify commas.
    {
        "sentence": "Bell, a telecommunication company, which is based in Los Angeles, makes and distributes electronic, computer and building products.",
        "clauses": [
            {"type": "ISA", "text": "(Bell) (\"is\") (a telecommunication company)"},
            {"type": "SVO", "text": "(Bell) (makes) (electronic products)"},
            {"type": "SVO", "text": "(Bell) (makes) (computer products)"},
            {"type": "SVO", "text": "(Bell) (makes) (building products)"},
            {"type": "SVO", "text": "(Bell) (distributes) (electronic products)"},
            {"type": "SVO", "text": "(Bell) (distributes) (computer products)"},
            {"type": "SVO", "text": "(Bell) (distributes) (building products)"},
            {"type": "SVA", "text": "(Bell) (is based) (in Los Angeles)"},
        ],
    } ,
    {
        "sentence": "Bell, a telecommunication company better known for its split into the so called baby bells, which is based in Los Angeles, makes and distributes electronic, computer and building products.",
        "clauses": [
            {"type": "ISA", "text": "(Bell) (\"is\") (a telecommunication company)"},
            {"type": "ISA", "text": "(Bell) (\"is\") (better known for its split into the so called baby bells)"},
            {"type": "SVO", "text": "(Bell) (makes) (electronic products)"},
            {"type": "SVO", "text": "(Bell) (makes) (computer products)"},
            {"type": "SVO", "text": "(Bell) (makes) (building products)"},
            {"type": "SVO", "text": "(Bell) (distributes) (electronic products)"},
            {"type": "SVO", "text": "(Bell) (distributes) (computer products)"},
            {"type": "SVO", "text": "(Bell) (distributes) (building products)"},
            {"type": "SVA", "text": "(Bell) (is based) (in Los Angeles)"},
        ],
    } ,
    {
        "sentence": "Bell, a telecommunication company, and a fortune 500 company, which is based in Los Angeles, makes and distributes electronic, computer and building products.",
        "clauses": [
            {"type": "ISA", "text": "(Bell) (\"is\") (a telecommunication company)"},
            {"type": "ISA", "text": "(Bell) (\"is\") (a fortune 500 company)"},
            {"type": "SVO", "text": "(Bell) (makes) (electronic products)"},
            {"type": "SVO", "text": "(Bell) (makes) (computer products)"},
            {"type": "SVO", "text": "(Bell) (makes) (building products)"},
            {"type": "SVO", "text": "(Bell) (distributes) (electronic products)"},
            {"type": "SVO", "text": "(Bell) (distributes) (computer products)"},
            {"type": "SVO", "text": "(Bell) (distributes) (building products)"},
            {"type": "SVA", "text": "(Bell) (is based) (in Los Angeles)"},
        ],
    } ,
    # XCOMP XCOMP
    #
    # Google produces this:
    # IDX   0      1        2     3     4      5
    # HEAD  1      2        2     4     2      4
    # DEP   det    nsubj    root  aux   xcomp  xcomp
    # SENT  The    boss     said  to    start  digging
    #                       die
    #       DET    NOUN     VERB  PRT   VERB   VERB
    #
    # Stanford parser is similar except "digging" is a DEP/POS dobj/NOUN.
    {
        "sentence": "The boss said to start digging.",
        "clauses": [
            {"type": "SVVCx", "text": "(The boss) (said) (to start digging)"}
        ],
    } ,
    # Different result between ClausIE and Ours. Which is better for our pipeline?
    #
    # Google and Stanford produce this:
    # IDX   0       1    2    3     4    5    6      7     8       9
    # HEAD  1       4    4    4     4    6    4      9     9       6
    # DEP   advmod  dep  aux  nsubj root aux  xcomp  nn    nn      dobj
    # SENT  How     much does it    cost to   join   World Resorts International
    #                    do         cost      join
    #       ADV     ADJ  VERB PRON  VERB PRT  VERB   NOUN  NOUN    NOUN
    #
    # EXPECTED:
    #   ClausIE: (it) (does cost) (to join World Resorts International)
    #   Ours: (it) (how much does cost) (to join World Resorts International)
    {
        "sentence": "How much does it cost to join World Resorts International",
        "clauses": [
            {"type": "aSVAO", "text": "(How much) (it) (cost) (to join) (World Resorts International)"},
        ],
    } ,
]


JSONFILE_NAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'google_testdata.json')
GOOGLE_PROBLEMS = None
if os.path.exists(JSONFILE_NAME):
    with open(JSONFILE_NAME, 'rt') as fd:
        GOOGLE_PROBLEMS = json.load(fd)


def save_google_testdata_in_json(compact=False):
    global GOOGLE_PROBLEMS
    from clausefinder import googlenlp
    nlp = googlenlp.GoogleNLP()
    GOOGLE_PROBLEMS = [x for x in PROBLEMS]
    changeCount = 0
    nounCount = 0
    for p in GOOGLE_PROBLEMS:
        result = nlp.parse(p['sentence'])
        p['google'] = result
        doc = Doc(result)
        prep,changed,nroot = preprocess(doc)
        if changed:
            changeCount += 1
            assert len(prep) == 1
            result = nlp.parse(prep[0])
            p['preprocessed'] = {}
            p['preprocessed']['sentence'] = prep[0]
            p['preprocessed']['google'] = result
            p['preprocessed']['rootnoun'] = nroot is not None
        if nroot is not None:
            nounCount += 1
    print('Preprocessed %i sentences. %i sentences had noun as root.' % (changeCount, nounCount))

    with open(JSONFILE_NAME, 'w') as fd:
        if compact:
            json.dump(GOOGLE_PROBLEMS, fp=fd)
        else:
            json.dump(GOOGLE_PROBLEMS, fp=fd, indent=2)


if __name__ == '__main__':
    print('Creating Google JSON file')
    save_google_testdata_in_json()