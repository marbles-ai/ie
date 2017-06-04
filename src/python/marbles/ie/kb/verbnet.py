"""Original code at https://github.com/eci-store/verbnet-gl.git"""
from __future__ import unicode_literals, print_function
import os
import bs4
import re
from marbles import future_string, native_string, safe_utf8_decode, safe_utf8_encode


VERBNET_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'vnxml')


class VerbnetDB(object):
    def __init__(self, max_count=None):
        """Parse verbnet files and return a list of VerbClasses. Read all the verbnet
        files, but just take the first max_count files if max_count is used, or read
        filenames from a file if file_list is used.
        """
        self.classes = None
        self.name_index = None
        fnames = [f for f in os.listdir(VERBNET_PATH) if f.endswith(".xml")]
        if max_count is not None:
            fnames = fnames[:max_count]
        filenames = [os.path.join(VERBNET_PATH, fname) for fname in fnames]
        soups = [bs4.BeautifulSoup(open(fname), "lxml-xml") for fname in filenames]
        self.classes = [VerbClass(fname, s) for fname, s in zip(filenames, soups)]
        self._create_name_index()

    def _create_name_index(self):
        results = {}
        classes = [x for x in self.classes]
        while len(classes) != 0:
            vc = classes.pop()
            for name in vc.names:
                if name not in results:
                    results[name] = [vc]
                else:
                    results[name].append(vc)
            classes.extend(vc.subclasses)
        self.name_index = results


class VerbClass(object):
    """Represents a single class of verbs in VerbNet (all verbs from the same
    XML file).
    """

    # TODO: Check if nested subclasses have issues

    def __init__(self, fname, soup):
        self.fname = fname
        vnclass = soup.VNCLASS
        if vnclass is not None:
            # see if you have a VNCLASS tag and get the ID from there
            self.ID = vnclass.get("ID")
        else:
            # else self.soup is a VNSUBCLASS tag and get the ID from there
            self.ID = soup.get("ID")
        self.members = [Member(mem_soup) for mem_soup in soup.MEMBERS.find_all("MEMBER")]
        self.frames = [Frame(frame_soup, self.ID) for frame_soup in soup.FRAMES.find_all("FRAME")]
        self.names = [mem.name for mem in self.members]
        self.themroles = [ThematicRole(them_soup)
                          for them_soup in soup.THEMROLES.find_all("THEMROLE")]
        self.subclasses = [VerbClass(self.fname, sub_soup)
                           for sub_soup in soup.SUBCLASSES.find_all("VNSUBCLASS", recursive=False)]

    def __str__(self):
        return safe_utf8_encode("<VerbClass \"%s\" roles=%s frames=%s subclasses=%s members=%s>" \
            % (self.ID, len(self.themroles), len(self.frames),
               len(self.subclasses), len(self.members)))

    def __unicode__(self):
        return safe_utf8_decode("<VerbClass \"%s\" roles=%s frames=%s subclasses=%s members=%s>" \
                                % (self.ID, len(self.themroles), len(self.frames),
                                   len(self.subclasses), len(self.members)))

    def __repr__(self):
        return native_string(future_string(self.ID) + "\n" + future_string([repr(mem) for mem in self.members]) \
               + "\nThemRoles: " + future_string(self.themroles) \
               + "\nNames: " + future_string(self.names) \
               + "\nFrames: " + future_string(self.frames) \
               + "\nSubclasses: " + future_string(self.subclasses))


class Member(object):
    """Represents a single member of a VerbClass, with associated name, WordNet
    category, and PropBank grouping.
    """

    def __init__(self, soup):
        self.name = soup.get('name')
        self.wn = soup.get('wn')
        self.grouping = soup.get('grouping')

    def __repr__(self):
        return native_string("<Member %s %s %s>" % (self.name, self.wn, self.grouping))


class Frame(object):
    """Represents a single verb frame in VerbNet, with a description, examples,
    syntax, and semantics.
    """

    def __init__(self, soup, class_ID):
        self.class_ID = class_ID
        self.description = soup.DESCRIPTION.get('primary')
        self.examples = [e.text for e in soup.EXAMPLES.find_all("EXAMPLE")]
        self.syntax = self._get_syntax(soup)
        self.predicates = [Predicate(p) for p in soup.SEMANTICS.find_all("PRED")]

    def __repr__(self):
        return native_string("\nDescription: " + future_string(self.description) + \
               "\nExamples: " + future_string(self.examples) + \
               "\nSyntax: " + future_string(self.syntax) + \
               "\nPredicates: " + future_string(self.predicates) + "\n")

    @staticmethod
    def _get_syntax(soup):
        syntax_elements = [c for c in soup.SYNTAX.children
                           if isinstance(c, bs4.element.Tag)]
        roles = [SyntacticRole(soup) for soup in syntax_elements]
        # there used to be a test for the value of pos, now just write a warning
        # if we find a missing pos
        for role in roles:
            if role.pos is None:
                # FIXME: should log this
                print("Warning: empty pos in %s" % role)
        return roles


class ThematicRole(object):

    """Represents an entry in the "Roles" section in VerbNet, which is basically
    a list of all roles for a given verb class, with possible selectional
    restrictions"""

    def __init__(self, soup):
        self.role_type = soup.get('type')
        self.sel_restrictions = SelectionalRestrictions(soup.SELRESTRS)

    def __str__(self):
        if self.sel_restrictions.is_empty():
            return safe_utf8_encode(self.role_type)
        else:
            return safe_utf8_encode("%s / %s" % (self.role_type, self.sel_restrictions))

    def __unicode__(self):
        if self.sel_restrictions.is_empty():
            return safe_utf8_decode(self.role_type)
        else:
            return safe_utf8_decode("%s / %s" % (self.role_type, self.sel_restrictions))

    def html(self):
        def role(text): return "<span class=role>%s</span>" % text
        if self.sel_restrictions.is_empty():
            return role(self.role_type)
        else:
            return "%s / %s" % (role(self.role_type), self.sel_restrictions)


class Predicate(object):

    """Represents the different predicates assigned to a frame"""

    def __init__(self, soup):
        self.value = soup.get('value')
        args = soup.find_all('ARG')
        self.args = [(arg.get('type'), arg.get('value')) for arg in args]

    def __str__(self):
        return safe_utf8_encode("%s(%s)" % (self.value, ', '.join([at[1] for at in self.args])))

    def __unicode__(self):
        return safe_utf8_decode("%s(%s)" % (self.value, ', '.join([at[1] for at in self.args])))

    def __repr__(self):
        return native_string("Value: " + future_string(self.value) + " -- " + future_string(self.args))

    def find_arguments(self, arg):
        """Return all arguments in self.args where arg matches one of the argument's
        elements.  Note that an argument is a pair of an argument type and an
        argument value, as in <Event,during(E)> or <ThemRole,Theme>."""
        return [a for a in self.args if arg in a]

    def html(self):
        args = ', '.join([arg[1] for arg in self.args])
        return "<span class=pred>%s</span>(%s)" % (self.value, args)


class SyntacticRole(object):
    """Represents a syntactic role assigned to a frame"""

    def __init__(self, soup):
        self.pos = soup.name
        self.value = soup.get('value')
        self.restrictions = None
        self.restrictions = SyntacticRestrictions(soup.SYNRESTRS)
        # some syntactic roles have semantic selection restrictions on them, try
        # to collect them when there are no syntactic restrictions
        # TODO: must check where all restrictions occur
        if self.restrictions.is_empty():
            if soup.SELRESTRS is not None:
                self.restrictions = SelectionalRestrictions(soup.SELRESTRS)

    def __str__(self):
        return safe_utf8_encode("<SyntacticRole pos=%s value=%s restrictions=%s>" \
                                % (self.pos, self.value, self.restrictions))

    def __unicode__(self):
        return safe_utf8_decode("<SyntacticRole pos=%s value=%s restrictions=%s>" \
                                % (self.pos, self.value, self.restrictions))

class Restrictions(object):

    """Abstract class with common functionality for selectional restrictions and
    syntactic restrictions."""
    def __init__(self):
        self.name = ''
        self.restrictions = []
        self.logic = None

    def __str__(self):
        if self.is_empty():
            return safe_utf8_encode('()')
        op = ' & ' if self.logic == 'and' else ' | '
        return safe_utf8_encode("(%s)" % op.join([future_string(s) for s in self.restrictions]))

    def __unicode__(self):
        if self.is_empty():
            return safe_utf8_decode('()')
        op = ' & ' if self.logic == 'and' else ' | '
        return safe_utf8_decode("(%s)" % op.join([s for s in self.restrictions]))

    def is_empty(self):
        return self.restrictions == []

    def _set_restrictions(self, soup, tagname):
        """Set the restrictions given the tagname. Make sure that self.logic is set to
        None if there are no restrictions."""
        soups = soup.find_all(tagname)
        self.restrictions = [Restriction(soup) for soup in soups]
        if not self.restrictions:
            self.logic = None


class SelectionalRestrictions(Restrictions):

    """Stores information in the SELRESTRS tag. The list of SELREST tags inside will
    be put in self.selections. The SELRESTRS tag has an optional attribute named
    'logic', if it is expressed its value is always 'or'. If not expressed and
    the list of SELRESTR is not empty, then it is assumed to be 'and', if the
    list is empty than 'logic' will be set to None."""

    # TODO: check whether absence of 'or' indeed means 'and'

    def __init__(self, soup):
        super(SelectionalRestrictions, self).__init__()
        self.name = soup.name
        self.logic = soup.get('logic', 'and')
        self._set_restrictions(soup, 'SELRESTR')


class SyntacticRestrictions(Restrictions):

    """Stores information in the SYNRESTRS tag. The list of SYNREST tags inside will
    be put in self.selections. This class is slightly simpler than its counterpart
    SelectionalRestrictions since it never has the 'logic' attribute. However, it
    is assumed to be 'and'."""

    # TODO: check whether absence of 'logic' attribute indeed means 'and'

    def __init__(self, soup):
        super(SyntacticRestrictions, self).__init__()
        if soup is None:
            self.logic = None
            self.restrictions = []
        else:
            self.name = soup.name
            self.logic = 'and'
            self._set_restrictions(soup, 'SYNRESTR')


class Restriction(object):
    """Stores the content of SELRESTR or SYNRESTR, which has 'Value' and 'type'
    attributes, for example <SELRESTR Value="+" type="animate"/>."""

    def __init__(self, soup):
        self.name = soup.name
        self.srvalue = soup.get('Value')
        self.srtype = soup.get('type')

    def __str__(self):
        return safe_utf8_encode("%s%s" % (self.srvalue, self.srtype))

    def __unicode__(self):
        return safe_utf8_decode("%s%s" % (self.srvalue, self.srtype))


VERBNETDB = VerbnetDB()


if __name__ == '__main__':
    featurespec = re.compile(r'\.[a-z_-]+')
    frames = {}
    simplified_frames = set()
    for vcls in VERBNETDB.classes:
        for vfrm in vcls.frames:
            simplified_frames.add(featurespec.sub('', vfrm.description))
            frames.setdefault(vfrm.description, [])
            frames[vfrm.description].append(vcls)
    for frm, vclasses in frames.iteritems():
        print('===================')
        print(frm)
        mbrs = {}
        for vcls in vclasses:
            for mbr in vcls.members:
                mbrs.setdefault(mbr.name, 0)
                mbrs[mbr.name] += 1
        s = u'  '
        for mbr, c in mbrs.iteritems():
            if c == 2:
                ss = u'(%d) %s, ' % (c, mbr)
            else:
                ss = u'%s, ' % mbr
            if (len(ss) + len(s)) > 128:
                print(s)
                s = u'  ' + ss
            else:
                s += ss
        print(s)
    print('===================')
    for frm in simplified_frames:
        print(frm)






