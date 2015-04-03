from django.core.exceptions import PermissionDenied
from django.http.response import HttpResponseRedirect
from django.http import HttpResponse
from django.core.urlresolvers import reverse_lazy, reverse, NoReverseMatch
from django.views import generic
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.core import serializers
import simplejson
from django.contrib import messages
from django_ical.views import ICalFeed

from RIGS import models, forms

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
        'profile': models.Profile,
    }

    perms = {
        'venue': 'RIGS.view_venue',
        'person': 'RIGS.view_person',
        'organisation': 'RIGS.view_organisation',
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

                    try: # See if there is an update url or don't bother with it otherwise
                        data['update'] = reverse("%s_update" % model, kwargs={'pk': o.pk})
                    except NoReverseMatch:
                        pass

                    results.append(data)
            json = simplejson.dumps(results[:20])
            return HttpResponse(json, content_type="application/json")  # Always json

        return HttpResponse(model)

class CalendarICS(ICalFeed):
    """
    A simple event calender
    """
    product_id = '-//example.com//Example//EN'
    timezone = 'UTC'
    file_name = "event.ics"

    def items(self):
        return models.Event.objects.all().order_by('-start_date')

    def item_title(self, item):
        title = ''
        if item.cancelled:
            title += 'CANCELLED: '

        if not item.is_rig:
            title += 'NON-RIG: '

        if item.dry_hire:
            title += 'DRY HIRE: '

        title += item.name
        
        title += ' ('+str(item.status)+')'

        return title

    def item_start_datetime(self, item):
        startDateTime = item.start_date#.strftime("%Y%M%d")

        #if item.start_time:
        #    startDateTime += 'T'+item.start_time.strftime("%H%i")

        return startDateTime

    def item_end_datetime(self, item):
        endDateTime = item.start_date.strftime("%Y%M%d")

        #if item.end_date:
        #    endDateTime = item.end_date.strftime("%Y%M%d")
        #
        #if item.start_time and item.end_time: # don't allow an event with specific end but no specific start
        #    endDateTime += 'T'+item.end_time.strftime("%H%i")
        #elif item.start_time: # if there's a start time specified then an end time should also be specified
        #    endDateTime += 'T2359'
        #elif item.end_time: # end time but no start time - this is weird - don't think ICS will like it so ignoring
        #    endDateTime += '' # do nothing

        return endDateTime

    def item_location(self,item):
        return item.venue

    def item_description(self, item):
        desc = 'Rig ID = '+str(item.pk)+'\n'
        desc += 'MIC = ' + (item.mic.name if item.mic else '---') + '\n'
        desc += 'Status = ' + str(item.status) + '\n'
        desc += 'Event = ' + item.name + '\n'
        desc += 'Venue = ' + (item.venue.name if item.venue else '---') + '\n'
        if item.is_rig and item.person:
            desc += 'Client = ' + item.person.name + ( ('for'+item.organisation.name) if item.organisation else '') + '\n'
        desc += '\n\n'
        if item.description:
            desc += 'Event Description:\n'+item.description
        if item.notes:
            desc += 'Notes:\n'+item.notes

        


        return item.description

    def item_link(self, item):
        return ''

    # def item_created(self, item):  #TODO - Implement created date-time (using django-reversion?)
    #     return ''

    def item_updated(self, item):
        return item.last_edited_at

    def item_guid(self, item):
        return item.pk

class ProfileDetail(generic.DetailView):
    model = models.Profile

    def get_queryset(self):
        try:
            pk = self.kwargs['pk']
        except KeyError:
            pk = self.request.user.id
            self.kwargs['pk'] = pk

        return self.model.objects.filter(pk=pk)

class ProfileUpdateSelf(generic.UpdateView):
    model = models.Profile
    fields = ['first_name', 'last_name', 'email', 'initials', 'phone']

    def get_queryset(self):
        pk = self.request.user.id
        self.kwargs['pk'] = pk

        return self.model.objects.filter(pk=pk)

    def get_success_url(self):
        url =  reverse_lazy('profile_detail')
        return url