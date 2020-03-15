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

"""
Displays the current rig count along with a few other bits and pieces
"""


class Index(generic.TemplateView):
    template_name = 'index.html'

    def get_context_data(self, **kwargs):
        context = super(Index, self).get_context_data(**kwargs)
        context['rig_count'] = models.Event.objects.rig_count()
        return context


class SearchHelp(generic.TemplateView):
    template_name = 'search_help.html'


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


"""
Called from a modal window (e.g. when an item is submitted to an event/invoice).
May optionally also include some javascript in a success message to cause a load of
the new information onto the page.
"""


class CloseModal(generic.TemplateView):
    template_name = 'closemodal.html'

    def get_context_data(self, **kwargs):
        return {'messages': messages.get_messages(self.request)}


class PersonList(generic.ListView):
    template_name = 'person_list.html'
    model = models.Person
    paginate_by = 20

    def get_queryset(self):
        q = self.request.GET.get('query', "")

        filter = Q(name__icontains=q) | Q(email__icontains=q) | Q(address__icontains=q) | Q(notes__icontains=q) | Q(phone__startswith=q) | Q(phone__endswith=q)

        # try and parse an int
        try:
            val = int(q)
            filter = filter | Q(pk=val)
        except:  # noqa
            # not an integer
            pass

        object_list = self.model.objects.filter(filter)

        orderBy = self.request.GET.get('orderBy', 'name')
        if orderBy is not None:
            object_list = object_list.order_by(orderBy)
        return object_list


class PersonDetail(generic.DetailView):
    template_name = 'person_detail.html'
    model = models.Person


class PersonCreate(generic.CreateView):
    model = models.Person
    fields = ['name', 'phone', 'email', 'address', 'notes']

    def get_success_url(self):
        if self.request.is_ajax():
            url = reverse_lazy('closemodal')
            update_url = str(reverse_lazy('person_update', kwargs={'pk': self.object.pk}))
            messages.info(self.request, "modalobject=" + serializers.serialize("json", [self.object]))
            messages.info(self.request, "modalobject[0]['update_url']='" + update_url + "'")
        else:
            url = reverse_lazy('person_detail', kwargs={
                'pk': self.object.pk,
            })
        return url


class PersonUpdate(generic.UpdateView):
    model = models.Person
    fields = ['name', 'phone', 'email', 'address', 'notes']

    def get_success_url(self):
        if self.request.is_ajax():
            url = reverse_lazy('closemodal')
            update_url = str(reverse_lazy('person_update', kwargs={'pk': self.object.pk}))
            messages.info(self.request, "modalobject=" + serializers.serialize("json", [self.object]))
            messages.info(self.request, "modalobject[0]['update_url']='" + update_url + "'")
        else:
            url = reverse_lazy('person_detail', kwargs={
                'pk': self.object.pk,
            })
        return url


class OrganisationList(generic.ListView):
    template_name='organisation_list.html'
    model = models.Organisation
    paginate_by = 20

    def get_queryset(self):
        q = self.request.GET.get('query', "")

        filter = Q(name__icontains=q) | Q(email__icontains=q) | Q(address__icontains=q) | Q(notes__icontains=q) | Q(phone__startswith=q) | Q(phone__endswith=q)

        # try and parse an int
        try:
            val = int(q)
            filter = filter | Q(pk=val)
        except:  # noqa
            # not an integer
            pass

        object_list = self.model.objects.filter(filter)

        orderBy = self.request.GET.get('orderBy', "name")
        if orderBy is not "":
            object_list = object_list.order_by(orderBy)
        return object_list


class OrganisationDetail(generic.DetailView):
    template_name = 'organisation_detail.html'
    model = models.Organisation


class OrganisationCreate(generic.CreateView):
    template_name = 'organisation_form.html'
    model = models.Organisation
    fields = ['name', 'phone', 'email', 'address', 'notes', 'union_account']

    def get_success_url(self):
        if self.request.is_ajax():
            url = reverse_lazy('closemodal')
            update_url = str(reverse_lazy('organisation_update', kwargs={'pk': self.object.pk}))
            messages.info(self.request, "modalobject=" + serializers.serialize("json", [self.object]))
            messages.info(self.request, "modalobject[0]['update_url']='" + update_url + "'")
        else:
            url = reverse_lazy('organisation_detail', kwargs={
                'pk': self.object.pk,
            })
        return url


class OrganisationUpdate(generic.UpdateView):
    template_name = 'organisation_form.html'
    model = models.Organisation
    fields = ['name', 'phone', 'email', 'address', 'notes', 'union_account']

    def get_success_url(self):
        if self.request.is_ajax():
            url = reverse_lazy('closemodal')
            update_url = str(reverse_lazy('organisation_update', kwargs={'pk': self.object.pk}))
            messages.info(self.request, "modalobject=" + serializers.serialize("json", [self.object]))
            messages.info(self.request, "modalobject[0]['update_url']='" + update_url + "'")
        else:
            url = reverse_lazy('organisation_detail', kwargs={
                'pk': self.object.pk,
            })
        return url


class VenueList(generic.ListView):
    template_name = "venue_list.html"
    model = models.Venue
    paginate_by = 20

    def get_queryset(self):
        q = self.request.GET.get('query', "")

        filter = Q(name__icontains=q) | Q(email__icontains=q) | Q(address__icontains=q) | Q(notes__icontains=q) | Q(phone__startswith=q) | Q(phone__endswith=q)

        # try and parse an int
        try:
            val = int(q)
            filter = filter | Q(pk=val)
        except:  # noqa
            # not an integer
            pass

        object_list = self.model.objects.filter(filter)

        orderBy = self.request.GET.get('orderBy', "name")
        if orderBy is not "":
            object_list = object_list.order_by(orderBy)
        return object_list


class VenueDetail(generic.DetailView):
    model = models.Venue


class VenueCreate(generic.CreateView):
    model = models.Venue
    fields = ['name', 'phone', 'email', 'address', 'notes', 'three_phase_available']

    def get_success_url(self):
        if self.request.is_ajax():
            url = reverse_lazy('closemodal')
            update_url = str(reverse_lazy('venue_update', kwargs={'pk': self.object.pk}))
            messages.info(self.request, "modalobject=" + serializers.serialize("json", [self.object]))
            messages.info(self.request, "modalobject[0]['update_url']='" + update_url + "'")
        else:
            url = reverse_lazy('venue_detail', kwargs={
                'pk': self.object.pk,
            })
        return url


class VenueUpdate(generic.UpdateView):
    model = models.Venue
    fields = ['name', 'phone', 'email', 'address', 'notes', 'three_phase_available']

    def get_success_url(self):
        if self.request.is_ajax():
            url = reverse_lazy('closemodal')
            update_url = str(reverse_lazy('venue_update', kwargs={'pk': self.object.pk}))
            messages.info(self.request, "modalobject=" + serializers.serialize("json", [self.object]))
            messages.info(self.request, "modalobject[0]['update_url']='" + update_url + "'")
        else:
            url = reverse_lazy('venue_detail', kwargs={
                'pk': self.object.pk,
            })
        return url


class SecureAPIRequest(generic.View):
    models = {
        'venue': models.Venue,
        'person': models.Person,
        'organisation': models.Organisation,
        'profile': models.Profile,
        'event': models.Event,
        'supplier': asset_models.Supplier
    }

    perms = {
        'venue': 'RIGS.view_venue',
        'person': 'RIGS.view_person',
        'organisation': 'RIGS.view_organisation',
        'profile': 'RIGS.view_profile',
        'event': None,
        'supplier': None
    }

    '''
    Validate the request is allowed based on user permissions.
    Raises 403 if denied.
    Potential to add API key validation at a later date.
    '''

    def __validate__(self, request, key, perm):
        if request.user.is_active:
            if request.user.is_superuser or perm is None:
                return True
            elif request.user.has_perm(perm):
                return True
        raise PermissionDenied()

    def get(self, request, model, pk=None, param=None):
        # Request permission validation things
        key = request.GET.get('apikey', None)
        perm = self.perms[model]
        self.__validate__(request, key, perm)

        # Response format where applicable
        format = request.GET.get('format', 'json')
        fields = request.GET.get('fields', None)
        if fields:
            fields = fields.split(",")

        # Supply data for one record
        if pk:
            object = get_object_or_404(self.models[model], pk=pk)
            data = serializers.serialize(format, [object], fields=fields)
            return HttpResponse(data, content_type="application/" + format)

        # Supply data for autocomplete ajax request in json form
        term = request.GET.get('term', None)
        if term:
            if fields is None:  # Default to just name
                fields = ['name']

            # Build a list of Q objects for use later
            queries = []
            for part in term.split(" "):
                qs = []
                for field in fields:
                    q = Q(**{field + "__icontains": part})
                    qs.append(q)
                queries.append(reduce(operator.or_, qs))

            # Build the data response list
            results = []
            query = reduce(operator.and_, queries)
            objects = self.models[model].objects.filter(query)
            for o in objects:
                data = {
                    'pk': o.pk,
                    'value': o.pk,
                    'label': o.name,
                }
                try:  # See if there is a valid update URL
                    data['update'] = reverse("%s_update" % model, kwargs={'pk': o.pk})
                except NoReverseMatch:
                    pass
                results.append(data)

            # return a data response
            json = simplejson.dumps(results)
            return HttpResponse(json, content_type="application/json")  # Always json

        start = request.GET.get('start', None)
        end = request.GET.get('end', None)

        if model == "event" and start and end:
            # Probably a calendar request
            start_datetime = datetime.datetime.strptime(start, "%Y-%m-%dT%H:%M:%S")
            end_datetime = datetime.datetime.strptime(end, "%Y-%m-%dT%H:%M:%S")

            objects = self.models[model].objects.events_in_bounds(start_datetime, end_datetime)

            results = []
            for item in objects:
                data = {
                    'pk': item.pk,
                    'title': item.name,
                    'is_rig': item.is_rig,
                    'status': str(item.get_status_display()),
                    'earliest': item.earliest_time.isoformat(),
                    'latest': item.latest_time.isoformat(),
                    'url': str(item.get_absolute_url())
                }

                results.append(data)
            json = simplejson.dumps(results)
            return HttpResponse(json, content_type="application/json")  # Always json

        return HttpResponse(model)


class ProfileDetail(generic.DetailView):
    template_name="profile_detail.html"
    model = models.Profile

    def get_queryset(self):
        try:
            pk = self.kwargs['pk']
        except KeyError:
            pk = self.request.user.id
            self.kwargs['pk'] = pk

        return self.model.objects.filter(pk=pk)


class ProfileUpdateSelf(generic.UpdateView):
    template_name="profile_form.html"
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
