##############################################################################
#
# Copyright (c) 2001, 2002 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Field equality tests
"""
import unittest


class FieldEqualityTests(unittest.TestCase):

    def test_equality(self):

        from zope.schema._compat import u
        from zope.schema import Int
        from zope.schema import Text

        # pep 8 friendlyness
        u, Int, Text

        equality = [
            'Text(title=u("Foo"), description=u("Bar"))',
            'Int(title=u("Foo"), description=u("Bar"))',
        ]
        for text in equality:
            self.assertEqual(eval(text), eval(text))


def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(FieldEqualityTests),
        ))
