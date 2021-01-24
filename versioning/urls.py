from django.conf.urls import url
from django.contrib.auth.decorators import login_required
from django.urls import path
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.generic import RedirectView
from PyRIGS.decorators import (api_key_required, has_oembed,
                               permission_required_with_403)
from RIGS import finance, ical, models, rigboard, views, hs
from versioning import views
from django.apps import apps

urlpatterns = [
    path('rigboard/activity/feed/',
         permission_required_with_403('RIGS.view_event')(views.ActivityFeed.as_view()),
         name='activity_feed'),
]

# Well except this specific hack for legacy URLs...if only the RIGS app had been named 'rigboard'!
for app in apps.get_app_configs():
    appname = str(app.label)

    if appname == 'RIGS':
        appname = 'rigboard'
        table_name = 'activity_table'
    else:
        table_name = appname + '_activity_table'

    # TODO Proper Permissions
    urlpatterns += [path(appname + '/activity/', permission_required_with_403('RIGS.add_event')(views.ActivityTable.as_view()),
                         name=table_name, kwargs={'app': appname, 'models': views.get_models(app.label)}), ]

    for model in views.get_models(app=app.label):
        modelname = model.__name__.lower()
        if appname == 'rigboard':
            urlpatterns += [
                path('{}/<str:pk>/history/'.format(modelname), permission_required_with_403('{}.change_{}'.format(app.label, modelname))(views.VersionHistory.as_view()),
                     name='{}_history'.format(modelname), kwargs={'model': model, 'app': appname, }),
            ]
        else:
            urlpatterns += [
                path('{}/{}/<str:pk>/history/'.format(appname, modelname), permission_required_with_403('{}.change_{}'.format(app.label, modelname))(views.VersionHistory.as_view()),
                     name='{}_history'.format(modelname), kwargs={'model': model, 'app': appname, }),
            ]
