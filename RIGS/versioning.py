import logging
from django.views import generic
from django.core.urlresolvers import reverse_lazy
from django.shortcuts import get_object_or_404
from django.template import RequestContext
from django.template.loader import get_template
from django.conf import settings
from django.http import HttpResponse
from django.db.models import Q
from django.contrib import messages

# Versioning
import reversion
import diff_match_patch
import simplejson
from reversion.helpers import generate_patch_html
from reversion.models import Version
from django.contrib.contenttypes.models import ContentType # Used to lookup the content_type

from RIGS import models, forms
import datetime
import re

logger = logging.getLogger('tec.pyrigs')


def compare_events(obj1, obj2, excluded_keys=[]):
    d1, d2 = obj1, obj2
    key, old, new = [],[],[]
    for k,v in d1.items():
        if k in excluded_keys:
            continue
        try:
            if v != d2[k]:
                key.append(models.Event._meta.get_field_by_name(k)[0].verbose_name)
                old.append(v)
                new.append(d2[k])
        except KeyError:
            old.append({k: v})
        except TypeError:
            # avoids issues with naive vs tz-aware datetimes
            old.append({k: v})
    
    return zip(key,old,new)

def compare_items(old, new):

    item_type = ContentType.objects.get_for_model(models.EventItem)
    old_items = old.revision.version_set.filter(content_type=item_type)
    new_items = new.revision.version_set.filter(content_type=item_type)

    class ItemCompare(object):
        def __init__(self, old=None, new=None):
            self.old = old
            self.new = new

    # Build some dicts of what we have
    item_dict = {}
    for item in old_items:
        compare = ItemCompare(old=item)
        compare.old.field_dict['event_id'] = compare.old.field_dict.pop('event')
        item_dict[item.object_id] = compare

    for item in new_items:
        try:
            compare = item_dict[item.object_id]
            compare.new = item
        except KeyError:
            compare = ItemCompare(new=item)
        compare.new.field_dict['event_id'] = compare.new.field_dict.pop('event')
        item_dict[item.object_id] = compare

    # calculate changes
    key, old, new = [], [], []
    for (_, items) in item_dict.items():
        if items.new is None:
            key.append("Deleted \"%s\"" % items.old.field_dict['name'])
            old.append(models.EventItem(**items.old.field_dict))
            new.append(None)

        elif items.old is None:
            key.append("Added \"%s\"" % items.new.field_dict['name'])
            old.append(None)
            new.append(models.EventItem(**items.new.field_dict))

        elif items.old.field_dict != items.new.field_dict:
            if items.old.field_dict['name'] == items.new.field_dict['name']:
                change_text = "\"%s\"" % items.old.field_dict['name']
            else:
                change_text = "\"%s\" to \"%s\"" % (items.old.field_dict['name'], items.new.field_dict['name'])
            key.append("Changed %s" % change_text)

            old.append(models.EventItem(**items.old.field_dict))
            new.append(models.EventItem(**items.new.field_dict))

    return zip(key,old,new)


class EventRevisions(generic.ListView):
    model = reversion.revisions.Version
    template_name = "RIGS/event_version_list.html"
    
    def get_context_data(self, **kwargs):
        thisEvent = get_object_or_404(models.Event, pk=self.kwargs['pk'])
        versions = reversion.get_for_object(thisEvent)
        items = []
        for revisionNo, thisRevision in enumerate(versions):
            thisItem = {'pk': thisRevision.pk}
            thisItem['revision'] = thisRevision.revision
            logger.info(thisRevision.revision.version_set.all())

            if revisionNo >= len(revisions)-1:
                # oldest version
                thisItem['changes'] = [["(initial version)",None,"Event Created"]]
            else:
                changes = compare_events(revisions[revisionNo+1].field_dict,thisRevision.field_dict)
                thisItem['item_changes'] = compare_items(revisions[revisionNo+1], thisRevision)
                logger.debug(thisItem['item_changes'])
                thisItem['changes'] = changes

            items.append(thisItem)
            logger.info(thisItem)

        context = {
            'object_list': items,
            'object': thisEvent
        }                     

        return context

