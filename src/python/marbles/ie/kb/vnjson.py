'''
    The purpose of this class is to interface with verbnet.
'''
import json


JSON_FOLDER = "json/"
CLASSES_FILE = "vn_classes.json"
VERB_FILE = "verb_lookup.json"


class Verbnet(object):

    def __init__(self, term):
        self.term = term.strip().lower()
        self._classes = self.grab_classes(self.term)
        if self._classes is None:
            raise KeyError
        self.frames = self.grab_frames(self._classes)
        self.roles = self.grab_roles(self._classes)

    # Load verbnet dictionary from json file
    def load_json(self, filename):
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
                return data
        except IOError as e:
            print "I/O error({0}): {1}".format(e.errno, e.strerror)
            exit(-1)

    def grab_classes(self, term):
        try:
            vn_classes = self.load_json(JSON_FOLDER + VERB_FILE)
            return [x['class'] for x in vn_classes[term]]
        except KeyError:
            print "Could not find class for verb: ", term
            return None

    def grab_frames(self, _classes):
        vn_lookup = self.load_json(JSON_FOLDER + CLASSES_FILE)
        frames = []
        for _class in _classes:
            frames.append(vn_lookup[_class]['frames'])
        return frames

    def grab_roles(self, _classes):
        vn_lookup = self.load_json(JSON_FOLDER + CLASSES_FILE)
        roles = []
        for _class in _classes:
            roles.append(vn_lookup[_class]['themeroles'])
        return roles


# For testing
if __name__ == '__main__':

    lu = Verbnet('run')
    #cprint lu.frames

    # for edge in lu.edges:
    #     for k, v in edge.iteritems():
    #         print k, ": ", v
    #     exit()
