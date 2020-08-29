from django.conf.urls import url
from django.contrib.auth.decorators import login_required
from django.urls import path
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.generic import RedirectView
from PyRIGS.decorators import (api_key_required, has_oembed,
                               permission_required_with_403)
from RIGS import finance, ical, models, rigboard, views, hs
from versioning import views
from django.views.decorators.cache import cache_page
from django.apps import apps

urlpatterns = [
    path('rigboard/activity/feed/',
         cache_page(60 * 10)(permission_required_with_403('RIGS.view_event')(views.ActivityFeed.as_view())),
         name='activity_feed'),
]

for app in apps.get_app_configs():
    appname = str(app.label)
    # Well except this specific hack for legacy URLs...if only the RIGS app had been named 'rigboard'!
    if appname == 'RIGS':
        appname = 'rigboard'
        urlpatterns += [path(appname + '/activity/', permission_required_with_403('RIGS.view_event')(views.ActivityTable.as_view()),
                name='activity_table', kwargs={'app': appname, 'models': views.get_models(app.label)}),]
    else:
        urlpatterns += [path(appname + '/activity/', permission_required_with_403('RIGS.view_event')(views.ActivityTable.as_view()),
                name=appname + '_activity_table', kwargs={'app': appname, 'models': views.get_models(app.label)}),]
    for model in views.get_models(app.label):
        modelname = model.__name__.lower()
        urlpatterns += [
            path(appname + '/' + modelname + '/<str:pk>/history/', permission_required_with_403('{}.change_{}'.format(app.label, modelname))(views.VersionHistory.as_view()),
                    name='{}_history'.format(modelname), kwargs={'model': model, 'app': appname,}),
        ]
