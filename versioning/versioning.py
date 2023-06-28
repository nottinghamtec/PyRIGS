import logging
from diff_match_patch import diff_match_patch
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import EmailField, IntegerField, TextField, CharField, BooleanField
from django.utils.functional import cached_property
from reversion.models import Version, VersionQuerySet


class RevisionMixin:
    @property
    def is_first_version(self):
        versions = RIGSVersion.objects.get_for_object(self)
        return len(versions) == 1

    @property
    def current_version(self):
        version = RIGSVersion.objects.get_for_object(self).select_related('revision').first()
        return version

    @property
    def last_edited_at(self):
        version = self.current_version
        if version is None:
            return None
        return version.revision.date_created

    @property
    def last_edited_by(self):
        version = self.current_version
        if version is None:
            return None
        return version.revision.user

    @property
    def current_version_id(self):
        version = self.current_version
        if version is None:
            return None
        return version.display_id

    @property
    def date_created(self):
        return self.current_version.revision.date_created


class FieldComparison:
    def __init__(self, field=None, old=None, new=None):
        self.field = field
        self._old = old
        self._new = new

    def display_value(self, value):
        if isinstance(self.field, (IntegerField, CharField)) and self.field.choices is not None and len(self.field.choices) > 0:
            choice = [x[1] for x in self.field.choices if x[0] == value]
            if len(choice) > 0:
                return choice[0]
        if isinstance(self.field, BooleanField):
            if value:
                return "&#10003;"
            else:
                return "&#10007"
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


class ModelComparison:
    def __init__(self, old=None, new=None, version=None, follow=False, excluded_keys=['date_joined']):
        # recieves two objects of the same model, and compares them. Returns an array of FieldCompare objects
        try:
            self.fields = old._meta.get_fields()
        except AttributeError:
            self.fields = new._meta.get_fields()

        self.old = old
        self.new = new
        self.excluded_keys = excluded_keys
        self.version = version
        self.follow = follow

    @cached_property
    def revision(self):
        return self.version.revision

    @cached_property
    def field_changes(self):
        changes = []
        for field in self.fields:
            field_name = field.name
            if field_name not in self.excluded_keys:  # if we're excluding this field, skip over it
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
        if self.follow and self.version.object is not None:
            from RIGS.models import EventAuthorisation
            from training.models import TrainingLevelQualification, TrainingItemQualification
            item_type = ContentType.objects.get_for_model(self.version.object)
            old_item_versions = self.version.parent.revision.version_set.exclude(content_type=item_type).exclude(content_type=ContentType.objects.get_for_model(TrainingItemQualification)) \
                .exclude(content_type=ContentType.objects.get_for_model(TrainingLevelQualification))
            new_item_versions = self.version.revision.version_set.exclude(content_type=item_type).exclude(content_type=ContentType.objects.get_for_model(EventAuthorisation))

            comparisonParams = {'excluded_keys': ['id', 'event', 'order', 'checklist', 'level', '_order', 'date_joined']}

            # Build some dicts of what we have
            item_dict = {}  # build a list of items, key is the item_pk
            for version in old_item_versions:  # put all the old versions in a list
                if version._model is None:
                    continue
                compare = ModelComparison(old=version._object_version.object, **comparisonParams)
                item_dict[version.object_id] = compare

            for version in new_item_versions:  # go through the new versions
                if version._model is None:
                    continue
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
    def name(self):
        obj = self.new if self.new else self.old

        if (hasattr(obj, 'activity_feed_string')):
            return obj.activity_feed_string
        else:
            return str(obj)

    @cached_property
    def items_changed(self):
        return self.item_changes is not None and len(self.item_changes) > 0

    @cached_property
    def anything_changed(self):
        return self.fields_changed or self.items_changed


class RIGSVersionManager(VersionQuerySet):
    def get_for_multiple_models(self, model_array):
        content_types = []
        for model in model_array:
            content_types.append(ContentType.objects.get_for_model(model))

        return self.filter(content_type__in=content_types).select_related("revision",).order_by(
            "-revision__date_created")


class RIGSVersion(Version):
    class Meta:
        proxy = True

    objects = RIGSVersionManager.as_manager()

    # Gets the most recent previous version
    @cached_property
    def parent(self):
        thisId = self.object_id

        versions = RIGSVersion.objects.get_for_object_reference(self.content_type.model_class(), thisId).select_related(
            "revision", "revision__user").all()

        try:
            previousVersion = versions.filter(revision_id__lt=self.revision_id).latest('revision__date_created')
        except ObjectDoesNotExist:
            return False

        return previousVersion

    @cached_property
    def changes(self):
        return ModelComparison(
            version=self,
            new=self._object_version.object,
            old=self.parent._object_version.object if self.parent else None,
            follow=True
        )

    @property
    def display_id(self):
        return f"V{self.pk} | R{self.revision.pk}"

    @property
    def display_name(self):
        if hasattr(self.changes.new, 'display_id'):
            id = self.changes.new.display_id
        else:
            id = self.changes.new.pk

        return f"{id} | {self.changes.new.__class__.__name__}"
