import datetime

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import title
from django.views import generic
from reversion import revisions as reversion

from versioning.versioning import RIGSVersion, activity_feed_version


class VersionHistory(generic.ListView):
    model = RIGSVersion
    template_name = "version_history.html"
    paginate_by = 25

    def get_queryset(self, **kwargs):
        return (
            RIGSVersion.objects.get_for_object(self.get_object())
            .select_related("revision", "revision__user")
            .all()
            .order_by("-revision__date_created")
        )

    def get_object(self, **kwargs):
        # Goddamit, almost got away without specific hacks
        if self.kwargs["model"].__name__ == "Asset":
            return get_object_or_404(self.kwargs["model"], asset_id=self.kwargs["pk"])
        else:
            return get_object_or_404(self.kwargs["model"], pk=self.kwargs["pk"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object"] = self.get_object()
        if self.kwargs["app"] != "rigboard":
            context["override"] = f"base_{self.kwargs['app']}.html"

        return context


def get_models(app=None):
    models = filter(lambda item: not hasattr(item, "reversion_hide"), reversion.get_registered_models())
    if app is not None:
        models = filter(lambda item: item in apps.get_app_config(app).get_models(), models)
    # Don't allow modifying original list!
    return list(models).copy()


# TODO Default filter of having permission to view associated object
def filter_models(models, user):
    if user is not None:
        models = filter(
            lambda model: not hasattr(model, "reversion_perm") or user.has_perm(model.reversion_perm), models
        )
    return models


class ActivityTable(generic.ListView):
    model = RIGSVersion
    template_name = "activity_table.html"
    paginate_by = 25

    def get_queryset(self):
        return RIGSVersion.objects.get_for_multiple_models(
            filter_models(self.kwargs.get("models"), self.request.user)
        ).order_by("-revision__date_created")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = f"{title(self.kwargs['app'])} Activity Stream"
        if self.kwargs["app"] != "rigboard":
            context["override"] = f"base_{self.kwargs['app']}.html"

        return context


class ActivityFeed(generic.ListView):  # Appears on homepage
    model = RIGSVersion
    template_name = "activity_feed_data.html"
    group_limit = 12
    version_limit = 500
    collapse_threshold = 3
    collapsible_models = ("trainingitemqualification", "invoice")

    def get_queryset(self):
        return RIGSVersion.objects.get_for_multiple_models(filter_models(get_models(), self.request.user)).order_by(
            "-revision__date_created"
        )[: self.version_limit]

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
                or version.converted_enquiry_name
                or version.deleted_enquiry_name is not None
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Activity Feed"
        context["feed_version"] = activity_feed_version()
        groups = self.build_groups(context["object_list"])
        for group in groups:
            group["entries"] = self.collapse_runs(group["versions"])
        context["groups"] = groups
        return context
