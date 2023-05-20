from django import forms
from django import template
from django.forms.forms import NON_FIELD_ERRORS
from django.forms.utils import ErrorDict
from django.template.defaultfilters import stringfilter
from django.template.defaultfilters import yesno, title, truncatewords
from django.urls import reverse
from django.utils.html import escape
from django.utils.safestring import SafeData, mark_safe
from django.utils.text import normalize_newlines

from RIGS import models

register = template.Library()


@register.filter(is_safe=True, needs_autoescape=True)
@stringfilter
def linebreaksxml(value, autoescape=True):
    autoescape = autoescape and not isinstance(value, SafeData)
    value = normalize_newlines(value)
    if autoescape:
        value = escape(value)
    return mark_safe(value.replace('\n', '<br />'))


@register.filter
def multiply(value, arg):
    return value * arg


@register.filter
def to_class_name(value):
    return value.__class__.__name__


@register.filter(needs_autoescape=True)
def nice_errors(form, non_field_msg='General form errors', autoescape=True):
    nice_errors = ErrorDict()
    if isinstance(form, forms.BaseForm):
        for field, errors in list(form.errors.items()):
            if field == NON_FIELD_ERRORS:
                key = non_field_msg
            else:
                key = form.fields[field].label
            nice_errors[key] = errors
    return nice_errors


@register.inclusion_tag('pagination.html', takes_context=True)
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
    if startPage <= 3:
        startPage = 1
    endPage = page.number + adjacent_pages + 1
    if endPage >= paginator.num_pages - 1:
        endPage = paginator.num_pages + 1
    page_numbers = [n for n in range(startPage, endPage)
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


@register.filter(needs_autoescape=True)  # Used for accessing outside of a form, i.e. in detail views of RiskAssessment and EventChecklist
def get_field(obj, field, autoescape=True):
    value = getattr(obj, field)
    if (isinstance(value, bool)):
        value = yesnoi(value, field in obj.inverted_fields)
    elif (isinstance(value, str)):
        value = truncatewords(value, 20)
    return mark_safe(value)


@register.filter
def help_text(obj, field):
    if hasattr(obj, '_meta'):
        return obj._meta.get_field(field).help_text


@register.filter
def verbose_name(obj, field):
    if hasattr(obj._meta.get_field(field), 'verbose_name'):
        return obj._meta.get_field(field).verbose_name


@register.filter
def get_list(dictionary, key):
    return dictionary.getlist(key)


@register.filter
def profile_by_index(value):
    if (value):
        return models.Profile.objects.get(pk=int(value))
    else:
        return ""


@register.filter(needs_autoescape=True)
def yesnoi(boolean, invert=False, autoescape=True):
    value = title(yesno(boolean))
    if invert:
        boolean = not boolean
    if boolean:
        value += ' <span class="fas fa-check-square" style="color: green;"></span>'
    else:
        value += ' <span class="fas fa-exclamation" style="color: red;"></span>'
    return mark_safe(value)


@register.filter
@stringfilter
def title_spaced(string):
    return title(string).replace('_', ' ')


@register.filter(needs_autoescape=True)
def namewithnotes(obj, url, autoescape=True):
    if hasattr(obj, 'notes') and obj.notes is not None and len(obj.notes) > 0:
        return mark_safe(obj.name + f" <a href='{reverse(url, kwargs={'pk': obj.pk})}'><span class='fas fa-sticky-note'></span></a>")
    else:
        return obj.name


@register.filter(needs_autoescape=True)
def linkornone(target, namespace=None, autoescape=True):
    if target is not None:
        if namespace is not None:
            link = namespace + "://" + target
        else:
            link = target
        return mark_safe(f"<a href='{link}' target='_blank'><span class='overflow-ellipsis'>{target}</span></a>")
    else:
        return "None"


@register.inclusion_tag('partials/button.html')
def button(type, url=None, pk=None, clazz="", icon=None, text="", id=None, style=None):
    if type == 'edit':
        clazz += " btn-warning "
        icon = "fa-edit"
        text = "Edit"
    elif type == 'print':
        clazz += " btn-primary "
        icon = "fa-download"
        text = "Export"
    elif type == 'duplicate':
        clazz += " btn-info "
        icon = "fa-copy"
        text = "Duplicate"
    elif type == 'view':
        clazz += " btn-primary "
        icon = "fa-eye"
        text = "View " + text
    elif type == 'new':
        clazz += " btn-primary "
        icon = "fa-plus"
        text = "New"
    elif type == 'copy':
        return {'copy': True, 'id': id, 'style': style}
    elif type == 'search':
        return {'submit': True, 'class': 'btn-info', 'icon': 'fa-search', 'text': 'Search', 'id': id, 'style': style}
    elif type == 'submit':
        return {'submit': True, 'class': 'btn-primary', 'icon': 'fa-save', 'text': 'Save', 'id': id, 'style': style}
    elif type == 'today':
        return {'today': True, 'id': id}
    return {'target': url, 'pk': pk, 'class': clazz, 'icon': icon, 'text': text, 'id': id, 'style': style}


@register.simple_tag  # TODO Can these be done with annotation/aggregation?
def invoices_waiting():
    return len(models.Event.objects.waiting_invoices())


@register.simple_tag
def invoices_outstanding():
    return len(models.Invoice.objects.outstanding_invoices())


@register.simple_tag
def total_invoices_todo():
    return len(models.Event.objects.waiting_invoices()) + len(models.Invoice.objects.outstanding_invoices())
