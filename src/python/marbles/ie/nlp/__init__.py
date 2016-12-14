# package clausefinder
from clause import Clause
from clause import ClauseFinder
from common import DELAY_SPACY_IMPORT
import googlenlp
if not DELAY_SPACY_IMPORT:
    import spacynlp
