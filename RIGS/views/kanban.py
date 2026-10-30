import calendar
import datetime
from collections import Counter

import reversion
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import connection, transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views import generic

from PyRIGS.views import get_related, is_ajax
from RIGS import forms, models
from versioning.versioning import CONVERTED_PREFIX, DELETED_PREFIX, record_deletion

# Finished events leave the board this long after they end, so the finance columns stay short
FALL_OFF = datetime.timedelta(weeks=2)

STATUS_COLUMNS = {
    models.Event.PROVISIONAL: "provisional",
    models.Event.CONFIRMED: "confirmed",
    models.Event.BOOKED: "booked",
}

# (key, title, when it is shown). Those who don't want finance data get a single Done column in place of the rest.
COLUMNS = (
    ("provisional", "Provisional", "always"),
    ("confirmed", "Confirmed", "always"),
    ("booked", "Booked", "always"),
    ("awaiting_invoice", "Awaiting invoice", "finance"),
    ("invoiced", "Invoiced", "finance"),
    ("paid", "Paid", "finance"),
    ("done", "Done", "no_finance"),
)

LANES = (
    ("internal", "Internal (SU accounts)"),
    ("university", "University"),
    ("external", "External"),
    ("dry_hire", "Dry hires"),
)

UNIVERSITY_EMAIL = "@nottingham.ac.uk"

# How far ahead the board looks: (key, label, months, None for no limit)
HORIZONS = (
    ("1m", "Next month", 1),
    ("3m", "Next 3 months", 3),
    ("6m", "Next 6 months", 6),
    ("12m", "Next year", 12),
    ("all", "No limit", None),
)
DEFAULT_HORIZON = "6m"


def months_after(day, months):
    month = day.month - 1 + months
    year = day.year + month // 12
    month = month % 12 + 1
    return day.replace(year=year, month=month, day=min(day.day, calendar.monthrange(year, month)[1]))


def has_finished(event, today):
    return (event.end_date or event.start_date) < today


def finance_visible(user):
    return user.has_perm("RIGS.view_invoice") and user.kanban_finance


def live_invoice(event):
    """The event's invoice, unless it has been voided"""
    invoice = getattr(event, "invoice", None)
    return invoice if invoice is not None and not invoice.void else None


def column_for(event, today, show_finance):
    """Where an event sits on the board: its status until it has finished, then how far its invoice has got.

    An invoice raised before the event is over doesn't move it, it just shows as a pill on the card."""
    if event.cancelled:
        return "cancelled"
    if not has_finished(event, today):
        return STATUS_COLUMNS[event.status]
    if not show_finance:
        return "done"
    invoice = live_invoice(event)
    if invoice:
        return "paid" if invoice.is_closed else "invoiced"
    return "awaiting_invoice"


def flags_for(event, today):
    """Things to chase on an event that hasn't happened yet: (key, icon, tooltip) for each"""
    if event.cancelled or has_finished(event, today):
        return []
    flags = []
    if event.status == models.Event.PROVISIONAL and not event.default_response_sent:
        flags.append(
            {
                "key": "default_response",
                "icon": "fa-envelope",
                "tip": "The client hasn't been sent our default response yet.",
                "action": "response",
                "action_tip": "Click to mark it as sent.",
            }
        )
    missing = []
    if not event.dry_hire and not event.venue_id:
        missing.append("venue")
    if not (event.organisation_id or event.person_id):
        missing.append("client")
    if event.start_time is None:
        missing.append("start time")
    if missing:
        flags.append(
            {
                "key": "details",
                "icon": "fa-exclamation-circle",
                "tip": f"Basic details are missing: {', '.join(missing)}",
            }
        )
    if event.status in (models.Event.CONFIRMED, models.Event.BOOKED) and not event.dry_hire and not event.forum_url:
        flags.append(
            {
                "key": "forum",
                "icon": "fa-comments",
                "tip": "There's no forum thread yet, so MIC and crew availability can't have been polled",
            }
        )
    if event.needs_mic and not event.mic_id:
        flags.append({"key": "mic", "icon": "fa-user-slash", "tip": "No MIC has been assigned yet", "level": "danger"})
    return flags


def lane_for(event):
    if event.dry_hire:
        return "dry_hire"
    if event.internal:
        return "internal"
    emails = (client.email for client in (event.organisation, event.person) if client)
    if any(email.lower().endswith(UNIVERSITY_EMAIL) for email in emails):
        return "university"
    return "external"


def board_events(today):
    cutoff = today - FALL_OFF
    return (
        models.Event.objects.filter(is_rig=True)
        .exclude(status=models.Event.CANCELLED)
        .filter(Q(end_date__gte=cutoff) | Q(end_date__isnull=True, start_date__gte=cutoff))
        .select_related("person", "organisation", "venue", "mic", "invoice")
        .prefetch_related("items", "invoice__payment_set")
        .order_by("start_date", "start_time", "pk")
    )


def older_counts(today):
    """Rigs that have fallen off the board but still need something doing: not yet invoiced, or still owed on.

    Only paid rigs leave for good, so these are counted by lane and column for each cell to report."""
    cutoff = today - FALL_OFF
    with connection.cursor() as cursor:
        cursor.execute("SELECT inv.event_id " + models.OUTSTANDING_INVOICES_FROM)
        outstanding = [row[0] for row in cursor.fetchall()]
    events = (
        models.Event.objects.filter(is_rig=True)
        .exclude(status=models.Event.CANCELLED)
        .filter(Q(end_date__lt=cutoff) | Q(end_date__isnull=True, start_date__lt=cutoff))
        .filter(Q(invoice__isnull=True) | Q(pk__in=outstanding))
        .select_related("person", "organisation", "invoice")
    )
    return Counter(
        (lane_for(event), "invoiced" if hasattr(event, "invoice") else "awaiting_invoice") for event in events
    )


class EventKanban(generic.TemplateView):
    template_name = "kanban.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = datetime.date.today()
        user = self.request.user
        can_see_finance = user.has_perm("RIGS.view_invoice")
        choice = self.request.GET.get("finance")
        if can_see_finance and choice in ("0", "1") and user.kanban_finance != (choice == "1"):
            user.kanban_finance = choice == "1"
            user.save(update_fields=["kanban_finance"])
        show_finance = finance_visible(user)
        columns = [
            (key, title)
            for key, title, shown in COLUMNS
            if shown == "always"
            or (shown == "finance" and show_finance)
            or (shown == "no_finance" and not show_finance)
        ]
        cells = {(lane, column): [] for lane, _ in LANES for column, _ in columns}

        horizons = {key: months for key, _, months in HORIZONS}
        horizon = self.request.GET.get("horizon")
        if horizon not in horizons:
            horizon = DEFAULT_HORIZON
        events = board_events(today)
        if horizons[horizon] is not None:
            limit = months_after(today, horizons[horizon])
            context["beyond_horizon"] = events.filter(start_date__gt=limit).count()
            events = events.filter(start_date__lte=limit)

        for event in events:
            finished = has_finished(event, today)
            if finished and hasattr(event, "invoice") and event.invoice.void:
                continue
            event.live_invoice = live_invoice(event)
            event.flags = flags_for(event, today)
            event.urgent = any(flag.get("level") == "danger" for flag in event.flags)
            event.movable = not (finished and event.live_invoice)
            cells[(lane_for(event), column_for(event, today, show_finance))].append(event)

        older = older_counts(today) if show_finance else Counter()

        context["show_finance"] = show_finance
        context["can_see_finance"] = can_see_finance
        context["horizon"] = horizon
        context["horizons"] = [(key, label) for key, label, _ in HORIZONS]
        context["columns"] = columns
        context["lanes"] = [
            {
                "key": lane,
                "title": title,
                "cells": [
                    {
                        "key": column,
                        "title": column_title,
                        "events": cells[(lane, column)],
                        "older": older[(lane, column)],
                    }
                    for column, column_title in columns
                ],
                "count": sum(len(cells[(lane, column)]) for column, _ in columns),
            }
            for lane, title in LANES
        ]
        context["enquiries"] = models.Enquiry.objects.select_related("created_by", "person", "organisation")
        context["status_choices"] = [
            (status, label) for status, label in models.Event.EVENT_STATUS_CHOICES if status in STATUS_COLUMNS
        ]
        context["page_title"] = "Kanban"
        return context


def event_json(event, user):
    today = datetime.date.today()
    return {
        "pk": event.pk,
        "display_id": event.display_id,
        "status": event.status,
        "column": column_for(event, today, finance_visible(user)),
        "flags": flags_for(event, today),
    }


class EventKanbanStatus(generic.View):
    """Move an event between the statuses that can be set by hand, or cancel it"""

    http_method_names = ["post"]

    @transaction.atomic()
    def post(self, request, pk):
        event = get_object_or_404(models.Event.objects.select_for_update(), pk=pk)
        try:
            status = int(request.POST.get("status", ""))
        except ValueError:
            return JsonResponse({"error": "No status given"}, status=400)
        if status not in dict(models.Event.EVENT_STATUS_CHOICES):
            return JsonResponse({"error": "Unknown status"}, status=400)
        invoiced = models.Invoice.objects.filter(event=event, void=False).exists()
        if invoiced and (status == models.Event.CANCELLED or has_finished(event, datetime.date.today())):
            return JsonResponse({"error": f"{event.display_id} has already been invoiced"}, status=409)

        previous = event.status
        event.status = status
        try:
            event.save()
        except ValidationError as e:
            return JsonResponse({"error": " ".join(e.messages)}, status=400)
        reversion.set_user(request.user)
        reversion.set_comment(f"Status changed to {event.get_status_display()} on the Kanban")
        return JsonResponse({**event_json(event, request.user), "previous_status": previous})


class EventKanbanResponse(generic.View):
    """Mark the client as having been sent our default response, or undo that"""

    http_method_names = ["post"]

    @transaction.atomic()
    def post(self, request, pk):
        event = get_object_or_404(models.Event.objects.select_for_update(), pk=pk)
        sent = request.POST.get("sent", "1") != "0"
        if event.default_response_sent != sent:
            event.default_response_sent = sent
            try:
                event.save()
            except ValidationError as e:
                return JsonResponse({"error": " ".join(e.messages)}, status=400)
            reversion.set_user(request.user)
            reversion.set_comment(
                "Default response marked as sent on the Kanban" if sent else "Default response unmarked on the Kanban"
            )
        return JsonResponse(event_json(event, request.user))


class EventKanbanInvoice(generic.View):
    http_method_names = ["post"]

    @transaction.atomic()
    def post(self, request, pk):
        event = get_object_or_404(models.Event.objects.select_for_update(), pk=pk)
        if event.cancelled:
            return JsonResponse({"error": f"{event.display_id} is cancelled"}, status=409)
        invoice, created = models.Invoice.objects.get_or_create(event=event)
        if invoice.void:
            return JsonResponse(
                {"error": f"{event.display_id} has a void invoice, which needs un-voiding first"}, status=409
            )
        if created:
            reversion.set_user(request.user)
            reversion.set_comment("Invoice created on the Kanban")
        return JsonResponse(
            {
                **event_json(event, request.user),
                "created": created,
                "invoice": {
                    "pk": invoice.pk,
                    "display_id": invoice.display_id,
                    "url": reverse("invoice_detail", kwargs={"pk": invoice.pk}),
                    "balance": f"{invoice.balance:.2f}",
                    "closed": invoice.is_closed,
                },
            }
        )


class EnquiryFormMixin:
    """Enquiries are edited in the modal, which closes and takes you to the Kanban once saved"""

    model = models.Enquiry
    form_class = forms.EnquiryForm
    template_name = "enquiry_form.html"

    def get_success_url(self):
        kanban = reverse("event_kanban")
        if is_ajax(self.request):
            messages.info(self.request, f"window.location.href = '{kanban}'")
            return reverse("closemodal")
        return kanban

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        get_related(context["form"], context)
        return context


class EnquiryCreate(EnquiryFormMixin, generic.CreateView):
    def get_initial(self):
        return {"start_date": datetime.date.today()}

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "New Enquiry"
        return context


class EnquiryUpdate(EnquiryFormMixin, generic.UpdateView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = f"Edit Enquiry: {self.object.name}"
        return context


class EnquiryConvert(generic.View):
    """Make an enquiry into a provisional event, to be filled in on the edit page"""

    http_method_names = ["post"]

    @transaction.atomic()
    def post(self, request, pk):
        enquiry = get_object_or_404(models.Enquiry.objects.select_for_update(), pk=pk)
        name = enquiry.name
        try:
            event = enquiry.convert()
        except ValidationError as e:
            return JsonResponse(
                {"error": " ".join(e.messages), "edit_url": reverse("enquiry_update", kwargs={"pk": pk})}, status=409
            )
        reversion.set_user(request.user)
        reversion.set_comment(f"{CONVERTED_PREFIX}{name}")
        return JsonResponse(
            {
                "pk": event.pk,
                "display_id": event.display_id,
                "url": reverse("event_update", kwargs={"pk": event.pk}),
            }
        )


class EnquiryDelete(generic.View):
    http_method_names = ["post"]

    @transaction.atomic()
    def post(self, request, pk):
        enquiry = get_object_or_404(models.Enquiry, pk=pk)
        record_deletion(enquiry, request.user, f"{DELETED_PREFIX}{enquiry.name}")
        enquiry.delete()
        return JsonResponse({"deleted": pk})
