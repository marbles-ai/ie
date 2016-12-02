from testdata import PROBLEMS
import unittest
from clausefinder import ClauseFinder
from clausefinder import spacynlp

class SpacyTest(unittest.TestCase):
    """Test ClauseFinder using spaCy NLP"""

    def testProblems(self):
        for p in PROBLEMS:
            doc = spacynlp.parse(p['sentence'].decode('utf-8'))
            self.assertIsNotNone(doc)
            cf = ClauseFinder(doc)
            clauses = []
            for sent in doc.sents:
                clauses.extend(cf.find_clauses(sent))
            self.assertEquals(len(clauses), len(p['clauses']))
            for expect, actual in zip(p['clauses'], clauses):
                self.assertEquals(expect['type'], actual.type)
                self.assertEquals(expect['text'], actual.text)


def run_tests():
    suite = unittest.TestLoader().loadTestsFromTestCase(SpacyTest)
    unittest.TextTestRunner(verbosity=2).run(suite)


if __name__ == '__main__':
    unittest.main()
