from __future__ import unicode_literals, print_function
from nltk.corpus import wordnet as wn
from nltk.corpus.reader.wordnet import Synset, Lemma
import networkx as nx


def closure_graph(wnobj, fn):
    """Get the closure graph for `wnobj` using fn as the adjacency function.

    Args:
        wnobj: A wordnet object instance; either nltk.corpus.wordnet.Synset
            or nltk.corpus.wordnet.Lemma
        fn: The adjacency function for the wordnet objects. Functions include hypernyms(),
            part_meronyms() etc...

    Returns.
        A networkx.DiGraph instance.

    See Also:
        hypernym_closure_graph()
        meronym_closure_graph()
    """
    seen = set()    # nodes whose adjacency has been traversed
    graph = nx.DiGraph()
    nodes = [wnobj] # traverse queue
    graph.add_node(wnobj.name())
    # Depth first search of WN using fn adjacency
    # To do Breadth first use a Collections.deque for nodes and popleft()
    while len(nodes) != 0:
        nd = nodes.pop()
        if not nd in seen:
            seen.add(nd)
            for ndAdj in fn(nd):
                graph.add_node(ndAdj.name())
                graph.add_edge(nd.name(), ndAdj.name())
                nodes.append(ndAdj)
    return graph


def hypernym_closure_graph(wnobj):
    """Shortcut for closure_graph(wnobj, lambda x: x.hypernyms()).

    Args:
        wnobj: A wordnet object instance; either nltk.corpus.wordnet.Synset
            or nltk.corpus.wordnet.Lemma

    Returns.
        A networkx.DiGraph instance.
    """
    assert isinstance(wnobj, (Synset, Lemma))
    return closure_graph(wnobj, lambda x: x.hypernyms())


def meronym_closure_graph(wnobj):
    """Shortcut for closure_graph(wnobj, lambda x: x.part_meronyms()).

    Args:
        wnobj: A wordnet object instance; either nltk.corpus.wordnet.Synset
            or nltk.corpus.wordnet.Lemma

    Returns.
        A networkx.DiGraph instance.
    """
    assert isinstance(wnobj, (Synset, Lemma))
    return closure_graph(wnobj, lambda x: x.part_meronyms())



if __name__ == '__main__':
    import matplotlib.pyplot as plt
    pasta=wn.synsets('pasta')
    gpasta=[hypernym_closure_graph(x) for x in pasta]
    nx.draw_networkx(gpasta[0])
    plt.show()
    pass
