from django.core.urlresolvers import reverse_lazy
from django.db import connection
from django.http import Http404, HttpResponseRedirect
from django.views import generic
from django.shortcuts import get_object_or_404
from django.contrib import messages
import datetime

from RIGS import models


class InvoiceIndex(generic.ListView):
    model = models.Invoice
    template_name = 'RIGS/invoice_list.html'

    def get_queryset(self):
        # Manual query is the only way I have found to do this efficiently. Not ideal but needs must
        sql = "SELECT * FROM " \
              "(SELECT " \
              "(SELECT COUNT(p.amount) FROM \"RIGS_payment\" as p WHERE p.invoice_id=\"RIGS_invoice\".id) AS \"payment_count\", " \
              "(SELECT SUM(ei.cost * ei.quantity) FROM \"RIGS_eventitem\" AS ei WHERE ei.event_id=\"RIGS_invoice\".event_id) AS \"cost\", " \
              "(SELECT SUM(p.amount) FROM \"RIGS_payment\" as p WHERE p.invoice_id=\"RIGS_invoice\".id) AS \"payments\", " \
              "\"RIGS_invoice\".\"id\", \"RIGS_invoice\".\"event_id\", \"RIGS_invoice\".\"invoice_date\", \"RIGS_invoice\".\"void\" FROM \"RIGS_invoice\") " \
              "AS sub " \
              "WHERE ((((cost - payments) <> 0.0) AND (payment_count=0)) OR (cost - payments) <> 0.0) AND void = '0'"

        query = self.model.objects.raw(sql)

        return query


class InvoiceDetail(generic.DetailView):
    model = models.Invoice


class InvoiceVoid(generic.View):
    def get(self, *args, **kwargs):
        pk = kwargs.get('pk')
        object = get_object_or_404(models.Invoice, pk=pk)
        object.void = not object.void
        object.save()

        if object.void:
            return HttpResponseRedirect(reverse_lazy('invoice_list'))
        return HttpResponseRedirect(reverse_lazy('invoice_detail', kwargs={'pk': object.pk}))


class InvoiceArchive(generic.ListView):
    model = models.Invoice
    paginate_by = 25


class InvoiceWaiting(generic.ListView):
    model = models.Event
    paginate_by = 25
    template_name = 'RIGS/event_invoice.html'

    def get_queryset(self):
        events = self.model.objects.filter(is_rig=True, end_date__lt=datetime.date.today(),
                                           invoice__isnull=True).select_related('person', 'organisation', 'venue',
                                                                                'mic')  # @todo find a way to select items
        return events


class InvoiceEvent(generic.View):
    def get(self, *args, **kwargs):
        epk = kwargs.get('pk')
        event = models.Event.objects.get(pk=epk)
        invoice, created = models.Invoice.objects.get_or_create(event=event)

        if created:
            invoice.invoice_date = datetime.date.today()

        return HttpResponseRedirect(reverse_lazy('invoice_detail', kwargs={'pk': invoice.pk}))


class PaymentCreate(generic.CreateView):
    model = models.Payment

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