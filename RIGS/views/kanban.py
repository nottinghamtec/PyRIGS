import calendar
import datetime
from collections import Counter

import reversion
from django.core.exceptions import ValidationError
from django.db import connection, transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views import generic

from RIGS import models

# Finished events leave the board this long after they end, so the finance columns stay short
FALL_OFF = datetime.timedelta(weeks=2)

STATUS_COLUMNS = {
    models.Event.PROVISIONAL: "provisional",
    models.Event.CONFIRMED: "confirmed",
    models.Event.BOOKED: "booked",
}

# (key, title, shown only to those who can see invoices)
COLUMNS = (
    ("provisional", "Provisional", False),
    ("confirmed", "Confirmed", False),
    ("booked", "Booked", False),
    ("awaiting_invoice", "Awaiting invoice", True),
    ("invoiced", "Invoiced", True),
    ("paid", "Paid", True),
)

LANES = (
    ("internal", "Internal (SU accounts)"),
    ("university", "University"),
    ("external", "External"),
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


def column_for(event, today):
    """Where an event sits on the board: its status until it has finished, then how far its invoice has got"""
    if event.cancelled:
        return "cancelled"
    if hasattr(event, "invoice"):
        return "paid" if event.invoice.is_closed else "invoiced"
    if has_finished(event, today):
        return "awaiting_invoice"
    return STATUS_COLUMNS[event.status]


def lane_for(event):
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
        .exclude(invoice__void=True)
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
        show_finance = self.request.user.has_perm("RIGS.view_invoice")
        columns = [(key, title) for key, title, finance in COLUMNS if show_finance or not finance]
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
            column = column_for(event, today)
            if column in STATUS_COLUMNS.values() or show_finance:
                event.movable = column not in ("invoiced", "paid")
                cells[(lane_for(event), column)].append(event)

        older = older_counts(today) if show_finance else Counter()

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
        context["status_choices"] = [
            (status, label) for status, label in models.Event.EVENT_STATUS_CHOICES if status in STATUS_COLUMNS
        ]
        context["page_title"] = "Kanban"
        return context


def event_json(event, today):
    return {"pk": event.pk, "display_id": event.display_id, "status": event.status, "column": column_for(event, today)}


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
        if models.Invoice.objects.filter(event=event).exists():
            return JsonResponse({"error": f"{event.display_id} has already been invoiced"}, status=409)

        previous = event.status
        event.status = status
        try:
            event.save()
        except ValidationError as e:
            return JsonResponse({"error": " ".join(e.messages)}, status=400)
        reversion.set_user(request.user)
        reversion.set_comment(f"Status changed to {event.get_status_display()} on the Kanban")
        return JsonResponse({**event_json(event, datetime.date.today()), "previous_status": previous})


class EventKanbanInvoice(generic.View):
    http_method_names = ["post"]

    @transaction.atomic()
    def post(self, request, pk):
        event = get_object_or_404(models.Event.objects.select_for_update(), pk=pk)
        if event.cancelled:
            return JsonResponse({"error": f"{event.display_id} is cancelled"}, status=409)
        invoice, created = models.Invoice.objects.get_or_create(event=event)
        if created:
            reversion.set_user(request.user)
            reversion.set_comment("Invoice created on the Kanban")
        return JsonResponse(
            {
                **event_json(event, datetime.date.today()),
                "created": created,
                "invoice": {
                    "pk": invoice.pk,
                    "display_id": invoice.display_id,
                    "url": reverse("invoice_detail", kwargs={"pk": invoice.pk}),
                    "void": invoice.void,
                },
            }
        )
