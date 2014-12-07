#
# This file is necessary to make this directory a package.

import re

from zope.schema._compat import PY3
from zope.testing import renormalizing

if PY3:
    py3_checker = renormalizing.RENormalizing([
        (re.compile(r"u'([^']*)'"),
                    r"'\1'"),
        (re.compile(r"^b'([^']*)'"),
                    r"'\1'"),
        (re.compile(r"([^'])b'([^']*)'"),
                    r"\1'\2'"),
        (re.compile(r"<class 'bytes'>"),
                    r"<type 'str'>"),
        (re.compile(r"<class 'str'>"),
                    r"<type 'unicode'>"),
        (re.compile(r"zope.schema._bootstrapinterfaces.InvalidValue"),
                    r"InvalidValue"),
        (re.compile(r"zope.schema.interfaces.InvalidId: '([^']*)'"),
                    r"InvalidId: \1"),
        (re.compile(r"zope.schema.interfaces.InvalidId:"),
                    r"InvalidId:"),
        (re.compile(r"zope.schema.interfaces.InvalidURI: '([^']*)'"),
                    r"InvalidURI: \1"),
        (re.compile(r"zope.schema.interfaces.InvalidURI:"),
                    r"InvalidURI:"),
        (re.compile(r"zope.schema.interfaces.InvalidDottedName: '([^']*)'"),
                    r"InvalidDottedName: \1"),
        (re.compile(r"zope.schema.interfaces.InvalidDottedName:"),
                    r"InvalidDottedName:"),
        (re.compile(
          r"zope.schema._bootstrapinterfaces.ConstraintNotSatisfied: '([^']*)'"
                   ),
                    r"ConstraintNotSatisfied: \1"),
        (re.compile(
           r"zope.schema._bootstrapinterfaces.ConstraintNotSatisfied:"),
                    r"ConstraintNotSatisfied:"),
        (re.compile(r"zope.schema._bootstrapinterfaces.WrongType:"),
                    r"WrongType:"),
      ])
else:
    py3_checker = renormalizing.RENormalizing([
        (re.compile(r"([^'])b'([^']*)'"),
                    r"\1'\2'"),
        ])
