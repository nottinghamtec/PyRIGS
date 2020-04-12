from django.core.exceptions import PermissionDenied
from django.http.response import HttpResponseRedirect
from django.http import HttpResponse
from django.urls import reverse_lazy, reverse, NoReverseMatch
from django.views import generic
from django.contrib.auth.views import LoginView
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.core import serializers
from django.conf import settings
import simplejson
from django.contrib import messages
import datetime
import pytz
import operator
from registration.views import RegistrationView
from django.views.decorators.csrf import csrf_exempt


from RIGS import models, forms
from assets import models as asset_models
from functools import reduce

# This view should be exempt from requiring CSRF token.
# Then we can check for it and show a nice error
# Don't worry, django.contrib.auth.views.login will
# check for it before logging  the user in
class LoginEmbed(LoginView):
    template_name = 'registration/login_embed.html'

    @csrf_exempt
    def dispatch(self, request, *args, **kwargs):
        if request.method == "POST":
            csrf_cookie = request.COOKIES.get('csrftoken', None)

            if csrf_cookie is None:
                messages.warning(request, 'Cookies do not seem to be enabled. Try logging in using a new tab.')
                request.method = 'GET'  # Render the page without trying to login

        return super().dispatch(request, *args, **kwargs)


class ProfileDetail(generic.DetailView):
    template_name = "profile_detail.html"
    model = models.Profile

    def get_queryset(self):
        try:
            pk = self.kwargs['pk']
        except KeyError:
            pk = self.request.user.id
            self.kwargs['pk'] = pk

        return self.model.objects.filter(pk=pk)


class ProfileUpdateSelf(generic.UpdateView):
    template_name = "profile_form.html"
    model = models.Profile
    fields = ['first_name', 'last_name', 'email', 'initials', 'phone']

    def get_queryset(self):
        pk = self.request.user.id
        self.kwargs['pk'] = pk

        return self.model.objects.filter(pk=pk)

    def get_success_url(self):
        url = reverse_lazy('profile_detail')
        return url


class ResetApiKey(generic.RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        self.request.user.api_key = self.request.user.make_api_key()

        self.request.user.save()

        return reverse_lazy('profile_detail')
