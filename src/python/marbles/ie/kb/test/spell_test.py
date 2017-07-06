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
        self.assertDictEqual(spellchecker1.dictionary, spellchecker2.dictionary)

    def test2_GetSuggestions(self):
        ldcpath = os.path.join(PROJDIR, 'data', 'ldc', 'ccgbank_1_1', 'data', 'RAW')
        dirlist = os.listdir(ldcpath)
        spellchecker = SymSpell()
        for fname in dirlist:
            f, x = os.path.splitext(fname)
            if x != '.raw':
                continue
            ldcpath1 = os.path.join(ldcpath, fname)
            spellchecker.build_from_corpus(ldcpath1)

        suggestion = spellchecker.get_suggestions('reprted', BEST_SUGGESTION)
        self.assertEqual('reported', suggestion)
        suggestion = spellchecker.get_suggestions('reprted', NBEST_SUGGESTIONS)
        self.assertList(['reported', 'report'], suggestion)


if __name__ == '__main__':
    unittest.main()
