from RIGS import models, forms
from django.views import generic
from django.utils import timezone
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from reversion import revisions as reversion


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
        return context

    def get_success_url(self):
        return reverse_lazy('ra_detail', kwargs={'pk': self.object.pk})


class EventRiskAssessmentEdit(generic.UpdateView):
    model = models.RiskAssessment
    template_name = 'risk_assessment_form.html'
    form_class = forms.EventRiskAssessmentForm

    def get_success_url(self):
        # TODO Invalidate review here
        return reverse_lazy('ra_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super(EventRiskAssessmentEdit, self).get_context_data(**kwargs)
        rpk = self.kwargs.get('pk')
        ra = models.RiskAssessment.objects.get(pk=rpk)
        context['event'] = ra.event
        context['edit'] = True
        return context


class EventRiskAssessmentDetail(generic.DetailView):
    model = models.RiskAssessment
    template_name = 'risk_assessment_detail.html'


class EventRiskAssessmentList(generic.ListView):
    paginate_by = 20
    model = models.RiskAssessment
    template_name = 'risk_assessment_list.html'


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
