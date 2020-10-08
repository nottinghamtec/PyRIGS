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

from PyRIGS.views import GenericListView, GenericDetailView


class PersonList(GenericListView):
    model = models.Person

    def get_context_data(self, **kwargs):
        context = super(PersonList, self).get_context_data(**kwargs)
        context['page_title'] = "People"
        context['create'] = 'person_create'
        context['edit'] = 'person_update'
        context['detail'] = 'person_detail'
        return context


class PersonDetail(GenericDetailView):
    model = models.Person

    def get_context_data(self, **kwargs):
        context = super(PersonDetail, self).get_context_data(**kwargs)
        context['history_link'] = 'person_history'
        context['detail_link'] = 'person_detail'
        context['update_link'] = 'person_update'
        context['associated'] = 'partials/associated_organisations.html'
        context['associated2'] = 'partials/associated_events.html'
        return context


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
    model = models.Organisation

    def get_context_data(self, **kwargs):
        context = super(OrganisationList, self).get_context_data(**kwargs)
        context['create'] = 'organisation_create'
        context['edit'] = 'organisation_update'
        context['detail'] = 'organisation_detail'
        context['union_account'] = True
        return context


class OrganisationDetail(GenericDetailView):
    model = models.Organisation

    def get_context_data(self, **kwargs):
        context = super(OrganisationDetail, self).get_context_data(**kwargs)
        context['history_link'] = 'organisation_history'
        context['detail_link'] = 'organisation_detail'
        context['update_link'] = 'organisation_update'
        context['associated'] = 'partials/associated_people.html'
        context['associated2'] = 'partials/associated_events.html'
        return context


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
    model = models.Venue

    def get_context_data(self, **kwargs):
        context = super(VenueList, self).get_context_data(**kwargs)
        context['create'] = 'venue_create'
        context['edit'] = 'venue_update'
        context['detail'] = 'venue_detail'
        return context


class VenueDetail(GenericDetailView):
    model = models.Venue

    def get_context_data(self, **kwargs):
        context = super(VenueDetail, self).get_context_data(**kwargs)
        context['history_link'] = 'venue_history'
        context['detail_link'] = 'venue_detail'
        context['update_link'] = 'venue_update'
        context['associated2'] = 'partials/associated_events.html'
        return context


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
