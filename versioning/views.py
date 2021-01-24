import datetime
import logging

from diff_match_patch import diff_match_patch
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import EmailField, IntegerField, TextField
from django.shortcuts import get_object_or_404
from django.utils.functional import cached_property
from django.views import generic
from reversion.models import Version, VersionQuerySet
from RIGS import models
from assets import models as asset_models
from django.apps import apps
from reversion import revisions as reversion
from versioning.versioning import RIGSVersion
from django.template.defaultfilters import title

from django.views.decorators.cache import never_cache, cache_page
from django.utils.decorators import method_decorator


class VersionHistory(generic.ListView):
    model = RIGSVersion
    template_name = "version_history.html"
    paginate_by = 25

    def get_queryset(self, **kwargs):
        return RIGSVersion.objects.get_for_object(self.get_object()).select_related("revision",
                                                                                    "revision__user").all().order_by(
            "-revision__date_created")

    def get_object(self, **kwargs):
        # Goddamit, almost got away without specific hacks
        if self.kwargs['model'].__name__ == 'Asset':
            return get_object_or_404(self.kwargs['model'], asset_id=self.kwargs['pk'])
        else:
            return get_object_or_404(self.kwargs['model'], pk=self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        context = super(VersionHistory, self).get_context_data(**kwargs)
        context['object'] = self.get_object()
        if self.kwargs['app'] != 'rigboard':
            context['override'] = 'base_{}.html'.format(self.kwargs['app'])

        return context


def get_models(app=None):
    models = filter(lambda item: not hasattr(item, 'reversion_hide'), reversion.get_registered_models())
    if app is not None:
        models = filter(lambda item: item in apps.get_app_config(app).get_models(), models)
    # Don't allow modifying original list!
    return list(models).copy()


# TODO Default filter of having permission to view associated object
def filter_models(models, user):
    if user is not None:
        models = filter(lambda model: not hasattr(model, 'reversion_perm') or user.has_perm(model.reversion_perm), models)
    return models


class ActivityTable(generic.ListView):
    model = RIGSVersion
    template_name = "activity_table.html"
    paginate_by = 25

    def get_queryset(self):
        return RIGSVersion.objects.get_for_multiple_models(filter_models(self.kwargs.get('models'), self.request.user)).order_by("-revision__date_created")

    def get_context_data(self, **kwargs):
        context = super(ActivityTable, self).get_context_data(**kwargs)
        context['page_title'] = "{} Activity Stream".format(title(self.kwargs['app']))
        if self.kwargs['app'] != 'rigboard':
            context['override'] = 'base_{}.html'.format(self.kwargs['app'])

        return context


class ActivityFeed(generic.ListView):  # Appears on homepage
    model = RIGSVersion
    template_name = "activity_feed_data.html"
    paginate_by = 25

    def get_queryset(self):
        return RIGSVersion.objects.get_for_multiple_models(filter_models(get_models(), self.request.user)).order_by("-revision__date_created")

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
