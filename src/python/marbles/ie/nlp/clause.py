import collections
import states
import googlenlp
import sys
# Delay import because it takes time
from common import DELAY_SPACY_IMPORT
from marbles.ie.utils.vmap import VectorMap
from common import SyntheticSpan
from common import IndexSpan
from common import SubtreeSpan
from common import TYPEOF_SUBJECT
from common import TYPEOF_OBJECT
from common import TYPEOF_CONJ
from common import TYPEOF_AMOD
from common import TYPEOF_ISA_END
from common import TYPEOF_APPOS
from common import TYPEOF_AUX

if not DELAY_SPACY_IMPORT:
    import spacynlp


def is_descendant(token, ancestor, module):
    '''Check if token is a descendant of ancestor.

    Args:
        token: The token to test.
        ancestor: The potential ancestor of token.
        module: googlenlp or spacynlp

    Returns:
        True if token is a descendant of ancestor.
    '''
    while token.dep != module.dep.ROOT:
        if token.i == ancestor.i:
            return True
        token = token.head
    return token.i == ancestor.i


def is_ancestor(token, descendant, module):
    '''Check if token is a ancestor of descendant.

    Args:
        token: The token to test.
        descendant: The potential descendant of token.
        module: googlenlp or spacynlp

    Returns:
        True if token is a descendant of ancestor.
    '''
    return is_descendant(descendant, token, module)


def preprocess(doc):
    '''Preprocess document text.  This can help the parser.

    Args:
        text: The input text. Can be multiple lines.

    Returns:
         An tuple containing:
         - A array or pre-processed sentences when each sentence is a unicode string.
         - a changed flag
         - the root Noun or None if the root of the tree is not a Noun
    '''
    if isinstance(doc, googlenlp.Doc):
        nlp = googlenlp
        space = ' '
        empty = ''
        comma = ', '
    else:
        global DELAY_SPACY_IMPORT
        if DELAY_SPACY_IMPORT:
            import spacynlp
        if isinstance(doc, spacynlp.Doc):
            nlp = spacynlp
            space = u' '
            empty = u''
            comma = u', '
        else:
            raise TypeError
    result = []
    changed = False
    rootNoun = None
    for s in doc.sents:
        # Remove punctuation in the sequence appos-punct-det
        state = 0
        txt = empty
        last = None
        for tok in s:
            if tok.dep == nlp.dep.ROOT and tok.pos == nlp.pos.NOUN:
                # If the root is a noun we sometimes have an issue
                rootNoun = tok

            if tok.dep == nlp.dep.APPOS:
                state = 1
                txt += space + tok.text
            elif tok.pos == nlp.pos.NOUN:
                state = 3
                txt += space + tok.text
            elif state == 3 and tok.pos == nlp.pos.DET:
                txt += comma + tok.text
                state = 0
            elif state == 1 and tok.dep == nlp.dep.P:
                state = 2
                last = tok
            elif state == 2 and tok.dep == nlp.dep.CC:
                # Remove punctuation, this can help getting the correct root of the tree
                txt += space + tok.text
                changed = True
                state = 0
            elif state == 2:
                txt += last.text + space + tok.text
                state = 0
            else:
                txt += space + tok.text
                state = 0
        result.append(txt.strip())
    return (result, changed, rootNoun)


class Clause(object):
    '''View of a clause in a sentence.'''

    def __init__(self, doc, type, subjectSpan, verbSpan, objectSpans):
        if isinstance(doc, googlenlp.Doc):
            self._nlp = googlenlp
        else:
            global DELAY_SPACY_IMPORT
            if DELAY_SPACY_IMPORT:
                import spacynlp
            if isinstance(doc, spacynlp.Doc):
                self._nlp = spacynlp
            else:
                raise TypeError
        self._doc = doc
        self._type = type
        self._subjSpan = subjectSpan
        self._span = verbSpan
        #if isinstance(objectSpans, SubtreeSpan):
        if not isinstance(objectSpans, (list, tuple)):
            self._objSpans = [ objectSpans ]
        else:
            self._objSpans = objectSpans

        # Order by first index
        self._objSpans.sort()

        # Now do final fixup
        self._subjSpan._indexes = filter(lambda x: x <= subjectSpan.i, subjectSpan._indexes)
        # Handle synthetic spans
        if isinstance(verbSpan, IndexSpan):
            self._span._indexes = filter(lambda x: x <= verbSpan.i, verbSpan._indexes)

    def __repr__(self):
        return '<' + self.text + '>'

    @property
    def text(self):
        '''Return a string represent the compoents of the clause.'''
        txt = '(%s) (%s)' % (self._subjSpan.text, self._span.text)
        for s in self._objSpans:
            txt += ' (%s)' % s.text
        return txt

    @property
    def type(self):
        '''Return the type of clause.'''
        return self._type

    @property
    def subject(self):
        '''Return the subject span. Use subject.root to get the token.'''
        return self._subjSpan

    @property
    def root(self):
        '''Return verb span. Use root.root to get the token.'''
        return self._span

    @property
    def objects(self):
        '''Iterate objects.

        Yields:
            A SubjectSpan instance.
        '''
        for o in self._objSpans:
            yield o


class ParsedClause(Clause):
    '''View of a clause in a sentence.'''

    def __init__(self, doc, type, subject, verb, objects=None, exclude=None, merge=None):
        module = None
        if isinstance(doc, googlenlp.Doc):
            module = googlenlp
        else:
            global DELAY_SPACY_IMPORT
            if DELAY_SPACY_IMPORT:
                import spacynlp
            if isinstance(doc, spacynlp.Doc):
                module = spacynlp
            else:
                raise TypeError

        if not isinstance(subject, module.Token):
            raise TypeError
        if not isinstance(verb, module.Token):
            raise TypeError

        # Calculate span of subject
        subjSpan = SubtreeSpan(subject, nofollow=exclude)
        # Calculate span of objects
        if objects is not None:
            if isinstance(objects, collections.Iterable):
                objSpans = []
                for o in objects:
                    if not isinstance(o, module.Token):
                        raise TypeError
                    objSpans.append(SubtreeSpan(o, nofollow=exclude))
                # O(n^2) but len(objects) is typically < 3
                for o, s in zip(objects, objSpans):
                    for p, t in zip(objects, objSpans):
                        if p.i == o.i:
                            continue
                        if is_descendant(p, o, module):
                            s._indexes = filter(lambda x: x not in t._indexes, s._indexes)
                        elif is_descendant(o, p, module):
                            t._indexes = filter(lambda x: x not in s._indexes, t._indexes)
            else:
                if not isinstance(objects, (googlenlp.Token, spacynlp.Token)):
                    raise TypeError
                objSpans = [SubtreeSpan(objects)]
        else:
            objSpans = []

        # Calculate span of verb - remove objects, subject, and exclude spans
        # Calc indexes to remove from verb span
        verbSpan = SubtreeSpan(verb, shallow=True)
        for i in reversed(range(verbSpan.i)):
            x = doc[i]
            if (module.TYPEOF_MAP.lookup(x.dep) & TYPEOF_AUX) == 0 or x.head != verbSpan.root:
                break
            verbSpan._indexes.append(i)
        verbSpan._indexes = [x for x in reversed(verbSpan._indexes)]

        subjSpan.repair()
        verbSpan.repair()
        # Process merges formatted as: [ [focusIdx1, idx1, ...], [focusIdx2, idxN, ...]]
        if merge is not None and len(merge) > 0:
            for m in merge:
                focus = objSpans[ m[0] ]
                m = m[1:]
                m.sort()
                for i in reversed(m):
                    focus.union(objSpans[i])
                    objSpans.pop(i)
        # Finally call base class
        super(ParsedClause, self).__init__(doc=doc, type=type, subjectSpan=subjSpan, verbSpan=verbSpan, objectSpans=objSpans)


class ClauseFinder(object):

    def __init__(self, doc):
        '''Constructor.

        Args:
             doc: A google.Doc or spacy.Doc
        '''
        if isinstance(doc, googlenlp.Doc):
            self._nlp = googlenlp
            self._is_google = True
        else:
            self._is_google = False
            global DELAY_SPACY_IMPORT
            if DELAY_SPACY_IMPORT:
                import spacynlp
            if isinstance(doc, spacynlp.Doc):
                self._nlp = spacynlp
            else:
                raise TypeError
        self._doc = doc
        self._map = VectorMap(len(doc))
        self._advMap = VectorMap(len(doc))
        self._conjAMap = VectorMap(len(doc))
        self._conjOMap = VectorMap(len(doc))
        self._conjVMap = VectorMap(len(doc))
        self._conjVAMap = VectorMap(len(doc))
        self._dispatcher = None
        self._excludeList = None
        self._stk = None
        self._state = None
        self._coordList = None
        self.build_dispatcher()

    def _process_as_obj(self, O, V=None):
        if V is None: V = self.get_governor_verb(O)
        if V is None: return
        if not self._map.insert_new(V, [V, O]):
            self._map.append(V, O)

    def _process_as_subj(self, S, V=None):
        if V is None: V = self.get_governor_verb(S)
        if V is None:
            return
        elif not self._map.insert_new(V, [S, V]):
            X = self._map.lookup(V)
            if X[1].i != V.i:
                newX = [S]
                newX.extend(X)
                self._map.replace(V, newX)

    def _process_conj(self, token):
        A = self.get_first_of_conj(token)
        V = self.get_governor_verb(A)
        if V is not None:
            if A.pos == self._nlp.pos.VERB:
                assert token.pos == self._nlp.pos.VERB
                assert A == V
                assert V != token
                self._conjVMap.insert_new(V, [A])
                self._conjVMap.append(V, token)
            elif self.is_typeof(A.dep, TYPEOF_OBJECT):
                self._conjOMap.insert_new(V, [A])
                self._conjOMap.append(V, token)
            else:
                O = self.get_governor_obj(A)
                if O is not None:
                    self._conjAMap.insert_new(O, [A])
                    self._conjAMap.append(O, token)

    def _check_conj(self, token):
        O = token.head
        V = self.get_governor_verb(O)
        if V is not None:
            if O.pos == self._nlp.pos.VERB or \
                            self.is_typeof(O.dep, TYPEOF_OBJECT) or \
                            self.get_governor_obj(O) is not None:
                return True
        return False

    def is_typeof(self, dep_or_pos, typeof):
        '''Quick O(1) test for type of a dependency relation.

        Args:
            dep_or_pos: The dependency-relation or part-of-speech
            typeof: The typeof integer mask.

        Returns:
            True if dep_or_pos if of type 'typeof'.
        '''
        x = self._nlp.TYPEOF_MAP.lookup(dep_or_pos)
        return (x & typeof) != 0

    def get_governor_in_dep_list(self, token, dep_list):
        '''Get the governor token with dependency in tok_dep_list.

        Args:
            token: A Token instance.
            dep_list: A list of dependency types.

        Returns:
            The governor if it exists or None.
        '''
        while token.dep != self._nlp.dep.ROOT:
            if token.dep in dep_list:
                return token
            token = token.head
        return None

    def get_governor_dep(self, token, dep):
        '''Get the governor token with dependency equal to dep.

        Args:
            token: A Token instance.
            dep:The dependency type.

        Returns:
            The governor if it exists or None.
        '''
        while token.dep != self._nlp.dep.ROOT:
            if token.dep == dep:
                return token
            token = token.head
        return None

    def get_governor_dep_typeof(self, token, typeof):
        '''Get the governor token with dependency type in typeof

        Args:
            token: A Token instance.
            typeof: An integer typeof mask.

        Returns:
            The governor if it exists or None.
        '''
        while token.dep != self._nlp.dep.ROOT:
            if self.is_typeof(token.dep, typeof):
                return token
            token = token.head
        return None

    def get_governor_verb(self, token):
        '''Get the verb governor of token. If the verb is part of a conjunction
         then the head of conjunction is returned.

        Args:
            token: A Token instance.

        Returns:
            The governor verb if it exists or None.
        '''
        while token.dep != self._nlp.dep.ROOT:
            if token.pos == self._nlp.pos.VERB:
                # Trace conjunctions
                while token.dep == self._nlp.dep.CONJ and token.head.pos == self._nlp.pos.VERB:
                    token = token.head
                return token
            token = token.head
        if token.pos == self._nlp.pos.VERB:
            return token
        return None

    def get_governor_in_pos_list(self, token, pos_list):
        '''Get the governor with part-of-speech in pos_list.

        Args:
            token: A Token instance.
            pos_list: The part-of-speech list

        Returns:
            The governor part-of-speech if it exists or None.
        '''
        while token.dep != self._nlp.dep.ROOT:
            if token.pos in pos_list:
                return token
            token = token.head
        if token.pos in pos_list:
            return token
        return None

    def get_governor_pos(self, token, pos):
        '''Get the governor with part-of-speech equal to pos.

        Args:
            token: A Token instance.
            pos: The part-of-speech

        Returns:
            The governor part-of-speech if it exists or None.
        '''
        while token.dep != self._nlp.dep.ROOT:
            if token.pos == pos:
                return token
            token = token.head
        if token.pos == pos:
            return token
        return None

    def get_governor_subj(self, token):
        '''Get the governor subject token.

        Args:
            token: A Token instance.

        Returns:
            The governor subject if it exists or None.
        '''
        return self.get_governor_dep(token, self._nlp.dep.NSUBJ)

    def get_governor_obj(self, token):
        '''Get the governor object token.

        Args:
            token: A Token instance.

        Returns:
            The governor object if it exists or None.
        '''
        return self.get_governor_dep_typeof(token, TYPEOF_OBJECT)

    def get_first_of_conj(self, token):
        '''Get the first conjunction linking to token.

        Args:
            token: A Token instance.

        Returns:
            The first token in the conjunction.
        '''
        assert token.dep == self._nlp.dep.CONJ
        while token.dep != self._nlp.dep.ROOT:
            if token.dep != self._nlp.dep.CONJ:
                return token
            token = token.head
        return token

    def _dispatch_case_nsubjpass(self, token, clauses):
        if token.text.lower() in ['which', 'that']:
            S = self.get_governor_subj(token)
            if S is None:
                V = self.get_governor_verb(token)
                if V is None:
                    self._process_as_subj(token)
                else:
                    Vu = self.get_governor_verb(V.head)
                    if Vu is not None:
                        L = self._map.lookup(Vu)
                        if L is not None and L[1] == Vu:
                            self._map.insert_new(V, [L[0], V])
                            self._excludeList.append(token)
            else:
                V = self.get_governor_verb(token)
                if V is not None:
                    self._stk.append(self._state)
                    self._excludeList.append(token)
                    self._state = (states.NSUBJ_FIND, S)
                    self._process_as_subj(S, V)
                else:
                    self._process_as_subj(token)
        else:
            self._process_as_subj(token)

    def _dispatch_case_nsubj(self, token, clauses):
        self._process_as_subj(token, None)

    def _dispatch_case_obj(self, token, clauses):
        self._process_as_obj(token)

    def _dispatch_case_conj(self, token, clauses):
        # Find the first conjunction and label all other the same
        A = self.get_first_of_conj(token)
        V = self.get_governor_verb(A)
        if V is not None:
            if A.pos == self._nlp.pos.VERB:
                assert token.pos == self._nlp.pos.VERB
                assert A == V
                assert V != token
                self._conjVMap.insert_new(V, [A])
                self._conjVMap.append(V, token)
            elif self.is_typeof(A.dep, TYPEOF_OBJECT):
                self._conjOMap.insert_new(V, [A])
                self._conjOMap.append(V, token)
            else:
                O = self.get_governor_obj(A)
                if O is not None:
                    self._conjAMap.insert_new(O, [A])
                    self._conjAMap.append(O, token)
                elif V.lemma == 'be' and A.dep == self._nlp.dep.ATTR:
                    self._conjVAMap.insert_new(V, [A])
                    self._conjVAMap.append(V, token)
                    L = self._map.lookup(V)
                    if L is not None and len(L) == 3 and L[2] == A:
                        del L[2]

    def _dispatch_case_pos_adp(self, token, clauses):
        # FIXME: Should check if this is the first token with XCOMP head
        if token.dep == self._nlp.dep.MARK and token.head.dep in [self._nlp.dep.XCOMP, self._nlp.dep.CCOMP]:
            self._excludeList.append(token)
            O = self._doc[token.i + 1]
        else:
            O = token
        '''
        if self.is_typeof(token.head.dep, TYPEOF_AMOD) and (token.head.i + 1) == token.i:
            self._process_as_obj(token.head, self.get_governor_verb(token))
        else:
            self._process_as_obj(O, self.get_governor_verb(token))
        '''

    def _dispatch_case_pobj(self, token, clauses):
        P = self.get_governor_pos(token, self._nlp.pos.ADP)
        if P is not None:
            self._process_as_obj(P, self.get_governor_verb(token))

    def _dispatch_case_cc(self, token, clauses):
        # Save for later. This will be excluded when we expand conjunctions
        if self._check_conj(token):
            self._coordList.append(token)

    def _dispatch_case_xcomp(self, token, clauses):
        # Xcomp can have a VERB or ADJ as a parent
        VA = self.get_governor_in_pos_list(token.head, [self._nlp.pos.VERB, self._nlp.pos.ADJ])
        if VA is not None:
            if VA.dep == self._nlp.dep.ROOT:
                # OK token will be used as is
                V = VA
                VA = token
            else:
                # TODO: can we further decompose xcomp
                if VA.pos == self._nlp.pos.VERB:
                    V = VA
                    VA = token
                else:
                    V = self.get_governor_verb(VA.head)
                    if V is None: return
            if not self._map.insert_new(V, [V, VA]):
                if VA not in self._map.lookup(V):
                    self._map.append(V, VA)

    def _dispatch_case_appos(self, token, clauses):
        # Check if we need to create a synthetic is-a relationship
        if self.is_typeof(token.head.dep, TYPEOF_SUBJECT):
            if self._state[0] == states.NSUBJ_FIND:
                assert token.head.dep == self._nlp.dep.NSUBJPASS
                S = self._state[1]
            else:
                S = token.head
            self._excludeList.append(token)
            self._stk.append(self._state)
            self._state = (states.ISA_FIND, S, [token], [])

    def _dispatch_case_advmod(self, token, clauses):
        if token.text.lower() == 'how':
            V = self.get_governor_verb(token)
            if V is not None:
                if token.head.dep == self._nlp.dep.DEP:
                    self._advMap.append(V, token.head)
                else:
                    self._advMap.append(V, token)

    def _dispatch_isa_default(self, token, clauses):
        # accumulate
        self._excludeList.append(token)

    def _dispatch_isa_case_conj(self, token, clauses):
        # Each element in self._state[2] list is the start of a new isa clause
        self._excludeList.append(token)
        self._state[2].append(token)

    def _dispatch_isa_case_punct(self, token, clauses):
        # Punctuation added to global exclude list before token processing. Also
        # add to our local exclude list for this state.
        self._state[3].append(token)

    def _dispatch_isa_case_cc(self, token, clauses):
        self._excludeList.append(token)
        # FIXME: to be in this state we must have a govenor APPOS so first test should not be required.
        if token.head.dep == self._nlp.dep.APPOS or token.head.dep == self._nlp.dep.CONJ:
            if token.text == 'and':
                self._state[3].append(token)

    def _dispatch_isa_case_vmod(self, token, clauses):
        # Indicates another isa item
        self._excludeList.append(token)
        self._state[2].append(token)

    def _close_isa_case(self, limitIdx, clauses):
        # stop
        other = []
        for i in range(len(self._state[2])):
            o = self._state[2][i]
            nofollow = []
            nofollow.extend(self._state[3])
            nofollow.extend(other)
            nofollow.extend(self._state[2][i + 1:])
            objSpan = SubtreeSpan(o, nofollow=nofollow)
            objSpan._indexes = filter(lambda x: x < limitIdx, objSpan._indexes)
            clauses.append(Clause(self._doc, \
                                  type='ISA', \
                                  subjectSpan=SubtreeSpan(self._state[1], shallow=True), \
                                  verbSpan=SyntheticSpan('is'), \
                                  objectSpans=objSpan))
            other.append(o)

    def build_dispatcher(self):
        '''Build dispatcher for O(1) execution of switch/case on dependency relation.'''
        # Dispatcher is parser dependent
        # FIXME: should only do this once per parser.
        self._dispatcher = [None] * states.STATE_LIMIT

        # default dispatcher
        self._dispatcher[states.ROOT_FIND.i] = VectorMap(max(self._nlp.dep.DEP_UPPER_BOUND, self._nlp.pos.POS_UPPER_BOUND) + 1)
        self._dispatcher[states.ROOT_FIND.i].insert_new(self._nlp.dep.NSUBJ, self._dispatch_case_nsubj)
        self._dispatcher[states.ROOT_FIND.i].insert_new(self._nlp.dep.NSUBJPASS, self._dispatch_case_nsubjpass)
        self._dispatcher[states.ROOT_FIND.i].insert_new(self._nlp.dep.DOBJ, self._dispatch_case_obj)
        self._dispatcher[states.ROOT_FIND.i].insert_new(self._nlp.dep.IOBJ, self._dispatch_case_obj)
        self._dispatcher[states.ROOT_FIND.i].insert_new(self._nlp.dep.ACOMP, self._dispatch_case_obj)
        self._dispatcher[states.ROOT_FIND.i].insert_new(self._nlp.dep.ATTR, self._dispatch_case_obj)
        self._dispatcher[states.ROOT_FIND.i].insert_new(self._nlp.dep.APPOS, self._dispatch_case_appos)
        self._dispatcher[states.ROOT_FIND.i].insert_new(self._nlp.dep.CONJ, self._dispatch_case_conj)
        self._dispatcher[states.ROOT_FIND.i].insert_new(self._nlp.dep.CC, self._dispatch_case_cc)
        self._dispatcher[states.ROOT_FIND.i].insert_new(self._nlp.dep.CCOMP, self._dispatch_case_xcomp)
        self._dispatcher[states.ROOT_FIND.i].insert_new(self._nlp.dep.XCOMP, self._dispatch_case_xcomp)
        self._dispatcher[states.ROOT_FIND.i].insert_new(self._nlp.dep.POBJ, self._dispatch_case_pobj)
        self._dispatcher[states.ROOT_FIND.i].insert_new(self._nlp.dep.ADVMOD, self._dispatch_case_advmod)
        self._dispatcher[states.ROOT_FIND.i].insert_new(self._nlp.pos.ADP, self._dispatch_case_pos_adp)
        if not self._is_google:
            self._dispatcher[states.ROOT_FIND.i].insert_new(self._nlp.dep.COMPLM, self._dispatch_case_xcomp)

        # Same dispatcher as root
        self._dispatcher[states.NSUBJ_FIND.i] = self._dispatcher[states.ROOT_FIND.i]

        # isa dispatcher
        self._dispatcher[states.ISA_FIND.i] = VectorMap(self._nlp.dep.DEP_UPPER_BOUND + 1)
        self._dispatcher[states.ISA_FIND.i].insert_new(self._nlp.dep.CONJ, self._dispatch_isa_case_conj)
        self._dispatcher[states.ISA_FIND.i].insert_new(self._nlp.dep.CC, self._dispatch_isa_case_cc)
        self._dispatcher[states.ISA_FIND.i].insert_new(self._nlp.dep.P, self._dispatch_isa_case_punct)
        self._dispatcher[states.ISA_FIND.i].insert_new(self._nlp.dep.VMOD, self._dispatch_isa_case_vmod)
        self._dispatcher[states.ISA_FIND.i].set_default_lookup(self._dispatch_isa_default)

    def find_clauses(self, sentence):
        '''Find all clauses in a sentence.

        Args:
            sentence: A Span describing a sentence.

        Returns:
            A list of Clause instances or a Clause instance.
        '''
        global DELAY_SPACY_IMPORT
        if not isinstance(sentence, SubtreeSpan):
            if DELAY_SPACY_IMPORT:
                import spacynlp
            if not isinstance(sentence, spacynlp.Span):
                raise TypeError
        # Reset lookup tables
        self._map.clear()
        self._conjAMap.clear()
        self._conjOMap.clear()
        self._conjVMap.clear()
        self._advMap.clear()
        self._conjVAMap.clear()
        self._excludeList = []
        self._coordList = []
        clauses = []
        self._state = (states.ROOT_FIND, None)
        self._stk = []
        # find all token indexes from this root
        for token in sentence:
            # TODO: remove this debug code
            if token.text == 'Bell':
                pass
            # We exclude all punctuation from clauses
            if token.pos == self._nlp.pos.PUNCT:
                self._excludeList.append(token)

            # Check for state change
            if self._state[0] == states.NSUBJ_FIND:
                if self.get_governor_subj(token) != self._state[1]:
                    self._state = self._stk.pop(-1)

            elif self._state[0] == states.ISA_FIND:
                # (state_id,subject,list,exclude)
                if not is_descendant(token, self._state[1], self._nlp):
                    self._close_isa_case(token.i, clauses)
                    self._state = self._stk.pop(-1)
                elif token.dep == self._nlp.dep.NSUBJPASS:
                    S = self.get_governor_subj(token.head)
                    if S is not None and S == self._state[1]:
                        self._close_isa_case(token.i, clauses)
                        self._state = self._stk.pop(-1)

            # Dispatch on POS then DEP
            dispatch = self._dispatcher[self._state[0].i].lookup(token.pos, nodefault=True)
            if dispatch is not None:
                dispatch(token, clauses)
            else:
                dispatch = self._dispatcher[self._state[0].i].lookup(token.dep)
                if dispatch is not None:
                    dispatch(token, clauses)

        # Ensure states are closed
        if self._state[0] == states.ISA_FIND:
            self._close_isa_case(token.i+1, clauses)

        for k, m in self._map:
            if m is None or self._nlp.get_type_name(m[0].dep) != 'S': continue
            type = ''
            for tok in m:
                type += self._nlp.get_type_name(tok.pos) + self._nlp.get_type_name(tok.dep)

            advList = self._advMap.lookup(m[1])
            if advList is None:
                advList = []

            if len(m) >= 3:
                # Check for conjunctions. Iterate and replace the object in SVO.
                conjVList = self._conjVMap.lookup(m[1])
                if conjVList is None:
                    conjVList = [m[1]]
                else: # sanity check
                    assert m[1] == conjVList[0]
                conjOList = self._conjOMap.lookup(m[1])
                if conjOList is None:
                    conjOList = [m[2]]
                else:
                    assert m[2] == conjOList[0]

                if len(m) > 3:
                    objs = [ None, None ]
                    objs.extend(m[3:])
                else:
                    objs = [ None, None ]

                objs.extend(advList)

                exclude = [x for x in self._excludeList]
                exclude.extend(self._coordList)
                for V in conjVList:
                    for O in conjOList:
                        objs[1] = O
                        conjAList = self._conjAMap.lookup(m[2])
                        if conjAList is None:
                            clauses.append(ParsedClause(doc=self._doc, type=type, subject=m[0], verb=V, objects=objs[1:],
                                                        exclude=exclude))
                        else:
                            excludeA = exclude
                            if conjAList[0].dep == self._nlp.dep.AMOD:
                                # Tell ParsedClause to combine objs[0:2] into a single term
                                merge = [ [1,0] ]
                            else:
                                merge = None
                            for i in range(len(conjAList)):
                                A = conjAList[i]
                                objs[0] = A
                                x = []
                                x.extend(excludeA)
                                x.extend(conjAList[i+1:])
                                clauses.append(ParsedClause(doc=self._doc, type=type, subject=m[0], verb=V, objects=objs,
                                                            exclude=x, merge=merge))
                                excludeA.append(A)
                            objs[0] = None
                        objs[1] = None
            else:
                conjVList = self._conjVMap.lookup(m[1])
                conjVAList = self._conjVAMap.lookup(m[1])
                if conjVList is None:
                    conjVList = [m[1]]
                else: # sanity check
                    assert m[1] == conjVList[0]
                if conjVAList is None:
                    for V in conjVList:
                        clauses.append(ParsedClause(doc=self._doc, type=type, subject=m[0], verb=V, exclude=self._excludeList))
                else:
                    exclude = []
                    exclude.extend(self._excludeList)
                    for V in conjVList:
                        for i in range(len(conjVAList)):
                            A = conjVAList[i]
                            x = []
                            x.extend(exclude)
                            x.extend(conjVAList[i+1:])
                            clauses.append(ParsedClause(doc=self._doc, type=type, subject=m[0], verb=V, objects=A, exclude=x))
                            exclude.append(A)

        # reset finder
        self._map.clear()
        self._conjAMap.clear()
        self._conjOMap.clear()
        self._conjVMap.clear()
        self._excludeList = None
        self._coordList = None
        self._stk = None
        self._state = None

        return clauses

