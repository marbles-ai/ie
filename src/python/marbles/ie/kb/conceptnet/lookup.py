'''
    The purpose of this class is to interface with conceptnet.
'''
import requests

BASEURL = 'http://api.conceptnet.io/c/en/'


class Lookup(object):

    def __init__(self, term):
        self.term = term.strip().lower()
        self.reply = self.request(term)
        self.edges = self.grab_edges()

    def request(self, term):
        reply = requests.get(BASEURL + self.term).json()
        return reply

    def grab_edges(self):
        edges = []
        for edge in self.reply['edges']:
            _edge = {'start': edge['start'],
                     'end': edge['end'],
                     'weight': edge['weight'],
                     'dataset': edge['dataset'],
                     'sources': edge['sources'],
                     'rel': edge['rel'],
                     'id': edge['@id'],
                     'surfaceText': edge['surfaceText']}
            edges.append(_edge)
        return edges


# For testing
if __name__ == '__main__':

    lu = Lookup('Apple')

    for edge in lu.edges:
        for k, v in edge.iteritems():
            print k, ": ", v
        exit()
