from __future__ import unicode_literals, print_function
from marbles.ie.ccg import *
from marbles.ie.core import constituent_types as ct
from marbles.ie.core import sentence
from marbles.ie.grpc.infox_service_pb2 import GSentence


def marshal_sentence(response):
    """Marshal data from gRPC call to infox service.

    Args:
        The gRPC response.

    Returns:
        A marbles.ie.core.sentence.Sentence instance.
    """
    assert isinstance(response, GSentence)

    lexemes = []
    constituents = []
    for glex in response.lexemes:
        lex = sentence.BasicLexeme()
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
            wd = sentence.Wikidata()
            wd.title = glex.wikidata.title
            wd.summary = glex.wikidata.summary
            wd.page_categories = [x for x in glex.wikidata.page_categories]
            wd.url = glex.wikidata.url
            lex.wiki_data = wd

    for gc in response.constituents:
        span = sentence.SimpleSpan(gc.span[0], gc.span[1])
        c = sentence.ConstituentNode(ct.from_cache(gc.ndtype), simple_span=span,
                                     parent_idx=gc.parent_idx, head_idx=gc.head_idx)
        constituents.append(c)

    return sentence.Sentence(lexemes, constituents)


