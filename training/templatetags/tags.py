from django import forms
from django import template
from django.utils.html import escape
from django.utils.safestring import SafeData, mark_safe
from django.utils.text import normalize_newlines

from training import models

register = template.Library()

@register.simple_tag
def user_has_qualification(user, item, depth):
    if models.TrainingItem.user_has_qualification(item, user, depth) is not None:
        return mark_safe("<span class='fas fa-check text-success'></span>")
    else:
        return mark_safe("<span class='fas fa-hourglass-start text-warning'></span>")

@register.simple_tag
def user_level_if_present(user, level):
    return models.TrainingLevelQualification.objects.filter(trainee=user, level=level).first()

@register.simple_tag
def percentage_complete(level, user):
    return level.percentage_complete(user)

@register.simple_tag
def colour_from_depth(depth):
    return models.TrainingItemQualification.get_colour_from_depth(depth)
