from django.apps import apps
from django.urls import path

from PyRIGS.decorators import permission_required_with_403
from versioning import views

urlpatterns = [
    path(
        "rigboard/activity/feed/",
        permission_required_with_403("RIGS.view_event")(views.ActivityFeed.as_view()),
        name="activity_feed",
    ),
    path(
        "activity/",
        permission_required_with_403("RIGS.view_event")(views.ActivityTable.as_view()),
        name="activity_all",
        kwargs={"app": "rigboard", "heading": "All", "models": views.get_models()},
    ),
    path(
        "event/<int:pk>/history/since-authorised/",
        permission_required_with_403("RIGS.change_event")(views.EventSinceAuthorised.as_view()),
        name="event_since_authorised",
    ),
]

for app in [apps.get_app_config(label) for label in ("RIGS", "assets", "training")]:
    appname = str(app.label)
    if appname == "RIGS":
        appname = "rigboard"
        table_name = "activity_table"
        prefix = ""
    else:
        table_name = appname + "_activity_table"
        prefix = f"{appname}/"

    urlpatterns += [
        path(
            appname + "/activity/",
            permission_required_with_403("RIGS.add_event")(views.ActivityTable.as_view()),
            name=table_name,
            kwargs={"app": appname, "models": views.get_models(app.label)},
        ),
    ]

    for model in views.get_models(app=app.label):
        modelname = model.__name__.lower()
        permission = permission_required_with_403(f"{app.label}.change_{modelname}")
        kwargs = {"model": model, "app": appname}
        urlpatterns += [
            path(
                f"{prefix}{modelname}/<str:pk>/history/",
                permission(views.VersionHistory.as_view()),
                name=f"{modelname}_history",
                kwargs=kwargs,
            ),
            path(
                f"{prefix}{modelname}/<str:pk>/history/compare/",
                permission(views.VersionCompare.as_view()),
                name=f"{modelname}_compare",
                kwargs=kwargs,
            ),
            path(
                f"{prefix}{modelname}/<str:pk>/history/<int:version_id>/",
                permission(views.VersionDetail.as_view()),
                name=f"{modelname}_version",
                kwargs=kwargs,
            ),
        ]
