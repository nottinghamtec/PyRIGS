import datetime

from django import forms

from training import models


class QualificationForm(forms.ModelForm):
    related_models = {"item": models.TrainingItem, "supervisor": models.Trainee}

    class Meta:
        model = models.TrainingItemQualification
        fields = "__all__"

    def clean_date(self):
        date = self.cleaned_data.get("date")
        if date > date.today():
            raise forms.ValidationError("Qualification date may not be in the future")
        return date

    def clean_supervisor(self):
        supervisor = self.cleaned_data.get("supervisor")
        if supervisor.pk == self.cleaned_data.get("trainee").pk:
            raise forms.ValidationError("One may not supervise oneself...")
        if self.user is not None and not self.user.is_supervisor and supervisor.pk != self.user.pk:
            raise forms.ValidationError("You may only record training that you delivered yourself")
        return supervisor

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["date"].widget.format = "%Y-%m-%d"


class AddQualificationForm(QualificationForm):
    def __init__(self, *args, **kwargs):
        pk = kwargs.pop("pk", None)
        super().__init__(*args, **kwargs)
        if pk:
            self.fields["trainee"].initial = models.Trainee.objects.get(pk=pk)


class RequirementForm(forms.ModelForm):
    related_models = {"item": models.TrainingItem}

    depth = forms.ChoiceField(choices=models.TrainingItemQualification.CHOICES)

    class Meta:
        model = models.TrainingLevelRequirement
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        pk = kwargs.pop("pk", None)
        super().__init__(*args, **kwargs)
        self.fields["level"].initial = models.TrainingLevel.objects.get(pk=pk)


class SessionLogForm(forms.Form):
    trainees = forms.ModelMultipleChoiceField(models.Trainee.objects.all())
    items_0 = forms.ModelMultipleChoiceField(models.TrainingItem.objects.all(), required=False)
    items_1 = forms.ModelMultipleChoiceField(models.TrainingItem.objects.all(), required=False)
    items_2 = forms.ModelMultipleChoiceField(models.TrainingItem.objects.all(), required=False)
    supervisor = forms.ModelChoiceField(models.Trainee.objects.all())
    date = forms.DateField(initial=datetime.date.today)
    notes = forms.CharField(required=False, widget=forms.Textarea)

    related_models = {"supervisor": models.Trainee}

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if self.user is not None and not self.user.is_supervisor:
            self.fields["supervisor"].initial = self.user.pk

    def clean(self):
        cleaned_data = super().clean()
        supervisor = cleaned_data.get("supervisor")
        # Supervisors may log anything (as before); technicians only what they are permitted to deliver
        if self.user is not None and not self.user.is_supervisor and supervisor is not None:
            if supervisor.pk != self.user.pk:
                self.add_error("supervisor", "You may only log sessions that you delivered yourself")
            else:
                if cleaned_data.get("items_2"):
                    self.add_error("items_2", "Technicians may not pass people out")
                for depth in (models.TrainingItemQualification.STARTED, models.TrainingItemQualification.COMPLETE):
                    for item in cleaned_data.get(f"items_{depth}", []):
                        if not supervisor.can_deliver_training(item, depth):
                            self.add_error(f"items_{depth}", f"You are not permitted to deliver training in {item}")
        return cleaned_data

    def clean_date(self):
        return QualificationForm.clean_date(self)

    def clean_supervisor(self):
        supervisor = self.cleaned_data["supervisor"]
        if supervisor in self.cleaned_data.get("trainees", []):
            raise forms.ValidationError("One may not supervise oneself...")
        return supervisor
