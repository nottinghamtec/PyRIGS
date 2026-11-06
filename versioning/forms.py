from django import forms
from django.contrib.auth import get_user_model


class ActivityFilterForm(forms.Form):
    q = forms.CharField(
        required=False,
        label="Search",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Object or comment"}),
    )
    model = forms.ChoiceField(required=False, label="Type", widget=forms.Select(attrs={"class": "form-select"}))
    user = forms.ModelChoiceField(queryset=get_user_model().objects.none(), required=False, label="Person")
    start = forms.DateField(
        required=False, label="From", widget=forms.DateInput(attrs={"class": "form-control", "type": "date"})
    )
    end = forms.DateField(
        required=False, label="To", widget=forms.DateInput(attrs={"class": "form-control", "type": "date"})
    )
    mine = forms.BooleanField(
        required=False, label="My changes", widget=forms.CheckboxInput(attrs={"class": "form-check-input"})
    )
    my_events = forms.BooleanField(
        required=False, label="Events I'm MIC on", widget=forms.CheckboxInput(attrs={"class": "form-check-input"})
    )

    def __init__(self, *args, models=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.models = {model._meta.model_name: model for model in models}
        self.fields["model"].choices = [("", "Everything")] + sorted(
            ((name, model._meta.verbose_name.title()) for name, model in self.models.items()),
            key=lambda choice: choice[1],
        )
        self.fields["user"].queryset = get_user_model().objects.filter(revision__isnull=False).distinct()

    @property
    def selected_user(self):
        return self.cleaned_data.get("user") if self.is_valid() else None
