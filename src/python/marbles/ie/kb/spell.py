"""
symspell_python.py

################

To run, execute python symspell_python.py at the prompt.
Make sure the dictionary "big.txt" is in the current working directory.
Enter word to correct when prompted.

################

v 1.3 last revised 29 Apr 2017
Please note: This code is no longer being actively maintained.

License:
This program is free software; you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License,
version 3.0 (LGPL-3.0) as published by the Free Software Foundation.
http://www.opensource.org/licenses/LGPL-3.0

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU General Public License for more details.

Please acknowledge Wolf Garbe, as the original creator of SymSpell,
(see note below) in any use.

################

This program is a Python version of a spellchecker based on SymSpell,
a Symmetric Delete spelling correction algorithm developed by Wolf Garbe
and originally written in C#.

From the original SymSpell documentation:

"The Symmetric Delete spelling correction algorithm reduces the complexity
 of edit candidate generation and dictionary lookup for a given Damerau-
 Levenshtein distance. It is six orders of magnitude faster and language
 independent. Opposite to other algorithms only deletes are required,
 no transposes + replaces + inserts. Transposes + replaces + inserts of the
 input term are transformed into deletes of the dictionary term.
 Replaces and inserts are expensive and language dependent:
 e.g. Chinese has 70,000 Unicode Han characters!"

For further information on SymSpell, please consult the original
documentation:
  URL: blog.faroo.com/2012/06/07/improved-edit-distance-based-spelling-correction/
  Description: blog.faroo.com/2012/06/07/improved-edit-distance-based-spelling-correction/

The current version of this program will output all possible suggestions for
corrections up to an edit distance (configurable) of max_edit_distance = 3.

With the exception of the use of a third-party method for calculating
Demerau-Levenshtein distance between two strings, we have largely followed
the structure and spirit of the original SymSpell algorithm and have not
introduced any major optimizations or improvements.

################

Changes from version (1.0):
We implement allowing for less suggest_mode options: e.g. when only a single
recommended correction is required, the search may terminate early, thereby
enhancing performance.

Changes from version (1.1):
Removed unnecessary condition in create_dictionary_entry

Changes from version (1.2):
Update maintenance status

#################

Sample output:

Please wait...
Creating dictionary...
total words processed: 1105285
total unique words in corpus: 29157
total items in dictionary (corpus words and deletions): 2151998
  edit distance for deletions: 3
  length of longest word in corpus: 18

Word correction
---------------
Enter your input (or enter to exit): there
('there', (2972, 0))

Enter your input (or enter to exit): hellot
('hello', (1, 1))

Enter your input (or enter to exit): accomodation
('accommodation', (5, 1))

Enter your input (or enter to exit):
goodbye


"""
from __future__ import unicode_literals, print_function
import re
import collections
import threading
import copy
import itertools
import StringIO
from marbles import safe_utf8_decode, safe_utf8_encode, PROJDIR


# Top suggestion
BEST_SUGGESTION = 0
# All suggestions of smallest edit distance
NBEST_SUGGESTIONS = 1
# All suggestions <= max_edit_distance (slower, no early termination)
ALL_SUGGESTIONS = 2


_CCGBANK_IGNORE = re.compile(r"^'(?:ll|s|ve|nt|m|re|d)(?:\s|$)|-[A-Z]+-?$", re.UNICODE | re.IGNORECASE)


def dameraulevenshtein(seq1, seq2):
    """Calculate the Damerau-Levenshtein distance between sequences.

    This method has not been modified from the original.
    Source: http://mwh.geek.nz/2009/04/26/python-damerau-levenshtein-distance/

    This distance is the number of additions, deletions, substitutions,
    and transpositions needed to transform the first sequence into the
    second. Although generally used with strings, any sequences of
    comparable objects will work.

    Transpositions are exchanges of *consecutive* characters; all other
    operations are self-explanatory.

    This implementation is O(N*M) time and O(M) space, for N and M the
    lengths of the two sequences.

    >>> dameraulevenshtein('ba', 'abc')
    2
    >>> dameraulevenshtein('fee', 'deed')
    2

    It works with arbitrary sequences too:
    >>> dameraulevenshtein('abcd', ['b', 'a', 'c', 'd', 'e'])
    2

    Remarks:
        Threadsafe.
    """
    # codesnippet:D0DE4716-B6E6-4161-9219-2903BF8F547F
    # Conceptually, this is based on a len(seq1) + 1 * len(seq2) + 1 matrix.
    # However, only the current and two previous rows are needed at once,
    # so we only store those.
    oneago = None
    thisrow = range(1, len(seq2) + 1) + [0]
    for x in xrange(len(seq1)):
        # Python lists wrap around for negative indices, so put the
        # leftmost column at the *end* of the list. This matches with
        # the zero-indexed strings and saves extra calculation.
        twoago, oneago, thisrow = oneago, thisrow, [0] * len(seq2) + [x + 1]
        for y in xrange(len(seq2)):
            delcost = oneago[y] + 1
            addcost = thisrow[y - 1] + 1
            subcost = oneago[y - 1] + (seq1[x] != seq2[y])
            thisrow[y] = min(delcost, addcost, subcost)
            # This block deals with transpositions
            if (x > 0 and y > 0 and seq1[x] == seq2[y - 1]
                and seq1[x-1] == seq2[y] and seq1[x] != seq2[y]):
                thisrow[y] = min(thisrow[y], twoago[y - 2] + 1)
    return thisrow[len(seq2) - 1]


class SymSpell(object):
    pattern = re.compile(r'[a-z]+')

    def __init__(self):
        self.max_edit_distance = 3
        self.dictionary = {}
        self.longest_word_length = 0
        self.modify_lock = threading.RLock()
        self.silent = True
        self.wnstats = None

    def get_deletes_list(self, w):
        """Given a word, derive strings with up to max_edit_distance characters deleted."""
        deletes = set()
        queue = set([w])
        for d in range(self.max_edit_distance):
            temp_queue = set()
            for word in itertools.ifilter(lambda w: len(w) > 1, queue):
                for c in range(len(word)):  # character index
                    word_minus_c = word[:c] + word[c+1:]
                    deletes.add(word_minus_c)
                    temp_queue.add(word_minus_c)
            queue = temp_queue
        return sorted(deletes)

    def create_dictionary_entry(self, w):
        """Add word `w` and its derived deletions to dictionary.

        Remarks:
            Not threadsafe.
        """
        # check if word is already in dictionary
        # dictionary entries are in the form: (list of suggested corrections,
        # frequency of word in corpus)
        w = safe_utf8_decode(w)
        new_real_word_added = False
        if w in self.dictionary:
            # increment frequency of word in corpus
            entry = (self.dictionary[w][0], self.dictionary[w][1] + 1)
        else:
            entry = ([], 1)
            self.longest_word_length = max(self.longest_word_length, len(w))
        self.dictionary[w] = entry

        if entry[1] == 1:
            # first appearance of word in corpus
            # n.b. word may already be in dictionary as a derived word
            # (deleting character from a real word)
            # but counter of frequency of word in corpus is not incremented
            # in those cases)
            new_real_word_added = True
            deletes = self.get_deletes_list(w)
            for item in deletes:
                # If not in dictionary add empty suggestion list and zero frequency
                # then add (correct) word to delete's suggested correction list
                self.dictionary.setdefault(item, ([], 0))[0].append(w)
                # TODO: remove commented code below
                #if item in self.dictionary:
                    # add (correct) word to delete's suggested correction list
                #    self.dictionary[item][0].append(w)
                #else:
                    # note frequency of word in corpus is not incremented
                #    self.dictionary[item] = ([w], 0)
        return new_real_word_added

    def save(self, stream):
        self.modify_lock.acquire()
        try:
            stream.write(b'%d:%d\n' % (self.max_edit_distance, self.longest_word_length))
            for k, v in self.dictionary.iteritems():
                stream.write(safe_utf8_encode(k))
                stream.write(b':')
                stream.write(safe_utf8_encode(str(v[1])))
                stream.write(b':')
                stream.write(safe_utf8_encode(':'.join(v[0])))
                stream.write(b'\n')
        finally:
            self.modify_lock.release()

    def restore(self, stream):
        self.modify_lock.acquire()
        try:
            ln = stream.readline().strip().split(b':')
            self.max_edit_distance = int(ln[0])
            self.longest_word_length = int(ln[1])
            for line in stream:
                ln = line.strip().split(b':')
                words = [safe_utf8_decode(x) for x in ln[2:] if len(x) != 0]
                self.dictionary[safe_utf8_decode(ln[0])] = (words, int(ln[1]))
        finally:
            self.modify_lock.release()

    def build_from_corpus(self, stream, stats=None):
        """Create from a file containing a corpus of words.

        Args:
            stream: A stream or file
            stats: A tuple of existing total-word-count, unique-word-count

        Returns:
            A tuple of total-word-count, unique-word-count

        Remarks:
            Threadsafe.
        """
        global _CCGBANK_IGNORE
        total_word_count = 0 if stats is None else stats[0]
        unique_word_count = 0 if stats is None else stats[1]
        self.modify_lock.acquire()
        try:
            if not self.silent:
                print("Creating dictionary...")
            for line in stream:
                # separate words by non-alphabetical characters
                words = self.pattern.findall(line.lower())
                for word in words:
                    if _CCGBANK_IGNORE.match(word):
                        continue
                    total_word_count += 1
                    if self.create_dictionary_entry(word):
                        unique_word_count += 1
        finally:
            self.modify_lock.release()

        if not self.silent:
            print("total words processed: %i" % total_word_count)
            print("total unique words in corpus: %i" % unique_word_count)
            print("total items in dictionary (corpus words and deletions): %i" % len(self.dictionary))
            print("  edit distance for deletions: %i" % self.max_edit_distance)
            print("  length of longest word in corpus: %i" % self.longest_word_length)
        return total_word_count, unique_word_count

    def build_from_wordnet(self):
        """Create from a wordnet.

        Returns:
            A tuple of total-word-count, unique-word-count

        Remarks:
            Threadsafe.
        """
        if self.wnstats is not None:
            return self.wnstats
        from nltk.corpus import wordnet as wn
        strm = StringIO.StringIO()
        i = 1000
        i_init = i
        stats = None
        for s in wn.all_synsets():
            nms = s.lemma_names()
            strm.write(' '.join(nms))
            strm.write('\n')
            i -= 1
            if i == 0:
                i = i_init
                strm.seek(0)
                stats = self.build_from_corpus(strm, stats)
                strm.seek(0)
                strm.truncate(0)
        strm.seek(0)
        self.wnstats = self.build_from_corpus(strm, stats)
        return self.wnstats

    def get_suggestions(self, string, suggest_mode=BEST_SUGGESTION):
        """Return list of suggested corrections for the potentially incorrectly spelled word.

        # get_suggestions('file', suggest_mode=BEST_SUGGESTION)
          returns 'file'
        # get_suggestions('file', suggest_mode=NBEST_SUGGESTIONS)
          returns ['file', 'five', 'fire', 'fine', ...]
        # get_suggestions('file', suggest_mode=ALL_SUGGESTIONS)
          returns [('file', (5, 0)), ('five', (67, 1)), ('fire', (54, 1)), ('fine', (17, 1))...]
        """
        global BEST_SUGGESTION, NBEST_SUGGESTIONS, ALL_SUGGESTIONS
        if (len(string) - self.longest_word_length) > self.max_edit_distance:
            if not self.silent:
                print("no items in dictionary within maximum edit distance")
            return []

        string = safe_utf8_decode(string)
        suggest_dict = {}
        min_suggest_len = float('inf')

        queue = collections.deque([string])
        q_dictionary = {}  # items other than string that we've checked

        while len(queue) != 0:
            q_item = queue.popleft()

            # early exit
            if suggest_mode < ALL_SUGGESTIONS and len(suggest_dict) > 0 and \
                    (len(string)-len(q_item)) > min_suggest_len:
                break

            # process queue item
            if q_item in self.dictionary and q_item not in suggest_dict:
                q_item_entry = self.dictionary[q_item]
                if q_item_entry[1] > 0:
                    # word is in dictionary, and is a word from the corpus, and
                    # not already in suggestion list so add to suggestion
                    # dictionary, indexed by the word with value (frequency in
                    # corpus, edit distance)
                    # note q_items that are not the input string are shorter
                    # than input string since only deletes are added (unless
                    # manual dictionary corrections are added)
                    assert len(string) >= len(q_item)
                    suggest_dict[q_item] = (q_item_entry[1], len(string) - len(q_item))
                    # early exit
                    if suggest_mode < ALL_SUGGESTIONS and len(string) == len(q_item):
                        break
                    elif (len(string) - len(q_item)) < min_suggest_len:
                        min_suggest_len = len(string) - len(q_item)

                # the suggested corrections for q_item as stored in
                # dictionary (whether or not q_item itself is a valid word
                # or merely a delete) can be valid corrections
                for sc_item in q_item_entry[0]:
                    if sc_item not in suggest_dict:

                        # compute edit distance
                        # suggested items should always be longer
                        # (unless manual corrections are added)
                        assert len(sc_item) > len(q_item)

                        # q_items that are not input should be shorter
                        # than original string
                        # (unless manual corrections added)
                        assert len(q_item) <= len(string)

                        if len(q_item) == len(string):
                            assert q_item == string
                            item_dist = len(sc_item) - len(q_item)

                        # item in suggestions list should not be the same as
                        # the string itself
                        assert sc_item != string

                        # calculate edit distance using, for example,
                        # Damerau-Levenshtein distance
                        item_dist = dameraulevenshtein(sc_item, string)

                        # do not add words with greater edit distance if
                        # suggest_mode setting not ALL_SUGGESTIONS
                        if suggest_mode < ALL_SUGGESTIONS and item_dist > min_suggest_len:
                            pass
                        elif item_dist <= self.max_edit_distance:
                            assert sc_item in self.dictionary  # should already be in dictionary if in suggestion list
                            suggest_dict[sc_item] = (self.dictionary[sc_item][1], item_dist)
                            if item_dist < min_suggest_len:
                                min_suggest_len = item_dist

                        # depending on order words are processed, some words
                        # with different edit distances may be entered into
                        # suggestions; trim suggestion dictionary if suggest_mode
                        # setting not ALL_SUGGESTIONS
                        if suggest_mode < ALL_SUGGESTIONS:
                            suggest_dict = {k:v for k, v in suggest_dict.items() if v[1]<=min_suggest_len}
                            #suggest_dict = dict(filter(lambda x: x[1][1] <= min_suggest_len, suggest_dict.items()))

            # now generate deletes (e.g. a substring of string or of a delete)
            # from the queue item
            # as additional items to check -- add to end of queue
            assert len(string)>=len(q_item)

            # do not add words with greater edit distance if suggest_mode setting
            # is not ALL_SUGGESTIONS
            if suggest_mode < ALL_SUGGESTIONS and (len(string)-len(q_item)) > min_suggest_len:
                pass
            elif (len(string)-len(q_item)) < self.max_edit_distance and len(q_item) > 1:
                for c in range(len(q_item)): # character index
                    word_minus_c = q_item[:c] + q_item[c+1:]
                    if word_minus_c not in q_dictionary:
                        queue.append(word_minus_c)
                        q_dictionary[word_minus_c] = None  # arbitrary value, just to identify we checked this

            # queue is now empty: convert suggestions in dictionary to
            # list for output
            if not self.silent and suggest_mode != BEST_SUGGESTION:
                print("number of possible corrections: %i" %len(suggest_dict))
                print("  edit distance for deletions: %i" % self.max_edit_distance)

            # output option NBEST_SUGGESTIONS
            # sort results by ascending order of edit distance and descending
            # order of frequency
            #     and return list of suggested word corrections only:
            # return sorted(suggest_dict, key = lambda x:
            #               (suggest_dict[x][1], -suggest_dict[x][0]))

            # output option ALL_SUGGESTIONS
            # return list of suggestions with (correction,
            #                                  (frequency in corpus, edit distance)):
            as_list = suggest_dict.items()
            outlist = sorted(as_list, key=lambda(term, (freq, dist)): (dist, -freq))
            if suggest_mode == BEST_SUGGESTION:
                return outlist[0][0]
            elif suggest_mode == NBEST_SUGGESTIONS:
                return [x[0] for x in outlist]
            return outlist

    def get_compound_suggestions(self, input):
        termList1 = filter(lambda y: len(y) != 0, [x.strip() for x in input.split(' ')])
        suggestionsPreviousTerm = []    # suggestions for a single term
        suggestions = []                # suggestions for a single term
        suggestionParts = []            # 1 line with separate parts

        # translate every term to its best suggestion, otherwise it remains unchanged
        lastCombi = False
        for i in range(len(termList1)):
            # suggestions for a single term
            suggestionsPreviousTerm = [copy.copy(x) for x in suggestions]
            suggestions = self.get_suggestions(termList1[i], ALL_SUGGESTIONS)

            # combi check, always before split
            if i > 0 and not lastCombi:
                suggestionsCombi = self.get_suggestions(termList1[i - 1] + termList1[i], ALL_SUGGESTIONS)

                if len(suggestionsCombi) != 0:
                    best1 = suggestionParts[len(suggestionParts) - 1]
                    best2 = suggestions[0] if len(suggestions) != 0 else (termList1[i], (0, self.max_edit_distance + 1))
                    if (suggestionsCombi[0][1][1] + 1) < dameraulevenshtein(termList1[i - 1] + " " + termList1[i],
                                                                            best1[0] + " " + best2[0]):
                        suggestionsCombi[0] = (suggestionsCombi[0][0], (suggestionsCombi[0][1][0],
                                                                        suggestionsCombi[0][1][1]+1))
                        suggestionParts[-1] = suggestionsCombi[0]
                        lastCombi = True
                        continue
            lastCombi = False
            # alway split terms without suggestion / never split terms with suggestion ed=0 / never split single char terms
            if len(suggestions) > 0 and (suggestions[0][1][1] == 0 or len(termList1[i]) == 1):
                # choose best suggestion
                suggestionParts.append(suggestions[0])
            else:
                # if no perfect suggestion, split word into pairs
                suggestionsSplit = [] if len(suggestions) == 0 else [suggestions[0]]
                if len(termList1) > 1:
                    for j in range(1,len(termList1)):
                        part1 = termList1[j][0:j]
                        part2 = termList1[j][j:]
                        suggestions1 = self.get_suggestions(part1, ALL_SUGGESTIONS)
                        if len(suggestions1) != 0:
                            if len(suggestions) != 0 and suggestions[0][0] == suggestions1[0][0]:
                                break   # if split correction1 == einzelwort correction
                        suggestions2 = self.get_suggestions(part2, ALL_SUGGESTIONS)
                        if len(suggestions2) != 0:
                            if len(suggestions) != 0 and suggestions[0][0] == suggestions2[0][0]:
                                break   # if split correction2 == einzelwort correction
                            # select best suggestion for split pair
                            term = suggestions1[0][0] + " " + suggestions2[0][0]
                            dist = dameraulevenshtein(termList1[i], term)
                            freq = min([suggestions1[0][1][0], suggestions2[0][1][0]])
                            suggestionsSplit.append((term, (freq, dist)))
                            if dist == 1:
                                break   # early termination of split

                    if len(suggestionsSplit) > 0:
                        # select best suggestion for split pair
                        suggestionsSplit = sorted(suggestionsSplit, key=lambda(term, (freq, dist)): (dist, -freq))
                        suggestionParts.append(suggestionsSplit[0])
                    else:
                        suggestionParts.append((termList1[i], (0, self.max_edit_distance+1)))

                else:
                    suggestionParts.append((termList1[i], (0, self.max_edit_distance+1)))

        term = []
        freq = []
        for si in suggestionParts:
            term.append(si[0])
            freq.append(si[1][0])
        freq = min(freq)
        term = ' '.join(term)
        dist = dameraulevenshtein(term, input)
        return (term, (freq, dist))

    def best_word(self, s):
        try:
            return self.get_suggestions(s, BEST_SUGGESTION)
        except:
            return None

    def correct_document(self, fname, printlist=True):
        # correct an entire document
        with open(fname) as file:
            doc_word_count = 0
            corrected_word_count = 0
            unknown_word_count = 0
            print("Finding misspelled words in your document...")

            for i, line in enumerate(file):
                # separate by words by non-alphabetical characters
                doc_words = self.pattern.findall(line.lower())
                for doc_word in doc_words:
                    doc_word_count += 1
                    suggestion = self.best_word(doc_word)
                    if suggestion is None:
                        if printlist:
                            print("In line %i, the word < %s > was not found (no suggested correction)" % (i, doc_word))
                        unknown_word_count += 1
                    elif suggestion[0] != doc_word:
                        if printlist:
                            print("In line %i, %s: suggested correction is < %s >" % (i, doc_word, suggestion[0]))
                        corrected_word_count += 1

        print("-----")
        print("total words checked: %i" % doc_word_count)
        print("total unknown words: %i" % unknown_word_count)
        print("total potential errors found: %i" % corrected_word_count)

## main

if __name__ == "__main__":
    import time
    import os
    print("Please wait...")
    start_time = time.time()
    spellcheck = SymSpell()
    with open(os.path.join(PROJDIR, 'src', 'python', 'marbles', 'ie', 'kb', 'data', 'dictionary-en.dat'), 'r') as fp:
        spellcheck.restore(fp)
    run_time = time.time() - start_time
    print('-----')
    print('%.2f seconds to restore' % run_time)
    print('-----\n')

    print("Word correction")
    print("---------------")

    while True:
        word_in = raw_input('Enter your input (or enter to exit): ').strip()
        if len(word_in) == 0:
            print("goodbye")
            break
        start_time = time.time()
        print(spellcheck.get_suggestions(word_in, NBEST_SUGGESTIONS))
        run_time = time.time() - start_time
        print('-----')
        print('%.5f seconds to search' % run_time)
        print('-----\n')
