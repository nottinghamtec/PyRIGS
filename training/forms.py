from django import forms

from datetime import date

from training import models
from RIGS.models import Profile

class SessionLogForm(forms.Form):
    pass


class QualificationForm(forms.ModelForm):
    class Meta:
        model = models.TrainingItemQualification
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        pk = kwargs.pop('pk', None)
        super().__init__()
        self.fields['trainee'].initial = Profile.objects.get(pk=pk)
        
    def clean_date(self):
        date = self.cleaned_data['date']
        if date > date.today():
            raise ValidationError('Qualification date may not be in the future')

class RequirementForm(forms.ModelForm):
    depth = forms.ChoiceField(choices=models.TrainingItemQualification.CHOICES)

    class Meta:
        model = models.TrainingLevelRequirement
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        pk = kwargs.pop('pk', None)
        super().__init__()
        self.fields['level'].initial = models.TrainingLevel.objects.get(pk=pk)
