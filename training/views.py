import reversion

from django.urls import reverse_lazy
from django.views import generic
from django.utils import timezone
from django.db import transaction
from django.db.models import Q, Count
from django.db.utils import IntegrityError

from PyRIGS.views import is_ajax, ModalURLMixin, get_related, PrintListView
from training import models, forms
from users import views
from reversion.views import RevisionMixin


class ItemList(generic.ListView):
    template_name = "item_list.html"
    model = models.TrainingItem

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Training Items"
        context["categories"] = models.TrainingCategory.objects.all()
        return context


class ItemListExport(PrintListView):
    model = models.TrainingItem
    template_name = 'item_list.xml'

    def get_queryset(self):
        return self.model.objects.filter(active=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filename'] = "TrainingItemList.pdf"
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
            context["page_title"] = f"{self.object.get_full_name()}'s Training Record"
        context["started_levels"] = self.object.started_levels()
        context["completed_levels"] = self.object.level_qualifications.all()
        context["categories"] = models.TrainingCategory.objects.all().prefetch_related('items')
        return context


class TraineeItemDetail(generic.ListView):
    model = models.TrainingItemQualification
    template_name = 'trainee_item_list.html'

    def get_queryset(self):
        return models.Trainee.objects.get(pk=self.kwargs['pk']).qualifications_obtained.search(self.request.GET.get('q')).order_by('item__category__reference_number', 'item__reference_number').select_related('item', 'trainee')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        trainee = models.Trainee.objects.get(pk=self.kwargs['pk'])
        context["trainee"] = models.Trainee.objects.get(pk=self.kwargs['pk'])
        context["page_title"] = f"Detailed Training Record for <a href='{trainee.get_absolute_url()}'>{trainee}</a>"
        return context


class LevelDetail(generic.DetailView):
    template_name = "level_detail.html"
    model = models.TrainingLevel

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = f"Training Level {self.object} {self.object.get_icon}"
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
        objects = self.model.objects.search(self.request.GET.get('q'))

        if self.request.GET.get('is_supervisor', ''):
            objects = objects.filter(is_supervisor=True)

        return objects.annotate(num_qualifications=Count('qualifications_obtained', filter=Q(qualifications_obtained__depth=models.TrainingItemQualification.PASSED_OUT))
                                ).order_by('-num_qualifications').prefetch_related('level_qualifications', 'qualifications_obtained', 'qualifications_obtained__item')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Training Profile List"
        return context


class AddQualification(generic.CreateView, ModalURLMixin):
    template_name = "edit_training_record.html"
    model = models.TrainingItemQualification
    form_class = forms.AddQualificationForm

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
        trainee = models.Trainee.objects.get(pk=self.kwargs['pk'])
        context['page_title'] = f"Add Qualification for {trainee}"
        get_related(context['form'], context)
        return context

    def get_success_url(self):
        return self.get_close_url('add_qualification', 'trainee_detail')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['pk'] = self.kwargs['pk']
        return kwargs


class EditQualification(generic.UpdateView, ModalURLMixin):
    template_name = 'edit_training_record.html'
    model = models.TrainingItemQualification
    form_class = forms.QualificationForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["depths"] = models.TrainingItemQualification.CHOICES
        context['page_title'] = f"Edit Qualification <em>{self.object}</em> for {self.object.trainee}"
        get_related(context['form'], context)
        return context

    @transaction.atomic()
    @reversion.create_revision()
    def form_valid(self, form, *args, **kwargs):
        reversion.add_to_revision(form.cleaned_data['trainee'])
        return super().form_valid(form, *args, **kwargs)

    def get_success_url(self):
        return self.get_close_url('edit_qualification', 'trainee_item_detail')


class AddLevelRequirement(generic.CreateView, ModalURLMixin):
    template_name = "add_level_requirement.html"
    model = models.TrainingLevelRequirement
    form_class = forms.RequirementForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        level = models.TrainingLevel.objects.get(pk=self.kwargs['pk'])
        context["page_title"] = f"Add Requirements to Training Level {level}"
        get_related(context['form'], context)
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
            user = self.request.user
            reversion.set_user(user)
            level_qualification.confirmed_by = self.request.user
            level_qualification.confirmed_on = timezone.now()
            level_qualification.save()
            reversion.add_to_revision(trainee)

        return reverse_lazy('trainee_detail', kwargs={'pk': kwargs['pk']})


class SessionLog(generic.FormView):
    template_name = 'session_log_form.html'
    form_class = forms.SessionLogForm
    success_url = reverse_lazy('trainee_list')

    def form_valid(self, form, *args, **kwargs):
        for trainee in form.cleaned_data.get('trainees', []):
            for depth in models.TrainingItemQualification.CHOICES:
                for item in form.cleaned_data.get(f'items_{depth[0]}', []):
                    try:
                        with transaction.atomic():
                            models.TrainingItemQualification.objects.create(trainee=trainee, item=item, supervisor=form.cleaned_data.get('supervisor'), depth=depth[0], notes=form.cleaned_data.get('notes'), date=form.cleaned_data.get('date'))
                            reversion.add_to_revision(trainee)
                    except IntegrityError:
                        pass  # There was an attempt to create a duplicate qualification, ignore it
        return super().form_valid(form, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["depths"] = models.TrainingItemQualification.CHOICES
        context["page_title"] = "Log Training Session"
        get_related(context['form'], context)
        return context


class ItemQualifications(generic.ListView):
    template_name = "item_qualification_list.html"
    model = models.TrainingItemQualification
    paginate_by = 40

    def get_queryset(self):
        return models.TrainingItemQualification.objects.filter(item=self.kwargs['pk']).order_by('-depth').select_related('trainee')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = f"People Qualified In {models.TrainingItem.objects.get(pk=self.kwargs['pk'])}"
        return context
