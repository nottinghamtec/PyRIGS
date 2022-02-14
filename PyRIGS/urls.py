from django.conf import settings
from django.conf.urls import include
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import path
from django.views.generic import TemplateView

from PyRIGS import views

urlpatterns = [
    path('', include('versioning.urls')),
    path('', include('RIGS.urls')),
    path('assets/', include('assets.urls')),
    path('training/', include('training.urls')),

    path('', login_required(views.Index.as_view()), name='index'),

    # API
    path('api/<str:model>/', login_required(views.SecureAPIRequest.as_view()),
         name="api_secure"),
    path('api/<str:model>/<int:pk>/', login_required(views.SecureAPIRequest.as_view()),
         name="api_secure"),

    path('closemodal/', views.CloseModal.as_view(), name='closemodal'),
    path('search/', login_required(views.Search.as_view()), name='search'),
    path('search_help/', login_required(views.SearchHelp.as_view()), name='search_help'),

    path('', include('users.urls')),

    path('admin/', include('massadmin.urls')),
    path('admin/', admin.site.urls),
    path("robots.txt", TemplateView.as_view(template_name="robots.txt", content_type="text/plain")),
]

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()

    import debug_toolbar
    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
        path('bootstrap/', TemplateView.as_view(template_name="bootstrap.html")),
    ]
