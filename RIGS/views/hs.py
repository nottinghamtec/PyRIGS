from datetime import timedelta

from django.apps import apps
from django.contrib import messages
from django.db.models import Exists, OuterRef, Q
from django.db.models.functions import Coalesce
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.views import generic
from reversion import revisions as reversion

from RIGS import models, forms
from RIGS.views.rigboard import get_related
from PyRIGS.views import PrintView, ModalURLMixin
from django.shortcuts import redirect


class HSCreateView(generic.CreateView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event = models.Event.objects.get(pk=self.kwargs.get("pk"))
        context["event"] = event
        context["page_title"] = f"Create {self.model.__name__} for Event {event.display_id}"
        get_related(context["form"], context)
        return context


class MarkReviewed(generic.RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        obj = apps.get_model("RIGS", kwargs.get("model")).objects.get(pk=kwargs.get("pk"))
        with reversion.create_revision():
            reversion.set_user(self.request.user)
            obj.reviewed_by = self.request.user
            obj.reviewed_at = timezone.now()
            obj.save()
        return self.request.META.get("HTTP_REFERER", reverse("hs_list"))


class EventRiskAssessmentCreate(HSCreateView):
    model = models.RiskAssessment
    template_name = "hs/risk_assessment_form.html"
    form_class = forms.EventRiskAssessmentForm

    def get(self, *args, **kwargs):
        epk = kwargs.get("pk")
        event = models.Event.objects.get(pk=epk)

        # Check if RA exists
        ra = models.RiskAssessment.objects.filter(event=event).first()

        if ra is not None:
            return HttpResponseRedirect(reverse("ra_edit", kwargs={"pk": ra.pk}))

        return super().get(self)

    def get_success_url(self):
        return reverse("ra_detail", kwargs={"pk": self.object.pk})


class EventRiskAssessmentEdit(generic.UpdateView):
    model = models.RiskAssessment
    template_name = "hs/risk_assessment_form.html"
    form_class = forms.EventRiskAssessmentForm

    def get_success_url(self):
        ra = self.get_object()
        ra.reviewed_by = None
        ra.reviewed_at = None
        ra.save()
        return reverse("ra_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        rpk = self.kwargs.get("pk")
        ra = models.RiskAssessment.objects.get(pk=rpk)
        context["event"] = ra.event
        context["edit"] = True
        context["page_title"] = f"Edit Risk Assessment for Event {ra.event.display_id}"
        get_related(context["form"], context)
        return context


class EventRiskAssessmentDetail(generic.DetailView):
    model = models.RiskAssessment
    template_name = "hs/risk_assessment_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = (
            f"Risk Assessment for Event <a href='{self.object.event.get_absolute_url()}'>{self.object.event.display_id} {self.object.event.name}</a>"
        )
        return context


class EventChecklistDetail(generic.DetailView):
    model = models.EventChecklist
    template_name = "hs/event_checklist_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = (
            f"Event Checklist for Event <a href='{self.object.event.get_absolute_url()}'>{self.object.event.display_id} {self.object.event.name}</a>"
        )
        return context


class EventChecklistEdit(generic.UpdateView):
    model = models.EventChecklist
    template_name = "hs/event_checklist_form.html"
    form_class = forms.EventChecklistForm

    def get_success_url(self):
        ec = self.get_object()
        ec.reviewed_by = None
        ec.reviewed_at = None
        ec.save()
        return reverse("ec_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get("pk")
        ec = models.EventChecklist.objects.get(pk=pk)
        context["event"] = ec.event
        context["edit"] = True
        context["page_title"] = f"Edit Event Checklist for Event {ec.event.display_id}"
        get_related(context["form"], context)
        return context


class EventChecklistCreate(HSCreateView):
    model = models.EventChecklist
    template_name = "hs/event_checklist_form.html"
    form_class = forms.EventChecklistForm

    # From both business logic and programming POVs, RAs must exist before ECs!
    def get(self, *args, **kwargs):
        epk = kwargs.get("pk")
        event = models.Event.objects.get(pk=epk)
        # Check if RA exists
        ra = models.RiskAssessment.objects.filter(event=event).first()
        if ra is None:
            messages.error(
                self.request,
                f"A Risk Assessment must exist prior to creating any Event Checklists for {event}! Please create one now.",
            )
            return HttpResponseRedirect(reverse("event_ra", kwargs={"pk": epk}))
        return super().get(self)

    def get_success_url(self):
        return reverse("ec_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if context["event"].venue:
            context["venue"] = context["event"].venue
        return context


class PowerTestDetail(generic.DetailView):
    model = models.PowerTestRecord
    template_name = "hs/power_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = (
            f"Power Test Record for Event <a href='{self.object.event.get_absolute_url()}'>{self.object.event.display_id} {self.object.event.name}</a>"
        )
        return context


class PowerTestEdit(generic.UpdateView):
    model = models.PowerTestRecord
    template_name = "hs/power_form.html"
    form_class = forms.PowerTestRecordForm

    def get_success_url(self):
        ec = self.get_object()
        ec.reviewed_by = None
        ec.reviewed_at = None
        ec.save()
        return reverse("pt_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get("pk")
        ec = models.PowerTestRecord.objects.get(pk=pk)
        context["event"] = ec.event
        context["edit"] = True
        context["page_title"] = f"Edit Power Test Record for Event {ec.event.display_id}"
        get_related(context["form"], context)
        return context


class PowerTestCreate(HSCreateView):
    model = models.PowerTestRecord
    template_name = "hs/power_form.html"
    form_class = forms.PowerTestRecordForm

    def get(self, *args, **kwargs):
        epk = kwargs.get("pk")
        event = models.Event.objects.get(pk=epk)
        # Check if RA exists
        ra = models.RiskAssessment.objects.filter(event=event).first()

        if ra is None:
            messages.error(
                self.request,
                f"A Risk Assessment must exist prior to creating any Power Test Records for {event}! Please create one now.",
            )
            return HttpResponseRedirect(reverse("event_ra", kwargs={"pk": epk}))

        return super().get(self)

    def get_success_url(self):
        return reverse("pt_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if context["event"].venue:
            context["venue"] = context["event"].venue
        if context["event"].riskassessment.power_mic:
            context["power_mic"] = context["event"].riskassessment.power_mic
        return context


class HSList(generic.ListView):
    paginate_by = 20
    model = models.Event
    template_name = "hs/hs_list.html"
    modern_template_name = "hs/hs_list_modern.html"
    legacy_template_name = "hs/hs_list_legacy.html"

    @property
    def use_legacy(self):
        return bool(self.request.GET.get("legacy"))

    def get_template_names(self):
        return [self.legacy_template_name if self.use_legacy else self.modern_template_name]

    @cached_property
    def options(self):
        """The display options in force (order, date range, only needing action).

        Submitting the options form saves the choices on the user's account; otherwise their saved choices are used.
        """
        user = self.request.user
        params = self.request.GET
        order, date_range, only_action = user.hs_order, user.hs_range, user.hs_only_action
        if self.use_legacy:
            return {"order": "newest", "range": "all", "only_action": False}
        if {"order", "range", "action"} & params.keys():
            if params.get("order") in dict(models.Profile.HS_ORDER_CHOICES):
                order = params["order"]
            if params.get("range") in dict(models.Profile.HS_RANGE_CHOICES):
                date_range = params["range"]
            only_action = params.get("action") == "1"
            if (order, date_range, only_action) != (user.hs_order, user.hs_range, user.hs_only_action):
                user.hs_order, user.hs_range, user.hs_only_action = order, date_range, only_action
                user.save(update_fields=["hs_order", "hs_range", "hs_only_action"])
        return {"order": order, "range": date_range, "only_action": only_action}

    @property
    def only_needing_action(self):
        return self.options["only_action"]

    @staticmethod
    def rag_filters():
        """Querysets filters mirroring Event.hs_rag_status; only confirmed events get a red or amber"""
        confirmed = Q(status__in=[models.Event.CONFIRMED, models.Event.BOOKED])
        red = confirmed & (Q(mic__isnull=True) | Q(riskassessment__isnull=True))
        unreviewed_power = Exists(models.PowerTestRecord.objects.filter(event=OuterRef("pk"), reviewed_by__isnull=True))
        amber = (
            confirmed
            & Q(mic__isnull=False, riskassessment__isnull=False)
            & (Q(riskassessment__reviewed_by__isnull=True) | unreviewed_power)
        )
        return red, amber

    def get_base_queryset(self):
        """Events within the chosen date range; the order is applied separately"""
        queryset = (
            models.Event.objects.all()
            .exclude(status=models.Event.CANCELLED)
            .exclude(dry_hire=True)
            .annotate(last_day=Coalesce("end_date", "start_date"))
        )
        today = timezone.localdate()
        if self.options["range"] == "upcoming":
            queryset = queryset.filter(last_day__gte=today)
        elif self.options["range"] == "recent":
            queryset = queryset.filter(last_day__gte=today - timedelta(days=14))
        return queryset

    def get_ordering(self):
        if self.use_legacy:
            return ["-start_date"]
        # Same order as the rigboard, soonest first (or the reverse)
        fields = ["start_date", "end_date", "start_time", "end_time", "meet_at", "pk"]
        if self.options["order"] == "newest":
            return [f"-{field}" for field in fields]
        return fields

    def get_queryset(self):
        queryset = (
            self.get_base_queryset()
            .order_by(*self.get_ordering())
            .select_related("riskassessment", "riskassessment__reviewed_by", "mic")
        )
        queryset = queryset.prefetch_related(
            "checklists", "checklists__reviewed_by", "power_tests", "power_tests__reviewed_by"
        )
        if self.only_needing_action:
            red, amber = self.rag_filters()
            queryset = queryset.filter(red | amber)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "H&S Overview"
        if not self.use_legacy:
            context["only_needing_action"] = self.only_needing_action
            context["order"] = self.options["order"]
            context["date_range"] = self.options["range"]
            context["order_choices"] = models.Profile.HS_ORDER_CHOICES
            context["range_choices"] = models.Profile.HS_RANGE_CHOICES
            context["summary"] = self.get_summary()
        return context

    def get_summary(self):
        """How many events (across every page) are currently red or amber"""
        red, amber = self.rag_filters()
        base = self.get_base_queryset()
        return {"red": base.filter(red).count(), "amber": base.filter(amber).count()}


class RAPrint(PrintView):
    model = models.RiskAssessment
    template_name = "hs/ra_print.xml"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filename"] = f"EventSpecificRiskAssessment_for_{context['object'].event.display_id}.pdf"
        return context


class PowerPrint(PrintView):
    model = models.PowerTestRecord
    template_name = "hs/power_print.xml"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filename"] = f"PowerTestRecord_for_{context['object'].event.display_id}.pdf"
        return context


class EventCheckIn(generic.CreateView, ModalURLMixin):
    model = models.EventCheckIn
    template_name = "hs/eventcheckin_form.html"
    form_class = forms.EventCheckInForm

    def get_success_url(self):
        return self.get_close_url("event_detail", "event_detail")  # Well, that's one way of doing that...!

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["event"] = models.Event.objects.get(pk=self.kwargs.get("pk"))
        context["page_title"] = f"Check In to Event {context['event'].display_id}"
        # get_related(context['form'], context)
        return context


class EventCheckInOverride(generic.CreateView):
    model = models.EventCheckIn
    template_name = "hs/eventcheckin_form.html"
    form_class = forms.EditCheckInForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["event"] = models.Event.objects.get(pk=self.kwargs.get("pk"))
        context["page_title"] = f"Manually add Check In to Event {context['event'].display_id}"
        context["manual"] = True
        return context


class EventCheckInEdit(generic.UpdateView, ModalURLMixin):
    model = models.EventCheckIn
    template_name = "hs/eventcheckin_form.html"
    form_class = forms.EditCheckInForm

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if not obj.person == self.request.user and not obj.event.mic == self.request.user:
            return redirect(self.request.META.get("HTTP_REFERER", "/"))
        return super().dispatch(request)

    def get_success_url(self):
        return self.get_close_url("event_detail", "event_detail")  # Well, that's one way of doing that...!

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["event"] = self.object.event
        context["page_title"] = f"Edit Check In for Event {context['event'].display_id}"
        context["edit"] = True
        # get_related(context['form'], context)
        return context


class EventCheckOut(generic.RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        checkin = self.request.user.current_event()
        if checkin:
            checkin.end_time = timezone.now()
            checkin.save()
        return self.request.META.get("HTTP_REFERER", "/")


class EventCheckOutCorrect(generic.UpdateView):
    model = models.EventCheckIn
    template_name = "hs/eventcheckout_form.html"
    form_class = forms.EventCheckOutForm

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.person != request.user and obj.event.mic != request.user:
            return redirect("event_detail", pk=obj.event_id)
        if obj.end_time:
            messages.info(request, "You are already checked out of this event.")
            return redirect("event_detail", pk=obj.event_id)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["event"] = self.object.event
        context["page_title"] = f"Check Out of Event {self.object.event.display_id}"
        return context


class CurrentlyCheckedIn(generic.ListView):
    template_name = "hs/currently_checked_in.html"
    context_object_name = "checkins"

    def get_queryset(self):
        return (
            models.EventCheckIn.objects.filter(end_time__isnull=True).select_related("person", "event").order_by("time")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Currently Checked In"
        return context
