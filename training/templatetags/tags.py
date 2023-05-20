from django import forms
from django import template
from django.utils.html import escape
from django.utils.safestring import SafeData, mark_safe
from django.utils.text import normalize_newlines
from django.urls import reverse

from training import models

register = template.Library()


@register.simple_tag
def user_has_qualification(user, item, depth):
    if models.TrainingItem.user_has_qualification(item, user, depth):
        return mark_safe("<span class='fas fa-check text-success' title='You have this requirement'></span>")
    else:
        return mark_safe("<span class='fas fa-hourglass-start text-warning' title='You do not yet have this requirement'></span>")


@register.simple_tag
def user_level_if_present(user, level):
    return models.TrainingLevelQualification.objects.filter(trainee=user, level=level).first()


@register.simple_tag
def percentage_complete(level, user):
    return level.percentage_complete(user)


@register.simple_tag
def colour_from_depth(depth):
    return models.TrainingItemQualification.get_colour_from_depth(depth)


@register.filter
def get_levels_of_depth(trainee, level):
    return trainee.level_qualifications.all().exclude(confirmed_on=None).exclude(level__department=None).exclude(level__department=models.TrainingLevel.HAULAGE).select_related('level').filter(level__level=level)


@register.simple_tag
def confirm_button(user, trainee, level):
    if level.user_has_requirements(trainee):
        string = "<span class='badge badge-warning p-2'>Awaiting Confirmation</span>"
        if models.Trainee.objects.get(pk=user.pk).is_supervisor or user.has_perm('training.add_traininglevelqualification'):
            string += f"<a class='btn btn-info' href='{reverse('confirm_level', kwargs={'pk': trainee.pk, 'level_pk': level.pk})}'>Confirm</a>"
        return mark_safe(string)
    else:
        return ""
