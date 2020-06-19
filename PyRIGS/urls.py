from django.urls import path
from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.views.decorators.clickjacking import xframe_options_exempt
from django.contrib.auth.views import LoginView
from registration.backends.default.views import RegistrationView
from PyRIGS.decorators import permission_required_with_403
import RIGS
import users
from PyRIGS import views

urlpatterns = [
    path('', include('users.urls')),
    path('', include('RIGS.urls')),
    path('assets/', include('assets.urls')),

    # API
    path('api/<str:model>/', login_required(views.SecureAPIRequest.as_view()),
         name="api_secure"),
    path('api/<str:model>/<int:pk>/', login_required(views.SecureAPIRequest.as_view()),
         name="api_secure"),

    path('closemodal/', views.CloseModal.as_view(), name='closemodal'),
    path('search_help/', views.SearchHelp.as_view(), name='search_help'),

    path('admin/', admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()

    import debug_toolbar
    urlpatterns = [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
