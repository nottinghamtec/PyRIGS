import datetime

from django import forms

from training import models


class QualificationForm(forms.ModelForm):
    related_models = {
        'item': models.TrainingItem,
        'supervisor': models.Trainee
    }

    class Meta:
        model = models.TrainingItemQualification
        fields = '__all__'

    def clean_date(self):
        date = self.cleaned_data.get('date')
        if date > date.today():
            raise forms.ValidationError('Qualification date may not be in the future')
        return date

    def clean_supervisor(self):
        supervisor = self.cleaned_data.get('supervisor')
        if supervisor.pk == self.cleaned_data.get('trainee').pk:
            raise forms.ValidationError('One may not supervise oneself...')
        return supervisor

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date'].widget.format = '%Y-%m-%d'


class AddQualificationForm(QualificationForm):
    def __init__(self, *args, **kwargs):
        pk = kwargs.pop('pk', None)
        super().__init__(*args, **kwargs)
        if pk:
            self.fields['trainee'].initial = models.Trainee.objects.get(pk=pk)


class RequirementForm(forms.ModelForm):
    related_models = {
        'item': models.TrainingItem
    }

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
    items_0 = forms.ModelMultipleChoiceField(models.TrainingItem.objects.all(), required=False)
    items_1 = forms.ModelMultipleChoiceField(models.TrainingItem.objects.all(), required=False)
    items_2 = forms.ModelMultipleChoiceField(models.TrainingItem.objects.all(), required=False)
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
        return supervisor
