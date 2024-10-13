from django.apps import apps
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from django.views import generic
from reversion import revisions as reversion

from RIGS import models, forms
from RIGS.views.rigboard import get_related
from PyRIGS.views import PrintView, ModalURLMixin
from django.shortcuts import redirect


class HSCreateView(generic.CreateView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event = models.Event.objects.get(pk=self.kwargs.get('pk'))
        context['event'] = event
        context['page_title'] = f'Create {self.model.__name__} for Event {event.display_id}'
        get_related(context['form'], context)
        return context


class MarkReviewed(generic.RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        obj = apps.get_model('RIGS', kwargs.get('model')).objects.get(pk=kwargs.get('pk'))
        with reversion.create_revision():
            reversion.set_user(self.request.user)
            obj.reviewed_by = self.request.user
            obj.reviewed_at = timezone.now()
            obj.save()
        return self.request.META.get('HTTP_REFERER', reverse('hs_list'))


class EventRiskAssessmentCreate(HSCreateView):
    model = models.RiskAssessment
    template_name = 'hs/risk_assessment_form.html'
    form_class = forms.EventRiskAssessmentForm

    def get(self, *args, **kwargs):
        epk = kwargs.get('pk')
        event = models.Event.objects.get(pk=epk)

        # Check if RA exists
        ra = models.RiskAssessment.objects.filter(event=event).first()

        if ra is not None:
            return HttpResponseRedirect(reverse('ra_edit', kwargs={'pk': ra.pk}))

        return super().get(self)

    def get_success_url(self):
        return reverse('ra_detail', kwargs={'pk': self.object.pk})


class EventRiskAssessmentEdit(generic.UpdateView):
    model = models.RiskAssessment
    template_name = 'hs/risk_assessment_form.html'
    form_class = forms.EventRiskAssessmentForm

    def get_success_url(self):
        ra = self.get_object()
        ra.reviewed_by = None
        ra.reviewed_at = None
        ra.save()
        return reverse('ra_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        rpk = self.kwargs.get('pk')
        ra = models.RiskAssessment.objects.get(pk=rpk)
        context['event'] = ra.event
        context['edit'] = True
        context['page_title'] = f'Edit Risk Assessment for Event {ra.event.display_id}'
        get_related(context['form'], context)
        return context


class EventRiskAssessmentDetail(generic.DetailView):
    model = models.RiskAssessment
    template_name = 'hs/risk_assessment_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f"Risk Assessment for Event <a href='{self.object.event.get_absolute_url()}'>{self.object.event.display_id} {self.object.event.name}</a>"
        return context


class EventChecklistDetail(generic.DetailView):
    model = models.EventChecklist
    template_name = 'hs/event_checklist_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f"Event Checklist for Event <a href='{self.object.event.get_absolute_url()}'>{self.object.event.display_id} {self.object.event.name}</a>"
        return context


class EventChecklistEdit(generic.UpdateView):
    model = models.EventChecklist
    template_name = 'hs/event_checklist_form.html'
    form_class = forms.EventChecklistForm

    def get_success_url(self):
        ec = self.get_object()
        ec.reviewed_by = None
        ec.reviewed_at = None
        ec.save()
        return reverse('ec_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get('pk')
        ec = models.EventChecklist.objects.get(pk=pk)
        context['event'] = ec.event
        context['edit'] = True
        context['page_title'] = f'Edit Event Checklist for Event {ec.event.display_id}'
        get_related(context['form'], context)
        return context


class EventChecklistCreate(HSCreateView):
    model = models.EventChecklist
    template_name = 'hs/event_checklist_form.html'
    form_class = forms.EventChecklistForm

    # From both business logic and programming POVs, RAs must exist before ECs!
    def get(self, *args, **kwargs):
        epk = kwargs.get('pk')
        event = models.Event.objects.get(pk=epk)
        # Check if RA exists
        ra = models.RiskAssessment.objects.filter(event=event).first()
        if ra is None:
            messages.error(self.request, f'A Risk Assessment must exist prior to creating any Event Checklists for {event}! Please create one now.')
            return HttpResponseRedirect(reverse('event_ra', kwargs={'pk': epk}))
        return super().get(self)

    def get_success_url(self):
        return reverse('ec_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if context['event'].venue:
            context['venue'] = context['event'].venue
        return context


class PowerTestDetail(generic.DetailView):
    model = models.PowerTestRecord
    template_name = 'hs/power_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f"Power Test Record for Event <a href='{self.object.event.get_absolute_url()}'>{self.object.event.display_id} {self.object.event.name}</a>"
        return context


class PowerTestEdit(generic.UpdateView):
    model = models.PowerTestRecord
    template_name = 'hs/power_form.html'
    form_class = forms.PowerTestRecordForm

    def get_success_url(self):
        ec = self.get_object()
        ec.reviewed_by = None
        ec.reviewed_at = None
        ec.save()
        return reverse('pt_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get('pk')
        ec = models.PowerTestRecord.objects.get(pk=pk)
        context['event'] = ec.event
        context['edit'] = True
        context['page_title'] = f'Edit Power Test Record for Event {ec.event.display_id}'
        get_related(context['form'], context)
        return context


class PowerTestCreate(HSCreateView):
    model = models.PowerTestRecord
    template_name = 'hs/power_form.html'
    form_class = forms.PowerTestRecordForm

    def get(self, *args, **kwargs):
        epk = kwargs.get('pk')
        event = models.Event.objects.get(pk=epk)
        # Check if RA exists
        ra = models.RiskAssessment.objects.filter(event=event).first()

        if ra is None:
            messages.error(self.request, f'A Risk Assessment must exist prior to creating any Power Test Records for {event}! Please create one now.')
            return HttpResponseRedirect(reverse('event_ra', kwargs={'pk': epk}))

        return super().get(self)

    def get_success_url(self):
        return reverse('pt_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if context['event'].venue:
            context['venue'] = context['event'].venue
        if context['event'].riskassessment.power_mic:
            context['power_mic'] = context['event'].riskassessment.power_mic
        return context


class HSList(generic.ListView):
    paginate_by = 20
    model = models.Event
    template_name = 'hs/hs_list.html'

    def get_queryset(self):
        return models.Event.objects.all().exclude(status=models.Event.CANCELLED).exclude(dry_hire=True).order_by('-start_date').select_related('riskassessment').prefetch_related('checklists')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'H&S Overview'
        return context


class RAPrint(PrintView):
    model = models.RiskAssessment
    template_name = 'hs/ra_print.xml'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filename'] = f"EventSpecificRiskAssessment_for_{context['object'].event.display_id}.pdf"
        return context


class PowerPrint(PrintView):
    model = models.PowerTestRecord
    template_name = 'hs/power_print.xml'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filename'] = f"PowerTestRecord_for_{context['object'].event.display_id}.pdf"
        return context


class EventCheckIn(generic.CreateView, ModalURLMixin):
    model = models.EventCheckIn
    template_name = 'hs/eventcheckin_form.html'
    form_class = forms.EventCheckInForm

    def get_success_url(self):
        return self.get_close_url('event_detail', 'event_detail')  # Well, that's one way of doing that...!

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['event'] = models.Event.objects.get(pk=self.kwargs.get('pk'))
        context['page_title'] = f'Check In to Event {context["event"].display_id}'
        # get_related(context['form'], context)
        return context


class EventCheckInOverride(generic.CreateView):
    model = models.EventCheckIn
    template_name = 'hs/eventcheckin_form.html'
    form_class = forms.EditCheckInForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['event'] = models.Event.objects.get(pk=self.kwargs.get('pk'))
        context['page_title'] = f'Manually add Check In to Event {context["event"].display_id}'
        context['manual'] = True
        return context


class EventCheckInEdit(generic.UpdateView, ModalURLMixin):
    model = models.EventCheckIn
    template_name = 'hs/eventcheckin_form.html'
    form_class = forms.EditCheckInForm

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if not obj.person == self.request.user and not obj.event.mic == self.request.user:
            return redirect(self.request.META.get('HTTP_REFERER', '/'))
        return super().dispatch(request)

    def get_success_url(self):
        return self.get_close_url('event_detail', 'event_detail')  # Well, that's one way of doing that...!

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['event'] = self.object.event
        context['page_title'] = f'Edit Check In for Event {context["event"].display_id}'
        context['edit'] = True
        # get_related(context['form'], context)
        return context


class EventCheckOut(generic.RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        checkin = self.request.user.current_event()
        if checkin:
            checkin.end_time = timezone.now()
            checkin.save()
        return self.request.META.get('HTTP_REFERER', '/')
