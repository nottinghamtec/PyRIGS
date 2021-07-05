from django import forms

from training import models
from RIGS.models import Profile

class SessionLogForm(forms.Form):
    pass


class QualificationForm(forms.ModelForm):
    class Meta:
        model = models.TrainingItemQualification
        fields = '__all__'
        # exclude = ['trainee']

    def __init__(self, *args, **kwargs):
        pk = kwargs.pop('pk', None)
        super(QualificationForm, self).__init__(*args, **kwargs)
        self.fields['trainee'].initial = Profile.objects.get(pk=pk)
        
