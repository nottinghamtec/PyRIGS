from django import template
from django import forms
from django.forms.forms import NON_FIELD_ERRORS
from django.forms.utils import ErrorDict

register = template.Library()

@register.filter
def multiply(value, arg):
    return value*arg

@register.filter
def to_class_name(value):
    return value.__class__.__name__
    
@register.filter
def nice_errors(form, non_field_msg='General form errors'):
    nice_errors = ErrorDict()
    if isinstance(form, forms.BaseForm):
        for field, errors in list(form.errors.items()):
            if field == NON_FIELD_ERRORS:
                key = non_field_msg
            else:
                key = form.fields[field].label
            nice_errors[key] = errors
    return nice_errors

def paginator(context, adjacent_pages=3):
    """
    To be used in conjunction with the object_list generic view.

    Adds pagination context variables for use in displaying first, adjacent and
    last page links in addition to those created by the object_list generic
    view.

    """
    page = context['page_obj']
    paginator = context['paginator']
    startPage = max(page.number - adjacent_pages, 1)
    if startPage <= 3: startPage = 1
    endPage = page.number + adjacent_pages + 1
    if endPage >= paginator.num_pages - 1: endPage = paginator.num_pages + 1
    page_numbers = [n for n in range(startPage, endPage) \
            if n > 0 and n <= paginator.num_pages]

    dict = {
        'request': context['request'],
        'is_paginated': paginator.num_pages > 0,
        'page_obj': page,
        'paginator': paginator,
        'results': paginator.per_page,
        'page_numbers': page_numbers,
        'show_first': 1 not in page_numbers,
        'show_last': paginator.num_pages not in page_numbers,
        'first': 1,
        'last': paginator.num_pages,
        'has_next': page.has_next(),
        'has_previous': page.has_previous(),
    }
    
    if page.has_next():
        dict['next'] = page.next_page_number()
    if page.has_previous():
        dict['previous'] = page.previous_page_number()

    return dict
register.inclusion_tag('pagination.html', takes_context=True)(paginator)

@register.simple_tag
def url_replace(request, field, value):

    dict_ = request.GET.copy()

    dict_[field] = value

    return dict_.urlencode()

@register.simple_tag
def orderby(request, field, attr):

    dict_ = request.GET.copy()

    if dict_.__contains__(field) and dict_[field] == attr:
        if not dict_[field].startswith("-"):
            dict_[field] = "-" + attr
        else:
            dict_[field] = attr
    else:
        dict_[field] = attr

    return dict_.urlencode()