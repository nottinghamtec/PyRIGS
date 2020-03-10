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
from RIGS import regbackend, forms, views

urlpatterns = [
    path('', include('RIGS.urls')),
    path('assets/', include('assets.urls')),

    path('user/register/', RegistrationView.as_view(form_class=forms.ProfileRegistrationFormUniqueEmail),
        name="registration_register"),
    path('user/login/', LoginView.as_view(authentication_form=forms.CheckApprovedForm), name='login'),
    path('user/login/embed/', xframe_options_exempt(views.LoginEmbed.as_view()), name='login_embed'),
    # User editing
    path('user/', login_required(views.ProfileDetail.as_view()), name='profile_detail'),
    path('user/<pk>/',
        permission_required_with_403('RIGS.view_profile')(views.ProfileDetail.as_view()),
        name='profile_detail'),
    path('user/edit/', login_required(views.ProfileUpdateSelf.as_view()),
        name='profile_update_self'),
    path('user/reset_api_key', login_required(views.ResetApiKey.as_view(permanent=False)),
        name='reset_api_key'),
    path('user/', include('django.contrib.auth.urls')),
    path('user/', include('registration.backends.default.urls')),

    path('admin/', admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()

    import debug_toolbar
    urlpatterns = [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
