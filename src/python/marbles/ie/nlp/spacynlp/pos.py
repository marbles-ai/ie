from spacy.parts_of_speech import NO_TAG as UNKNOWN
from spacy.parts_of_speech import ADJ
from spacy.parts_of_speech import CONJ
from spacy.parts_of_speech import DET
from spacy.parts_of_speech import NUM
from spacy.parts_of_speech import PRON
from spacy.parts_of_speech import ADP
from spacy.parts_of_speech import NOUN
from spacy.parts_of_speech import VERB
from spacy.parts_of_speech import X
from spacy.parts_of_speech import ADV
from spacy.parts_of_speech import PUNCT
from spacy.parts_of_speech import PART as PRT

# No Google equivalent
from spacy.parts_of_speech import AUX
from spacy.parts_of_speech import INTJ
from spacy.parts_of_speech import SCONJ
from spacy.parts_of_speech import SYM
from spacy.parts_of_speech import EOL
from spacy.parts_of_speech import SPACE


POS_UPPER_BOUND = max([UNKNOWN, ADJ, CONJ, DET, NUM, PRON, ADP, NOUN, VERB, X, ADV, PUNCT, PRT, AUX, INTJ, SCONJ, SYM, EOL, SPACE])
POS_LOWER_BOUND = min([UNKNOWN, ADJ, CONJ, DET, NUM, PRON, ADP, NOUN, VERB, X, ADV, PUNCT, PRT, AUX, INTJ, SCONJ, SYM, EOL, SPACE])

