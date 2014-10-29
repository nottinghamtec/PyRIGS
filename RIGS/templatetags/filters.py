from django import template
from django import forms
from django.forms.forms import NON_FIELD_ERRORS
from django.forms.util import ErrorDict

register = template.Library()

@register.filter
def multiply(value, arg):
    return value*arg

@register.filter
def nice_errors(form, non_field_msg='General form errors'):
    nice_errors = ErrorDict()
    if isinstance(form, forms.BaseForm):
        for field, errors in form.errors.items():
            if field == NON_FIELD_ERRORS:
                key = non_field_msg
            else:
                key = form.fields[field].label
            nice_errors[key] = errors
    return nice_errors