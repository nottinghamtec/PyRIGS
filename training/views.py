from django.shortcuts import render

from django.urls import reverse_lazy
from django.views import generic
from PyRIGS.views import OEmbedView, is_ajax
from training import models, forms

from users import views

class ItemList(generic.ListView):
    template_name = "item_list.html"
    model = models.TrainingItem

    def get_context_data(self, **kwargs):
        context = super(ItemList, self).get_context_data(**kwargs)
        context["page_title"] = "Training Items"
        context["categories"] = models.TrainingCategory.objects.all()    
        return context


class TraineeDetail(views.ProfileDetail):
    template_name = "trainee_detail.html"
    model = models.Trainee

    def get_context_data(self, **kwargs):
        context = super(TraineeDetail, self).get_context_data(**kwargs)
        context["page_title"] = "{}'s Training Record".format(self.object)
        context["levels"] = models.TrainingLevel.objects.all()
        context["categories"] = models.TrainingCategory.objects.all() 
        choices = models.TrainingItemQualification.CHOICES
        context["depths"] = choices
        for i in [x for x,_ in choices]:
            context[str(i)] = self.object.get_records_of_depth(i)
        return context


class TraineeList(generic.ListView):
    model = models.Trainee
    template_name = 'trainee_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Profile List"
        return context


class SessionLog(generic.FormView):
    template_name = "session_log_form.html"
    form_class = forms.SessionLogForm

    def get_context_data(self, **kwargs):
        context = super(SessionLog, self).get_context_data(**kwargs)
        context["page_title"] = "Log New Training Session"
        context["depths"] = models.TrainingItemQualification.CHOICES
        return context


class AddQualification(generic.CreateView):
    template_name = "edit_training_record.html"
    model = models.TrainingItemQualification
    form_class = forms.QualificationForm

    def get_context_data(self, **kwargs):
        context = super(AddQualification, self).get_context_data(**kwargs)
        # context["page_title"] = "Edit {}'s Training Record".format(self.object)
        context["depths"] = models.TrainingItemQualification.CHOICES
        if is_ajax(self.request):
            context['override'] = "base_ajax.html"
        else:
            context['override'] = 'base_rigs.html' # TODO
        return context

    def get_success_url(self):
        return reverse_lazy('trainee_detail')

    def get_form_kwargs(self):
        kwargs = super(AddQualification, self).get_form_kwargs()
        kwargs['pk'] = self.kwargs['pk']
        return kwargs


class AddLevelRequirement(generic.CreateView): 
    template_name = "edit_training_level.html"
    model = models.TrainingLevelRequirement
    form_class = forms.RequirementForm

    def get_context_data(self, **kwargs):
        context = super(AddLevelRequirement, self).get_context_data(**kwargs)
        context["page_title"] = "Add Requirements to Training Level {}".format(models.TrainingLevel.objects.get(pk=self.kwargs['pk']))
        return context

    def get_form_kwargs(self):
        kwargs = super(AddLevelRequirement, self).get_form_kwargs()
        kwargs['pk'] = self.kwargs['pk']
        return kwargs

    def get_success_url(self):
        return reverse_lazy('trainee_detail')


class LevelDetail(generic.DetailView):
    template_name = "level_detail.html"
    model = models.TrainingLevel

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Training Level {}".format(self.object)
        return context


class RemoveRequirement(generic.DeleteView):
    model = models.TrainingLevelRequirement
    template_name = 'traininglevelrequirement_confirm_delete.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Delete Requirement '{}' from Training Level {}?".format(self.object, self.object.level)
        return context

    def get_success_url(self):
        return self.request.POST.get('next')

