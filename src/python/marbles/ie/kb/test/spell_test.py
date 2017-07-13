from __future__ import unicode_literals, print_function
import unittest
import os
import StringIO
from marbles.ie.kb.spell import SymSpell, BEST_SUGGESTION, NBEST_SUGGESTIONS, ALL_SUGGESTIONS
from marbles import PROJDIR


class SymSpellTestCase(unittest.TestCase):
    def test1_ReadWrite(self):
        ldcpath = os.path.join(PROJDIR, 'data', 'ldc', 'ccgbank_1_1', 'data', 'RAW')
        dirlist = os.listdir(ldcpath)
        spellchecker1 = SymSpell()
        for fname in dirlist[0:1]:
            f, x = os.path.splitext(fname)
            if x != '.raw':
                continue
            ldcpath1 = os.path.join(ldcpath, fname)
            spellchecker1.build_from_corpus(ldcpath1)

        fp = StringIO.StringIO()
        spellchecker1.save(fp)
        fp.seek(0)
        spellchecker2 = SymSpell()
        spellchecker2.restore(fp)

        self.assertEqual(spellchecker1.longest_word_length, spellchecker2.longest_word_length)
        self.assertEqual(spellchecker1.max_edit_distance, spellchecker2.max_edit_distance)
        self.assertEqual(len(spellchecker1.dictionary), len(spellchecker2.dictionary))
        l1 = sorted(spellchecker1.dictionary.items(), key=lambda(word, (suggest, freq)): word)
        l2 = sorted(spellchecker2.dictionary.items(), key=lambda(word, (suggest, freq)): word)

        for s1, s2 in zip(l1, l2):
            self.assertEqual(s1[0], s2[0])
            self.assertListEqual(s1[1][0], s2[1][0])
            self.assertEqual(s1[1][1], s2[1][1])
        # self.assertDictEqual(spellchecker1.dictionary, spellchecker2.dictionary)

    def test2_GetSuggestions(self):
        spellchecker = SymSpell()
        strm = StringIO.StringIO()
        strm.write("accepted accept acceptance acceptable\n")
        strm.write("excepted except exception exceptional sceptered\n")
        strm.seek(0)
        spellchecker.build_from_corpus(strm)
        suggestion = spellchecker.get_suggestions('acept', BEST_SUGGESTION)
        self.assertEqual('accept', suggestion)
        suggestion = spellchecker.get_suggestions('cepted', NBEST_SUGGESTIONS)
        self.assertListEqual(['accepted', 'excepted'], sorted(suggestion))

    def test3_GetSuggestions(self):
        ldcpath = os.path.join(PROJDIR, 'data', 'ldc', 'ccgbank_1_1', 'data', 'RAW')
        dirlist = os.listdir(ldcpath)
        spellchecker = SymSpell()
        stats = spellchecker.build_from_wordnet()
        for fname in dirlist:
            f, x = os.path.splitext(fname)
            if x != '.raw':
                continue
            ldcpath1 = os.path.join(ldcpath, fname)
            with open(ldcpath1, 'r') as fp:
                stats = spellchecker.build_from_corpus(fp, stats)

        if True:
            print("total words processed: %i" % stats[0])
            print("total unique words in corpus: %i" % stats[1])
            print("total items in dictionary (corpus words and deletions): %i" % len(spellchecker.dictionary))
            print("  edit distance for deletions: %i" % spellchecker.max_edit_distance)
            print("  length of longest word in corpus: %i" % spellchecker.longest_word_length)

        strm = StringIO.StringIO()
        strm.write("excepted except exception exceptional\n")
        strm.seek(0)
        spellchecker.build_from_corpus(strm)

        suggestion = spellchecker.get_suggestions('acept', BEST_SUGGESTION)
        self.assertEqual('accept', suggestion)
        suggestion = spellchecker.get_suggestions('cepted', NBEST_SUGGESTIONS)
        self.assertListEqual(['accepted', 'excepted', 'sceptred'], sorted(suggestion))


if __name__ == '__main__':
    unittest.main()
