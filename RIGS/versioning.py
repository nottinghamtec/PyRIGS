import logging

from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import get_object_or_404
from django.views import generic

# Versioning
import reversion
from reversion.models import Version
from django.contrib.contenttypes.models import ContentType  # Used to lookup the content_type
from django.db.models import IntegerField, EmailField, TextField
from diff_match_patch import diff_match_patch

from RIGS import models
import datetime

logger = logging.getLogger('tec.pyrigs')


def model_compare(oldObj, newObj, excluded_keys=[]):
    # recieves two objects of the same model, and compares them. Returns an array of FieldCompare objects
    try:
        theFields = oldObj._meta.fields  # This becomes deprecated in Django 1.8!!!!!!!!!!!!! (but an alternative becomes available)
    except AttributeError:
        theFields = newObj._meta.fields

    class FieldCompare(object):
        def __init__(self, field=None, old=None, new=None):
            self.field = field
            self._old = old
            self._new = new

        def display_value(self, value):
            if isinstance(self.field, IntegerField) and len(self.field.choices) > 0:
                return [x[1] for x in self.field.choices if x[0] == value][0]
            return value

        @property
        def old(self):
            return self.display_value(self._old)

        @property
        def new(self):
            return self.display_value(self._new)

        @property
        def long(self):
            if isinstance(self.field, EmailField):
                return True
            return False

        @property
        def linebreaks(self):
            if isinstance(self.field, TextField):
                return True
            return False

        @property
        def diff(self):
            oldText = unicode(self.display_value(self._old)) or ""
            newText = unicode(self.display_value(self._new)) or ""
            dmp = diff_match_patch()
            diffs = dmp.diff_main(oldText, newText)
            dmp.diff_cleanupSemantic(diffs)

            outputDiffs = []

            for (op, data) in diffs:
                if op == dmp.DIFF_INSERT:
                    outputDiffs.append({'type': 'insert', 'text': data})
                elif op == dmp.DIFF_DELETE:
                    outputDiffs.append({'type': 'delete', 'text': data})
                elif op == dmp.DIFF_EQUAL:
                    outputDiffs.append({'type': 'equal', 'text': data})
            return outputDiffs

    changes = []

    for thisField in theFields:
        name = thisField.name

        if name in excluded_keys:
            continue  # if we're excluding this field, skip over it

        try:
            oldValue = getattr(oldObj, name, None)
        except ObjectDoesNotExist:
            oldValue = None

        try:
            newValue = getattr(newObj, name, None)
        except ObjectDoesNotExist:
            newValue = None

        try:
            bothBlank = (not oldValue) and (not newValue)
            if oldValue != newValue and not bothBlank:
                compare = FieldCompare(thisField, oldValue, newValue)
                changes.append(compare)
        except TypeError:  # logs issues with naive vs tz-aware datetimes
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
    item_dict = {}  # build a list of items, key is the item_pk
    for version in old_item_versions:  # put all the old versions in a list
        if version.field_dict["event"] == old.object_id_int:
            compare = ItemCompare(old=version.object_version.object)
            item_dict[version.object_id] = compare

    for version in new_item_versions:  # go through the new versions
        if version.field_dict["event"] == new.object_id_int:
            try:
                compare = item_dict[version.object_id]  # see if there's a matching old version
                compare.new = version.object_version.object  # then add the new version to the dictionary
            except KeyError:  # there's no matching old version, so add this item to the dictionary by itself
                compare = ItemCompare(new=version.object_version.object)

            item_dict[version.object_id] = compare  # update the dictionary with the changes

    changes = []
    for (_, compare) in item_dict.items():
        compare.changes = model_compare(compare.old, compare.new, ['id', 'event', 'order'])  # see what's changed
        if len(compare.changes) >= 1:
            changes.append(compare)  # transfer into a sequential array to make it easier to deal with later

    return changes


def get_versions_for_model(models):
    content_types = []
    for model in models:
        content_types.append(ContentType.objects.get_for_model(model))

    versions = reversion.models.Version.objects.filter(
        content_type__in=content_types,
    ).select_related("revision").order_by("-pk")

    return versions


def get_previous_version(version):
    thisId = version.object_id
    thisVersionId = version.pk

    versions = reversion.revisions.get_for_object_reference(version.content_type.model_class(), thisId)

    try:
        previousVersions = versions.filter(revision_id__lt=version.revision_id).latest(
            field_name='revision__date_created')
    except ObjectDoesNotExist:
        return False

    return previousVersions


def get_changes_for_version(newVersion, oldVersion=None):
    # Pass in a previous version if you already know it (for efficiancy)
    # if not provided then it will be looked up in the database

    if oldVersion == None:
        oldVersion = get_previous_version(newVersion)

    modelClass = newVersion.content_type.model_class()

    compare = {
        'revision': newVersion.revision,
        'new': newVersion.object_version.object,
        'current': modelClass.objects.filter(pk=newVersion.pk).first(),
        'version': newVersion,

        # Old things that may not be used
        'old': None,
        'field_changes': None,
        'item_changes': None,
    }

    if oldVersion:
        compare['old'] = oldVersion.object_version.object
        compare['field_changes'] = model_compare(compare['old'], compare['new'])
        compare['item_changes'] = compare_event_items(oldVersion, newVersion)

    return compare


class VersionHistory(generic.ListView):
    model = reversion.revisions.Version
    template_name = "RIGS/version_history.html"
    paginate_by = 25

    def get_queryset(self, **kwargs):
        thisModel = self.kwargs['model']

        # thisObject = get_object_or_404(thisModel, pk=self.kwargs['pk'])
        versions = reversion.revisions.get_for_object_reference(thisModel, self.kwargs['pk'])

        return versions

    def get_context_data(self, **kwargs):
        thisModel = self.kwargs['model']

        context = super(VersionHistory, self).get_context_data(**kwargs)

        versions = context['object_list']
        thisObject = get_object_or_404(thisModel, pk=self.kwargs['pk'])

        items = []

        for versionNo, thisVersion in enumerate(versions):
            if versionNo >= len(versions) - 1:
                thisItem = get_changes_for_version(thisVersion, None)
            else:
                thisItem = get_changes_for_version(thisVersion, versions[versionNo + 1])

            items.append(thisItem)

        context['object_list'] = items
        context['object'] = thisObject

        return context


class ActivityTable(generic.ListView):
    model = reversion.revisions.Version
    template_name = "RIGS/activity_table.html"
    paginate_by = 25

    def get_queryset(self):
        versions = get_versions_for_model([models.Event, models.Venue, models.Person, models.Organisation])
        return versions

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(ActivityTable, self).get_context_data(**kwargs)

        items = []

        for thisVersion in context['object_list']:
            thisItem = get_changes_for_version(thisVersion, None)
            items.append(thisItem)

        context['object_list'] = items

        return context


class ActivityFeed(generic.ListView):
    model = reversion.revisions.Version
    template_name = "RIGS/activity_feed_data.html"
    paginate_by = 25

    def get_queryset(self):
        versions = get_versions_for_model([models.Event, models.Venue, models.Person, models.Organisation])
        return versions

    def get_context_data(self, **kwargs):
        maxTimeDelta = []

        maxTimeDelta.append({'maxAge': datetime.timedelta(days=1), 'group': datetime.timedelta(hours=1)})
        maxTimeDelta.append({'maxAge': None, 'group': datetime.timedelta(days=1)})

        # Call the base implementation first to get a context
        context = super(ActivityFeed, self).get_context_data(**kwargs)

        items = []

        for thisVersion in context['object_list']:
            thisItem = get_changes_for_version(thisVersion, None)
            if thisItem['item_changes'] or thisItem['field_changes'] or thisItem['old'] == None:
                thisItem['withPrevious'] = False
                if len(items) >= 1:
                    timeAgo = datetime.datetime.now(thisItem['revision'].date_created.tzinfo) - thisItem[
                        'revision'].date_created
                    timeDiff = items[-1]['revision'].date_created - thisItem['revision'].date_created
                    timeTogether = False
                    for params in maxTimeDelta:
                        if params['maxAge'] is None or timeAgo <= params['maxAge']:
                            timeTogether = timeDiff < params['group']
                            break

                    sameUser = thisItem['revision'].user == items[-1]['revision'].user
                    thisItem['withPrevious'] = timeTogether & sameUser

                items.append(thisItem)

        context['object_list'] = items

        return context
