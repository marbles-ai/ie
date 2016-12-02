#from spacy.en import English  # NLP with spaCy https://spacy.io
from spacy.tokens import Token
from spacy.tokens import Doc
from spacy.tokens import Span
from clausefinder.common import build_typeof_map
from . import dep
from . import pos
from collections import OrderedDict
import sys

# done in .dep
#NLP = English() # will take some time to load

SPACY_TYPE_NAMES = {
    dep.ACOMP: 'C',        # Adjectival complement
    dep.ADVMOD: 'Av',      # Adverbial modifier
    dep.ATTR: 'c',         # Attribute dependent of a copular verb
    dep.CCOMP: 'Cz',       # Clausal complement of a verb or adjective
    dep.CSUBJ: 'S',        # Clausal subject
    dep.CSUBJPASS: 'S',    # Clausal passive subject
    dep.DOBJ: 'O',         # Direct object
    dep.IOBJ: 'Oi',        # Indirect object
    #dep.NOMCSUBJ: 'S',     # Nominalized clausal subject
    #dep.NOMCSUBJPASS: 'S', # Nominalized clausal passive
    dep.NSUBJ: 'S',        # Nominal subject
    dep.NSUBJPASS: 'S',    # Passive nominal subject
    dep.QUANTMOD: 'Aq',    # Quantifier phrase modifier
    dep.XCOMP: 'Cx',       # Open clausal complement
    pos.ADP: 'A',          # Adposition (preposition and postposition)
    pos.VERB: 'V',         # Verb (all tenses and modes)
}


TYPEOF_MAP = build_typeof_map(sys.modules[__name__])


def get_type_name(tag):
    '''Get a spacy type string from the grammatical relation id.

    Args:
        tag: The grammatical-relation or part-of-speech tag.

    Returns:
        A string.
    '''
    if SPACY_TYPE_NAMES.has_key(tag):
        return SPACY_TYPE_NAMES[tag]
    return ''


# Helper methods

def merge_ents(doc):
    '''Merge adjacent entities into single tokens; modifies the doc.'''
    for ent in doc.ents:
        ent.merge(ent.root.tag_, ent.text, ent.label_)
    return doc


def format_POS(token, light=False, flat=False):
    '''helper: form the POS output for a token'''
    subtree = OrderedDict([
        ("word", token.text),
        ("lemma", token.lemma_),  # trigger
        ("NE", token.ent_type_),  # trigger
        ("POS_fine", token.tag_),
        ("POS_coarse", token.pos_),
        ("arc", token.dep_),
        ("modifiers", [])
    ])
    if light:
        subtree.pop("lemma")
        subtree.pop("NE")
    if flat:
        subtree.pop("arc")
        subtree.pop("modifiers")
    return subtree


def POS_tree_(root, light=False):
    '''
    Helper: generate a POS tree for a root token.
    The doc must have merge_ents(doc) ran on it.
    '''
    subtree = format_POS(root, light=light)
    for c in root.children:
        subtree["modifiers"].append(POS_tree_(c))
    return subtree


def parse_tree(doc, light=False):
    '''generate the POS tree for all sentences in a doc'''
    merge_ents(doc)  # merge the entities into single tokens first
    return [POS_tree_(sent.root, light=light) for sent in doc.sents]


def parse_list(doc, light=False):
    '''tag the doc first by NER (merged as tokens) then
    POS. Can be seen as the flat version of parse_tree'''
    merge_ents(doc)  # merge the entities into single tokens first
    return [format_POS(token, light=light, flat=True) for token in doc]

'''
def parse_sentence(sentence):
    doc = Doc(sentence);
    reply = OrderedDict([
        ("text", doc.text),
        ("len", len(doc)),
        ("tokens", [token.text for token in doc]),
        ("noun_phrases", [token.text for token in doc.noun_chunks]),
        ("parse_tree", parse_tree(doc)),
        ("parse_list", parse_list(doc))
    ])
    return reply
'''

def parse(text):
    '''Parser for multi-sentences; split and apply parse in a list.

    Args:
        text: The text to parse.
    '''
    return dep.NLP(text, tag=True, entity=True)
    #doc = NLP(text, tag=False, entity=False)
    #return [NLP(sent.text) for sent in doc.sents]

