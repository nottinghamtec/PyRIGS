import datetime
import re

import reversion
from django import forms
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum
from django.http import Http404, HttpResponseRedirect
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import get_template
from django.urls import reverse
from django.views import generic
from z3c.rml import rml2pdf

from RIGS import models

forms.DateField.widget = forms.DateInput(attrs={'type': 'date'})

TIME_FILTERS = ["all", "year", "month", "week"]


def days_between(d1, d2):
    diff = d2 - d1
    return diff.total_seconds() / datetime.timedelta(days=1).total_seconds()


class InvoiceDashboard(generic.TemplateView):
    template_name = 'invoice_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = "Invoice Dashboard"
        context['description'] = "Overview of financial status of TEC rigs."

        time_filter = self.request.GET.get('time_filter', 'all')

        if time_filter not in TIME_FILTERS:
            time_filter = 'all'

        if time_filter == 'all':
            context['events'] = models.Event.objects.filter(is_rig=True)
            context['invoices'] = models.Invoice.objects.all()
            context['payments'] = models.Payment.objects.all()
        elif time_filter == 'year':
            context['events'] = models.Event.objects.filter(is_rig=True, start_date__gte=datetime.date.today() - datetime.timedelta(days=365))
            context['invoices'] = models.Invoice.objects.filter(invoice_date__gte=datetime.date.today() - datetime.timedelta(days=365))
            context['payments'] = models.Payment.objects.filter(date__gte=datetime.date.today() - datetime.timedelta(days=365))
        elif time_filter == 'month':
            context['events'] = models.Event.objects.filter(is_rig=True, start_date__gte=datetime.date.today() - datetime.timedelta(days=30))
            context['invoices'] = models.Invoice.objects.filter(invoice_date__gte=datetime.date.today() - datetime.timedelta(days=30))
            context['payments'] = models.Payment.objects.filter(date__gte=datetime.date.today() - datetime.timedelta(days=30))
        elif time_filter == 'week':
            context['events'] = models.Event.objects.filter(is_rig=True, start_date__gte=datetime.date.today() - datetime.timedelta(days=7))
            context['invoices'] = models.Invoice.objects.filter(invoice_date__gte=datetime.date.today() - datetime.timedelta(days=7))
            context['payments'] = models.Payment.objects.filter(date__gte=datetime.date.today() - datetime.timedelta(days=7))

        context["time_filter"] = time_filter

        context['total_outstanding'] = sum([i.balance for i in models.Invoice.objects.outstanding_invoices()])
        context['total_waiting'] = sum([i.sum_total for i in models.Event.objects.waiting_invoices()])
        context['total_events'] = len(context['events'])
        context['total_invoices'] = len(context['invoices'])
        context['total_payments'] = len(context['payments'])

        payment_methods = dict(models.Payment.METHODS)

        context['payment_methods'] = context["payments"].values('method').annotate(total=Sum('amount')).order_by('method')

        for method in context['payment_methods']:
            method['method'] = payment_methods.get(method['method'], f"Unknown method ({method['method']})")

        context["total_income"] = sum([i['total'] for i in context['payment_methods']])

        payments = context['payments']
        mean_duration = 0

        for payment in payments:
            mean_duration += days_between(payment.invoice.invoice_date, payment.date)

        if len(payments) > 0:
            mean_duration /= len(payments)

        context['mean_invoice_to_payment'] = mean_duration

        return context


class InvoiceOutstanding(generic.ListView):
    model = models.Invoice
    template_name = 'invoice_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        total = 0
        for i in context['object_list']:
            total += i.balance
        event_count = len(list(context['object_list']))
        context['page_title'] = f"Outstanding Invoices ({event_count} Events, £{total:.2f})"
        context['description'] = "Paperwork for these events has been sent to treasury, but the full balance has not yet appeared on a ledger"
        return context

    def get_queryset(self):
        return self.model.objects.outstanding_invoices()


class InvoiceDetail(generic.DetailView):
    model = models.Invoice
    template_name = 'invoice_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        invoice_date = self.object.invoice_date.strftime("%d/%m/%Y")
        context['page_title'] = f"Invoice {self.object.display_id} ({invoice_date})"
        if self.object.void:
            context['page_title'] += "<span class='badge badge-warning float-right'>VOID</span>"
        elif self.object.is_closed:
            context['page_title'] += "<span class='badge badge-success float-right'>PAID</span>"
        else:
            context['page_title'] += "<span class='badge badge-info float-right'>OUTSTANDING</span>"
        return context


class InvoicePrint(generic.View):
    def get(self, request, pk):
        invoice = get_object_or_404(models.Invoice, pk=pk)
        object = invoice.event
        template = get_template('event_print.xml')

        name = re.sub(r'[^a-zA-Z0-9 \n\.]', '', object.name)
        filename = f"Invoice {invoice.display_id} for {object.display_id} {name}.pdf"

        context = {
            'object': object,
            'invoice': invoice,
            'current_user': request.user,
            'filename': filename
        }

        rml = template.render(context)

        buffer = rml2pdf.parseString(rml)

        pdfData = buffer.read()

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'filename="{filename}"'
        response.write(pdfData)
        return response


class InvoiceVoid(generic.View):
    def get(self, *args, **kwargs):
        pk = kwargs.get('pk')
        object = get_object_or_404(models.Invoice, pk=pk)
        object.void = not object.void
        object.save()

        if object.void:
            return HttpResponseRedirect(reverse('invoice_list'))
        return HttpResponseRedirect(reverse('invoice_detail', kwargs={'pk': object.pk}))


class InvoiceDelete(generic.DeleteView):
    model = models.Invoice
    template_name = 'invoice_confirm_delete.html'

    def get(self, request, pk):
        obj = self.get_object()
        if obj.payment_set.all().count() > 0:
            messages.info(self.request, 'To delete an invoice, delete the payments first.')
            return HttpResponseRedirect(reverse('invoice_detail', kwargs={'pk': obj.pk}))
        return super(InvoiceDelete, self).get(pk)

    def post(self, request, pk):
        obj = self.get_object()
        if obj.payment_set.all().count() > 0:
            messages.info(self.request, 'To delete an invoice, delete the payments first.')
            return HttpResponseRedirect(reverse('invoice_detail', kwargs={'pk': obj.pk}))
        return super(InvoiceDelete, self).post(pk)

    def get_success_url(self):
        return self.request.POST.get('next')


class InvoiceArchive(generic.ListView):
    model = models.Invoice
    template_name = 'invoice_list_archive.html'
    paginate_by = 25

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = "Invoice Archive"
        context['description'] = "This page displays all invoices: outstanding, paid, and void"
        return context

    def get_queryset(self):
        return self.model.objects.search(self.request.GET.get('q')).order_by('-invoice_date')


class InvoiceWaiting(generic.ListView):
    model = models.Event
    paginate_by = 25
    template_name = 'invoice_list_waiting.html'

    def get_context_data(self, **kwargs):
        context = super(InvoiceWaiting, self).get_context_data(**kwargs)
        total = 0
        objects = self.get_queryset()
        for obj in objects:
            total += obj.sum_total
        context['page_title'] = f"Events for Invoice ({len(objects)} Events, £{total:.2f})"
        return context

    def get_queryset(self):
        return self.model.objects.waiting_invoices()


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

        return HttpResponseRedirect(reverse('invoice_detail', kwargs={'pk': invoice.pk}))


class PaymentCreate(generic.CreateView):
    model = models.Payment
    fields = ['invoice', 'date', 'amount', 'method']
    template_name = 'payment_form.html'

    def get_initial(self):
        initial = super().get_initial()
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
        return reverse('closemodal')


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
