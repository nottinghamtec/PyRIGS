__author__ = 'ghost'

import unittest
from importer import fix_email


class EmailFixerTest(unittest.TestCase):
    def test_correct(self):
        e = fix_email("tom@ghost.uk.net")
        self.assertEqual(e, "tom@ghost.uk.net")

    def test_partial(self):
        e = fix_email("psytp")
        self.assertEqual(e, "psytp@nottingham.ac.uk")

    def test_none(self):
        old = None
        new = fix_email(old)
        self.assertEqual(old, new)

    def test_empty(self):
        old = ""
        new = fix_email(old)
        self.assertEqual(old, new)


if __name__ == '__main__':
    unittest.main()
