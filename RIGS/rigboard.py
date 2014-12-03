from django.views import generic
from django.core.urlresolvers import reverse_lazy

from RIGS import models, forms


__author__ = 'ghost'


class RigboardIndex(generic.TemplateView):
    template_name = 'RIGS/rigboard.html'

    def get_context_data(self, **kwargs):
        # get super context
        context = super(RigboardIndex, self).get_context_data(**kwargs)

        # call out method to get current events
        context['events'] = models.Event.objects.current_events()
        return context


class EventDetail(generic.DetailView):
    model = models.Event


class EventCreate(generic.CreateView):
    model = models.Event
    form_class = forms.EventForm

    def get_context_data(self, **kwargs):
        context = super(EventCreate, self).get_context_data(**kwargs)
        context['edit'] = True
        return context

    def get_success_url(self):
        return reverse_lazy('event_detail', kwargs={'pk': self.object.pk})


class EventUpdate(generic.UpdateView):
    model = models.Event
    form_class = forms.EventForm

    def get_context_data(self, **kwargs):
        context = super(EventUpdate, self).get_context_data(**kwargs)
        context['edit'] = True
        return context

    def get_success_url(self):
        return reverse_lazy('event_detail', kwargs={'pk': self.object.pk})
