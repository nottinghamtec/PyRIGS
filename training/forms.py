import datetime

from django import forms

from training import models
from RIGS.models import Profile


def validate_user_can_train_in(supervisor, item):
    if item.category.training_level:
        if not supervisor.level_qualifications.filter(level=item.category.training_level):
            raise forms.ValidationError('Selected supervising person is missing requisite training level to train in this department')
    elif not supervisor.is_supervisor:
        raise forms.ValidationError('Selected supervisor must actually *be* a supervisor...')


class QualificationForm(forms.ModelForm):
    class Meta:
        model = models.TrainingItemQualification
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        item = cleaned_data.get('item')
        trainee = cleaned_data.get('trainee')
        if not item.user_has_requirements(trainee):
            self.add_error('item', 'Missing prerequisites')

    def clean_date(self):
        date = self.cleaned_data['date']
        if date > date.today():
            raise forms.ValidationError('Qualification date may not be in the future')
        return date

    def clean_supervisor(self):
        supervisor = self.cleaned_data['supervisor']
        item = self.cleaned_data['item']
        if supervisor.pk == self.cleaned_data['trainee'].pk:
            raise forms.ValidationError('One may not supervise oneself...')
        validate_user_can_train_in(supervisor, item)
        return supervisor

    def __init__(self, *args, **kwargs):
        pk = kwargs.pop('pk', None)
        super().__init__(*args, **kwargs)
        if pk:
            self.fields['trainee'].initial = Profile.objects.get(pk=pk)
        self.fields['date'].widget.format = '%Y-%m-%d'


class RequirementForm(forms.ModelForm):
    depth = forms.ChoiceField(choices=models.TrainingItemQualification.CHOICES)

    class Meta:
        model = models.TrainingLevelRequirement
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        pk = kwargs.pop('pk', None)
        super().__init__(*args, **kwargs)
        self.fields['level'].initial = models.TrainingLevel.objects.get(pk=pk)


class SessionLogForm(forms.Form):
    trainees = forms.ModelMultipleChoiceField(models.Trainee.objects.all())
    items = forms.ModelMultipleChoiceField(models.TrainingItem.objects.all())
    depth = forms.ChoiceField(choices=models.TrainingItemQualification.CHOICES)
    supervisor = forms.ModelChoiceField(models.Trainee.objects.all())
    date = forms.DateField(initial=datetime.date.today)
    notes = forms.CharField(required=False, widget=forms.Textarea)

    related_models = {
        'supervisor': models.Trainee
    }

    def clean_date(self):
        return QualificationForm.clean_date(self)

    def clean_supervisor(self):
        supervisor = self.cleaned_data['supervisor']
        if supervisor in self.cleaned_data.get('trainees', []):
            raise forms.ValidationError('One may not supervise oneself...')
        for item in self.cleaned_data.get('items', []):
            validate_user_can_train_in(supervisor, item)
        return supervisor
