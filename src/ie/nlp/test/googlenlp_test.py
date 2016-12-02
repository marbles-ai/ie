from testdata import PROBLEMS
from testdata import GOOGLE_PROBLEMS
import unittest
from clausefinder import ClauseFinder
from clausefinder import googlenlp


class GoogleTest(unittest.TestCase):
    """Test ClauseFinder using Google NLP"""

    def test0_JsonProblems(self):
        if GOOGLE_PROBLEMS is None:
            return
        i = -1
        for p in GOOGLE_PROBLEMS:
            i += 1
            if p.has_key('preprocessed'):
                doc = googlenlp.Doc(p['preprocessed']['google'])
            else:
                doc = googlenlp.Doc(p['google'])
            cf = ClauseFinder(doc)
            clauses = []
            for sent in doc.sents:
                clauses.extend(cf.find_clauses(sent))
            self.assertEqual(len(clauses), len(p['clauses']), doc.text)
            for expect,actual in zip(p['clauses'],clauses):
                self.assertEqual(expect['type'], actual.type, doc.text)
                self.assertEqual(expect['text'], actual.text, doc.text)

    def disabled_test1_TextProblems(self):
        nlp = googlenlp.GoogleNLP()
        for p in PROBLEMS:
            result = nlp.parse(p['sentence'])
            self.assertIsNotNone(result)
            doc = googlenlp.Doc(result)
            cf = ClauseFinder(doc)
            clauses = []
            for sent in doc.sents:
                clauses.extend(cf.find_clauses(sent))
            self.assertEquals(len(clauses), len(p['clauses']))
            for expect,actual in zip(p['clauses'],clauses):
                self.assertEquals(expect['type'], actual.type)
                self.assertEquals(expect['text'], actual.text)


def run_tests():
    suite = unittest.TestLoader().loadTestsFromTestCase(GoogleTest)
    unittest.TextTestRunner(verbosity=2).run(suite)


if __name__ == '__main__':
    unittest.main()
