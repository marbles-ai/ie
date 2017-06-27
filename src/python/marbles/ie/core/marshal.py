from __future__ import unicode_literals, print_function
from marbles.ie.ccg import *
from marbles.ie.core import constituent_types as ct
from sentence import Constituent, BasicLexeme, Wikidata, Sentence, Span
from marbles.ie.grpc.infox_service_pb2 import GSentence


def marshal_sentence(response):
    """Marshal data from gRPC call to infox service.

    Args:
        The gRPC response.

    Returns:
        A marbles.ie.core.Sentence instance.
    """
    assert isinstance(response, GSentence)

    lexemes = []
    constituents = []
    sentence = Sentence(lexemes, constituents)
    for glex in response.lexemes:
        lex = BasicLexeme()
        lexemes.append(lex)
        lex.head = glex.head
        lex.idx = glex.idx
        lex.mask = glex.mask
        lex.refs = [r for r in glex.refs]
        lex.pos = POS.from_cache(glex.pos)
        lex.word = glex.word
        lex.stem = glex.stem
        lex.category = Category.from_cache(glex.category)
        if len(glex.wikidata.title) != 0:
            wd = Wikidata()
            wd.title = glex.wikidata.title
            wd.summary = glex.wikidata.summary
            wd.page_categories = [x for x in glex.wikidata.page_categories]
            wd.url = glex.wikidata.url
            lex.wiki_data = wd

    for gc in response.constituents:
        indexes = [x for x in gc.span]
        c = Constituent(Span(sentence, indexes), ct.from_cache(gc.vntype), gc.head)
        constituents.append(c)

    sentence.map_heads_to_constituents()
    return sentence


