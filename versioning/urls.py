from django.urls import path
from django.apps import apps
from django.urls import path
from django.template.loader import get_template
from django.template import TemplateDoesNotExist

from PyRIGS.decorators import (permission_required_with_403)
from versioning import views

urlpatterns = [
    path('rigboard/activity/feed/',
         permission_required_with_403('RIGS.view_event')(views.ActivityFeed.as_view()),
         name='activity_feed'),
]

for app in [apps.get_app_config(label) for label in ("RIGS", "assets", "training")]:
    appname = str(app.label)
    if appname == 'RIGS':
        appname = 'rigboard'
        table_name = 'activity_table'
    else:
        table_name = appname + '_activity_table'

    # TODO Proper Permissions
    urlpatterns += [
        path(appname + '/activity/', permission_required_with_403('RIGS.add_event')(views.ActivityTable.as_view()),
             name=table_name, kwargs={'app': appname, 'models': views.get_models(app.label)}), ]

    for model in views.get_models(app=app.label):
        modelname = model.__name__.lower()
        if appname == 'rigboard':
            urlpatterns += [
                path(f'{modelname}/<str:pk>/history/',
                     permission_required_with_403(f'{app.label}.change_{modelname}')(
                         views.VersionHistory.as_view()),
                     name=f'{modelname}_history', kwargs={'model': model, 'app': appname, }),
            ]
        else:
            urlpatterns += [
                path(f'{appname}/{modelname}/<str:pk>/history/',
                     permission_required_with_403(f'{app.label}.change_{modelname}')(
                         views.VersionHistory.as_view()),
                     name=f'{modelname}_history', kwargs={'model': model, 'app': appname, }),
            ]
