'''
    The purpose of this code is to suck in the verbnet xml files
    and order them in a way for fast verb lookups

    Each VERBNET class is assigned to one of several THEMATIC ROLES


    What we wanna know is:
    1. What's the wordnet id?
    2. What's the class?
    3. What Frames are associated with this verb?

    Current Bugs:
    1. Frame object cannot be serialized; still figuring out why

    Features to Add:

'''

# Utility Imports
from optparse import OptionParser
import os
import logging
import json

# lxml Imports
from lxml import etree


# Turn on logging
logging.basicConfig(format='%(asctime)s : %(message)s', level=logging.INFO)


# Pretty prints for lxml elements
def pprint(tree):
    print etree.tostring(tree, pretty_print=True)
    return 0


# Dump verbnet dictionary to json for rapid loading
def dump_json(dictionary, filename):
    with open(filename, 'w') as f:
        json.dump(dictionary, f)
    return 0


# Load verbnet dictionary from json file
def load_json(filename):
    with open(filename, 'r') as f:
        MEMBER_LOOKUP = json.load(f)
    return MEMBER_LOOKUP

# JSON Frame is not serializable... hm why?
#  For now, I'm going to make Frame a dictionary


'''
class Frame(object):

    def __init__(self):
        self.description = None
        self.examples = []
        self.syntax = []
        self.semantics = None

    def __str__(self):
        string = ""
        string += "Description: %s\n" % str(self.description)

        index = 0
        string += "Examples\n"
        for example in self.examples:
            string += "\tEx %d: %s\n" % (index, str(example))
            index += 1
        string += "Syntax\n"
        for pos in self.syntax:
            string += "\t%s\n" % str(pos)
        string += "Semantics\n"
        for sem in self.semantics:
            string += "\t%s\n" % str(sem)

        return string
    '''


if __name__ == '__main__':

    # Parse Command Line Arguments
    usage = '%prog [options][text]'
    parser = OptionParser(usage)
    parser.add_option('-x', '--xml', type='string', dest='xml',
                      help='Directory containing verbnet xml files')
    parser.add_option('-v', '--verbose', action='store_true',
                      default=False, dest='verbose', help='Verbose')
    options, args = parser.parse_args()

    MEMBER_LOOKUP = {}

    VNCLASSES = {}

    # Iterate through all files in the directory
    for file in os.listdir(options.xml):

        # If the filename in the directory ends with .xml, parse it
        if file.endswith('.xml'):
            filename = os.path.join(options.xml, file)
            logging.info("Parsing: %s" % filename)

            tree = etree.parse(filename)
            root = tree.getroot()

            MEMBERS = {}
            THEMROLES = {}
            FRAMES = []

            # VerbNet class ID
            if root.tag == "VNCLASS":
                _id = root.attrib['ID']
            else:
                print "ERROR"
                exit()

            for _i in root:

                # Parse the MEMBERS
                if _i.tag == "MEMBERS":
                    for _m in _i:
                        if _m.tag is etree.Comment:
                            continue

                        # Name of the member
                        _name = _m.attrib['name']

                        # Wordnet entry
                        _wn = _m.attrib['wn'].split()\
                            if 'wn' in _m.attrib\
                            else None

                        # Grouping entry
                        _grouping = _m.attrib['grouping'].split()\
                            if 'grouping' in _m.attrib\
                            else None

                        # We're assuming that verbs only map to one class
                        assert _name not in MEMBERS.keys()

                        # Map member name to wordnet entry and grouping
                        MEMBERS[_name] = {'wn': _wn, 'grouping': _grouping}

                        # If we haven't seen this verb, initialize a list
                        if _name not in MEMBER_LOOKUP.keys():
                            MEMBER_LOOKUP[_name] = []

                        # For each verb, get wordnet, grouping, class ID
                        member_attributes = {
                            'wn': _wn, 'grouping': _grouping, 'class': _id}

                        MEMBER_LOOKUP[_name].append(member_attributes)

                # Parse roles;
                # Some verbnet classes don't have roles...
                elif _i.tag == "THEMROLES":
                    for _r in _i:
                        if _r.tag is etree.Comment:
                            continue

                        # Grab the thematic role type
                        _type = _r.attrib['type']
                        assert _type not in THEMROLES

                        roles = []
                        for _roles in _r:
                            roles.append(_roles.tag)

                        THEMROLES[_type] = roles

                elif _i.tag == "FRAMES":
                    for _frame in _i:
                        if _frame.tag is etree.Comment:
                            continue

                        # Create a new frame object (for the time being
                        # non-serializable)
                        frame = {}

                        for _d in _frame:

                            if _d.tag == 'DESCRIPTION':

                                _descriptionNumber = _d.attrib[
                                    'descriptionNumber']\
                                    if 'descriptionNumber' in _d.attrib\
                                    else None

                                _primary = _d.attrib[
                                    'primary']\
                                    if 'primary' in _d.attrib\
                                    else None

                                _secondary = _d.attrib[
                                    'secondary']\
                                    if 'secondary' in _d.attrib\
                                    else None

                                _xtag = _d.attrib[
                                    'xtag']\
                                    if 'primary' in _d.attrib\
                                    else None

                                frame['description'] = {
                                    'dn': _descriptionNumber,
                                    'primary': _primary,
                                    'secondary': _secondary,
                                    'xtag': _xtag}

                            if _d.tag == 'EXAMPLES':
                                examples = []

                                for _example in _d:
                                    examples.append(_example.text)

                                frame['examples'] = examples

                            if _d.tag == 'SYNTAX':

                                syntax = []

                                for _pos in _d:

                                    _tag = _pos.tag
                                    _value = _pos.attrib[
                                        'value'] if 'value' in _pos.attrib\
                                        else None

                                    _type = _pos[0].tag if len(
                                        _pos) != 0\
                                        else None

                                    syntax.append((_tag, _value, _type))

                                frame['syntax'] = syntax

                            if _d.tag == 'SEMANTICS':

                                semantics = []

                                # Parse predicates
                                for _pred in _d:

                                    _predvalue = _pred.attrib[
                                        'value'] if 'value' in _pred.attrib\
                                        else None

                                    arguments = []

                                    # Arguments of the predicate
                                    for _args in _pred:

                                        for _a in _args:

                                            _type = _a.attrib['type']
                                            _value = _a.attrib['value']

                                            arguments.append((_type, _value))

                                    semantics.append(
                                        {'pred': _predvalue,
                                         'args': arguments})

                                frame['semantics'] = semantics

                    FRAMES.append(frame)

            VNCLASSES[_id] = {'members': MEMBERS,
                              'themroles': THEMROLES,
                              'frames': FRAMES}

    # Dump Verb ID lookup into JSON
    dump_json(VNCLASSES, 'vn_classes.json')
    dump_json(MEMBER_LOOKUP, 'verb_lookup.json')

    print "----- Testing Time -----"

    vn_lookup = load_json('vn_classes.json')
    verb_lookup = load_json('verb_lookup.json')

    for verb in verb_lookup.keys():
        print("Verb: ", verb)
        for attribute in verb_lookup[verb]:
            print("\tWordnet:%s, Class:%s" %
                  (attribute['wn'], attribute['class']))
