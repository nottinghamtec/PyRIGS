from django import template

from training import models

__author__ = 'Tom Price'

register = template.Library()


@register.filter
def item_record(item, user):
    if item in user.trainingitem_set.all():
        return user.trainingrecords.get(training_item=item)
    return models.TrainingRecord(training_item=item)
