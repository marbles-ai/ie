'''
    The purpose of this class is to interface with conceptnet.

    Available Relationships:
    ['RelatedTo', 'HasProperty', 'ReceivesAction', 'AtLocation',
     'CapableOf', 'HasA', 'UsedFor', 'Synonym', 'DerivedFrom',
     'ExternalURL', 'FormOf']

'''
import requests
from collections import OrderedDict


BASEURL = 'http://api.conceptnet.io/c/en/'


class Conceptnet(object):

    def __init__(self, term):
        self.term = term.strip().lower()
        self._reply = self.request()
        self._edges = self.process_edges(self._reply)
        self.relations = self._edges.keys()

    def request(self):
        reply = requests.get(BASEURL + self.term).json()
        return reply

    def process_edges(self, reply):
        edges = OrderedDict()
        for edge in reply['edges']:
            _edge = {'start': edge['start'],
                     'end': edge['end'],
                     'weight': edge['weight'],
                     'dataset': edge['dataset'],
                     'sources': edge['sources'],
                     'rel': edge['rel'],
                     'id': edge['@id'],
                     'surfaceText': edge['surfaceText']}
            # For now, indexing by label of relation
            rel = _edge['rel']['label']
            if rel not in edges.keys():
                edges[rel] = []
            edges[rel].append(_edge)
        return edges

    # Return the edges of relationship type rel
    def edges(self, rel):
        try:
            return self._edges[rel]
        except KeyError:
            print "Could not find edges with rel:", rel
            return None


# For testing
if __name__ == '__main__':

    lu = Conceptnet('Paul')

    print lu.relations
    print "-----"
    for relation in lu.relations:
        print "Relation: ", relation
        print lu.edges(relation)
        print "::::::::::"
