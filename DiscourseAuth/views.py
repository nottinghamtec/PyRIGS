
from django.views.generic import View, FormView, TemplateView

from django.http import HttpResponseRedirect
from django.contrib.auth import login
from django.contrib.auth.backends import ModelBackend
from django.core.urlresolvers import reverse

from django.core.exceptions import PermissionDenied

from django.contrib.auth import get_user_model
import urllib
from hashlib import sha256
import hmac
from base64 import b64decode, b64encode
from django.db.models import Q

from django.conf import settings

from django.core.exceptions import ValidationError

from django.contrib import messages

from models import AuthAttempt, DiscourseUserLink


import time
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from registration.forms import RegistrationForm


class StartDiscourseAuth(View):
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        # Where do we want to go once authentication is complete?
        request.session['discourse_next'] = request.GET.get('next', "/")

        # Generate random 'nonce'
        attempt = AuthAttempt.objects.create()
        nonce = attempt.nonce

        # Where do we want discourse to send authenticated users?
        redirect_uri = reverse('continue-auth')
        redirect_uri = request.build_absolute_uri(redirect_uri)

        # Data to sent to Discourse (payload)
        data = {
            'nonce': nonce,
            'return_sso_url': redirect_uri
        }

        payload = urllib.urlencode(data)
        b64payload = b64encode(payload.encode())

        sig = hmac.new(settings.DISCOURSE_SECRET_KEY.encode(), b64payload, sha256).hexdigest()

        return HttpResponseRedirect(settings.DISCOURSE_BASE_URL + '/session/sso_provider?' + urllib.urlencode({'sso': b64payload, 'sig': sig}))


class ContinueDiscourseAuth(View):
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        # Where do we want to go once authentication is complete?
        nextUrl = request.session.get('discourse_next', "/")

        rawSig = request.GET['sig']
        rawSSO = request.GET['sso']

        payload = urllib.unquote(rawSSO)

        computed_sig = hmac.new(
            settings.DISCOURSE_SECRET_KEY.encode(),
            payload.encode(),
            sha256
        ).hexdigest()

        successful = hmac.compare_digest(computed_sig, rawSig.encode())

        if not successful:  # The signature doesn't match, not legit
            raise ValidationError("Signature does not match, data has been manipulated")

        decodedPayload = urllib.unquote_plus(b64decode(urllib.unquote(payload)).decode())
        data = dict(data.split("=") for data in decodedPayload.split('&'))

        # Get the nonce that's been returned by discourse
        returnedNonce = data['nonce']

        try:  # See if it's in the database
            storedAttempt = AuthAttempt.objects.get_acceptable().get(nonce=returnedNonce)
        except AuthAttempt.DoesNotExist:  # If it's not, this attempt is not valid
            raise ValidationError("Nonce does not exist in database")

        # Delete the nonce from the database - don't allow it to be reused
        storedAttempt.delete()
        # While we're at it, delete all the other expired attempts
        AuthAttempt.objects.purge_unacceptable()

        # If we've got this far, the attempt is valid, so let's load user information
        external_id = int(data['external_id'])

        # See if the user is already linked to a django user
        try:
            userLink = DiscourseUserLink.objects.get(discourse_user_id=external_id)
        except DiscourseUserLink.DoesNotExist:
            return self.linkNewUser(request, data)

        # Load the user
        user = userLink.django_user
        # Slightly hacky way to login user without calling authenticate()
        user.backend = "%s.%s" % (ModelBackend.__module__, ModelBackend.__name__)
        # Login the user
        login(request, user)

        return HttpResponseRedirect(nextUrl)

    def linkNewUser(self, request, data):
        # Great, let's save the new user info in the session
        request.session['discourse_data'] = data
        request.session['discourse_started_registration'] = time.time()

        if request.user is not None:
            return HttpResponseRedirect(reverse('associate-user'))
        else:
            return HttpResponseRedirect(reverse('new-user'))


class SocialRegisterForm(RegistrationForm):
    def __init__(self, *args, **kwargs):
        super(SocialRegisterForm, self).__init__(*args, **kwargs)
        self.fields.pop('password1')
        self.fields.pop('password2')

        self.fields['email'].widget.attrs['readonly'] = True

    def clean_email(self):
        initial = getattr(self, 'initial', None)
        if(initial['email'] != self.cleaned_data['email']):
            raise ValidationError("You cannot change the email")

        return initial['email']


class AssociateDiscourseUser(TemplateView):
    template_name = "DiscourseAuth/associate_user.html"

    @method_decorator(login_required)  # Require user is logged in for associating their account
    def dispatch(self, request, *args, **kwargs):
        self.data = self.request.session.get('discourse_data', None)
        timeStarted = self.request.session.get('discourse_started_registration', 0)

        max_reg_time = 20 * 60  # Seconds

        if timeStarted < (time.time() - max_reg_time):
            raise PermissionDenied('The Discourse authentication has expired, please try again')

        if self.data is None:
            raise PermissionDenied('Discourse authentication data is not present in this session')

        return super(AssociateDiscourseUser, self).dispatch(request, *args, **kwargs)

    def get(self, request, **kwargs):
        return super(AssociateDiscourseUser, self).get(self, request, **kwargs)

    def get_context_data(self, *args, **kwargs):
        c = super(AssociateDiscourseUser, self).get_context_data()
        c['discourseuser'] = self.data['username']
        c['djangouser'] = self.request.user.username

        return c

    def post(self, request, **kwargs):
        DiscourseUserLink.objects.filter(Q(django_user=request.user) | Q(discourse_user_id=self.data['external_id'])).delete()
        DiscourseUserLink.objects.create(django_user=request.user, discourse_user_id=self.data['external_id'])

        messages.success(self.request, 'Accounts successfully linked, you are now logged in.')

        # Redirect them to the discourse login URL
        nextUrl = "{}?next={}".format(reverse('start-auth'), request.session.get('discourse_next', "/"))
        return HttpResponseRedirect(nextUrl)


class NewDiscourseUser(FormView):
    template_name = 'registration/registration_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.data = self.request.session.get('discourse_data', None)
        timeStarted = self.request.session.get('discourse_started_registration', 0)

        max_reg_time = 20 * 60  # Seconds

        if timeStarted < (time.time() - max_reg_time):
            raise PermissionDenied('The Discourse authentication has expired, please try again')

        if self.data is None:
            raise PermissionDenied('Discourse authentication data is not present in this session')

        return super(NewDiscourseUser, self).dispatch(request, *args, **kwargs)

    def get_initial(self):
        data = self.data
        initialForm = {
            'username': data['username'],
            'email': data['email'],
            'name': data['name']
        }

        return initialForm

    def get_form_class(self):
        if settings.DISCOURSE_REGISTRATION_FORM:
            return settings.DISCOURSE_REGISTRATION_FORM
        else:
            return SocialRegisterForm

    def form_valid(self, form):
        # This method is called when valid form data has been POSTed.
        user = get_user_model().objects.create_user(**form.cleaned_data)

        # Link the user to Discourse account
        DiscourseUserLink.objects.filter(discourse_user_id=self.data['external_id']).delete()
        DiscourseUserLink.objects.create(django_user=user, discourse_user_id=self.data['external_id'])

        messages.success(self.request, 'Account successfully created, you are now logged in.')

        # Redirect them to the discourse login URL
        nextUrl = "{}?next={}".format(reverse('start-auth'), self.request.session.get('discourse_next', "/"))
        return HttpResponseRedirect(nextUrl)


class DisassociateDiscourseUser(TemplateView):
    template_name = "DiscourseAuth/disassociate_user.html"

    @method_decorator(login_required)  # Require user is logged in for associating their account
    def dispatch(self, request, *args, **kwargs):
        return super(DisassociateDiscourseUser, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        c = super(DisassociateDiscourseUser, self).get_context_data()

        links = DiscourseUserLink.objects.filter(django_user=self.request.user)

        c['haslink'] = links.count() > 0

        return c

    def post(self, request, **kwargs):
        DiscourseUserLink.objects.filter(django_user=request.user).delete()

        return self.get(self, request, **kwargs)
