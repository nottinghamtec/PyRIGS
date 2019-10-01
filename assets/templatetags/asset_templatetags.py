from django import template
from django.template.defaultfilters import stringfilter
from django.utils.safestring import SafeData, mark_safe
from django.utils.text import normalize_newlines
from django.utils.html import escape

register = template.Library()


@register.filter(is_safe=True, needs_autoescape=True)
@stringfilter
def linebreaksn(value, autoescape=True):
    """
    Convert all newlines in a piece of plain text to jQuery line breaks
    (`\n`).
    """
    autoescape = autoescape and not isinstance(value, SafeData)
    value = normalize_newlines(value)
    if autoescape:
        value = escape(value)
    return mark_safe(value.replace('\n', '\\n'))
