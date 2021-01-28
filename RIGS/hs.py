from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import generic
from reversion import revisions as reversion

from RIGS import models, forms


class EventRiskAssessmentCreate(generic.CreateView):
    model = models.RiskAssessment
    template_name = 'risk_assessment_form.html'
    form_class = forms.EventRiskAssessmentForm

    def get(self, *args, **kwargs):
        epk = kwargs.get('pk')
        event = models.Event.objects.get(pk=epk)

        # Check if RA exists
        ra = models.RiskAssessment.objects.filter(event=event).first()

        if ra is not None:
            return HttpResponseRedirect(reverse_lazy('ra_edit', kwargs={'pk': ra.pk}))

        return super(EventRiskAssessmentCreate, self).get(self)

    def get_form(self, **kwargs):
        form = super(EventRiskAssessmentCreate, self).get_form(**kwargs)
        epk = self.kwargs.get('pk')
        event = models.Event.objects.get(pk=epk)
        form.instance.event = event
        return form

    def get_context_data(self, **kwargs):
        context = super(EventRiskAssessmentCreate, self).get_context_data(**kwargs)
        epk = self.kwargs.get('pk')
        event = models.Event.objects.get(pk=epk)
        context['event'] = event
        context['page_title'] = 'Create Risk Assessment for Event {}'.format(event.display_id)
        return context

    def get_success_url(self):
        return reverse_lazy('ra_detail', kwargs={'pk': self.object.pk})


class EventRiskAssessmentEdit(generic.UpdateView):
    model = models.RiskAssessment
    template_name = 'risk_assessment_form.html'
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
        context['page_title'] = 'Edit Risk Assessment for Event {}'.format(ra.event.display_id)
        return context


class EventRiskAssessmentDetail(generic.DetailView):
    model = models.RiskAssessment
    template_name = 'risk_assessment_detail.html'


class EventRiskAssessmentList(generic.ListView):
    paginate_by = 20
    model = models.RiskAssessment
    template_name = 'hs_object_list.html'

    def get_context_data(self, **kwargs):
        context = super(EventRiskAssessmentList, self).get_context_data(**kwargs)
        context['title'] = 'Risk Assessment'
        context['view'] = 'ra_detail'
        context['edit'] = 'ra_edit'
        context['review'] = 'ra_review'
        context['perm'] = 'perms.RIGS.review_riskassessment'
        context['fields'] = [n.name for n in list(self.model._meta.get_fields()) if n.name != 'reviewed_at' and n.name != 'reviewed_by' and not n.is_relation and not n.auto_created]
        return context


class EventRiskAssessmentReview(generic.View):
    def get(self, *args, **kwargs):
        rpk = kwargs.get('pk')
        ra = models.RiskAssessment.objects.get(pk=rpk)
        with reversion.create_revision():
            reversion.set_user(self.request.user)
            ra.reviewed_by = self.request.user
            ra.reviewed_at = timezone.now()
            ra.save()
        return HttpResponseRedirect(reverse_lazy('ra_list'))


class EventChecklistDetail(generic.DetailView):
    model = models.EventChecklist
    template_name = 'event_checklist_detail.html'

    def get_context_data(self, **kwargs):
        context = super(EventChecklistDetail, self).get_context_data(**kwargs)
        context['page_title'] = "Event Checklist for Event {} {}".format(self.object.event.display_id, self.object.event.name)
        return context


class EventChecklistEdit(generic.UpdateView):
    model = models.EventChecklist
    template_name = 'event_checklist_form.html'
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
        context['page_title'] = 'Edit Event Checklist for Event {}'.format(ec.event.display_id)
        form = context['form']
        # Get some other objects to include in the form. Used when there are errors but also nice and quick.
        for field, model in form.related_models.items():
            value = form[field].value()
            if value is not None and value != '':
                context[field] = model.objects.get(pk=value)
        return context


class EventChecklistCreate(generic.CreateView):
    model = models.EventChecklist
    template_name = 'event_checklist_form.html'
    form_class = forms.EventChecklistForm

    # From both business logic and programming POVs, RAs must exist before ECs!
    def get(self, *args, **kwargs):
        epk = kwargs.get('pk')
        event = models.Event.objects.get(pk=epk)

        # Check if RA exists
        ra = models.RiskAssessment.objects.filter(event=event).first()

        if ra is None:
            messages.error(self.request, 'A Risk Assessment must exist prior to creating any Event Checklists for {}! Please create one now.'.format(event))
            return HttpResponseRedirect(reverse_lazy('event_ra', kwargs={'pk': epk}))

        return super(EventChecklistCreate, self).get(self)

    def get_form(self, **kwargs):
        form = super(EventChecklistCreate, self).get_form(**kwargs)
        epk = self.kwargs.get('pk')
        event = models.Event.objects.get(pk=epk)
        form.instance.event = event
        return form

    def get_context_data(self, **kwargs):
        context = super(EventChecklistCreate, self).get_context_data(**kwargs)
        epk = self.kwargs.get('pk')
        event = models.Event.objects.get(pk=epk)
        context['event'] = event
        context['page_title'] = 'Create Event Checklist for Event {}'.format(event.display_id)
        return context

    def get_success_url(self):
        return reverse_lazy('ec_detail', kwargs={'pk': self.object.pk})


class EventChecklistList(generic.ListView):
    paginate_by = 20
    model = models.EventChecklist
    template_name = 'hs_object_list.html'

    def get_context_data(self, **kwargs):
        context = super(EventChecklistList, self).get_context_data(**kwargs)
        context['title'] = 'Event Checklist'
        context['view'] = 'ec_detail'
        context['edit'] = 'ec_edit'
        context['review'] = 'ec_review'
        context['perm'] = 'perms.RIGS.review_eventchecklist'
        context['fields'] = [n.name for n in list(self.model._meta.get_fields()) if n.name != 'reviewed_at' and n.name != 'reviewed_by' and not n.is_relation and not n.auto_created]
        return context


class EventChecklistReview(generic.View):
    def get(self, *args, **kwargs):
        rpk = kwargs.get('pk')
        ec = models.EventChecklist.objects.get(pk=rpk)
        with reversion.create_revision():
            reversion.set_user(self.request.user)
            ec.reviewed_by = self.request.user
            ec.reviewed_at = timezone.now()
            ec.save()
        return HttpResponseRedirect(reverse_lazy('ec_list'))


class HSList(generic.ListView):
    paginate_by = 20
    model = models.Event
    template_name = 'hs_list.html'

    def get_queryset(self):
        return models.Event.objects.all().order_by('-start_date')

    def get_context_data(self, **kwargs):
        context = super(HSList, self).get_context_data(**kwargs)
        context['page_title'] = 'H&S Overview'
        return context
