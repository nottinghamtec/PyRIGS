import reversion

from django.shortcuts import render
from django.urls import reverse_lazy
from django.views import generic
from PyRIGS.views import OEmbedView, is_ajax, ModalURLMixin
from training import models, forms
from django.utils import timezone
from django.db import transaction

from users import views

class ItemList(generic.ListView):
    template_name = "item_list.html"
    model = models.TrainingItem

    def get_context_data(self, **kwargs):
        context = super(ItemList, self).get_context_data(**kwargs)
        context["page_title"] = "Training Items"
        context["categories"] = models.TrainingCategory.objects.all()
        return context


class TraineeDetail(views.ProfileDetail, ModalURLMixin):
    template_name = "trainee_detail.html"
    model = models.Trainee

    def get_context_data(self, **kwargs):
        context = super(TraineeDetail, self).get_context_data(**kwargs)
        context["page_title"] = "{}'s Training Record".format(self.object.first_name + " " + self.object.last_name)
        # TODO Filter this to levels the user has
        # context["completed_levels"] = 
        context["levels"] = models.TrainingLevel.objects.all()
        context["categories"] = models.TrainingCategory.objects.all().prefetch_related('items')
        choices = models.TrainingItemQualification.CHOICES
        context["depths"] = choices
        for i in [x for x,_ in choices]:
            context[str(i)] = self.object.get_records_of_depth(i)
        return context

    def get_success_url(self):
        return self.get_close_url('trainee_detail', 'trainee_detail')


class TraineeItemDetail(generic.ListView):
    model = models.TrainingItemQualification
    template_name = 'trainee_item_list.html'

    def get_queryset(self):
        return models.Trainee.objects.get(pk=self.kwargs['pk']).qualifications_obtained.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Detailed Training Record for {}".format(models.Trainee.objects.get(pk=self.kwargs['pk']))
        return context


class LevelList(generic.ListView):
    model = models.TrainingLevel
    template_name = "level_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "All Training Levels"
        context["levels"] = models.TrainingLevel.objects.all().order_by('level','department')
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
        context["depths"] = models.TrainingItemQualification.CHOICES
        if is_ajax(self.request):
            context['override'] = "base_ajax.html"
        else:
            context['override'] = 'base_training.html'
        context['page_title'] = "Add Qualification for {}".format(models.Trainee.objects.get(pk=self.kwargs['pk']))
        return context

    def get_success_url(self):
        return reverse_lazy('trainee_detail', kwargs={"pk": self.object.pk })

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
        return reverse_lazy('level_detail', kwargs={"pk": self.kwargs['pk']})

    @transaction.atomic()
    @reversion.create_revision()
    def form_valid(self, form, *args, **kwargs):
        reversion.add_to_revision(form.cleaned_data['level'])
        reversion.set_comment("Level requirement added")
        return super().form_valid(form, *args, **kwargs)


class LevelDetail(generic.DetailView):
    template_name = "level_detail.html"
    model = models.TrainingLevel

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Training Level {} <span class='badge badge-{} badge-pill'><span class='fas fa-{}'></span></span>".format(self.object, self.object.get_department_colour(), self.object.icon)
        context["users_with"] = map(lambda qual: qual.trainee, models.TrainingLevelQualification.objects.filter(level=self.object))
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

    @transaction.atomic()
    @reversion.create_revision()
    def delete(self, *args, **kwargs):
        reversion.add_to_revision(self.get_object().level)
        return super().delete(*args, **kwargs)


class ConfirmLevel(generic.RedirectView):
    @transaction.atomic()
    @reversion.create_revision()
    def get_redirect_url(self, *args, **kwargs):
        level_qualification = models.TrainingLevelQualification.objects.get(trainee=kwargs['pk'], level=kwargs['level_pk'])
        level_qualification.confirmed_by = self.request.user
        level_qualification.confirmed_on = timezone.now()
        level_qualification.save()
        reversion.add_to_revision(level_qualification.trainee)
        reversion.set_user(self.request.user)
        return reverse_lazy('trainee_detail', kwargs={'pk': kwargs['pk']})
