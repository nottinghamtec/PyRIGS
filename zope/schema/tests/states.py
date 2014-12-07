##############################################################################
#
# Copyright (c) 2003 Zope Foundation and Contributors.
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
"""Sample vocabulary supporting state abbreviations.
"""
from zope.schema._compat import u
from zope.interface import implementer
from zope.schema import interfaces
from zope.schema import Choice

# This table is based on information from the United States Postal Service:
# http://www.usps.com/ncsc/lookups/abbreviations.html#states
_states = {
    'AL': u('Alabama'),
    'AK': u('Alaska'),
    'AS': u('American Samoa'),
    'AZ': u('Arizona'),
    'AR': u('Arkansas'),
    'CA': u('California'),
    'CO': u('Colorado'),
    'CT': u('Connecticut'),
    'DE': u('Delaware'),
    'DC': u('District of Columbia'),
    'FM': u('Federated States of Micronesia'),
    'FL': u('Florida'),
    'GA': u('Georgia'),
    'GU': u('Guam'),
    'HI': u('Hawaii'),
    'ID': u('Idaho'),
    'IL': u('Illinois'),
    'IN': u('Indiana'),
    'IA': u('Iowa'),
    'KS': u('Kansas'),
    'KY': u('Kentucky'),
    'LA': u('Louisiana'),
    'ME': u('Maine'),
    'MH': u('Marshall Islands'),
    'MD': u('Maryland'),
    'MA': u('Massachusetts'),
    'MI': u('Michigan'),
    'MN': u('Minnesota'),
    'MS': u('Mississippi'),
    'MO': u('Missouri'),
    'MT': u('Montana'),
    'NE': u('Nebraska'),
    'NV': u('Nevada'),
    'NH': u('New Hampshire'),
    'NJ': u('New Jersey'),
    'NM': u('New Mexico'),
    'NY': u('New York'),
    'NC': u('North Carolina'),
    'ND': u('North Dakota'),
    'MP': u('Northern Mariana Islands'),
    'OH': u('Ohio'),
    'OK': u('Oklahoma'),
    'OR': u('Oregon'),
    'PW': u('Palau'),
    'PA': u('Pennsylvania'),
    'PR': u('Puerto Rico'),
    'RI': u('Rhode Island'),
    'SC': u('South Carolina'),
    'SD': u('South Dakota'),
    'TN': u('Tennessee'),
    'TX': u('Texas'),
    'UT': u('Utah'),
    'VT': u('Vermont'),
    'VI': u('Virgin Islands'),
    'VA': u('Virginia'),
    'WA': u('Washington'),
    'WV': u('West Virginia'),
    'WI': u('Wisconsin'),
    'WY': u('Wyoming'),
    }


@implementer(interfaces.ITerm)
class State(object):
    __slots__ = 'value', 'title'

    def __init__(self, value, title):
        self.value = value
        self.title = title

for v, p in _states.items():
    _states[v] = State(v, p)


class IStateVocabulary(interfaces.IVocabulary):
    """Vocabularies that support the states database conform to this."""


@implementer(IStateVocabulary)
class StateVocabulary(object):
    __slots__ = ()

    def __init__(self, object=None):
        pass

    def __contains__(self, value):
        return value in _states

    def __iter__(self):
        return iter(_states.values())

    def __len__(self):
        return len(_states)

    def getTerm(self, value):
        return _states[value]


class StateSelectionField(Choice):

    vocabulary = StateVocabulary()

    def __init__(self, **kw):
        super(StateSelectionField, self).__init__(
            vocabulary=StateSelectionField.vocabulary,
            **kw)
        self.vocabularyName = "states"
