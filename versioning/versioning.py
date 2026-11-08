import hashlib
import uuid
from collections import defaultdict

from django.apps import apps
from django.core.cache import cache
from diff_match_patch import diff_match_patch
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import (
    BooleanField,
    CharField,
    EmailField,
    Exists,
    IntegerField,
    OuterRef,
    Q,
    Subquery,
    TextField,
)
from django.db.models.functions import Cast
from django.db.transaction import on_commit
from django.urls import NoReverseMatch, reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.core import serializers
from reversion import revisions as reversion
from reversion.models import Revision, Version, VersionQuerySet
from reversion.revisions import _get_content_type, _get_options

from versioning.models import RevisionAction


class RevisionMixin:
    @property
    def is_first_version(self):
        return RIGSVersion.objects.get_for_object(self).count() == 1

    @property
    def current_version(self):
        version = self.__dict__.get("_current_version")
        if version is None:
            version = RIGSVersion.objects.get_for_object(self).select_related("revision", "revision__user").first()
            self.__dict__["_current_version"] = version
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


EMPTY_VALUE = "\u2014"
SHORT_VALUE_LIMIT = 48
DIFF_CONTEXT = 40


class FieldComparison:
    def __init__(self, field=None, old=None, new=None):
        self.field = field
        self._old = old
        self._new = new

    def display_value(self, value):
        if (
            isinstance(self.field, (IntegerField, CharField))
            and self.field.choices is not None
            and len(self.field.choices) > 0
        ):
            choice = [x[1] for x in self.field.choices if x[0] == value]
            if len(choice) > 0:
                return choice[0]
        if isinstance(self.field, BooleanField):
            return None if value is None else ("Yes" if value else "No")
        return value

    @property
    def old(self):
        return self.display_value(self._old)

    @property
    def new(self):
        return self.display_value(self._new)

    @property
    def boolean(self):
        return isinstance(self.field, BooleanField)

    @property
    def old_text(self):
        return EMPTY_VALUE if self.old in (None, "") else self.old

    @property
    def new_text(self):
        return EMPTY_VALUE if self.new in (None, "") else self.new

    @property
    def short(self):
        if self.linebreaks or self.long:
            return False
        return len(str(self.old_text)) + len(str(self.new_text)) <= SHORT_VALUE_LIMIT

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

        for op, data in diffs:
            if op == dmp.DIFF_INSERT:
                outputDiffs.append({"type": "insert", "text": data})
            elif op == dmp.DIFF_DELETE:
                outputDiffs.append({"type": "delete", "text": data})
            elif op == dmp.DIFF_EQUAL:
                outputDiffs.append({"type": "equal", "text": data})
        return outputDiffs

    @property
    def compact_diff(self):
        diffs = self.diff
        compact = []
        for index, part in enumerate(diffs):
            text = part["text"]
            if part["type"] == "equal" and len(text) > DIFF_CONTEXT * 2:
                before = text[:DIFF_CONTEXT] if index > 0 else ""
                after = text[-DIFF_CONTEXT:] if index < len(diffs) - 1 else ""
                text = f"{before}\u2026{after}"
            compact.append({"type": part["type"], "text": text})
        return compact


def related_value(obj, field, raw):
    if not field.is_relation or raw is None:
        return raw
    try:
        return getattr(obj, field.name)
    except ObjectDoesNotExist:
        return f"Deleted #{raw}"


class ModelComparison:
    def __init__(self, old=None, new=None, version=None, follow=False, excluded_keys=("date_joined",), parent=None):
        # recieves two objects of the same model, and compares them. Returns an array of FieldCompare objects
        self.fields = (old if old is not None else new)._meta.concrete_fields
        self.old = old
        self.new = new
        self.excluded_keys = set(excluded_keys) | set(version.hidden_fields if version else ())
        self.version = version
        self.parent = parent
        self.follow = follow

    @cached_property
    def revision(self):
        return self.version.revision

    @cached_property
    def field_changes(self):
        changes = []
        for field in self.fields:
            if field.name in self.excluded_keys or getattr(field, "generated", False):
                continue
            old_value = getattr(self.old, field.attname, None)
            new_value = getattr(self.new, field.attname, None)
            if old_value != new_value and (old_value or new_value):
                changes.append(
                    FieldComparison(
                        field,
                        related_value(self.old, field, old_value),
                        related_value(self.new, field, new_value),
                    )
                )
        return changes

    @cached_property
    def fields_changed(self):
        return len(self.field_changes) > 0

    @cached_property
    def item_changes(self):
        if not (self.follow and self.parent and self.version.object_exists):
            return None
        if not _get_options(self.version._model).follow:
            return None

        comparisonParams = {"excluded_keys": ["id", "event", "order", "checklist", "level", "_order", "date_joined"]}

        item_dict = {}
        for version in self.parent.revision_versions:
            if version._model is None or version.content_type_id in item_exclusions(self.version, old=True):
                continue
            compare = ModelComparison(old=version._object_version.object, **comparisonParams)
            item_dict[(version.content_type_id, version.object_id)] = compare

        for version in self.version.revision_versions:
            if version._model is None or version.content_type_id in item_exclusions(self.version):
                continue
            key = (version.content_type_id, version.object_id)
            try:
                compare = item_dict[key]
                compare.new = version._object_version.object
            except KeyError:
                compare = ModelComparison(new=version._object_version.object, **comparisonParams)
            item_dict[key] = compare

        return [compare for compare in item_dict.values() if compare.fields_changed]

    @cached_property
    def name(self):
        obj = self.new if self.new else self.old

        if hasattr(obj, "activity_feed_string"):
            return obj.activity_feed_string
        else:
            return str(obj)

    @cached_property
    def items_changed(self):
        return self.item_changes is not None and len(self.item_changes) > 0

    @cached_property
    def anything_changed(self):
        return self.fields_changed or self.items_changed


def item_exclusions(version, old=False):
    from RIGS.models import EventAuthorisation
    from training.models import TrainingItemQualification, TrainingLevelQualification

    models = [version._model, EventAuthorisation]
    if old:
        models += [TrainingItemQualification, TrainingLevelQualification]
    return {ContentType.objects.get_for_model(model).pk for model in models}


class RIGSVersionManager(VersionQuerySet):
    def get_for_multiple_models(self, model_array):
        content_types = []
        for model in model_array:
            content_types.append(ContentType.objects.get_for_model(model))

        return (
            self.filter(content_type__in=content_types)
            .select_related("revision", "revision__user", "revision__action")
            .order_by("-revision__date_created")
        )


COMMENTS_NOT_WORTH_SHOWING = ("", "Initial version.")


class RIGSVersion(Version):
    class Meta:
        proxy = True

    objects = RIGSVersionManager.as_manager()

    hidden_fields = frozenset()
    earliest = None
    session = None
    session_template = None
    session_detail_template = None

    # Gets the most recent previous version
    @cached_property
    def parent(self):
        versions = RIGSVersion.objects.get_for_object_reference(self._model, self.object_id).select_related(
            "revision", "revision__user"
        )

        try:
            return versions.filter(revision_id__lt=self.revision_id).latest("revision_id")
        except ObjectDoesNotExist:
            return False

    @cached_property
    def revision_versions(self):
        return list(RIGSVersion.objects.filter(revision_id=self.revision_id))

    @cached_property
    def object_exists(self):
        id_field = _get_options(self._model).object_id_field
        return self._model._base_manager.filter(**{id_field: self.object_id}).exists()

    @cached_property
    def changes(self):
        parent = (self.earliest or self).parent
        return ModelComparison(
            version=self,
            new=self._object_version.object,
            old=parent._object_version.object if parent else None,
            follow=True,
            parent=parent,
        )

    @cached_property
    def action(self):
        try:
            return self.revision.action
        except RevisionAction.DoesNotExist:
            return None

    @property
    def converted_enquiry_name(self):
        """The name of the enquiry this event was made from, if that's how it came about"""
        return self.action.name if self.action and self.action.kind == RevisionAction.CONVERTED else None

    @property
    def deleted_name(self):
        """What was deleted, if this version is the record of it being deleted"""
        return self.action.name if self.action and self.action.kind == RevisionAction.DELETED else None

    @property
    def note(self):
        comment = self.revision.comment
        return None if self.action or comment in COMMENTS_NOT_WORTH_SHOWING else comment

    @cached_property
    def notes(self):
        return [self.note] if self.note else []

    def absorb(self, older):
        """Report this version as covering every change since before an older version of the same object"""
        self.earliest = older
        if older.note and older.note not in self.notes:
            self.notes.append(older.note)
        self.__dict__.pop("changes", None)

    @property
    def history_url(self):
        obj = self._object_version.object
        try:
            return reverse(f"{self._model._meta.model_name}_history", kwargs={"pk": getattr(obj, "asset_id", obj.pk)})
        except NoReverseMatch:
            return None

    @property
    def object_url(self):
        if not self.object_exists:
            return self.history_url
        try:
            return self._object_version.object.get_absolute_url()
        except AttributeError, ObjectDoesNotExist, NoReverseMatch:
            return None

    @cached_property
    def snapshot(self):
        return ModelComparison(
            new=self._object_version.object,
            version=self,
            excluded_keys=("id", "date_joined"),
        ).field_changes

    @cached_property
    def snapshot_items(self):
        if not _get_options(self._model).follow:
            return []
        excluded = item_exclusions(self)
        return [
            version
            for version in self.revision_versions
            if version._model is not None and version.content_type_id not in excluded
        ]

    @property
    def summary(self):
        if self.deleted_name:
            return f"Deleted {self.deleted_name}"
        if self.converted_enquiry_name and self.changes.old is None:
            return f"Converted enquiry {self.converted_enquiry_name}"
        if self.changes.old is None:
            return "Created"
        parts = [
            f"{change.field.verbose_name}: {change.old_text} -> {change.new_text}"
            if change.short
            else str(change.field.verbose_name)
            for change in self.changes.field_changes
        ]
        parts += [str(item.name) for item in self.changes.item_changes or []]
        parts += self.notes
        return "; ".join(parts)

    @property
    def display_id(self):
        return f"V{self.pk} | R{self.revision.pk}"

    @property
    def display_name(self):
        if hasattr(self.changes.new, "display_id"):
            id = self.changes.new.display_id
        else:
            id = self.changes.new.pk

        return f"{id} | {self.changes.new.__class__.__name__}"


ACTIVITY_FEED_VERSION_KEY = "activity-feed-version"


def new_activity_feed_version():
    return uuid.uuid4().hex


def activity_feed_version():
    """Identifies the current state of the activity feed, so the cached fragment can be told apart.

    Always a value no earlier fragment was cached under: if the cache has lost the key (expiry, culling, a restart of
    an in-memory cache), a fresh one is made rather than falling back to a default that old fragments may carry."""
    version = cache.get(ACTIVITY_FEED_VERSION_KEY)
    if version is None:
        cache.add(ACTIVITY_FEED_VERSION_KEY, new_activity_feed_version(), None)
        version = cache.get(ACTIVITY_FEED_VERSION_KEY) or new_activity_feed_version()
    return version


def bump_activity_feed_version(sender=None, **kwargs):
    # Explicitly no timeout: cache.incr() would re-set the key with the default 5 minute timeout
    cache.set(ACTIVITY_FEED_VERSION_KEY, new_activity_feed_version(), None)


def get_models(app=None):
    models = [model for model in reversion.get_registered_models() if not hasattr(model, "reversion_hide")]
    if app is not None:
        app_models = list(apps.get_app_config(app).get_models())
        models = [model for model in models if model in app_models]
    return models


def filter_models(models, user):
    if user is None:
        return list(models)
    return [model for model in models if not hasattr(model, "reversion_perm") or user.has_perm(model.reversion_perm)]


def hidden_fields(model, user):
    perm, fields = getattr(model, "reversion_field_perm", (None, ()))
    return frozenset(fields) if perm and not (user and user.has_perm(perm)) else frozenset()


def feed_audience(user):
    """Identifies what a user can see in the feed, so everyone who sees the same thing can share a cached copy"""
    visible = sorted(
        (model._meta.label, *sorted(hidden_fields(model, user))) for model in filter_models(get_models(), user)
    )
    return hashlib.sha256(repr(visible).encode()).hexdigest()


def revision_committed(sender=None, versions=(), **kwargs):
    visible = get_models()
    if any(version._model in visible for version in versions):
        on_commit(bump_activity_feed_version)


def record_deletions(objects, label, user=None):
    """
    Keep a version of each of some objects that are about to be deleted, in one revision, as reversion only saves
    versions of objects that exist. The revision is called "Deleted <label>".
    """
    revision = Revision.objects.create(
        date_created=timezone.now(),
        user=user or (reversion.get_user() if reversion.is_active() else None),
        comment=f"Deleted {label}",
    )
    versions = []
    for obj in objects:
        model = obj.__class__
        options = _get_options(model)
        versions.append(
            Version(
                revision=revision,
                object_id=str(getattr(obj, options.object_id_field)),
                content_type=_get_content_type(model, "default"),
                db=obj._state.db or "default",
                format=options.format,
                serialized_data=serializers.serialize(
                    options.format,
                    (obj,),
                    fields=options.fields,
                    use_natural_foreign_keys=options.use_natural_foreign_keys,
                ),
                object_repr=str(obj),
            )
        )
    Version.objects.bulk_create(versions)
    RevisionAction.objects.create(revision=revision, kind=RevisionAction.DELETED, name=label)
    on_commit(bump_activity_feed_version)


def record_deletion(obj):
    """Keep a version of an object that is about to be deleted, as reversion only saves versions of objects that exist"""
    record_deletions([obj], f"{obj._meta.verbose_name} {obj}")


def record_deleted_object(sender, instance, **kwargs):
    if not getattr(instance, "skip_deletion_record", False):
        record_deletion(instance)


def last_edited_subquery(model):
    content_type = _get_content_type(model, "default")
    return Subquery(
        Version.objects.filter(content_type=content_type, object_id=Cast(OuterRef("pk"), CharField()))
        .order_by("-revision__date_created")
        .values("revision__date_created")[:1]
    )


def prepare_versions(versions, user):
    """Fetch what displaying a list of versions needs in bulk, and hide the fields this user can't see"""
    versions = list(versions)
    if not versions:
        return versions

    parent_ids = dict(
        RIGSVersion.objects.filter(pk__in=[version.pk for version in versions])
        .annotate(
            parent_id=Subquery(
                Version.objects.filter(
                    content_type_id=OuterRef("content_type_id"),
                    object_id=OuterRef("object_id"),
                    db=OuterRef("db"),
                    revision_id__lt=OuterRef("revision_id"),
                )
                .order_by("-revision_id")
                .values("pk")[:1]
            )
        )
        .values_list("pk", "parent_id")
    )
    parents = RIGSVersion.objects.select_related("revision").in_bulk([pk for pk in parent_ids.values() if pk])

    followed = []
    object_ids = defaultdict(set)
    for version in versions:
        version.hidden_fields = hidden_fields(version._model, user)
        version.__dict__["parent"] = parents.get(parent_ids.get(version.pk), False)
        object_ids[version._model].add(version.object_id)
        if _get_options(version._model).follow:
            followed.append(version)
            if version.parent:
                followed.append(version.parent)

    for model, ids in object_ids.items():
        id_field = _get_options(model).object_id_field
        existing = {
            str(pk) for pk in model._base_manager.filter(**{f"{id_field}__in": ids}).values_list(id_field, flat=True)
        }
        for version in versions:
            if version._model is model:
                version.__dict__["object_exists"] = version.object_id in existing

    if followed:
        by_revision = defaultdict(list)
        for version in RIGSVersion.objects.filter(revision_id__in={version.revision_id for version in followed}):
            by_revision[version.revision_id].append(version)
        for version in followed:
            version.__dict__["revision_versions"] = by_revision[version.revision_id]

    return versions


def session_models(models):
    return [model for model in models if hasattr(model, "summarise_sessions")]


def collapse_sessions(versions, models):
    """Keep one version of each model per revision for models that summarise a whole session in one row"""
    content_types = [ContentType.objects.get_for_model(model).pk for model in session_models(models)]
    if not content_types:
        return versions
    earlier = Version.objects.filter(
        revision_id=OuterRef("revision_id"), content_type_id=OuterRef("content_type_id"), pk__lt=OuterRef("pk")
    )
    return versions.filter(~Q(content_type_id__in=content_types) | ~Exists(earlier))


def attach_sessions(versions, collapsed=True):
    by_model = defaultdict(list)
    for version in versions:
        if hasattr(version._model, "summarise_sessions") and version.action is None:
            by_model[version._model].append(version)

    for model, model_versions in by_model.items():
        members = defaultdict(list)
        if collapsed:
            content_type = _get_content_type(model, "default")
            for member in RIGSVersion.objects.filter(
                revision_id__in={version.revision_id for version in model_versions}, content_type=content_type
            ):
                members[member.revision_id].append(member)
        sessions = [(version, members[version.revision_id] if collapsed else [version]) for version in model_versions]
        sessions = [(version, group) for version, group in sessions if len(group) > 1 or not version.parent]
        summaries = model.summarise_sessions(
            [[member._object_version.object for member in group] for _, group in sessions]
        )
        for (version, _), summary in zip(sessions, summaries):
            version.session = summary
            version.session_template = model.session_template
            version.session_detail_template = model.session_detail_template
    return versions
