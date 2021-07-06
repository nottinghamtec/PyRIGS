from django import forms

from training import models
from RIGS.models import Profile

class SessionLogForm(forms.Form):
    pass

# TODO Validation that dates cannot be in the future
class QualificationForm(forms.ModelForm):
    class Meta:
        model = models.TrainingItemQualification
        fields = '__all__'
        # exclude = ['trainee']

    def __init__(self, *args, **kwargs):
        pk = kwargs.pop('pk', None)
        super(QualificationForm, self).__init__(*args, **kwargs)
        self.fields['trainee'].initial = Profile.objects.get(pk=pk)
        

class RequirementForm(forms.ModelForm):
    class Meta:
        model = models.TrainingLevelRequirement
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        pk = kwargs.pop('pk', None)
        super(RequirementForm, self).__init__(*args, **kwargs)
        self.fields['level'].initial = models.TrainingLevel.objects.get(pk=pk)
