import csv
import datetime
import re

import reversion
from django import forms
from django.contrib import messages
from django.db import transaction
from django.http import Http404, HttpResponseRedirect
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import get_template
from django.urls import reverse
from django.views import generic
from z3c.rml import rml2pdf

from RIGS import finance_stats, models

forms.DateField.widget = forms.DateInput(attrs={"type": "date"})


class InvoiceDashboard(generic.TemplateView):
    template_name = "invoice_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Invoice Dashboard"
        context["description"] = "Overview of financial status of TEC rigs."
        context.update(finance_stats.build_dashboard(self.request.GET.get("time_filter", "all"), datetime.date.today()))
        return context


class InvoiceDashboardExport(generic.View):
    """The invoices or payments behind the dashboard's chosen period, as a spreadsheet"""

    def get(self, request, kind):
        if kind not in ("invoices", "payments"):
            raise Http404()
        period = finance_stats.get_period(request.GET.get("time_filter", "all"), datetime.date.today())
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="rigs-{kind}-{period.key}.csv"'
        writer = csv.writer(response)
        if kind == "invoices":
            writer.writerow(
                [
                    "Invoice",
                    "Invoice date",
                    "Event",
                    "Event name",
                    "Event date",
                    "Client",
                    "Internal",
                    "Value (ex. VAT)",
                    "Paid",
                    "Balance",
                    "Void",
                ]
            )
            invoices = finance_stats.with_totals(period.filter(models.Invoice.objects.all(), "invoice_date"))
            for invoice in invoices.select_related("event__organisation", "event__person").order_by(
                "invoice_date", "pk"
            ):
                event = invoice.event
                writer.writerow(
                    [
                        invoice.display_id,
                        invoice.invoice_date.isoformat(),
                        event.display_id,
                        spreadsheet_safe(event.name),
                        event.start_date.isoformat(),
                        spreadsheet_safe(finance_stats.client_of(event)[1]),
                        "Yes" if event.internal else "No",
                        f"{invoice.value:.2f}",
                        f"{invoice.paid:.2f}",
                        f"{invoice.value - invoice.paid:.2f}",
                        "Yes" if invoice.void else "No",
                    ]
                )
        else:
            writer.writerow(
                [
                    "Payment date",
                    "Invoice",
                    "Invoice date",
                    "Event",
                    "Event name",
                    "Client",
                    "Method",
                    "Amount (ex. VAT)",
                ]
            )
            payments = period.filter(models.Payment.objects.all(), "date")
            for payment in payments.select_related("invoice__event__organisation", "invoice__event__person").order_by(
                "date", "pk"
            ):
                event = payment.invoice.event
                writer.writerow(
                    [
                        payment.date.isoformat(),
                        payment.invoice.display_id,
                        payment.invoice.invoice_date.isoformat(),
                        event.display_id,
                        spreadsheet_safe(event.name),
                        spreadsheet_safe(finance_stats.client_of(event)[1]),
                        finance_stats.PAYMENT_METHOD_NAMES.get(payment.method, payment.method),
                        f"{payment.amount:.2f}",
                    ]
                )
        return response


def spreadsheet_safe(text):
    """Stop names that start like a formula being run as one when the file is opened"""
    return f"'{text}" if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


class InvoiceOutstanding(generic.ListView):
    model = models.Invoice
    template_name = "invoice_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        total = 0
        for i in context["object_list"]:
            total += i.balance
        event_count = len(list(context["object_list"]))
        context["page_title"] = f"Outstanding Invoices ({event_count} Events, £{total:.2f})"
        context["description"] = (
            "Paperwork for these events has been sent to treasury, but the full balance has not yet appeared on a ledger"
        )
        return context

    def get_queryset(self):
        return self.model.objects.outstanding_invoices()


class InvoiceDetail(generic.DetailView):
    model = models.Invoice
    template_name = "invoice_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        invoice_date = self.object.invoice_date.strftime("%d/%m/%Y")
        context["page_title"] = f"Invoice {self.object.display_id} ({invoice_date})"
        if self.object.void:
            context["page_title"] += "<span class='badge text-bg-warning float-end'>VOID</span>"
        elif self.object.is_closed:
            context["page_title"] += "<span class='badge text-bg-success float-end'>PAID</span>"
        else:
            context["page_title"] += "<span class='badge text-bg-info float-end'>OUTSTANDING</span>"
        return context


class InvoicePrint(generic.View):
    def get(self, request, pk):
        invoice = get_object_or_404(models.Invoice, pk=pk)
        object = invoice.event
        template = get_template("event_print.xml")

        name = re.sub(r"[^a-zA-Z0-9 \n\.]", "", object.name)
        filename = f"Invoice {invoice.display_id} for {object.display_id} {name}.pdf"

        context = {"object": object, "invoice": invoice, "current_user": request.user, "filename": filename}

        rml = template.render(context)

        buffer = rml2pdf.parseString(rml)

        pdfData = buffer.read()

        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = f'filename="{filename}"'
        response.write(pdfData)
        return response


class InvoiceVoid(generic.View):
    def get(self, *args, **kwargs):
        pk = kwargs.get("pk")
        object = get_object_or_404(models.Invoice, pk=pk)
        object.void = not object.void
        object.save()

        if object.void:
            return HttpResponseRedirect(reverse("invoice_list"))
        return HttpResponseRedirect(reverse("invoice_detail", kwargs={"pk": object.pk}))


class InvoiceDelete(generic.DeleteView):
    model = models.Invoice
    template_name = "invoice_confirm_delete.html"

    def get(self, request, pk):
        obj = self.get_object()
        if obj.payment_set.all().count() > 0:
            messages.info(self.request, "To delete an invoice, delete the payments first.")
            return HttpResponseRedirect(reverse("invoice_detail", kwargs={"pk": obj.pk}))
        return super(InvoiceDelete, self).get(pk)

    def post(self, request, pk):
        obj = self.get_object()
        if obj.payment_set.all().count() > 0:
            messages.info(self.request, "To delete an invoice, delete the payments first.")
            return HttpResponseRedirect(reverse("invoice_detail", kwargs={"pk": obj.pk}))
        return super(InvoiceDelete, self).post(pk)

    def get_success_url(self):
        return self.request.POST.get("next")


class InvoiceArchive(generic.ListView):
    model = models.Invoice
    template_name = "invoice_list_archive.html"
    paginate_by = 25

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Invoice Archive"
        context["description"] = "This page displays all invoices: outstanding, paid, and void"
        return context

    def get_queryset(self):
        return self.model.objects.search(self.request.GET.get("q")).order_by("-invoice_date")


class InvoiceWaiting(generic.ListView):
    model = models.Event
    paginate_by = 25
    template_name = "invoice_list_waiting.html"

    def get_context_data(self, **kwargs):
        context = super(InvoiceWaiting, self).get_context_data(**kwargs)
        total = 0
        objects = self.get_queryset()
        for obj in objects:
            total += obj.sum_total
        context["page_title"] = f"Events for Invoice ({len(objects)} Events, £{total:.2f})"
        return context

    def get_queryset(self):
        return self.model.objects.waiting_invoices()


class InvoiceEvent(generic.View):
    @transaction.atomic()
    @reversion.create_revision()
    def get(self, *args, **kwargs):
        reversion.set_user(self.request.user)
        epk = kwargs.get("pk")
        event = models.Event.objects.get(pk=epk)
        invoice, created = models.Invoice.objects.get_or_create(event=event)

        if created:
            invoice.invoice_date = datetime.date.today()
            messages.success(self.request, "Invoice created successfully")

        if kwargs.get("void"):
            invoice.void = not invoice.void
            invoice.save()
            messages.warning(self.request, "Invoice voided")

        return HttpResponseRedirect(reverse("invoice_detail", kwargs={"pk": invoice.pk}))


class PaymentCreate(generic.CreateView):
    model = models.Payment
    fields = ["invoice", "date", "amount", "method"]
    template_name = "payment_form.html"

    def get_initial(self):
        initial = super().get_initial()
        invoicepk = self.request.GET.get("invoice", self.request.POST.get("invoice", None))
        if invoicepk is None:
            raise Http404()
        invoice = get_object_or_404(models.Invoice, pk=invoicepk)
        initial.update({"invoice": invoice})
        return initial

    @transaction.atomic()
    @reversion.create_revision()
    def form_valid(self, form, *args, **kwargs):
        reversion.add_to_revision(form.cleaned_data["invoice"])
        reversion.set_comment("Payment added")
        return super().form_valid(form, *args, **kwargs)

    def get_success_url(self):
        messages.info(self.request, "location.reload()")
        return reverse("closemodal")


class PaymentDelete(generic.DeleteView):
    model = models.Payment
    template_name = "payment_confirm_delete.html"

    @transaction.atomic()
    @reversion.create_revision()
    def delete(self, *args, **kwargs):
        reversion.add_to_revision(self.get_object().invoice)
        reversion.set_comment("Payment removed")
        return super().delete(*args, **kwargs)

    def get_success_url(self):
        return self.request.POST.get("next")
