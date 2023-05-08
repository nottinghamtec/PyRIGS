from django.apps import apps
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import generic
from reversion import revisions as reversion

from RIGS import models, forms
from RIGS.views.rigboard import get_related
from PyRIGS.views import PrintView


class HSCreateView(generic.CreateView):
    def get_form(self, **kwargs):
        form = super().get_form(**kwargs)
        epk = self.kwargs.get('pk')
        event = models.Event.objects.get(pk=epk)
        form.instance.event = event
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        epk = self.kwargs.get('pk')
        event = models.Event.objects.get(pk=epk)
        context['event'] = event
        context['page_title'] = f'Create {self} for Event {event.display_id}'
        return context


class MarkReviewed(generic.View):
    def get(self, *args, **kwargs):
        obj = apps.get_model('RIGS', kwargs.get('model')).objects.get(pk=kwargs.get('pk'))
        with reversion.create_revision():
            reversion.set_user(self.request.user)
            obj.reviewed_by = self.request.user
            obj.reviewed_at = timezone.now()
            obj.save()
        return HttpResponseRedirect(reverse_lazy('hs_list'))


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
            return HttpResponseRedirect(reverse_lazy('ra_edit', kwargs={'pk': ra.pk}))

        return super(EventRiskAssessmentCreate, self).get(self)

    def get_success_url(self):
        return reverse_lazy('ra_detail', kwargs={'pk': self.object.pk})


class EventRiskAssessmentEdit(generic.UpdateView):
    model = models.RiskAssessment
    template_name = 'hs/risk_assessment_form.html'
    form_class = forms.EventRiskAssessmentForm

    def get_success_url(self):
        ra = self.get_object()
        ra.reviewed_by = None
        ra.reviewed_at = None
        ra.save()
        return reverse_lazy('ra_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super(EventRiskAssessmentEdit, self).get_context_data(**kwargs)
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
        context = super(EventRiskAssessmentDetail, self).get_context_data(**kwargs)
        context['page_title'] = f"Risk Assessment for Event <a href='{self.object.event.get_absolute_url()}'>{self.object.event.display_id} {self.object.event.name}</a>"
        return context


class EventRiskAssessmentList(generic.ListView):
    paginate_by = 20
    model = models.RiskAssessment
    template_name = 'hs/hs_object_list.html'

    def get_queryset(self):
        return self.model.objects.exclude(event__status=models.Event.CANCELLED).order_by('reviewed_at').select_related('event')

    def get_context_data(self, **kwargs):
        context = super(EventRiskAssessmentList, self).get_context_data(**kwargs)
        context['title'] = 'Risk Assessment'
        context['view'] = 'ra_detail'
        context['edit'] = 'ra_edit'
        context['review'] = 'ra_review'
        context['perm'] = 'perms.RIGS.review_riskassessment'
        return context


class EventChecklistDetail(generic.DetailView):
    model = models.EventChecklist
    template_name = 'hs/event_checklist_detail.html'

    def get_context_data(self, **kwargs):
        context = super(EventChecklistDetail, self).get_context_data(**kwargs)
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
        return reverse_lazy('ec_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super(EventChecklistEdit, self).get_context_data(**kwargs)
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
            return HttpResponseRedirect(reverse_lazy('event_ra', kwargs={'pk': epk}))

        return super(EventChecklistCreate, self).get(self)

    def get_success_url(self):
        return reverse_lazy('ec_detail', kwargs={'pk': self.object.pk})


class EventChecklistList(generic.ListView):
    paginate_by = 20
    model = models.EventChecklist
    template_name = 'hs/hs_object_list.html'

    def get_queryset(self):
        return self.model.objects.exclude(event__status=models.Event.CANCELLED).order_by('reviewed_at').select_related('event')

    def get_context_data(self, **kwargs):
        context = super(EventChecklistList, self).get_context_data(**kwargs)
        context['title'] = 'Event Checklist'
        context['view'] = 'ec_detail'
        context['edit'] = 'ec_edit'
        context['review'] = 'ec_review'
        context['perm'] = 'perms.RIGS.review_eventchecklist'
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
        return reverse_lazy('ec_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get('pk')
        ec = models.PowerTestRecord.objects.get(pk=pk)
        context['event'] = ec.event
        context['edit'] = True
        context['page_title'] = f'Edit Power Test Record for Event {ec.event.display_id}'
        # get_related(context['form'], context)
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
            return HttpResponseRedirect(reverse_lazy('event_ra', kwargs={'pk': epk}))

        return super().get(self)

    def get_success_url(self):
        return reverse_lazy('pt_detail', kwargs={'pk': self.object.pk})


class HSList(generic.ListView):
    paginate_by = 20
    model = models.Event
    template_name = 'hs/hs_list.html'

    def get_queryset(self):
        return models.Event.objects.all().exclude(status=models.Event.CANCELLED).order_by('-start_date').select_related('riskassessment').prefetch_related('checklists')

    def get_context_data(self, **kwargs):
        context = super(HSList, self).get_context_data(**kwargs)
        context['page_title'] = 'H&S Overview'
        return context


class RAPrint(PrintView):
    model = models.RiskAssessment
    template_name = 'hs/ra_print.xml'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filename'] = f"EventSpecificRiskAssessment_for_{context['object'].event.display_id}.pdf"
        return context
