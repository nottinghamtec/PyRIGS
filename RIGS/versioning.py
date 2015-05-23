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
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from RIGS import models, forms
import datetime
import re

logger = logging.getLogger('tec.pyrigs')


def model_compare(oldObj, newObj, excluded_keys=[]):
    # recieves two objects of the same model, and compares them. Returns an array of FieldCompare objects
    try:
        theFields = oldObj._meta.fields #This becomes deprecated in Django 1.8!!!!!!!!!!!!! (but an alternative becomes available)
    except AttributeError:
        theFields = newObj._meta.fields


    class FieldCompare(object):
        def __init__(self, field=None, old=None, new=None):
            self.field = field
            self.old = old
            self.new = new

    changes = []

    for thisField in theFields:
        name = thisField.name
        oldValue = getattr(oldObj, name, None)
        newValue = getattr(newObj, name, None)

        if name in excluded_keys:
            continue # if we're excluding this field, skip over it

        try:
            if oldValue != newValue:
                compare = FieldCompare(thisField,oldValue,newValue) 
                changes.append(compare)
        except TypeError: # logs issues with naive vs tz-aware datetimes
            logger.error('TypeError when comparing models')
    
    return changes

def compare_event_items(old, new):
    # Recieves two event version objects and compares their items, returns an array of ItemCompare objects

    item_type = ContentType.objects.get_for_model(models.EventItem)
    old_item_versions = old.revision.version_set.filter(content_type=item_type)
    new_item_versions = new.revision.version_set.filter(content_type=item_type)

    class ItemCompare(object):
        def __init__(self, old=None, new=None, changes=None):
            self.old = old
            self.new = new
            self.changes = changes

    # Build some dicts of what we have
    item_dict = {} # build a list of items, key is the item_pk
    for version in old_item_versions: # put all the old versions in a list
        compare = ItemCompare(old=version.object_version.object)
        item_dict[version.object_id] = compare

    for version in new_item_versions: # go through the new versions
        try: 
            compare = item_dict[version.object_id] # see if there's a matching old version
            compare.new = version.object_version.object # then add the new version to the dictionary
        except KeyError: # there's no matching old version, so add this item to the dictionary by itself
            compare = ItemCompare(new=version.object_version.object)
        
        item_dict[version.object_id] = compare # update the dictionary with the changes

    changes = [] 
    for (_, compare) in item_dict.items():
        compare.changes = model_compare(compare.old, compare.new, ['id','event','order']) # see what's changed
        if len(compare.changes) >= 1:
            changes.append(compare) # transfer into a sequential array to make it easier to deal with later

    return changes

def get_versions_for_model(model):
    content_type = ContentType.objects.get_for_model(model)
    versions = reversion.models.Version.objects.filter(
        content_type = content_type,
    ).select_related("revision","revision.version_set").order_by("-pk")

    return versions

def get_previous_version(version):
    thisEventId = version.object_id
    thisVersionId = version.pk

    versions = reversion.get_for_object_reference(models.Event, thisEventId)

    try:
        previousVersions = versions.filter(pk__lt=thisVersionId).latest(field_name='pk') # this is very slow :(
    except:
        return False

    return previousVersions

def get_changes_for_version(newVersion, oldVersion=None):
    #Pass in a previous version if you already know it (for efficiancy)
    #if not provided then it will be looked up in the database

    if oldVersion == None: 
        oldVersion = get_previous_version(newVersion)

    compare = {}
    compare['revision'] = newVersion.revision    
    compare['new'] = newVersion.object_version.object
    compare['current'] = models.Event.objects.get(pk=compare['new'].pk)
    compare['version'] = newVersion

    if oldVersion:
        compare['old'] = oldVersion.object_version.object
        compare['field_changes'] = model_compare(compare['old'], compare['new'])
        compare['item_changes'] = compare_event_items(oldVersion, newVersion)

    return compare

class EventRevisions(generic.TemplateView):
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
    paginate_by = 25
    
    def get_queryset(self):
        versions = get_versions_for_model(models.Event)
        return versions

    def get_context_data(self, **kwargs):

        # Call the base implementation first to get a context
        context = super(ActivityStream, self).get_context_data(**kwargs)
        
        items = []

        for thisVersion in context['object_list']:
            thisItem = get_changes_for_version(thisVersion, None)
            items.append(thisItem)

        context ['object_list'] = items
         

        return context