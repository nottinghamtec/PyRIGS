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
import simplejson
from reversion.models import Version
from django.contrib.contenttypes.models import ContentType # Used to lookup the content_type

from RIGS import models, forms
import datetime
import re

logger = logging.getLogger('tec.pyrigs')


def compare_events(obj1, obj2, excluded_keys=[]):
    theFields = obj1._meta.fields

    d1, d2 = obj1, obj2
    field, old, new = [],[],[]

    for thisField in theFields:
        k = thisField.name
        v1 = getattr(d1, k)
        v2 = getattr(d2, k)
        logger.info('k:'+str(k)+" v1:"+str(v1)+" v2:"+str(v2))
        if k in excluded_keys:
            continue
        try:
            if v1 != v2:
                field.append(thisField.verbose_name)
                old.append(v1)
                new.append(v2)
        except KeyError:
            field.append(thisField.verbose_name)
            old.append(v1)
            new.append(v2)
        except TypeError:
            # avoids issues with naive vs tz-aware datetimes
            field.append(thisField.verbose_name)
            old.append(v1)
            new.append(v2)
    
    return zip(field,old,new)

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

def get_versions_for_model(model):
    content_type = ContentType.objects.get_for_model(model)
    versions = reversion.models.Version.objects.filter(
        content_type = content_type,
    ).select_related("revision").order_by("-pk")

    return versions

def get_previous_version(version):
    thisEventId = version.object_id
    thisVersionId = version.pk

    versions = reversion.get_for_object_reference(models.Event, thisEventId)

    previousVersions = versions.filter(pk__lt=thisVersionId)

    if len(previousVersions) >= 1:
      return previousVersions[0]
    else: #this is probably the initial version
      return False 

def get_changes_for_version(thisVersion, previousVersion=None):

    if previousVersion == None:
        previousVersion = get_previous_version(thisVersion)

    compare = {}
    compare['pk'] = thisVersion.pk
    compare['thisVersion'] = thisVersion
    compare['prevVersion'] = previousVersion
    compare['revision'] = thisVersion.revision

    if previousVersion:
        compare['changes'] = compare_events(previousVersion.object_version.object, thisVersion.object_version.object)
        compare['item_changes'] = compare_items(previousVersion, thisVersion)
    else:
        compare['changes'] = [["(initial version)",None,"Event Created"]]

    return compare

    

class EventRevisions(generic.ListView):
    model = reversion.revisions.Version
    template_name = "RIGS/event_version_list.html"
    
    def get_context_data(self, **kwargs):
        thisEvent = get_object_or_404(models.Event, pk=self.kwargs['pk'])
        versions = reversion.get_for_object(thisEvent)
        items = []
        for versionNo, thisVersion in enumerate(versions):
            if versionNo >= len(versions)-1:
                thisItem = get_changes_for_version(thisVersion, None)
            else:
                thisItem = get_changes_for_version(thisVersion, versions[versionNo+1])

            items.append(thisItem)

        context = {
            'object_list': items,
            'object': thisEvent
        }                     

        return context

class ActivityStream(generic.ListView):
    model = reversion.revisions.Version
    template_name = "RIGS/activity_stream.html"
    
    def get_context_data(self, **kwargs):
        
        versions = get_versions_for_model(models.Event);

        items = []

        for thisVersion in versions[:20]:
            thisItem = get_changes_for_version(thisVersion, None)
            items.append(thisItem)

        context =  {
            'object_list': items,
        } 

        return context