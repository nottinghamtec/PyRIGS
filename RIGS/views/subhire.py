from django.urls import reverse_lazy
from django.views import generic
from django.db.models import Sum
from PyRIGS.views import ModalURLMixin, get_related
from RIGS import models, forms
from RIGS.views import EventArchive


class SubhireDetail(generic.DetailView, ModalURLMixin):
    template_name = 'subhire_detail.html'
    model = models.Subhire

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f"{self.object.display_id} | {self.object.name}"
        return context


class SubhireCreate(generic.CreateView):
    model = models.Subhire
    form_class = forms.SubhireForm
    template_name = 'subhire_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = "New Subhire"
        context['edit'] = True
        form = context['form']
        get_related(form, context)
        return context

    def get_success_url(self):
        return reverse_lazy('subhire_detail', kwargs={'pk': self.object.pk})


class SubhireEdit(generic.UpdateView):
    model = models.Subhire
    form_class = forms.SubhireForm
    template_name = 'subhire_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f"Edit Subhire: {self.object.display_id} | {self.object.name}"
        context['edit'] = True
        form = context['form']
        get_related(form, context)
        return context

    def get_success_url(self):
        return reverse_lazy('subhire_detail', kwargs={'pk': self.object.pk})


class SubhireList(EventArchive):
    template_name = 'subhire_list.html'
    model = models.Subhire
    paginate_by = 25

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_value'] = self.get_queryset().aggregate(sum=Sum('insurance_value'))['sum']
        context['page_title'] = "Subhire List"
        return context
