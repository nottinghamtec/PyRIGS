import datetime
import re

import reversion
from django import forms
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.http import Http404, HttpResponseRedirect
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import get_template
from django.urls import reverse_lazy
from django.views import generic
from z3c.rml import rml2pdf

from RIGS import models

forms.DateField.widget = forms.DateInput(attrs={'type': 'date'})


class InvoiceIndex(generic.ListView):
    model = models.Invoice
    template_name = 'invoice_list.html'

    def get_context_data(self, **kwargs):
        context = super(InvoiceIndex, self).get_context_data(**kwargs)
        total = 0
        for i in context['object_list']:
            total += i.balance
        context['page_title'] = "Outstanding Invoices ({} Events, £{:.2f})".format(len(list(context['object_list'])), total)
        context['description'] = "Paperwork for these events has been sent to treasury, but the full balance has not yet appeared on a ledger"
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
    template_name = 'invoice_detail.html'

    def get_context_data(self, **kwargs):
        context = super(InvoiceDetail, self).get_context_data(**kwargs)
        context['page_title'] = "Invoice {} ({})".format(self.object.display_id, self.object.invoice_date.strftime("%d/%m/%Y"))
        return context


class InvoicePrint(generic.View):
    def get(self, request, pk):
        invoice = get_object_or_404(models.Invoice, pk=pk)
        object = invoice.event
        template = get_template('event_print.xml')

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
            'filename': 'Invoice {} for {} {}.pdf'.format(invoice.display_id, object.display_id, re.sub(r'[^a-zA-Z0-9 \n\.]', '', object.name))
        }

        rml = template.render(context)

        buffer = rml2pdf.parseString(rml)

        pdfData = buffer.read()

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'filename="{}"'.format(context['filename'])
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
    template_name = 'invoice_confirm_delete.html'

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
    template_name = 'invoice_list_archive.html'
    paginate_by = 25

    def get_context_data(self, **kwargs):
        context = super(InvoiceArchive, self).get_context_data(**kwargs)
        context['page_title'] = "Invoice Archive"
        context['description'] = "This page displays all invoices: outstanding, paid, and void"
        return context

    def get_queryset(self):
        q = self.request.GET.get('q', "")

        filter = Q(event__name__icontains=q)

        # try and parse an int
        try:
            val = int(q)
            filter = filter | Q(pk=val)
            filter = filter | Q(event__pk=val)
        except:  # noqa
            # not an integer
            pass

        try:
            if q[0] == "N":
                val = int(q[1:])
                filter = Q(event__pk=val)  # If string is Nxxxxx then filter by event number
            elif q[0] == "#":
                val = int(q[1:])
                filter = Q(pk=val)  # If string is #xxxxx then filter by invoice number
        except:  # noqa
            pass

        object_list = self.model.objects.filter(filter).order_by('-invoice_date')

        return object_list


class InvoiceWaiting(generic.ListView):
    model = models.Event
    paginate_by = 25
    template_name = 'invoice_list_waiting.html'

    def get_context_data(self, **kwargs):
        context = super(InvoiceWaiting, self).get_context_data(**kwargs)
        total = 0
        for obj in self.get_objects():
            total += obj.sum_total
        context['page_title'] = "Events for Invoice ({} Events, £{:.2f})".format(len(self.get_objects()), total)
        return context

    def get_queryset(self):
        return self.get_objects()

    def get_objects(self):
        # @todo find a way to select items
        events = self.model.objects.filter(
            (
                Q(start_date__lte=datetime.date.today(), end_date__isnull=True) |  # Starts before with no end
                Q(end_date__lte=datetime.date.today())  # Has end date, finishes before
            ) & Q(invoice__isnull=True) &  # Has not already been invoiced
            Q(is_rig=True)  # Is a rig (not non-rig)

        ).order_by('start_date') \
            .select_related('person',
                            'organisation',
                            'venue', 'mic') \
            .prefetch_related('items')

        return events


class InvoiceEvent(generic.View):
    @transaction.atomic()
    @reversion.create_revision()
    def get(self, *args, **kwargs):
        reversion.set_user(self.request.user)
        epk = kwargs.get('pk')
        event = models.Event.objects.get(pk=epk)
        invoice, created = models.Invoice.objects.get_or_create(event=event)

        if created:
            invoice.invoice_date = datetime.date.today()
            messages.success(self.request, 'Invoice created successfully')

        if kwargs.get('void'):
            invoice.void = not invoice.void
            invoice.save()
            messages.warning(self.request, 'Invoice voided')

        return HttpResponseRedirect(reverse_lazy('invoice_detail', kwargs={'pk': invoice.pk}))


class PaymentCreate(generic.CreateView):
    model = models.Payment
    fields = ['invoice', 'date', 'amount', 'method']
    template_name = 'payment_form.html'

    def get_initial(self):
        initial = super(generic.CreateView, self).get_initial()
        invoicepk = self.request.GET.get('invoice', self.request.POST.get('invoice', None))
        if invoicepk is None:
            raise Http404()
        invoice = get_object_or_404(models.Invoice, pk=invoicepk)
        initial.update({'invoice': invoice})
        return initial

    @transaction.atomic()
    @reversion.create_revision()
    def form_valid(self, form, *args, **kwargs):
        reversion.add_to_revision(form.cleaned_data['invoice'])
        reversion.set_comment("Payment added")
        return super().form_valid(form, *args, **kwargs)

    def get_success_url(self):
        messages.info(self.request, "location.reload()")
        return reverse_lazy('closemodal')


class PaymentDelete(generic.DeleteView):
    model = models.Payment
    template_name = 'payment_confirm_delete.html'

    @transaction.atomic()
    @reversion.create_revision()
    def delete(self, *args, **kwargs):
        reversion.add_to_revision(self.get_object().invoice)
        reversion.set_comment("Payment removed")
        return super().delete(*args, **kwargs)

    def get_success_url(self):
        return self.request.POST.get('next')
