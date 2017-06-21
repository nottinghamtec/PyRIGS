

import logging
import datetime

from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import get_object_or_404
from django.views import generic
from django.utils.functional import cached_property
from django.db.models import IntegerField, EmailField, TextField
from django.contrib.contenttypes.models import ContentType

from reversion.models import Version, VersionQuerySet
from diff_match_patch import diff_match_patch

from RIGS import models

logger = logging.getLogger('tec.pyrigs')


class FieldComparison(object):
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
        oldText = str(self.display_value(self._old)) or ""
        newText = str(self.display_value(self._new)) or ""
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


class ModelComparison(object):

    def __init__(self, old=None, new=None, version=None, excluded_keys=[]):
        # recieves two objects of the same model, and compares them. Returns an array of FieldCompare objects
        try:
            self.fields = old._meta.get_fields()
        except AttributeError:
            self.fields = new._meta.get_fields()

        self.old = old
        self.new = new
        self.excluded_keys = excluded_keys
        self.version = version

    @cached_property
    def revision(self):
        return self.version.revision

    @cached_property
    def field_changes(self):
        changes = []
        for field in self.fields:
            field_name = field.name

            if field_name in self.excluded_keys:
                continue  # if we're excluding this field, skip over it

            try:
                oldValue = getattr(self.old, field_name, None)
            except ObjectDoesNotExist:
                oldValue = None

            try:
                newValue = getattr(self.new, field_name, None)
            except ObjectDoesNotExist:
                newValue = None

            bothBlank = (not oldValue) and (not newValue)
            if oldValue != newValue and not bothBlank:
                comparison = FieldComparison(field, oldValue, newValue)
                changes.append(comparison)

        return changes

    @cached_property
    def fields_changed(self):
        return len(self.field_changes) > 0

    @cached_property
    def item_changes(self):
        # Recieves two event version objects and compares their items, returns an array of ItemCompare objects

        item_type = ContentType.objects.get_for_model(models.EventItem)
        old_item_versions = self.version.parent.revision.version_set.filter(content_type=item_type)
        new_item_versions = self.version.revision.version_set.filter(content_type=item_type)

        comparisonParams = {'excluded_keys': ['id', 'event', 'order']}

        # Build some dicts of what we have
        item_dict = {}  # build a list of items, key is the item_pk
        for version in old_item_versions:  # put all the old versions in a list
            if version.field_dict["event_id"] == int(self.new.pk):
                compare = ModelComparison(old=version._object_version.object, **comparisonParams)
                item_dict[version.object_id] = compare

        for version in new_item_versions:  # go through the new versions
            if version.field_dict["event_id"] == int(self.new.pk):
                try:
                    compare = item_dict[version.object_id]  # see if there's a matching old version
                    compare.new = version._object_version.object  # then add the new version to the dictionary
                except KeyError:  # there's no matching old version, so add this item to the dictionary by itself
                    compare = ModelComparison(new=version._object_version.object, **comparisonParams)

                item_dict[version.object_id] = compare  # update the dictionary with the changes

        changes = []
        for (_, compare) in list(item_dict.items()):
            if compare.fields_changed:
                changes.append(compare)

        return changes

    @cached_property
    def items_changed(self):
        return len(self.item_changes) > 0

    @cached_property
    def anything_changed(self):
        return self.fields_changed or self.items_changed


class RIGSVersionManager(VersionQuerySet):
    def get_for_multiple_models(self, model_array):
        content_types = []
        for model in model_array:
            content_types.append(ContentType.objects.get_for_model(model))

        return self.filter(content_type__in=content_types).select_related("revision").order_by("-pk")


class RIGSVersion(Version):
    class Meta:
        proxy = True

    objects = RIGSVersionManager.as_manager()

    @cached_property
    def parent(self):
        thisId = self.object_id

        versions = RIGSVersion.objects.get_for_object_reference(self.content_type.model_class(), thisId).select_related("revision", "revision__user").all()

        try:
            previousVersion = versions.filter(revision_id__lt=self.revision_id).latest(
                field_name='revision__date_created')
        except ObjectDoesNotExist:
            return False

        return previousVersion

    @cached_property
    def changes(self):
        return ModelComparison(
            version=self,
            new=self._object_version.object,
            old=self.parent._object_version.object if self.parent else None
        )


class VersionHistory(generic.ListView):
    model = RIGSVersion
    template_name = "RIGS/version_history.html"
    paginate_by = 25

    def get_queryset(self, **kwargs):
        thisModel = self.kwargs['model']

        versions = RIGSVersion.objects.get_for_object_reference(thisModel, self.kwargs['pk']).select_related("revision", "revision__user").all()

        return versions

    def get_context_data(self, **kwargs):
        thisModel = self.kwargs['model']
        context = super(VersionHistory, self).get_context_data(**kwargs)
        thisObject = get_object_or_404(thisModel, pk=self.kwargs['pk'])
        context['object'] = thisObject

        return context


class ActivityTable(generic.ListView):
    model = RIGSVersion
    template_name = "RIGS/activity_table.html"
    paginate_by = 25

    def get_queryset(self):
        versions = RIGSVersion.objects.get_for_multiple_models([models.Event, models.Venue, models.Person, models.Organisation, models.EventAuthorisation])
        return versions


class ActivityFeed(generic.ListView):
    model = RIGSVersion
    template_name = "RIGS/activity_feed_data.html"
    paginate_by = 25

    def get_queryset(self):
        versions = RIGSVersion.objects.get_for_multiple_models([models.Event, models.Venue, models.Person, models.Organisation, models.EventAuthorisation])
        return versions

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(ActivityFeed, self).get_context_data(**kwargs)

        maxTimeDelta = datetime.timedelta(hours=1)

        items = []

        for thisVersion in context['object_list']:
            thisVersion.withPrevious = False
            if len(items) >= 1:
                timeDiff = items[-1].revision.date_created - thisVersion.revision.date_created
                timeTogether = timeDiff < maxTimeDelta
                sameUser = thisVersion.revision.user_id == items[-1].revision.user_id
                thisVersion.withPrevious = timeTogether & sameUser

            items.append(thisVersion)

        return context
