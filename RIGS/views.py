from django.core.exceptions import PermissionDenied
from django.http.response import HttpResponseRedirect
from django.http import HttpResponse
from django.core.urlresolvers import reverse_lazy
from django.views import generic
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.core import serializers
import simplejson
from django.contrib import messages

from RIGS import models

"""
Displays the current rig count along with a few other bits and pieces
"""
class Index(generic.TemplateView):
    template_name = 'RIGS/index.html'

    def get_context_data(self, **kwargs):
        context = super(Index, self).get_context_data(**kwargs)
        context['rig_count'] = models.Event.objects.rig_count()
        return context

def login(request, **kwargs):
    if request.user.is_authenticated():
        next = request.REQUEST.get('next', '/')
        return HttpResponseRedirect(request.REQUEST.get('next', '/'))
    else:
        from django.contrib.auth.views import login

        return login(request)


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
    model = models.Person
    paginate_by = 20

    def get_queryset(self):
        q = self.request.GET.get('q', "")
        if len(q) >= 3:
            object_list = self.model.objects.filter(Q(name__icontains=q) | Q(email__icontains=q))
        else:
            object_list = self.model.objects.all()
        orderBy = self.request.GET.get('orderBy', None)
        if orderBy is not None:
            object_list = object_list.order_by(orderBy)
        return object_list


class PersonDetail(generic.DetailView):
    model = models.Person


class PersonCreate(generic.CreateView):
    model = models.Person

    def get_success_url(self):
        if self.request.is_ajax():
            url = reverse_lazy('closemodal')
            messages.info(self.request, "modalobject="+serializers.serialize("json", [self.object]))
        else:
            url =  reverse_lazy('person_detail', kwargs={
                'pk': self.object.pk,
            })
        return url


class PersonUpdate(generic.UpdateView):
    model = models.Person

    def get_success_url(self):
        if self.request.is_ajax():
            url = reverse_lazy('closemodal')
            messages.info(self.request, "modalobject="+serializers.serialize("json", [self.object]))
        else:
            url =  reverse_lazy('person_detail', kwargs={
                'pk': self.object.pk,
            })
        return url


class OrganisationList(generic.ListView):
    model = models.Organisation
    paginate_by = 20

    def get_queryset(self):
        q = self.request.GET.get('q', "")
        if len(q) >= 3:
            object_list = self.model.objects.filter(Q(name__icontains=q) | Q(address__icontains=q))
        else:
            object_list = self.model.objects.all()
        orderBy = self.request.GET.get('orderBy', "")
        if orderBy is not "":
            object_list = object_list.order_by(orderBy)
        return object_list


class OrganisationDetail(generic.DetailView):
    model = models.Organisation


class OrganisationCreate(generic.CreateView):
    model = models.Organisation

    def get_success_url(self):
        if self.request.is_ajax():
            url = reverse_lazy('closemodal')
            messages.info(self.request, "modalobject="+serializers.serialize("json", [self.object]))
        else:
            url =  reverse_lazy('organisation_detail', kwargs={
                'pk': self.object.pk,
            })
        return url


class OrganisationUpdate(generic.UpdateView):
    model = models.Organisation

    def get_success_url(self):
        if self.request.is_ajax():
            url = reverse_lazy('closemodal')
            messages.info(self.request, "modalobject="+serializers.serialize("json", [self.object]))
        else:
            url =  reverse_lazy('organisation_detail', kwargs={
                'pk': self.object.pk,
            })
        return url


class VenueList(generic.ListView):
    model = models.Venue
    paginate_by = 20

    def get_queryset(self):
        q = self.request.GET.get('q', "")
        if len(q) >= 3:
            object_list = self.model.objects.filter(Q(name__icontains=q) | Q(address__icontains=q))
        else:
            object_list = self.model.objects.all()
        orderBy = self.request.GET.get('orderBy', "")
        if orderBy is not "":
            object_list = object_list.order_by(orderBy)
        return object_list


class VenueDetail(generic.DetailView):
    model = models.Venue


class VenueCreate(generic.CreateView):
    model = models.Venue

    def get_success_url(self):
        if self.request.is_ajax():
            url = reverse_lazy('closemodal')
            messages.info(self.request, "modalobject="+serializers.serialize("json", [self.object]))
        else:
            url =  reverse_lazy('venue_detail', kwargs={
                'pk': self.object.pk,
            })
        return url


class VenueUpdate(generic.UpdateView):
    model = models.Venue

    def get_success_url(self):
        if self.request.is_ajax():
            url = reverse_lazy('closemodal')
            messages.info(self.request, "modalobject="+serializers.serialize("json", [self.object]))
        else:
            url =  reverse_lazy('venue_detail', kwargs={
                'pk': self.object.pk,
            })
        return url


class SecureAPIRequest(generic.View):
    models = {
        'venue': models.Venue,
        'person': models.Person,
        'organisation': models.Organisation,
        'mic': models.Profile,
        'profile': models.Profile,
    }

    perms = {
        'venue': 'RIGS.view_venue',
        'person': 'RIGS.view_person',
        'organisation': 'RIGS.view_organisation',
        'mic': None,
        'profile': None,
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
            if fields is None:
                fields = ['name']
            all_objects = self.models[model].objects
            results = []
            for field in fields:
                filter = field + "__icontains"
                objects = all_objects.filter(**{filter: term})
                for o in objects:
                    data = {
                        'pk': o.pk,
                        'value': o.pk,
                        'label': o.name,
                    }
                    results.append(data)
            json = simplejson.dumps(results[:20])
            return HttpResponse(json, content_type="application/json")  # Always json

        return HttpResponse(model)