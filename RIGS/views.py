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

from PyRIGS.views import GenericListView

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


"""
Called from a modal window (e.g. when an item is submitted to an event/invoice).
May optionally also include some javascript in a success message to cause a load of
the new information onto the page.
"""


class CloseModal(generic.TemplateView):
    template_name = 'closemodal.html'

    def get_context_data(self, **kwargs):
        return {'messages': messages.get_messages(self.request)}


class PersonList(GenericListView):
    template_name = 'person_list.html'
    model = models.Person


class PersonDetail(generic.DetailView):
    template_name = 'person_detail.html'
    model = models.Person


class PersonCreate(generic.CreateView):
    template_name = 'person_form.html'
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
    template_name = 'person_form.html'
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


class OrganisationList(GenericListView):
    template_name = 'organisation_list.html'
    model = models.Organisation


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


class VenueList(GenericListView):
    template_name = "venue_list.html"
    model = models.Venue


class VenueDetail(generic.DetailView):
    template_name = 'venue_detail.html'
    model = models.Venue


class VenueCreate(generic.CreateView):
    template_name = 'venue_form.html'
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
