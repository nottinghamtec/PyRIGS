import os
import cStringIO as StringIO
from io import BytesIO
import urllib2
import logging


from django.views import generic
from django.core.urlresolvers import reverse_lazy
from django.shortcuts import get_object_or_404
from django.template import RequestContext
from django.template.loader import get_template
from django.conf import settings
from django.http import HttpResponse
from django.db.models import Q
from django.contrib import messages
from z3c.rml import rml2pdf
from PyPDF2 import PdfFileMerger, PdfFileReader

# Versioning
import reversion
import diff_match_patch
import simplejson
from reversion.helpers import generate_patch_html
from reversion.models import Version
from django.contrib.contenttypes.models import ContentType # Used to lookup the content_type

from RIGS import models, forms
import datetime
import re

__author__ = 'ghost'

logger = logging.getLogger('project.interesting.stuff')
class RigboardIndex(generic.TemplateView):
    template_name = 'RIGS/rigboard.html'

    def get_context_data(self, **kwargs):
        # get super context
        context = super(RigboardIndex, self).get_context_data(**kwargs)

        # call out method to get current events
        context['events'] = models.Event.objects.current_events()
        return context

class WebCalendar(generic.TemplateView):
    template_name = 'RIGS/calendar.html'

class EventDetail(generic.DetailView):
    model = models.Event


class EventCreate(generic.CreateView):
    model = models.Event
    form_class = forms.EventForm

    def get_context_data(self, **kwargs):
        context = super(EventCreate, self).get_context_data(**kwargs)
        context['edit'] = True

        form = context['form']
        if re.search('"-\d+"', form['items_json'].value()):
            messages.info(self.request, "Your item changes have been saved. Please fix the errors and save the event.")
        

        # Get some other objects to include in the form. Used when there are errors but also nice and quick.
        for field, model in form.related_models.iteritems():
            value = form[field].value()
            if value is not None and value != '':
                context[field] = model.objects.get(pk=value)
        return context

    def get_success_url(self):
        return reverse_lazy('event_detail', kwargs={'pk': self.object.pk})


class EventUpdate(generic.UpdateView):
    model = models.Event
    form_class = forms.EventForm

    def get_context_data(self, **kwargs):
        context = super(EventUpdate, self).get_context_data(**kwargs)
        context['edit'] = True

        form = context['form']

        # Get some other objects to include in the form. Used when there are errors but also nice and quick.
        for field, model in form.related_models.iteritems():
            value = form[field].value()
            if value is not None and value != '':
                context[field] = model.objects.get(pk=value)
        return context

    def get_success_url(self):
        return reverse_lazy('event_detail', kwargs={'pk': self.object.pk})


class EventPrint(generic.View):
    def get(self, request, pk):
        object = get_object_or_404(models.Event, pk=pk)
        template = get_template('RIGS/event_print.xml')
        copies = ('TEC', 'Client')
        context = RequestContext(request, {
            'object': object,
            'fonts': {
                'opensans': {
                    'regular': 'RIGS/static/fonts/OPENSANS-REGULAR.TTF',
                    'bold': 'RIGS/static/fonts/OPENSANS-BOLD.TTF',
                }
            },
        })

        merger = PdfFileMerger()

        for copy in copies:
            context['copy'] = copy
            rml = template.render(context)
            buffer = StringIO.StringIO()

            buffer = rml2pdf.parseString(rml)

            merger.append(PdfFileReader(buffer))

            buffer.close()

        terms = urllib2.urlopen(settings.TERMS_OF_HIRE_URL)
        merger.append(StringIO.StringIO(terms.read()))

        merged = BytesIO()
        merger.write(merged)

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = "filename=N%05d | %s.pdf" % (object.pk, object.name)
        response.write(merged.getvalue())
        return response


class EventDuplicate(generic.RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        new = get_object_or_404(models.Event, pk=kwargs['pk'])
        new.pk = None
        new.based_on = models.Event.objects.get(pk=kwargs['pk'])
        new.save()

        old = get_object_or_404(models.Event, pk=kwargs['pk'])
        for item in old.items.all():
            item.pk = None
            item.event = new
            item.save()

        return reverse_lazy('event_update', kwargs={'pk': new.pk})


class EventArchive(generic.ArchiveIndexView):
    model = models.Event
    date_field = "start_date"
    paginate_by = 25

    def get_queryset(self):
        start = self.request.GET.get('start', None)
        end = self.request.GET.get('end', datetime.date.today())

        # Assume idiots, always check
        if start and start > end:
            messages.add_message(self.request, messages.INFO,
                                 "Muppet! Check the dates, it has been fixed for you.")
            start, end = end, start  # Stop the impending fail

        filter = False
        if end != "":
            filter = Q(start_date__lte=end)
        if start:
            if filter:
                filter = filter & Q(start_date__gte=start)
            else:
                filter = Q(start_date__gte=start)

        if filter:
            qs = self.model.objects.filter(filter)
        else:
            qs = self.model.objects.all()

        # Preselect related for efficiency
        qs.select_related('person', 'organisation', 'venue', 'mic')

        if len(qs) == 0:
            messages.add_message(self.request, messages.WARNING, "No events have been found matching those criteria.")

        return qs

class EventRevisions(generic.ListView):
    model = reversion.revisions.Version
    template_name = "RIGS/event_version_list.html"

    # def get_queryset(self):
    #     thisEvent = get_object_or_404(models.Event, pk=self.kwargs['pk'])
    #     items = reversion.get_for_object(thisEvent)
    #     #logger.info('There are '+items[0].date_created)
    #     return items

    def compare(self, obj1, obj2, excluded_keys=[]):
        d1, d2 = obj1, obj2
        key, old, new = [],[],[]
        for k,v in d1.items():
            if k in excluded_keys:
                continue
            try:
                if v != d2[k]:
                    key.append(models.Event._meta.get_field_by_name(k)[0].verbose_name)
                    old.append(v)
                    new.append(d2[k])
            except KeyError:
                old.update({k: v})
        
        return zip(key,old,new)

    def compare_items(self, old, new):

        item_type = ContentType.objects.get_for_model(models.EventItem)
        old_items = old.revision.version_set.filter(content_type=item_type)
        new_items = new.revision.version_set.filter(content_type=item_type)

        class ItemCompare(object):
            def __init__(self, old=None, new=None):
                self.old = old
                self.new = new

        # Build some dicts of what we have
        item_dict = {}
        for item in old_items:
            compare = ItemCompare(old=item)
            compare.old.field_dict['event_id'] = compare.old.field_dict.pop('event')
            item_dict[item.object_id] = compare

        for item in new_items:
            try:
                compare = item_dict[item.object_id]
                compare.new = item
            except KeyError:
                compare = ItemCompare(new=item)
            compare.new.field_dict['event_id'] = compare.new.field_dict.pop('event')
            item_dict[item.object_id] = compare

        # calculate changes
        key, old, new = [], [], []
        for (_, items) in item_dict.items():
            if items.new is None:
                key.append("Deleted \"%s\"" % items.old.field_dict['name'])
                old.append(models.EventItem(**items.old.field_dict))
                new.append(None)

            elif items.old is None:
                key.append("Added \"%s\"" % items.new.field_dict['name'])
                old.append(None)
                new.append(models.EventItem(**items.new.field_dict))

            elif items.old.field_dict != items.new.field_dict:
                if items.old.field_dict['name'] == items.new.field_dict['name']:
                    change_text = "\"%s\"" % items.old.field_dict['name']
                else:
                    change_text = "\"%s\" to \"%s\"" % (items.old.field_dict['name'], items.new.field_dict['name'])
                key.append("Changed %s" % change_text)

                old.append(models.EventItem(**items.old.field_dict))
                new.append(models.EventItem(**items.new.field_dict))

        return zip(key,old,new)

    
    def get_context_data(self, **kwargs):

        
        thisEvent = get_object_or_404(models.Event, pk=self.kwargs['pk'])
        revisions = reversion.get_for_object(thisEvent)
        items = []
        for revisionNo, thisRevision in enumerate(revisions):
            thisItem = {'pk': thisRevision.pk}
            thisItem['revision'] = thisRevision.revision
            logger.info(thisRevision.revision.version_set.all())

            if revisionNo >= len(revisions)-1:
                # oldest version
                thisItem['changes'] = [["(initial version)",None,"Event Created"]]
            else:
                changes = self.compare(revisions[revisionNo+1].field_dict,thisRevision.field_dict)
                thisItem['item_changes'] = self.compare_items(revisions[revisionNo+1], thisRevision)
                logger.debug(thisItem['item_changes'])
                thisItem['changes'] = changes

            items.append(thisItem)
            logger.info(thisItem)

        context = {
            'object_list': items,
            'object': thisEvent
        }                     

        return context
