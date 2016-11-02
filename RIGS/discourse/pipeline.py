from django.core.urlresolvers import reverse
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.shortcuts import render_to_response
from django.core.exceptions import ValidationError

from social.pipeline.partial import partial

from RIGS.models import Profile
from RIGS import forms


class SocialRegisterForm(forms.ProfileRegistrationFormUniqueEmail):
    def __init__(self, *args, **kwargs):
        super(SocialRegisterForm, self).__init__(*args, **kwargs)
        self.fields.pop('password1')
        self.fields.pop('password2')
        self.fields.pop('captcha')

        self.fields['email'].widget.attrs['readonly'] = True

    def clean_email(self):
        initial = getattr(self, 'initial', None)
        if(initial['email'] != self.cleaned_data['email']):
            raise ValidationError("You cannot change the email")

        return initial['email']


@partial
def new_connection(backend, details, response, user=None, is_new=False, social=None, request=None, *args, **kwargs):
    if social is not None:
        return

    data = backend.strategy.request_data()

    if data.get('UseCurrentAccount') is not None:
        return

    alreadyLoggedIn = user is not None

    context = {
        'details': details,
        'alreadyLoggedIn': alreadyLoggedIn,
        'loggedInUser': user,
    }

    if not alreadyLoggedIn:
        completeUrl = reverse('social:complete', kwargs={'backend': backend.name})
        context['login_url'] = "{0}?{1}={2}".format(reverse('login'), REDIRECT_FIELD_NAME, completeUrl)

        if data.get('username') is None:
            form = SocialRegisterForm(initial=details)
        else:
            form = SocialRegisterForm(data, initial=details)

        if form.is_valid():
            new_user = Profile.objects.create_user(**form.cleaned_data)
            return {'user': new_user}

        context['form'] = form

    return render_to_response('RIGS/social-associate.html', context)
