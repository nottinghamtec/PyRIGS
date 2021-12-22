from django.conf.urls import include
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.urls import path
from django.views.decorators.clickjacking import xframe_options_exempt
from registration.backends.default.views import RegistrationView

from PyRIGS.decorators import permission_required_with_403
from users import forms, views

urlpatterns = [
    path('user/register/', RegistrationView.as_view(form_class=forms.ProfileRegistrationFormUniqueEmail),
         name="registration_register"),
    path('user/login/', LoginView.as_view(authentication_form=forms.CheckApprovedForm), name='login'),
    path('user/login/embed/', xframe_options_exempt(views.LoginEmbed.as_view()), name='login_embed'),
    # User editing
    path('user/edit/', login_required(views.ProfileUpdateSelf.as_view()),
         name='profile_update_self'),
    path('user/reset_api_key', login_required(views.ResetApiKey.as_view(permanent=False)),
         name='reset_api_key'),
    path('user/', login_required(views.ProfileDetail.as_view()), name='profile_detail'),
    path('user/<int:pk>/',
         permission_required_with_403('RIGS.view_profile')(views.ProfileDetail.as_view()),
         name='profile_detail'),
    path('user/', include('django.contrib.auth.urls')),
    path('user/', include('registration.backends.default.urls')),
]
