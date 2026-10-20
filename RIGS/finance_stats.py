"""Figures for the finance dashboard.

Everything here costs a fixed number of queries however much history there is: totals are summed by the database,
and the few figures it can't work out portably (medians, quartiles) come from one narrow fetch of dates.
"""

import datetime
import statistics
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from django.db.models import Count, DecimalField, F, Min, OuterRef, Q, Subquery, Sum, Value
from django.db.models.functions import Coalesce, TruncMonth
from django.urls import reverse

from RIGS import models

# Years follow the academic year, September to August
ACADEMIC_YEAR_START_MONTH = 9
# Anything earlier is a mistyped year rather than a real payment
EARLIEST_PLAUSIBLE_DATE = datetime.date(2000, 1, 1)
# Well above the largest genuine payments on record (around £50k), so anything bigger is worth a second look
SUSPICIOUSLY_LARGE_PAYMENT = Decimal("75000")

MONEY = DecimalField(max_digits=12, decimal_places=2)
ZERO = Decimal("0.00")

ROLLING_PERIODS = {
    "week": ("Last week (7 days)", 7),
    "month": ("Last month (30 days)", 30),
    "year": ("Last year (365 days)", 365),
}

# Payments recorded before methods existed have none, and SU Core has since been retired as a choice
PAYMENT_METHOD_NAMES = {**dict(models.Payment.METHODS), "": "Not recorded", "SU": "SU Core"}
# Each method keeps its colour whichever period is shown (0 is the neutral grey). Adjustments aren't income, so
# they never appear in the income charts.
PAYMENT_METHOD_SERIES = {models.Payment.EXTERNAL: 1, models.Payment.INTERNAL: 2, models.Payment.CASH: 3, "SU": 4, "": 0}

AGE_BANDS = [("0-30 days", 0, 30), ("31-90 days", 31, 90), ("91-365 days", 91, 365), ("Over a year", 366, None)]
DAYS_TO_PAY_BANDS = [
    ("Before invoice", None, -1),
    ("Same day", 0, 0),
    ("1-7 days", 1, 7),
    ("8-30 days", 8, 30),
    ("31-90 days", 31, 90),
    ("91-365 days", 91, 365),
    ("Over a year", 366, None),
]
INVOICE_DELAY_BANDS = [
    ("Before the event ended", None, -1),
    ("Within a week", 0, 7),
    ("1-4 weeks", 8, 28),
    ("1-3 months", 29, 91),
    ("Over 3 months", 92, None),
]

QUALITY_LIST_LIMIT = 20


def band_of(value, bands):
    for index, (_, low, high) in enumerate(bands):
        if (low is None or value >= low) and (high is None or value <= high):
            return index


def band_counts(values, bands):
    counts = [0] * len(bands)
    for value in values:
        counts[band_of(value, bands)] += 1
    return counts


def academic_year_of(day):
    return day.year if day.month >= ACADEMIC_YEAR_START_MONTH else day.year - 1


def academic_year_label(year):
    return f"{year}/{(year + 1) % 100:02d}"


def academic_year_bounds(year):
    return (
        datetime.date(year, ACADEMIC_YEAR_START_MONTH, 1),
        datetime.date(year + 1, ACADEMIC_YEAR_START_MONTH, 1) - datetime.timedelta(days=1),
    )


def shift_years(day, years):
    try:
        return day.replace(year=day.year + years)
    except ValueError:  # 29th February
        return day.replace(year=day.year + years, day=28)


def format_date(day):
    # strftime can't be trusted with the odd mistyped two-digit year
    return f"{day.day:02d}/{day.month:02d}/{day.year:04d}"


@dataclass(frozen=True)
class Period:
    key: str
    label: str
    start: datetime.date | None  # None for since records began
    end: datetime.date  # Inclusive

    def filter(self, queryset, field):
        if self.start is not None:
            queryset = queryset.filter(**{f"{field}__gte": self.start})
        return queryset.filter(**{f"{field}__lte": self.end})

    @property
    def academic_year(self):
        return int(self.key[2:]) if self.key.startswith("ay") else None


def get_period(key, today):
    if key in ROLLING_PERIODS:
        label, days = ROLLING_PERIODS[key]
        return Period(key, label, today - datetime.timedelta(days=days), today)
    if key.startswith("ay") and key[2:].isdigit():
        year = int(key[2:])
        start, end = academic_year_bounds(year)
        if start <= today:
            return Period(key, f"Academic year {academic_year_label(year)}", start, min(end, today))
    return Period("all", "All time", None, today)


def previous_period(period):
    """The period to compare against: the one just before, or for a year still in progress, the same point last year"""
    if period.start is None:
        return None
    if period.academic_year is not None:
        year = period.academic_year - 1
        start, end = academic_year_bounds(year)
        if period.end < academic_year_bounds(period.academic_year)[1]:
            return Period(
                f"ay{year}", f"the same point in {academic_year_label(year)}", start, shift_years(period.end, -1)
            )
        return Period(f"ay{year}", academic_year_label(year), start, end)
    end = period.start - datetime.timedelta(days=1)
    return Period(
        "previous", f"the {ROLLING_PERIODS[period.key][1]} days before", end - (period.end - period.start), end
    )


def period_options(today):
    first = models.Event.objects.filter(is_rig=True).aggregate(first=Min("start_date"))["first"] or today
    first = max(first, EARLIEST_PLAUSIBLE_DATE)
    return {
        "rolling": [(key, label) for key, (label, _) in ROLLING_PERIODS.items()],
        "academic_years": [
            (f"ay{year}", academic_year_label(year))
            for year in range(academic_year_of(today), academic_year_of(min(first, today)) - 1, -1)
        ],
    }


def finished_rigs(today):
    """Rigs that have happened: cancelled ones and those still to finish aren't work done"""
    return (
        models.Event.objects.filter(is_rig=True)
        .exclude(status=models.Event.CANCELLED)
        .filter(Q(end_date__lte=today) | Q(end_date__isnull=True, start_date__lte=today))
    )


def item_total(event_ref):
    """The ex. VAT value of an event's items, as a subquery so it can't multiply rows of anything else being summed"""
    totals = (
        models.EventItem.objects.filter(event=event_ref)
        .order_by()
        .values("event")
        .annotate(total=Sum(F("cost") * F("quantity"), output_field=MONEY))
        .values("total")
    )
    return Coalesce(Subquery(totals), Value(ZERO), output_field=MONEY)


def payment_total(invoice_ref):
    totals = (
        models.Payment.objects.filter(invoice=invoice_ref)
        .order_by()
        .values("invoice")
        .annotate(total=Sum("amount"))
        .values("total")
    )
    return Coalesce(Subquery(totals), Value(ZERO), output_field=MONEY)


def with_totals(invoices):
    return invoices.annotate(value=item_total(OuterRef("event")), paid=payment_total(OuterRef("pk")))


def client_of(event):
    if event.organisation_id:
        return (
            ("organisation", event.organisation_id),
            event.organisation.name,
            reverse("organisation_detail", kwargs={"pk": event.organisation_id}),
        )
    if event.person_id:
        return ("person", event.person_id), event.person.name, reverse("person_detail", kwargs={"pk": event.person_id})
    return None, "No client", None


def summarise(period, today):
    payments = period.filter(models.Payment.objects.all(), "date")
    by_method = {
        row["method"]: row["total"] for row in payments.values("method").annotate(total=Sum("amount")).order_by()
    }
    durations = [(paid - invoiced).days for paid, invoiced in payments.values_list("date", "invoice__invoice_date")]
    return {
        "period": period,
        "events": period.filter(finished_rigs(today), "start_date").count(),
        **period.filter(models.Invoice.objects.all(), "invoice_date").aggregate(
            invoices=Count("pk", filter=Q(void=False)), void_invoices=Count("pk", filter=Q(void=True))
        ),
        "payments": len(durations),
        # Adjustments are corrections rather than money received, so they're kept apart from income
        "income": sum((total for method, total in by_method.items() if method != models.Payment.ADJUSTMENT), ZERO),
        "adjustments": by_method.get(models.Payment.ADJUSTMENT, ZERO),
        # The median, as a handful of mistyped or backdated payments can drag a mean years off
        "median_days_to_pay": statistics.median(durations) if durations else None,
        "by_method": by_method,
        "durations": durations,
    }


def delta(current, previous, key, previous_label, lower_is_better=False):
    """A summary figure's change on the period before, worded for its card"""
    if previous is None or current[key] is None or previous[key] is None:
        return None
    if key == "median_days_to_pay":
        change = current[key] - previous[key]
        amount = f"{abs(change):g} day{'' if abs(change) == 1 else 's'}"
    else:
        if not previous[key]:
            return None
        change = (current[key] - previous[key]) / abs(previous[key]) * 100
        amount = f"{abs(change):.0f}%"
    if round(change) == 0:
        return {"text": f"No change on {previous_label}", "tone": "secondary", "icon": "fa-equals"}
    better = (change < 0) if lower_is_better else (change > 0)
    return {
        "text": f"{amount} {'up' if change > 0 else 'down'} on {previous_label}",
        "tone": "success" if better else "danger",
        "icon": "fa-arrow-up" if change > 0 else "fa-arrow-down",
    }


def payment_method_rows(summary):
    income = summary["income"]
    rows = [
        {
            "method": PAYMENT_METHOD_NAMES.get(method, f"Unknown method ({method})"),
            "series": PAYMENT_METHOD_SERIES.get(method, 0),
            "total": total,
            "share": float(total / income * 100) if income else 0,
        }
        for method, total in summary["by_method"].items()
        if method != models.Payment.ADJUSTMENT
    ]
    return sorted(rows, key=lambda row: -row["total"])


def internal_split(period):
    """Income from union accounts (internal) against everyone else"""
    rows = (
        period.filter(models.Payment.objects.exclude(method=models.Payment.ADJUSTMENT), "date")
        .values("invoice__event__organisation__union_account")
        .annotate(total=Sum("amount"))
        .order_by()
    )
    split = {"internal": ZERO, "external": ZERO}
    for row in rows:
        split["internal" if row["invoice__event__organisation__union_account"] else "external"] += row["total"]
    total = split["internal"] + split["external"]
    split["internal_share"] = float(split["internal"] / total * 100) if total else 0
    return split


def top_clients_by_income(period, limit=10):
    rows = (
        period.filter(models.Payment.objects.exclude(method=models.Payment.ADJUSTMENT), "date")
        .values(
            "invoice__event__organisation",
            "invoice__event__organisation__name",
            "invoice__event__person",
            "invoice__event__person__name",
        )
        .annotate(total=Sum("amount"))
        .order_by()
    )
    clients = {}
    for row in rows:
        if row["invoice__event__organisation"]:
            key = ("organisation", row["invoice__event__organisation"])
            name, url = row["invoice__event__organisation__name"], reverse("organisation_detail", kwargs={"pk": key[1]})
        elif row["invoice__event__person"]:
            key = ("person", row["invoice__event__person"])
            name, url = row["invoice__event__person__name"], reverse("person_detail", kwargs={"pk": key[1]})
        else:
            key, name, url = None, "No client", None
        client = clients.setdefault(key, {"name": name, "url": url, "total": ZERO})
        client["total"] += row["total"]
    return sorted(clients.values(), key=lambda client: -client["total"])[:limit]


def outstanding_invoices(today):
    """Invoices with money still owed, each carrying its balance and age"""
    # The raw query has already worked out each invoice's cost and payments, so there's no need to ask again
    balances = {
        row.pk: Decimal(str(row.cost)) - Decimal(str(row.payments or 0))
        for row in models.Invoice.objects.outstanding_invoices()
    }
    invoices = list(
        models.Invoice.objects.filter(pk__in=balances)
        .select_related("event__organisation", "event__person")
        .order_by("invoice_date", "pk")
    )
    for invoice in invoices:
        invoice.outstanding_balance = balances[invoice.pk]
        invoice.age_days = (today - invoice.invoice_date).days
        invoice.client_key, invoice.client_name, invoice.client_url = client_of(invoice.event)
    return invoices


def aged_debt(outstanding):
    bands = [{"label": label, "count": 0, "total": ZERO, "invoices": []} for label, _, _ in AGE_BANDS]
    for invoice in outstanding:
        band = bands[band_of(invoice.age_days, AGE_BANDS)]
        band["count"] += 1
        band["total"] += invoice.outstanding_balance
        band["invoices"].append(invoice)
    return bands


def outstanding_by_client(outstanding, limit=10):
    clients = {}
    for invoice in outstanding:
        client = clients.setdefault(
            invoice.client_key, {"name": invoice.client_name, "url": invoice.client_url, "total": ZERO, "count": 0}
        )
        client["total"] += invoice.outstanding_balance
        client["count"] += 1
    return sorted(clients.values(), key=lambda client: -client["total"])[:limit]


def waiting_total():
    return models.EventItem.objects.filter(event__in=models.Event.objects.waiting_invoices().values("pk")).aggregate(
        total=Coalesce(Sum(F("cost") * F("quantity"), output_field=MONEY), Value(ZERO), output_field=MONEY)
    )["total"]


def invoicing_delay(period):
    """How long after an event finished it was invoiced"""
    delays = [
        (invoiced - (ended or started)).days
        for invoiced, started, ended in period.filter(
            models.Invoice.objects.filter(void=False), "invoice_date"
        ).values_list("invoice_date", "event__start_date", "event__end_date")
    ]
    return {
        "median": statistics.median(delays) if delays else None,
        "count": len(delays),
        "labels": [label for label, _, _ in INVOICE_DELAY_BANDS],
        "counts": band_counts(delays, INVOICE_DELAY_BANDS),
    }


def funnel(period, today):
    """How the work done in a period has made its way through invoicing to being paid"""
    events = period.filter(finished_rigs(today), "start_date")
    rows = list(events.annotate(value=item_total(OuterRef("pk"))).values_list("value", "invoice__pk", "invoice__void"))
    paid = {
        row["invoice"]: row["total"]
        for row in models.Payment.objects.filter(invoice__event__in=events.values("pk"))
        .values("invoice")
        .annotate(total=Sum("amount"))
        .order_by()
    }
    invoiced = [(value, invoice) for value, invoice, void in rows if invoice is not None and not void]
    settled = [(value, invoice) for value, invoice in invoiced if paid.get(invoice, ZERO) >= value]
    voided = sum(1 for _, invoice, void in rows if invoice is not None and void)
    not_invoiced = sum(1 for _, invoice, _ in rows if invoice is None)
    return [
        {"label": "Events done", "count": len(rows), "value": sum((value for value, _, _ in rows), ZERO), "note": ""},
        {
            "label": "Invoiced",
            "count": len(invoiced),
            "value": sum((value for value, _ in invoiced), ZERO),
            "note": f"{voided} voided, {not_invoiced} not invoiced yet",
        },
        {
            "label": "Paid in full",
            "count": len(settled),
            "value": sum((value for value, _ in settled), ZERO),
            "note": f"{len(invoiced) - len(settled)} still owed",
        },
    ]


def _method_datasets(totals, keys):
    """One dataset per payment method, in the methods' fixed colour order"""
    methods = sorted({method for method, _ in totals}, key=lambda m: (PAYMENT_METHOD_SERIES.get(m, 0) or 99, m))
    return [
        {
            "label": PAYMENT_METHOD_NAMES.get(method, f"Unknown method ({method})"),
            "series": PAYMENT_METHOD_SERIES.get(method, 0),
            "data": [float(totals.get((method, key), 0)) for key in keys],
        }
        for method in methods
    ]


def income_over_time(period, today):
    """Income in a period, stacked by payment method, in days, months or academic years depending on its length"""
    payments = period.filter(
        models.Payment.objects.exclude(method=models.Payment.ADJUSTMENT).filter(date__gte=EARLIEST_PLAUSIBLE_DATE),
        "date",
    ).order_by()
    span = None if period.start is None else (period.end - period.start).days
    if span is not None and span <= 62:
        totals = {
            (row["method"], row["date"]): row["total"]
            for row in payments.values("method", "date").annotate(total=Sum("amount"))
        }
        keys = [period.start + datetime.timedelta(days=offset) for offset in range(span + 1)]
        labels = [f"{day.day} {day:%b}" for day in keys]
    else:
        monthly = payments.annotate(month=TruncMonth("date")).values("method", "month").annotate(total=Sum("amount"))
        totals = defaultdict(Decimal)
        if span is not None and span <= 800:
            for row in monthly:
                totals[(row["method"], row["month"])] += row["total"]
            keys, month = [], period.start.replace(day=1)
            while month <= period.end:
                keys.append(month)
                month = (month + datetime.timedelta(days=32)).replace(day=1)
            labels = [f"{month:%b %Y}" for month in keys]
        else:
            for row in monthly:
                totals[(row["method"], academic_year_of(row["month"]))] += row["total"]
            years = [year for _, year in totals] or [academic_year_of(today)]
            keys = list(range(min(years), academic_year_of(today) + 1))
            labels = [academic_year_label(year) for year in keys]
    return {"labels": labels, "datasets": _method_datasets(totals, keys)}


def seasonality(today):
    """Income for each month of every academic year, to show when in the year the money comes in"""
    totals = defaultdict(Decimal)
    for row in (
        models.Payment.objects.exclude(method=models.Payment.ADJUSTMENT)
        .filter(date__gte=EARLIEST_PLAUSIBLE_DATE, date__lte=today)
        .annotate(month=TruncMonth("date"))
        .values("month")
        .annotate(total=Sum("amount"))
        .order_by()
    ):
        totals[row["month"]] += row["total"]
    if not totals:
        return None
    months = [(ACADEMIC_YEAR_START_MONTH - 1 + offset) % 12 + 1 for offset in range(12)]
    # Shaded by rank rather than size, so one exceptional (or mistyped) month can't wash out every other
    ranked = sorted(value for value in totals.values() if value > 0)
    rank = {value: index for index, value in enumerate(ranked)}
    rows = []
    for year in range(academic_year_of(today), academic_year_of(min(totals)) - 1, -1):
        cells = []
        for month in months:
            day = datetime.date(year if month >= ACADEMIC_YEAR_START_MONTH else year + 1, month, 1)
            value = totals.get(day, ZERO)
            # Seven steps of the sequential ramp, 0 being nothing at all
            step = 0 if value <= 0 else rank[value] * 7 // len(ranked) + 1
            cells.append({"label": f"{day:%b %Y}", "value": value, "step": step, "future": day > today})
        rows.append(
            {"year": academic_year_label(year), "cells": cells, "total": sum((c["value"] for c in cells), ZERO)}
        )
    return {"months": [datetime.date(2000, month, 1).strftime("%b") for month in months], "rows": rows}


def days_to_pay_by_year(history):
    """The spread of payment times in each academic year: the middle half, and the median"""
    by_year = defaultdict(list)
    for payment in history:
        if payment["date"] >= EARLIEST_PLAUSIBLE_DATE:
            by_year[academic_year_of(payment["date"])].append(payment["days"])
    years = sorted(by_year)
    quartiles = [
        statistics.quantiles(by_year[year], n=4) if len(by_year[year]) > 1 else by_year[year] * 3 for year in years
    ]
    return {
        "labels": [academic_year_label(year) for year in years],
        "lower": [q[0] for q in quartiles],
        "median": [q[1] for q in quartiles],
        "upper": [q[2] for q in quartiles],
    }


def cumulative_income(period, today):
    """Income built up week by week through an academic year, against the year before"""
    year = period.academic_year if period.academic_year is not None else academic_year_of(today)
    start, end = academic_year_bounds(year)
    last_start, _ = academic_year_bounds(year - 1)
    daily = {
        row["date"]: row["total"]
        for row in models.Payment.objects.exclude(method=models.Payment.ADJUSTMENT)
        .filter(date__gte=last_start, date__lte=min(end, today))
        .values("date")
        .annotate(total=Sum("amount"))
        .order_by()
    }

    def series(year_start, stop):
        points, running, day = [], ZERO, year_start
        for week in range(53):
            week_end = year_start + datetime.timedelta(days=7 * week + 6)
            if week_end > stop + datetime.timedelta(days=6):
                points.append(None)
                continue
            while day <= min(week_end, stop):
                running += daily.get(day, ZERO)
                day += datetime.timedelta(days=1)
            points.append(float(running))
        return points

    weeks = [start + datetime.timedelta(days=7 * week) for week in range(53)]
    return {
        "labels": [f"{day.day} {day:%b}" for day in weeks],
        "datasets": [
            {"label": academic_year_label(year), "series": 1, "data": series(start, min(end, today))},
            {
                "label": academic_year_label(year - 1),
                "series": 0,
                "data": series(last_start, start - datetime.timedelta(days=1)),
            },
        ],
    }


def payment_history():
    """Every payment's dates, fetched once for the figures that need to look at each one"""
    return [
        {
            "pk": pk,
            "date": paid,
            "amount": amount,
            "invoice": invoice,
            "invoice_date": invoiced,
            "void": void,
            "event": event,
            "days": (paid - invoiced).days,
        }
        for pk, paid, amount, invoice, invoiced, void, event in models.Payment.objects.values_list(
            "pk", "date", "amount", "invoice", "invoice__invoice_date", "invoice__void", "invoice__event__name"
        ).order_by("date", "pk")
    ]


def _payment_item(payment):
    return {
        "url": reverse("invoice_detail", kwargs={"pk": payment["invoice"]}),
        "label": f"£{payment['amount']} paid {format_date(payment['date'])} against #{payment['invoice']:05d}",
        "detail": f"{payment['event']}, invoiced {format_date(payment['invoice_date'])}",
    }


def _invoice_item(invoice, detail):
    return {
        "url": reverse("invoice_detail", kwargs={"pk": invoice.pk}),
        "label": f"{invoice.display_id}: {invoice.event.name}",
        "detail": detail,
    }


def _check(title, description, items):
    return {"title": title, "description": description, "count": len(items), "items": items[:QUALITY_LIST_LIMIT]}


def data_quality(today, history, outstanding):
    """Records that look wrong, each with links to put them right. Only checks that find something are returned."""
    cancelled_empty = (
        with_totals(models.Invoice.objects.filter(void=False, event__status=models.Event.CANCELLED))
        .filter(value=0, payment__isnull=True)
        .select_related("event")
        .order_by("invoice_date")
    )
    overpaid = (
        with_totals(models.Invoice.objects.filter(void=False))
        .filter(paid__gt=F("value"))
        .select_related("event")
        .order_by("invoice_date")
    )
    checks = [
        _check(
            "Payments with impossible dates",
            "Dated before 2000 or in the future, so probably a typo in the year.",
            [_payment_item(p) for p in history if p["date"] < EARLIEST_PLAUSIBLE_DATE or p["date"] > today],
        ),
        _check(
            "Unusually large payments",
            f"£{SUSPICIOUSLY_LARGE_PAYMENT:,.0f} or more in one go, which is far beyond any real rig. "
            "Placeholder or joke entries like these inflate income totals.",
            [_payment_item(p) for p in history if p["amount"] >= SUSPICIOUSLY_LARGE_PAYMENT],
        ),
        _check(
            "Payments against void invoices",
            "These still count towards income, though the invoice they were paid against has been voided.",
            [_payment_item(p) for p in history if p["void"] and p["amount"]],
        ),
        _check(
            "Payments dated well before their invoice",
            "Paid more than 30 days before the invoice date: either the payment or the invoice is misdated, "
            "and they make payment times look shorter than they are.",
            [_payment_item(p) for p in history if p["days"] < -30 and p["date"] >= EARLIEST_PLAUSIBLE_DATE],
        ),
        _check(
            "Invoices owed for over a year",
            "Likely to need chasing, writing off or voiding.",
            [
                _invoice_item(i, f"£{i.outstanding_balance:.2f} owed since {format_date(i.invoice_date)}")
                for i in outstanding
                if i.age_days > 365
            ],
        ),
        _check(
            "Empty invoices for cancelled events",
            "Nothing to pay and nothing paid. Voiding them stops them padding out the invoice count.",
            [_invoice_item(i, f"Invoiced {format_date(i.invoice_date)}") for i in cancelled_empty],
        ),
        _check(
            "Overpaid invoices",
            "More has been paid than the invoice is worth.",
            [_invoice_item(i, f"Worth £{i.value:.2f}, paid £{i.paid:.2f}") for i in overpaid],
        ),
    ]
    return [check for check in checks if check["count"]]


def build_dashboard(time_filter, today):
    period = get_period(time_filter, today)
    previous = previous_period(period)
    current = summarise(period, today)
    before = summarise(previous, today) if previous else None
    compare_to = previous.label if previous else None

    outstanding = outstanding_invoices(today)
    aged = aged_debt(outstanding)
    history = payment_history()
    delay = invoicing_delay(period)
    stages = funnel(period, today)

    return {
        "period": period,
        "previous_period": previous,
        "period_options": period_options(today),
        "summary": current,
        "deltas": {
            "events": delta(current, before, "events", compare_to),
            "invoices": delta(current, before, "invoices", compare_to),
            "income": delta(current, before, "income", compare_to),
            "median_days_to_pay": delta(current, before, "median_days_to_pay", compare_to, lower_is_better=True),
        },
        "payment_methods": payment_method_rows(current),
        "internal_split": internal_split(period),
        "top_clients": top_clients_by_income(period),
        "total_waiting": waiting_total(),
        "total_outstanding": sum((i.outstanding_balance for i in outstanding), ZERO),
        "outstanding_count": len(outstanding),
        "aged_debt": aged,
        "outstanding_clients": outstanding_by_client(outstanding),
        "invoicing_delay": delay,
        "funnel": stages,
        "seasonality": seasonality(today),
        "data_quality": data_quality(today, history, outstanding),
        "charts": {
            "income": income_over_time(period, today),
            "cumulative": cumulative_income(period, today),
            "daysToPay": {
                "labels": [label for label, _, _ in DAYS_TO_PAY_BANDS],
                "counts": band_counts(current["durations"], DAYS_TO_PAY_BANDS),
            },
            "daysToPayByYear": days_to_pay_by_year(history),
            "invoicingDelay": {"labels": delay["labels"], "counts": delay["counts"]},
            "funnel": {
                "labels": [stage["label"] for stage in stages],
                "counts": [stage["count"] for stage in stages],
                "values": [float(stage["value"]) for stage in stages],
            },
            "agedDebt": {
                "labels": [band["label"] for band in aged],
                "totals": [float(band["total"]) for band in aged],
                "counts": [band["count"] for band in aged],
            },
        },
    }
