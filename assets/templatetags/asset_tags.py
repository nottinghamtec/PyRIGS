from django import template
from assets import models

register = template.Library()


@register.filter
def ids_from_objects(object_list):
    id_list = []
    for obj in object_list:
        id_list.append(obj.asset_id)
    return id_list


@register.filter
def index(indexable, i):
    return indexable[i] if i < len(indexable) else None
