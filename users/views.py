from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.views import generic
from django.views.decorators.csrf import csrf_exempt

from RIGS import models


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

    def get_context_data(self, **kwargs):
        context = super(ProfileDetail, self).get_context_data(**kwargs)
        context['page_title'] = f"Profile: {self.object}"
        context["completed_levels"] = self.object.level_qualifications.all().select_related('level')
        return context


class ProfileUpdateSelf(generic.UpdateView):
    template_name = "profile_form.html"
    model = models.Profile
    fields = ['first_name', 'last_name', 'email', 'initials', 'phone', 'dark_theme']

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
