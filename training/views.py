import reversion

from django.urls import reverse_lazy
from django.views import generic
from django.utils import timezone
from django.db import transaction
from django.db.models import Q, Count

from PyRIGS.views import is_ajax, ModalURLMixin
from training import models, forms
from users import views


class ItemList(generic.ListView):
    template_name = "item_list.html"
    model = models.TrainingItem

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Training Items"
        context["categories"] = models.TrainingCategory.objects.all()
        return context


class TraineeDetail(views.ProfileDetail):
    template_name = "trainee_detail.html"
    model = models.Trainee

    def get_queryset(self):
        return self.model.objects.prefetch_related('qualifications_obtained')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.pk == self.object.pk:
            context["page_title"] = "Your Training Record"
        else:
            context["page_title"] = "{}'s Training Record".format(self.object.first_name + " " + self.object.last_name)
        context["started_levels"] = self.object.started_levels()
        context["completed_levels"] = self.object.level_qualifications.all()
        context["categories"] = models.TrainingCategory.objects.all().prefetch_related('items')
        return context


class TraineeItemDetail(generic.ListView):
    model = models.TrainingItemQualification
    template_name = 'trainee_item_list.html'

    def get_queryset(self):
        q = self.request.GET.get('q', "")

        filter = Q(item__name__icontains=q) | Q(supervisor__first_name__icontains=q) | Q(supervisor__last_name__icontains=q)

        try:
            q = q.split('.')
            filter = filter | Q(item__category__reference_number=int(q[0]), item__reference_number=int(q[1]))
        except:  # noqa
            # not an integer
            pass

        return models.Trainee.objects.get(pk=self.kwargs['pk']).qualifications_obtained.all().filter(filter).order_by('-date').select_related('item', 'trainee', 'supervisor', 'item__category')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        trainee = models.Trainee.objects.get(pk=self.kwargs['pk'])
        context["trainee"] = models.Trainee.objects.get(pk=self.kwargs['pk'])
        context["page_title"] = "Detailed Training Record for <a href='{}'>{}</a>".format(trainee.get_absolute_url(), trainee)
        return context


class LevelDetail(generic.DetailView):
    template_name = "level_detail.html"
    model = models.TrainingLevel

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Training Level {} {}".format(self.object, self.object.get_icon)
        context["users_with"] = map(lambda qual: qual.trainee, models.TrainingLevelQualification.objects.filter(level=self.object))
        context["u"] = models.Trainee.objects.get(pk=self.kwargs['u']) if 'u' in self.kwargs else self.request.user
        return context


class LevelList(generic.ListView):
    model = models.TrainingLevel
    template_name = "level_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "All Training Levels"
        return context


class TraineeList(generic.ListView):
    model = models.Trainee
    template_name = 'trainee_list.html'
    paginate_by = 25

    def get_queryset(self):
        q = self.request.GET.get('q', "")

        fil = Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(initials__icontains=q)

        # try and parse an int
        try:
            val = int(q)
            fil = fil | Q(pk=val)
        except:  # noqa
            # not an integer
            pass

        return self.model.objects.filter(filter).annotate(num_qualifications=Count('qualifications_obtained')).order_by('-num_qualifications').prefetch_related('level_qualifications', 'qualifications_obtained', 'qualifications_obtained__item')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Training Profile List"
        return context


class AddQualification(generic.CreateView, ModalURLMixin):
    template_name = "edit_training_record.html"
    model = models.TrainingItemQualification
    form_class = forms.QualificationForm

    @transaction.atomic()
    @reversion.create_revision()
    def form_valid(self, form, *args, **kwargs):
        reversion.add_to_revision(form.cleaned_data['trainee'])
        return super().form_valid(form, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["depths"] = models.TrainingItemQualification.CHOICES
        if is_ajax(self.request):
            context['override'] = "base_ajax.html"
        else:
            context['override'] = 'base_training.html'
        context['page_title'] = "Add Qualification for {}".format(models.Trainee.objects.get(pk=self.kwargs['pk']))
        return context

    def get_success_url(self):
        return self.get_close_url('trainee_detail', 'trainee_detail')

    def get_form_kwargs(self):
        kwargs = super(AddQualification, self).get_form_kwargs()
        kwargs['pk'] = self.kwargs['pk']
        return kwargs


class EditQualification(generic.UpdateView):
    template_name = 'edit_training_record.html'
    model = models.TrainingItemQualification
    form_class = forms.QualificationForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["depths"] = models.TrainingItemQualification.CHOICES
        context['page_title'] = "Edit Qualification {} for {}".format(self.object, models.Trainee.objects.get(pk=self.kwargs['pk']))
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['pk'] = self.kwargs['pk']
        return kwargs

    @transaction.atomic()
    @reversion.create_revision()
    def form_valid(self, form, *args, **kwargs):
        reversion.add_to_revision(form.cleaned_data['trainee'])
        return super().form_valid(form, *args, **kwargs)


class AddLevelRequirement(generic.CreateView, ModalURLMixin):
    template_name = "add_level_requirement.html"
    model = models.TrainingLevelRequirement
    form_class = forms.RequirementForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Add Requirements to Training Level {}".format(models.TrainingLevel.objects.get(pk=self.kwargs['pk']))
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['pk'] = self.kwargs['pk']
        return kwargs

    def get_success_url(self):
        return self.get_close_url('level_detail', 'level_detail')

    @transaction.atomic()
    @reversion.create_revision()
    def form_valid(self, form, *args, **kwargs):
        reversion.add_to_revision(form.cleaned_data['level'])
        return super().form_valid(form, *args, **kwargs)


class RemoveRequirement(generic.DeleteView):
    model = models.TrainingLevelRequirement
    template_name = 'traininglevelrequirement_confirm_delete.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = f"Delete Requirement '{self.object}' from Training Level {self.object.level}?"
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
        trainee = models.Trainee.objects.get(pk=kwargs['pk'])
        level_qualification, created = models.TrainingLevelQualification.objects.get_or_create(trainee=trainee, level=models.TrainingLevel.objects.get(pk=kwargs['level_pk']))

        if created:
            level_qualification.confirmed_by = self.request.user
            level_qualification.confirmed_on = timezone.now()
            level_qualification.save()

        reversion.add_to_revision(trainee)
        return reverse_lazy('trainee_detail', kwargs={'pk': kwargs['pk']})
