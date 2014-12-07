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
"""Field Properties tests
"""

import unittest


class _Base(unittest.TestCase):

    def _makeOne(self, field=None, name=None):
        from zope.schema import Text
        if field is None:
            field = Text(__name__='testing')
        if name is None:
            return self._getTargetClass()(field)
        return self._getTargetClass()(field, name)


class _Integration(object):

    def _makeImplementer(self):
        schema = _getSchema()

        class _Implementer(object):
            title = self._makeOne(schema['title'])
            weight = self._makeOne(schema['weight'])
            code = self._makeOne(schema['code'])
            date = self._makeOne(schema['date'])

        return _Implementer()

    def test_basic(self):
        from zope.schema._compat import b
        from zope.schema._compat import u
        from zope.schema.interfaces import ValidationError
        c = self._makeImplementer()
        self.assertEqual(c.title, u('say something'))
        self.assertEqual(c.weight, None)
        self.assertEqual(c.code, b('xxxxxx'))
        self.assertRaises(ValidationError, setattr, c, 'title', b('foo'))
        self.assertRaises(ValidationError, setattr, c, 'weight', b('foo'))
        self.assertRaises(ValidationError, setattr, c, 'weight', -1.0)
        self.assertRaises(ValidationError, setattr, c, 'weight', 2)
        self.assertRaises(ValidationError, setattr, c, 'code', -1)
        self.assertRaises(ValidationError, setattr, c, 'code', b('xxxx'))
        self.assertRaises(ValidationError, setattr, c, 'code', u('xxxxxx'))

        c.title = u('c is good')
        c.weight = 10.0
        c.code = b('abcdef')

        self.assertEqual(c.title, u('c is good'))
        self.assertEqual(c.weight, 10)
        self.assertEqual(c.code, b('abcdef'))

    def test_readonly(self):
        c = self._makeImplementer()
        # The date should be only settable once
        c.date = 0.0
        # Setting the value a second time should fail.
        self.assertRaises(ValueError, setattr, c, 'date', 1.0)


class FieldPropertyTests(_Base, _Integration):

    def _getTargetClass(self):
        from zope.schema.fieldproperty import FieldProperty
        return FieldProperty

    def test_ctor_defaults(self):
        from zope.schema import Text
        field = Text(__name__='testing')
        cname = self._getTargetClass().__name__
        prop = self._makeOne(field)
        self.assertTrue(getattr(prop, '_%s__field' % cname) is field)
        self.assertEqual(getattr(prop, '_%s__name' % cname), 'testing')
        self.assertEqual(prop.__name__, 'testing')
        self.assertEqual(prop.description, field.description)
        self.assertEqual(prop.default, field.default)
        self.assertEqual(prop.readonly, field.readonly)
        self.assertEqual(prop.required, field.required)

    def test_ctor_explicit(self):
        from zope.schema import Text
        from zope.schema._compat import u
        field = Text(
            __name__='testing',
            description=u('DESCRIPTION'),
            default=u('DEFAULT'),
            readonly=True,
            required=True,
        )
        cname = self._getTargetClass().__name__
        prop = self._makeOne(field, name='override')
        self.assertTrue(getattr(prop, '_%s__field' % cname) is field)
        self.assertEqual(getattr(prop, '_%s__name' % cname), 'override')
        self.assertEqual(prop.description, field.description)
        self.assertEqual(prop.default, field.default)
        self.assertEqual(prop.readonly, field.readonly)
        self.assertEqual(prop.required, field.required)

    def test_query_value_with_default(self):
        from zope.schema import Text
        from zope.schema._compat import u
        field = Text(
            __name__='testing',
            description=u('DESCRIPTION'),
            default=u('DEFAULT'),
            readonly=True,
            required=True,
        )

        prop = self._makeOne(field=field)

        class Foo(object):
            testing = prop
        foo = Foo()
        self.assertEqual(prop.queryValue(foo, 'test'), u('DEFAULT'))
        foo.testing = u('NO')
        self.assertEqual(prop.queryValue(foo, 'test'), u('NO'))

    def test_query_value_without_default(self):
        from zope.schema import Text
        from zope.schema._compat import u
        field = Text(
            __name__='testing',
            description=u('DESCRIPTION'),
            readonly=True,
            required=True,
        )

        prop = self._makeOne(field=field)

        class Foo(object):
            testing = prop
        foo = Foo()
        # field initialize its default to None if it hasn't any default
        # it should be zope.schema.NO_VALUE as 'None' has another semantic
        self.assertEqual(prop.queryValue(foo, 'test'), None)

    def test___get___from_class(self):
        prop = self._makeOne()

        class Foo(object):
            testing = prop

        self.assertTrue(Foo.testing is prop)

    def test___get___from_instance_pseudo_field_wo_default(self):
        class _Faux(object):
            def bind(self, other):
                return self
        prop = self._makeOne(_Faux(), 'nonesuch')

        class Foo(object):
            testing = prop

        foo = Foo()
        self.assertRaises(AttributeError, getattr, foo, 'testing')

    def test___get___from_instance_miss_uses_field_default(self):
        prop = self._makeOne()

        class Foo(object):
            testing = prop

        foo = Foo()
        self.assertEqual(foo.testing, None)

    def test___get___from_instance_hit(self):
        prop = self._makeOne(name='other')

        class Foo(object):
            testing = prop

        foo = Foo()
        foo.other = '123'
        self.assertEqual(foo.testing, '123')

    def test___get___from_instance_hit_after_bind(self):
        class _Faux(object):
            default = '456'

            def bind(self, other):
                return self

        prop = self._makeOne(_Faux(), 'testing')

        class Foo(object):
            testing = prop

        foo = Foo()
        self.assertEqual(foo.testing, '456')

    def test___set___not_readonly(self):
        class _Faux(object):
            readonly = False
            default = '456'

            def bind(self, other):
                return self

        faux = _Faux()
        _validated = []
        faux.validate = _validated.append
        prop = self._makeOne(faux, 'testing')

        class Foo(object):
            testing = prop

        foo = Foo()
        foo.testing = '123'
        self.assertEqual(foo.__dict__['testing'], '123')

    def test___set___w_readonly_not_already_set(self):
        class _Faux(object):
            readonly = True
            default = '456'

            def bind(self, other):
                return self

        faux = _Faux()
        _validated = []
        faux.validate = _validated.append
        prop = self._makeOne(faux, 'testing')

        class Foo(object):
            testing = prop

        foo = Foo()
        foo.testing = '123'
        self.assertEqual(foo.__dict__['testing'], '123')
        self.assertEqual(_validated, ['123'])

    def test___set___w_readonly_and_already_set(self):
        class _Faux(object):
            readonly = True
            default = '456'

            def bind(self, other):
                return self

        faux = _Faux()
        _validated = []
        faux.validate = _validated.append
        prop = self._makeOne(faux, 'testing')

        class Foo(object):
            testing = prop

        foo = Foo()
        foo.__dict__['testing'] = '789'
        self.assertRaises(ValueError, setattr, foo, 'testing', '123')
        self.assertEqual(_validated, ['123'])

    def test_field_event(self):
        from zope.schema import Text
        from zope.schema._compat import u
        from zope.event import subscribers
        from zope.schema.fieldproperty import FieldUpdatedEvent
        log = []
        subscribers.append(log.append)
        self.assertEqual(log, [])
        field = Text(
            __name__='testing',
            description=u('DESCRIPTION'),
            default=u('DEFAULT'),
            readonly=True,
            required=True,
        )
        self.assertEqual(len(log), 6)
        event = log[0]
        self.assertTrue(isinstance(event, FieldUpdatedEvent))
        self.assertEqual(event.inst, field)
        self.assertEqual(event.old_value, 0)
        self.assertEqual(event.new_value, 0)
        self.assertEqual(
            [ev.field.__name__ for ev in log],
            ['min_length', 'max_length', 'title', 'description', 'required', 'readonly'])

    def test_field_event_update(self):
        from zope.schema import Text
        from zope.schema._compat import u
        from zope.event import subscribers
        from zope.schema.fieldproperty import FieldUpdatedEvent
        field = Text(
            __name__='testing',
            description=u('DESCRIPTION'),
            default=u('DEFAULT'),
            required=True,
        )
        prop = self._makeOne(field=field)

        class Foo(object):
            testing = prop
        foo = Foo()

        log = []
        subscribers.append(log.append)
        foo.testing = u('Bar')
        foo.testing = u('Foo')
        self.assertEqual(len(log), 2)
        event = log[1]
        self.assertTrue(isinstance(event, FieldUpdatedEvent))
        self.assertEqual(event.inst, foo)
        self.assertEqual(event.field, field)
        self.assertEqual(event.old_value, u('Bar'))
        self.assertEqual(event.new_value, u('Foo'))


class FieldPropertyStoredThroughFieldTests(_Base, _Integration):

    def _getTargetClass(self):
        from zope.schema.fieldproperty import FieldPropertyStoredThroughField
        return FieldPropertyStoredThroughField

    def test_ctor_defaults(self):
        from zope.schema import Text
        field = Text(__name__='testing')
        cname = self._getTargetClass().__name__
        prop = self._makeOne(field)
        self.assertTrue(isinstance(prop.field, field.__class__))
        self.assertFalse(prop.field is field)
        self.assertEqual(prop.field.__name__, '__st_testing_st')
        self.assertEqual(prop.__name__, '__st_testing_st')
        self.assertEqual(getattr(prop, '_%s__name' % cname), 'testing')
        self.assertEqual(prop.description, field.description)
        self.assertEqual(prop.default, field.default)
        self.assertEqual(prop.readonly, field.readonly)
        self.assertEqual(prop.required, field.required)

    def test_ctor_explicit(self):
        from zope.schema import Text
        from zope.schema._compat import u
        field = Text(
            __name__='testing',
            description=u('DESCRIPTION'),
            default=u('DEFAULT'),
            readonly=True,
            required=True,
        )
        cname = self._getTargetClass().__name__
        prop = self._makeOne(field, name='override')
        self.assertTrue(isinstance(prop.field, field.__class__))
        self.assertFalse(prop.field is field)
        self.assertEqual(prop.field.__name__, '__st_testing_st')
        self.assertEqual(prop.__name__, '__st_testing_st')
        self.assertEqual(getattr(prop, '_%s__name' % cname), 'override')
        self.assertEqual(prop.description, field.description)
        self.assertEqual(prop.default, field.default)
        self.assertEqual(prop.readonly, field.readonly)
        self.assertEqual(prop.required, field.required)

    def test_setValue(self):
        from zope.schema import Text

        class Foo(object):
            pass

        foo = Foo()
        prop = self._makeOne()
        field = Text(__name__='testing')
        prop.setValue(foo, field, '123')
        self.assertEqual(foo.testing, '123')

    def test_getValue_miss(self):
        from zope.schema import Text
        from zope.schema.fieldproperty import _marker

        class Foo(object):
            pass

        foo = Foo()
        prop = self._makeOne()
        field = Text(__name__='testing')
        value = prop.getValue(foo, field)
        self.assertTrue(value is _marker)

    def test_getValue_hit(self):
        from zope.schema import Text

        class Foo(object):
            pass

        foo = Foo()
        foo.testing = '123'
        prop = self._makeOne()
        field = Text(__name__='testing')
        value = prop.getValue(foo, field)
        self.assertEqual(value, '123')

    def test_queryValue_miss(self):
        from zope.schema import Text

        class Foo(object):
            pass

        foo = Foo()
        prop = self._makeOne()
        field = Text(__name__='testing')
        default = object()
        value = prop.queryValue(foo, field, default)
        self.assertTrue(value is default)

    def test_queryValue_hit(self):
        from zope.schema import Text

        class Foo(object):
            pass

        foo = Foo()
        foo.testing = '123'
        prop = self._makeOne()
        field = Text(__name__='testing')
        default = object()
        value = prop.queryValue(foo, field, default)
        self.assertEqual(value, '123')

    def test___get___from_class(self):
        prop = self._makeOne()

        class Foo(object):
            testing = prop

        self.assertTrue(Foo.testing is prop)

    def test___get___from_instance_pseudo_field_wo_default(self):
        class _Faux(object):
            __name__ = 'Faux'

            def bind(self, other):
                return self

            def query(self, inst, default):
                return default

        prop = self._makeOne(_Faux(), 'nonesuch')

        class Foo(object):
            testing = prop

        foo = Foo()
        self.assertRaises(AttributeError, getattr, foo, 'testing')

    def test___get___from_instance_miss_uses_field_default(self):
        prop = self._makeOne()

        class Foo(object):
            testing = prop

        foo = Foo()
        self.assertEqual(foo.testing, None)

    def test___get___from_instance_hit(self):
        from zope.schema import Text
        field = Text(__name__='testing')
        prop = self._makeOne(field, name='other')

        class Foo(object):
            testing = prop

        foo = Foo()
        foo.__dict__['__st_testing_st'] = '456'
        foo.other = '123'
        self.assertEqual(foo.testing, '456')

    def test___set___not_readonly(self):
        class _Faux(object):
            __name__ = 'Faux'
            readonly = False
            default = '456'

            def query(self, inst, default):
                return default

            def bind(self, other):
                return self

            def set(self, inst, value):
                setattr(inst, 'faux', value)

        faux = _Faux()
        _validated = []
        faux.validate = _validated.append
        prop = self._makeOne(faux, 'testing')

        class Foo(object):
            testing = prop

        foo = Foo()
        foo.testing = '123'
        self.assertEqual(foo.__dict__['faux'], '123')
        self.assertEqual(_validated, ['123'])

    def test___set___w_readonly_not_already_set(self):
        class _Faux(object):
            __name__ = 'Faux'
            readonly = True
            default = '456'

            def bind(self, other):
                return self

            def query(self, inst, default):
                return default

            def set(self, inst, value):
                if self.readonly:
                    raise ValueError
                setattr(inst, 'faux', value)

        faux = _Faux()
        _validated = []
        faux.validate = _validated.append
        prop = self._makeOne(faux, 'testing')

        class Foo(object):
            testing = prop

        foo = Foo()
        foo.testing = '123'
        self.assertEqual(foo.__dict__['faux'], '123')
        self.assertEqual(_validated, ['123'])

    def test___set___w_readonly_and_already_set(self):
        class _Faux(object):
            __name__ = 'Faux'
            readonly = True
            default = '456'

            def bind(self, other):
                return self

            def query(self, inst, default):
                return '789'

        faux = _Faux()
        _validated = []
        faux.validate = _validated.append
        prop = self._makeOne(faux, 'testing')

        class Foo(object):
            testing = prop

        foo = Foo()
        foo.__dict__['testing'] = '789'
        self.assertRaises(ValueError, setattr, foo, 'testing', '123')

    def test_field_event_update(self):
        from zope.schema import Text
        from zope.schema._compat import u
        from zope.event import subscribers
        from zope.schema.fieldproperty import FieldUpdatedEvent
        field = Text(
            __name__='testing',
            description=u('DESCRIPTION'),
            default=u('DEFAULT'),
            required=True,
        )
        prop = self._makeOne(field=field)

        class Foo(object):
            testing = prop
        foo = Foo()

        log = []
        subscribers.append(log.append)
        foo.testing = u('Bar')
        foo.testing = u('Foo')
        self.assertEqual(len(log), 2)
        event = log[1]
        self.assertTrue(isinstance(event, FieldUpdatedEvent))
        self.assertEqual(event.inst, foo)
        self.assertEqual(event.field, field)
        self.assertEqual(event.old_value, u('Bar'))
        self.assertEqual(event.new_value, u('Foo'))

    def test_field_event(self):
        # fieldproperties are everywhere including in field themselfs
        # so event are triggered
        from zope.schema import Text
        from zope.schema._compat import u
        from zope.event import subscribers
        from zope.schema.fieldproperty import FieldUpdatedEvent
        log = []
        subscribers.append(log.append)
        self.assertEqual(log, [])
        field = Text(
            __name__='testing',
            description=u('DESCRIPTION'),
            default=u('DEFAULT'),
            readonly=True,
            required=True,
        )
        self.assertEqual(len(log), 6)
        # these are fieldproperties in the field
        self.assertEqual(
            [ev.field.__name__ for ev in log],
            ['min_length', 'max_length', 'title', 'description', 'required', 'readonly'])
        event = log[0]
        self.assertTrue(isinstance(event, FieldUpdatedEvent))
        self.assertEqual(event.inst, field)
        self.assertEqual(event.old_value, 0)
        self.assertEqual(event.new_value, 0)


def _getSchema():
    from zope.interface import Interface
    from zope.schema import Bytes
    from zope.schema import Float
    from zope.schema import Text
    from zope.schema._compat import b
    from zope.schema._compat import u

    class Schema(Interface):
        title = Text(description=u("Short summary"),
                     default=u('say something'))
        weight = Float(min=0.0)
        code = Bytes(min_length=6, max_length=6, default=b('xxxxxx'))
        date = Float(title=u('Date'), readonly=True)

    return Schema


class CreateFieldPropertiesTests(unittest.TestCase):
    """Testing ..fieldproperty.createFieldProperties."""

    def test_creates_fieldproperties_on_class(self):
        from zope.schema.fieldproperty import createFieldProperties
        from zope.schema.fieldproperty import FieldProperty
        schema = _getSchema()

        class Dummy(object):
            createFieldProperties(schema)

        self.assertTrue(isinstance(Dummy.title, FieldProperty))
        self.assertTrue(isinstance(Dummy.date, FieldProperty))
        self.assertTrue(Dummy.date._FieldProperty__field is schema['date'])

    def test_fields_in_omit_are_not_created_on_class(self):
        from zope.schema.fieldproperty import createFieldProperties

        class Dummy(object):
            createFieldProperties(_getSchema(), omit=['date', 'code'])

        self.assertFalse(hasattr(Dummy, 'date'))
        self.assertFalse(hasattr(Dummy, 'code'))
        self.assertTrue(hasattr(Dummy, 'title'))


def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(FieldPropertyTests),
        unittest.makeSuite(FieldPropertyStoredThroughFieldTests),
        unittest.makeSuite(CreateFieldPropertiesTests),
    ))
