import os
import cStringIO as StringIO
from io import BytesIO
import urllib2

from django.views import generic
from django.core.urlresolvers import reverse_lazy
from django.shortcuts import get_object_or_404
from django.template import Context, RequestContext
from django.template.loader import get_template
from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest
from django.db.models import Q
from z3c.rml import rml2pdf
from PyPDF2 import PdfFileMerger, PdfFileReader

from RIGS import models, forms
import datetime

__author__ = 'ghost'


class RigboardIndex(generic.TemplateView):
    template_name = 'RIGS/rigboard.html'

    def get_context_data(self, **kwargs):
        # get super context
        context = super(RigboardIndex, self).get_context_data(**kwargs)

        # call out method to get current events
        context['events'] = models.Event.objects.current_events()
        return context


class EventDetail(generic.DetailView):
    model = models.Event


class EventCreate(generic.CreateView):
    model = models.Event
    form_class = forms.EventForm

    def get_context_data(self, **kwargs):
        context = super(EventCreate, self).get_context_data(**kwargs)
        context['edit'] = True
        return context

    def get_success_url(self):
        return reverse_lazy('event_detail', kwargs={'pk': self.object.pk})


class EventUpdate(generic.UpdateView):
    model = models.Event
    form_class = forms.EventForm

    def get_context_data(self, **kwargs):
        context = super(EventUpdate, self).get_context_data(**kwargs)
        context['edit'] = True
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

        return qs.select_related('person', 'organisation', 'venue', 'mic')