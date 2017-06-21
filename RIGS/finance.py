import io as StringIO
import datetime
import re

from django.contrib import messages
from django.core.urlresolvers import reverse_lazy
from django.http import Http404, HttpResponseRedirect
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template import RequestContext
from django.template.loader import get_template
from django.views import generic
from django.db.models import Q
from z3c.rml import rml2pdf

from RIGS import models

from django import forms
forms.DateField.widget = forms.DateInput(attrs={'type': 'date'})


class InvoiceIndex(generic.ListView):
    model = models.Invoice
    template_name = 'RIGS/invoice_list_active.html'

    def get_context_data(self, **kwargs):
        context = super(InvoiceIndex, self).get_context_data(**kwargs)
        total = 0
        for i in context['object_list']:
            total += i.balance
        context['total'] = total
        context['count'] = len(list(context['object_list']))
        return context

    def get_queryset(self):
        # Manual query is the only way I have found to do this efficiently. Not ideal but needs must
        sql = "SELECT * FROM " \
              "(SELECT " \
              "(SELECT COUNT(p.amount) FROM \"RIGS_payment\" AS p WHERE p.invoice_id=\"RIGS_invoice\".id) AS \"payment_count\", " \
              "(SELECT SUM(ei.cost * ei.quantity) FROM \"RIGS_eventitem\" AS ei WHERE ei.event_id=\"RIGS_invoice\".event_id) AS \"cost\", " \
              "(SELECT SUM(p.amount) FROM \"RIGS_payment\" AS p WHERE p.invoice_id=\"RIGS_invoice\".id) AS \"payments\", " \
              "\"RIGS_invoice\".\"id\", \"RIGS_invoice\".\"event_id\", \"RIGS_invoice\".\"invoice_date\", \"RIGS_invoice\".\"void\" FROM \"RIGS_invoice\") " \
              "AS sub " \
              "WHERE (((cost > 0.0) AND (payment_count=0)) OR (cost - payments) <> 0.0) AND void = '0'" \
              "ORDER BY invoice_date"

        query = self.model.objects.raw(sql)

        return query


class InvoiceDetail(generic.DetailView):
    model = models.Invoice


class InvoicePrint(generic.View):
    def get(self, request, pk):
        invoice = get_object_or_404(models.Invoice, pk=pk)
        object = invoice.event
        template = get_template('RIGS/event_print.xml')

        context = {
            'object': object,
            'fonts': {
                'opensans': {
                    'regular': 'RIGS/static/fonts/OPENSANS-REGULAR.TTF',
                    'bold': 'RIGS/static/fonts/OPENSANS-BOLD.TTF',
                }
            },
            'invoice': invoice,
            'current_user': request.user,
        }

        rml = template.render(context)
        buffer = StringIO.StringIO()

        buffer = rml2pdf.parseString(rml)

        pdfData = buffer.read()

        escapedEventName = re.sub('[^a-zA-Z0-9 \n\.]', '', object.name)

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = "filename=Invoice %05d - N%05d | %s.pdf" % (invoice.pk, invoice.event.pk, escapedEventName)
        response.write(pdfData)
        return response


class InvoiceVoid(generic.View):
    def get(self, *args, **kwargs):
        pk = kwargs.get('pk')
        object = get_object_or_404(models.Invoice, pk=pk)
        object.void = not object.void
        object.save()

        if object.void:
            return HttpResponseRedirect(reverse_lazy('invoice_list'))
        return HttpResponseRedirect(reverse_lazy('invoice_detail', kwargs={'pk': object.pk}))

class InvoiceDelete(generic.DeleteView):
    model = models.Invoice

    def get(self, request, pk):
        obj = self.get_object()
        if obj.payment_set.all().count() > 0:
            messages.info(self.request, 'To delete an invoice, delete the payments first.')
            return HttpResponseRedirect(reverse_lazy('invoice_detail', kwargs={'pk': obj.pk}))
        return super(InvoiceDelete, self).get(pk)

    def post(self, request, pk):
        obj = self.get_object()
        if obj.payment_set.all().count() > 0:
            messages.info(self.request, 'To delete an invoice, delete the payments first.')
            return HttpResponseRedirect(reverse_lazy('invoice_detail', kwargs={'pk': obj.pk}))
        return super(InvoiceDelete, self).post(pk)

    def get_success_url(self):
        return self.request.POST.get('next')

class InvoiceArchive(generic.ListView):
    model = models.Invoice
    template_name = 'RIGS/invoice_list_archive.html'
    paginate_by = 25


class InvoiceWaiting(generic.ListView):
    model = models.Event
    paginate_by = 25
    template_name = 'RIGS/event_invoice.html'

    def get_context_data(self, **kwargs):
        context = super(InvoiceWaiting, self).get_context_data(**kwargs)
        total = 0
        for obj in self.get_objects():
            total += obj.sum_total
        context['total'] = total
        context['count'] = len(self.get_objects())
        return context

    def get_queryset(self):
        return self.get_objects()

    def get_objects(self):
        # @todo find a way to select items
        events = self.model.objects.filter(
            (
                Q(start_date__lte=datetime.date.today(), end_date__isnull=True) |  # Starts before with no end
                Q(end_date__lte=datetime.date.today()) # Has end date, finishes before
            ) & Q(invoice__isnull=True) # Has not already been invoiced
            & Q(is_rig=True) # Is a rig (not non-rig)
            
            ).order_by('start_date') \
            .select_related('person',
                            'organisation',
                            'venue', 'mic') \
            .prefetch_related('items')

        return events


class InvoiceEvent(generic.View):
    def get(self, *args, **kwargs):
        epk = kwargs.get('pk')
        event = models.Event.objects.get(pk=epk)
        invoice, created = models.Invoice.objects.get_or_create(event=event)

        if created:
            invoice.invoice_date = datetime.date.today()
            messages.success(self.request, 'Invoice created successfully')

        return HttpResponseRedirect(reverse_lazy('invoice_detail', kwargs={'pk': invoice.pk}))


class PaymentCreate(generic.CreateView):
    model = models.Payment
    fields = ['invoice', 'date', 'amount', 'method']

    def get_initial(self):
        initial = super(generic.CreateView, self).get_initial()
        invoicepk = self.request.GET.get('invoice', self.request.POST.get('invoice', None))
        if invoicepk == None:
            raise Http404()
        invoice = get_object_or_404(models.Invoice, pk=invoicepk)
        initial.update({'invoice': invoice})
        return initial

    def get_success_url(self):
        messages.info(self.request, "location.reload()")
        return reverse_lazy('closemodal')


class PaymentDelete(generic.DeleteView):
    model = models.Payment

    def get_success_url(self):
        return self.request.POST.get('next')
