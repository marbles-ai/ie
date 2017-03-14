
# Utility Imports
from optparse import OptionParser
import logging
import os

# lxml Imports
from lxml import etree
from lxml import objectify

# Turn on logging
logging.basicConfig(format='%(asctime)s : %(message)s', level=logging.INFO)

def pprint(tree):

    print etree.tostring(tree, pretty_print=True)

class Frame(object):

    def __init__(self):
        self.description = None
        self.examples = []
        self.syntax = []
        self.semantics = None

    #def __str__(self):




if __name__ == '__main__':

    # Parse Command Line Arguments
    usage = '%prog [options][text]'
    parser = OptionParser(usage)
    parser.add_option('-x', '--xml', type='string', dest='xml', help='Directory containing verbnet xml files')
    parser.add_option('-v', '--verbose', action='store_true', default=False, dest='verbose', help='Verbose')
    options, args = parser.parse_args()

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
            FRAMES = {}

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

                        _name = _m.attrib['name']

                        _wn = _m.attrib['wn'].split() if 'wn' in _m.attrib else None

                        _grouping = _m.attrib['grouping'].split() if 'grouping' in _m.attrib else None

                        assert _name not in MEMBERS.keys()

                        MEMBERS[_name] = {'wn':_wn, 'grouping':_grouping}

                #if _i.tag == "THEMROLES":
                #    for _r in _i:

                #        _type = _r.attrib['type']
                #        assert _type not in THEMROLES

                #        THEMROLES[type] = _r[0].tag

                elif _i.tag == "FRAMES":

                    for _frame in _i:

                        frame = Frame()

                        for _d in _frame:

                            if _d.tag == 'DESCRIPTION':

                                _descriptionNumber = _d.attrib['descriptionNumber'] if 'descriptionNumber' in _d.attrib else None
                                _primary = _d.attrib['primary'] if 'primary' in _d.attrib else None
                                _secondary = _d.attrib['secondary'] if 'secondary' in _d.attrib else None
                                _xtag = _d.attrib['xtag'] if 'primary' in _d.attrib else None

                                frame.description = {'dn':_descriptionNumber, 'primary':_primary, 'secondary':_secondary, 'xtag':_xtag}

                            if _d.tag == 'EXAMPLES':

                                examples = []

                                for _example in _d:

                                    examples.append(_example.text)

                                frame.examples = examples

                            if _d.tag == 'SYNTAX':

                                syntax = []

                                for _pos in _d:

                                    _tag = _pos.tag
                                    _value = _pos.attrib['value'] if 'value' in _pos.attrib else None
                                    _type = _pos[0].tag if len(_pos) != 0 else None

                                    syntax.append((_tag, _value, _type))

                                frame.syntax = syntax


                            if _d.tag == 'SEMANTICS':

                                semantics = []

                                for _pred in _d:

                                    _predvalue = _pred.attrib['value'] if 'value' in _pred.attrib else None

                                    arguments = []

                                    for _args in _pred:

                                        for _a in _args:

                                            _type = _a.attrib['type']
                                            _value = _a.attrib['value']

                                            arguments.append((_type, _value))

                                    semantics.append({'pred':_predvalue, 'args': arguments})

                                frame.semantics = semantics

                        if _name not in FRAMES.keys():
                            FRAMES[_name] = [frame]
                        else:
                            FRAMES[_name].append(frame)




