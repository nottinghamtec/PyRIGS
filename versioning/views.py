import csv
import datetime

from django.apps import apps
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.db.models import CharField, Exists, OuterRef, Q, Value
from django.db.models.functions import Cast, Concat
from django.http import Http404, HttpResponseRedirect, JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import title
from django.urls import NoReverseMatch, reverse
from django.utils.dateparse import parse_date, parse_datetime
from django.utils.functional import cached_property
from django.views import generic
from reversion.models import Revision

from versioning.forms import ActivityFilterForm
from versioning.versioning import (
    ModelComparison,
    RIGSVersion,
    activity_feed_version,
    attach_sessions,
    collapse_sessions,
    feed_audience,
    filter_models,
    get_models,
    prepare_versions,
)

EXPORT_BATCH_SIZE = 500
PERSON_SEARCH_LIMIT = 20

ACTIVITY_PERMISSIONS = {
    "RIGS": "RIGS.view_event",
    "assets": "assets.view_asset",
    "training": "training.view_trainingitemqualification",
}


class HistoryObjectMixin:
    @property
    def history_model(self):
        return self.kwargs["model"]

    @cached_property
    def history_lookup(self):
        # Goddamit, almost got away without specific hacks
        return {"asset_id": self.kwargs["pk"]} if self.history_model.__name__ == "Asset" else {"pk": self.kwargs["pk"]}

    def deleted_version(self):
        if "asset_id" in self.history_lookup:
            return (
                RIGSVersion.objects.get_for_model(self.history_model)
                .filter(serialized_data__contains=f'"asset_id": "{self.kwargs["pk"]}"')
                .first()
            )
        return RIGSVersion.objects.get_for_object_reference(self.history_model, self.kwargs["pk"]).first()

    @cached_property
    def history_object(self):
        try:
            obj = self.history_model._base_manager.filter(**self.history_lookup).first()
        except ValueError:
            raise Http404
        if obj is not None:
            return obj
        version = self.deleted_version()
        if version is None:
            raise Http404
        return version._object_version.object

    @cached_property
    def object_deleted(self):
        return not self.history_model._base_manager.filter(pk=self.history_object.pk).exists()

    def object_versions(self):
        return RIGSVersion.objects.get_for_object_reference(self.history_model, self.history_object.pk).select_related(
            "revision", "revision__user", "revision__action"
        )

    def url_name(self, suffix, **kwargs):
        name = f"{self.history_model._meta.model_name}_{suffix}"
        try:
            reverse(name, kwargs={"pk": self.kwargs["pk"], **kwargs})
        except NoReverseMatch:
            return None
        return name

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object"] = self.history_object
        context["object_deleted"] = self.object_deleted
        context["history_pk"] = self.kwargs["pk"]
        context["history_url"] = reverse(self.url_name("history"), kwargs={"pk": self.kwargs["pk"]})
        if self.kwargs["app"] != "rigboard":
            context["override"] = f"base_{self.kwargs['app']}.html"
        return context


class VersionHistory(HistoryObjectMixin, generic.ListView):
    model = RIGSVersion
    template_name = "version_history.html"
    paginate_by = 25

    def get(self, request, *args, **kwargs):
        at = parse_date(request.GET.get("at", ""))
        if at is None or self.version_url_name is None:
            return super().get(request, *args, **kwargs)
        version = self.object_versions().filter(revision__date_created__date__lte=at).first()
        if version is None:
            messages.warning(request, f"There is no history from {at:%d/%m/%Y} or earlier.")
            return HttpResponseRedirect(request.path)
        return HttpResponseRedirect(
            reverse(self.version_url_name, kwargs={"pk": self.kwargs["pk"], "version_id": version.pk})
        )

    @cached_property
    def version_url_name(self):
        return self.url_name("version", version_id=0)

    @cached_property
    def timeline_models(self):
        related = [apps.get_model(label) for label in getattr(self.history_model, "reversion_timeline", ())]
        return filter_models(related, self.request.user)

    def get_queryset(self, **kwargs):
        versions = self.object_versions()
        if self.timeline_models:
            versions = RIGSVersion.objects.filter(
                Q(pk__in=versions.values("pk"))
                | Q(
                    content_type__in=[ContentType.objects.get_for_model(model) for model in self.timeline_models],
                    serialized_data__regex=rf'"event": {self.history_object.pk}[,}}]',
                )
            ).select_related("revision", "revision__user", "revision__action")
        return versions.order_by("-revision__date_created", "-pk")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object_list"] = prepare_versions(context["object_list"], self.request.user)
        for version in context["object_list"]:
            version.is_own = version._model is self.history_model
        context["timeline"] = bool(self.timeline_models)
        context["version_url_name"] = self.version_url_name
        context["compare_url_name"] = self.url_name("compare")
        return context


class VersionDetail(HistoryObjectMixin, generic.TemplateView):
    template_name = "version_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        version = get_object_or_404(self.object_versions(), pk=self.kwargs["version_id"])
        context["version"] = prepare_versions([version], self.request.user)[0]
        return context


class VersionCompare(HistoryObjectMixin, generic.TemplateView):
    template_name = "version_compare.html"

    def get_version(self, name):
        version_id = self.request.GET.get(name, "")
        if not version_id.isdecimal():
            raise Http404
        return get_object_or_404(self.object_versions(), pk=version_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        first, second = sorted((self.get_version("from"), self.get_version("to")), key=lambda version: version.pk)
        first, second = prepare_versions([first, second], self.request.user)
        context["from_version"] = first
        context["to_version"] = second
        context["comparison"] = ModelComparison(
            old=first._object_version.object,
            new=second._object_version.object,
            version=second,
            follow=True,
            parent=first,
        )
        return context


class EventSinceAuthorised(generic.RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        Event = apps.get_model("RIGS", "Event")
        event = get_object_or_404(Event, pk=kwargs["pk"])
        history = reverse("event_history", kwargs={"pk": event.pk})
        authorisation = getattr(event, "authorisation", None)
        authorised_at = authorisation.last_edited_at if authorisation else None
        versions = RIGSVersion.objects.get_for_object(event)
        authorised = versions.filter(revision__date_created__lte=authorised_at).first() if authorised_at else None
        if authorised is None:
            return history
        return f"{reverse('event_compare', kwargs={'pk': event.pk})}?from={authorised.pk}&to={versions.first().pk}"


def csv_safe(value):
    text = str(value)
    return f"'{text}" if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


class EchoBuffer:
    def write(self, value):
        return value


class ActivityTable(generic.ListView):
    model = RIGSVersion
    template_name = "activity_table.html"
    paginate_by = 25

    @cached_property
    def visible_models(self):
        return filter_models(self.kwargs.get("models"), self.request.user)

    @cached_property
    def filter_form(self):
        return ActivityFilterForm(self.request.GET, models=self.visible_models)

    @property
    def show_sessions(self):
        return self.request.GET.get("export") != "csv" and not self.request.GET.get("q")

    def get_queryset(self):
        versions = self.filtered_versions()
        return collapse_sessions(versions, self.visible_models) if self.show_sessions else versions

    def filtered_versions(self):
        versions = RIGSVersion.objects.get_for_multiple_models(self.visible_models)
        if not self.filter_form.is_valid():
            return versions
        filters = self.filter_form.cleaned_data
        if filters["model"]:
            model = self.filter_form.models[filters["model"]]
            versions = versions.filter(content_type=ContentType.objects.get_for_model(model))
        if filters["q"]:
            versions = versions.filter(
                Q(object_repr__icontains=filters["q"]) | Q(revision__comment__icontains=filters["q"])
            )
        if filters["user"]:
            versions = versions.filter(revision__user=filters["user"])
        if filters["start"]:
            versions = versions.filter(revision__date_created__date__gte=filters["start"])
        if filters["end"]:
            versions = versions.filter(revision__date_created__date__lte=filters["end"])
        if filters["mine"]:
            versions = versions.filter(revision__user=self.request.user)
        if filters["my_events"]:
            Event = apps.get_model("RIGS", "Event")
            versions = versions.filter(
                content_type=ContentType.objects.get_for_model(Event),
                object_id__in=Event.objects.filter(mic=self.request.user)
                .annotate(object_id=Cast("pk", CharField()))
                .values("object_id"),
            )
        return versions

    def get(self, request, *args, **kwargs):
        if request.GET.get("export") == "csv":
            return self.export()
        return super().get(request, *args, **kwargs)

    def export_rows(self):
        writer = csv.writer(EchoBuffer())
        yield writer.writerow(["Date", "Type", "Object", "Version ID", "User", "Changes"])
        versions = self.get_queryset()
        start = 0
        while batch := list(versions[start : start + EXPORT_BATCH_SIZE]):
            start += EXPORT_BATCH_SIZE
            for version in prepare_versions(batch, self.request.user):
                user = version.revision.user
                yield writer.writerow(
                    [
                        version.revision.date_created.isoformat(),
                        version._model._meta.verbose_name.title(),
                        csv_safe(version.object_repr),
                        version.display_id,
                        csv_safe(user.name if user else "System"),
                        csv_safe(version.summary),
                    ]
                )

    def export(self):
        response = StreamingHttpResponse(self.export_rows(), content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="recent-changes.csv"'
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object_list"] = attach_sessions(
            prepare_versions(context["object_list"], self.request.user), collapsed=self.show_sessions
        )
        context["page_title"] = f"{title(self.kwargs.get('heading', self.kwargs['app']))} Activity Stream"
        context["filter_form"] = self.filter_form
        query = self.request.GET.copy()
        query.pop("page", None)
        query["export"] = "csv"
        context["export_query"] = query.urlencode()
        if self.kwargs["app"] != "rigboard":
            context["override"] = f"base_{self.kwargs['app']}.html"

        return context


class ActivityPeopleSearch(generic.View):
    def get(self, request):
        if not any(request.user.has_perm(permission) for permission in ACTIVITY_PERMISSIONS.values()):
            raise PermissionDenied
        query = request.GET.get("q", "").strip()
        if not query:
            return JsonResponse([], safe=False)
        people = (
            get_user_model()
            .objects.annotate(
                full_name=Concat("first_name", Value(" "), "last_name"),
                has_changes=Exists(Revision.objects.filter(user=OuterRef("pk"))),
            )
            .filter(Q(full_name__icontains=query) | Q(initials__icontains=query), has_changes=True)
            .order_by("first_name", "last_name")[:PERSON_SEARCH_LIMIT]
        )
        return JsonResponse([{"pk": person.pk, "text": person.name} for person in people], safe=False)


class ActivityFeed(generic.ListView):  # Appears on homepage
    model = RIGSVersion
    template_name = "activity_feed_data.html"
    group_limit = 12
    version_limit = 500
    collapse_threshold = 3
    collapsible_models = ("trainingitemqualification", "invoice")

    @cached_property
    def before(self):
        return parse_datetime(self.request.GET.get("before", ""))

    def get_queryset(self):
        versions = RIGSVersion.objects.get_for_multiple_models(filter_models(get_models(), self.request.user))
        if self.before:
            versions = versions.filter(revision__date_created__lt=self.before)
        return versions.order_by("-revision__date_created")[: self.version_limit]

    def build_groups(self, versions):
        """Groups consecutive versions by the same user within an hour of each other, newest first"""
        maxTimeDelta = datetime.timedelta(hours=1)
        groups = []
        for version in versions:
            if groups:
                last = groups[-1]["versions"][-1]
                together = last.revision.date_created - version.revision.date_created < maxTimeDelta
                if together and version.revision.user_id == last.revision.user_id:
                    groups[-1]["versions"].append(version)
                    continue
            if len(groups) >= self.group_limit:
                break
            groups.append({"revision": version.revision, "versions": [version]})
        return groups

    def merge_edits(self, versions):
        """Reports repeated edits of one object as a single change, from before the first to after the last"""
        latest = {}
        merged = []
        for version in versions:
            key = (version.content_type_id, version.object_id)
            if version.action or not version.parent:
                merged.append(version)
            elif key in latest:
                latest[key].absorb(version)
            else:
                latest[key] = version
                merged.append(version)
        return merged

    def collapse_runs(self, versions):
        """Folds long runs of versions of the same kind of object into one expandable entry"""
        entries = []
        run = []

        def flush():
            if len(run) > self.collapse_threshold:
                model = ContentType.objects.get_for_id(run[0].content_type_id).model_class()
                entries.append(
                    {
                        "collapsed": True,
                        "versions": list(run),
                        "count": len(run),
                        "verb": "Created" if run[0].changes.old is None else "Changed",
                        "name": model._meta.verbose_name_plural,
                    }
                )
            else:
                entries.extend({"collapsed": False, "version": v} for v in run)
            run.clear()

        for version in versions:
            plain = (
                ContentType.objects.get_for_id(version.content_type_id).model not in self.collapsible_models
                or version.action
            )
            if plain or (run and not self.same_kind(run[0], version)):
                flush()
            if plain:
                entries.append({"collapsed": False, "version": version})
            else:
                run.append(version)
        flush()
        return entries

    @staticmethod
    def same_kind(first, other):
        return first.content_type_id == other.content_type_id and (first.changes.old is None) == (
            other.changes.old is None
        )

    def build_feed(self):
        versions = list(self.get_queryset())
        groups = self.build_groups(versions)
        consumed = [version for group in groups for version in group["versions"]]
        prepare_versions(consumed, self.request.user)
        for group in groups:
            group["entries"] = self.collapse_runs(self.merge_edits(group["versions"]))
        more = len(consumed) < len(versions)
        return {
            "groups": groups,
            "next_before": consumed[-1].revision.date_created.isoformat() if more else None,
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Activity Feed"
        context["feed_version"] = activity_feed_version()
        context["feed_audience"] = feed_audience(self.request.user)
        context["feed_before"] = self.before.isoformat() if self.before else ""
        context["build_feed"] = self.build_feed
        return context
