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
        term = request.GET.get('q', None)
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
                    'text': o.name,
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


class GenericListView(generic.ListView):
    paginate_by = 20

    def get_queryset(self):
        q = self.request.GET.get('q', "")

        filter = Q(name__icontains=q) | Q(email__icontains=q) | Q(address__icontains=q) | Q(notes__icontains=q) | Q(
            phone__startswith=q) | Q(phone__endswith=q)

        # try and parse an int
        try:
            val = int(q)
            filter = filter | Q(pk=val)
        except:  # noqa
            # not an integer
            pass

        object_list = self.model.objects.filter(filter)

        orderBy = self.request.GET.get('orderBy', "name")
        if orderBy != "":
            object_list = object_list.order_by(orderBy)
        return object_list


class SearchHelp(generic.TemplateView):
    template_name = 'search_help.html'


"""
Called from a modal window (e.g. when an item is submitted to an event/invoice).
May optionally also include some javascript in a success message to cause a load of
the new information onto the page.
"""


class CloseModal(generic.TemplateView):
    template_name = 'closemodal.html'

    def get_context_data(self, **kwargs):
        return {'messages': messages.get_messages(self.request)}
