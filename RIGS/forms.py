from datetime import datetime, timedelta

import simplejson
from django import forms
from django.conf import settings
from django.core import serializers
from django.utils import timezone
from django.utils.html import format_html
from reversion import revisions as reversion

from RIGS import models
from training.models import TrainingLevel

# Override the django form defaults to use the HTML date/time/datetime UI elements
forms.DateField.widget = forms.DateInput(attrs={'type': 'date'})
forms.TimeField.widget = forms.TimeInput(attrs={'type': 'time'}, format='%H:%M')
forms.DateTimeField.widget = forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%d %H:%M')


# Events Shit
class EventForm(forms.ModelForm):
    datetime_input_formats = list(settings.DATETIME_INPUT_FORMATS)
    meet_at = forms.DateTimeField(input_formats=datetime_input_formats, required=False)
    access_at = forms.DateTimeField(input_formats=datetime_input_formats, required=False)
    parking_and_access = forms.BooleanField(label="Additional parking or access requirements (i.e. campus parking permits, wristbands)?", required=False)

    items_json = forms.CharField()

    items = {}

    related_models = {
        'person': models.Person,
        'organisation': models.Organisation,
        'venue': models.Venue,
        'mic': models.Profile,
        'checked_in_by': models.Profile,
    }

    @property
    def _get_items_json(self):
        items = {}
        for item in self.instance.items.all():
            data = serializers.serialize('json', [item])
            struct = simplejson.loads(data)
            items[item.pk] = simplejson.dumps(struct[0])
        return simplejson.dumps(items)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['items_json'].initial = self._get_items_json
        self.fields['start_date'].widget.format = '%Y-%m-%d'
        self.fields['end_date'].widget.format = '%Y-%m-%d'

        self.fields['access_at'].widget.format = '%Y-%m-%dT%H:%M:%S'
        self.fields['meet_at'].widget.format = '%Y-%m-%dT%H:%M:%S'

    def init_items(self):
        self.items = self.process_items_json()
        return self.items

    def process_items_json(self, event=None):
        data = simplejson.loads(self.cleaned_data['items_json'])
        items = {}
        for key in data:
            pk = int(key)
            items[pk] = self._get_or_initialise_item(pk, data[key]['fields'], event)

        return items

    def _get_or_initialise_item(self, pk, data, event):
        try:
            item = models.EventItem.objects.get(pk=pk, event=event)
        except models.EventItem.DoesNotExist:
            # This occurs for one of two reasons
            # 1) The event has been duplicated, so the item PKs belong to another event
            # 2) The items are brand new, with negative PK values
            # In either case, we want to create the items
            item = models.EventItem()

        # Take the data from the form and update the item object
        item.name = data['name']
        item.description = data['description']
        item.quantity = data['quantity']
        item.cost = data['cost']
        item.order = data['order']

        if (event):
            item.event = event
            item.full_clean()
        else:
            item.full_clean('event')

        return item

    def clean(self):
        if self.cleaned_data.get("is_rig") and not (
                self.cleaned_data.get('person') or self.cleaned_data.get('organisation')):
            raise forms.ValidationError(
                'You haven\'t provided any client contact details. Please add a person or organisation.',
                code='contact')
        access = self.cleaned_data.get("access_at")
        if 'warn-access' not in self.data and access is not None and access.date() < (self.cleaned_data.get("start_date") - timedelta(days=7)):
            raise forms.ValidationError(format_html("Are you sure about that? Your access time seems a bit optimistic. If you're sure, save again. <input type='hidden' id='warn-access' name='warn-access' value='0'/>"), code='access_sanity')
        return super().clean()

    def save(self, commit=True):
        m = super().save(commit=False)

        if (commit):
            m.save()
            cur_items = m.items.all()
            items = self.process_items_json(m)
            # Delete any unneeded items
            for item in cur_items:
                if item.pk not in items:
                    item.delete()

            for key in items:
                items[key].save()

        return m

    class Meta:
        model = models.Event
        fields = ['is_rig', 'name', 'venue', 'start_time', 'end_date', 'start_date',
                  'end_time', 'meet_at', 'access_at', 'description', 'notes', 'mic',
                  'person', 'organisation', 'dry_hire', 'checked_in_by', 'status',
                  'purchase_order', 'collector', 'forum_url', 'parking_and_access']


class BaseClientEventAuthorisationForm(forms.ModelForm):
    tos = forms.BooleanField(required=True, label="Terms of hire")
    name = forms.CharField(label="Your Name")

    def clean(self):
        if self.cleaned_data.get('amount') != self.instance.event.total:
            self.add_error('amount', 'The amount authorised must equal the total for the event (inc VAT).')
        return super().clean()

    class Meta:
        abstract = True


class InternalClientEventAuthorisationForm(BaseClientEventAuthorisationForm):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.fields['uni_id'].required = True
        self.fields['account_code'].required = True

    class Meta:
        model = models.EventAuthorisation
        fields = ('tos', 'name', 'amount', 'uni_id', 'account_code')


class EventAuthorisationRequestForm(forms.Form):
    email = forms.EmailField(required=True, label='Authoriser Email')


class EventRiskAssessmentForm(forms.ModelForm):
    related_models = {
        'power_mic': models.Profile,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if str(name) == 'supervisor_consulted':
                field.widget = forms.CheckboxInput()
            elif field.__class__ == forms.BooleanField:
                field.widget = forms.RadioSelect(choices=[
                    (True, 'Yes'),
                    (False, 'No')
                ], attrs={'class': 'custom-control-input', 'required': 'true'})

    def clean(self):
        if self.cleaned_data.get('big_power'):
            if not self.cleaned_data.get('power_mic').level_qualifications.filter(level__department=TrainingLevel.POWER).exists():
                self.add_error('power_mic', forms.ValidationError("Your Power MIC must be a Power Technician.", code="power_tech_required"))
        # Check expected values
        unexpected_values = []
        for field, value in models.RiskAssessment.expected_values.items():
            if self.cleaned_data.get(field) != value:
                unexpected_values.append(f"<li>{self._meta.model._meta.get_field(field).help_text}</li>")
        if len(unexpected_values) > 0 and not self.cleaned_data.get('supervisor_consulted'):
            raise forms.ValidationError(f"Your answers to these questions: <ul>{''.join([str(elem) for elem in unexpected_values])}</ul> require consulting with a supervisor.", code='unusual_answers')
        return super().clean()

    class Meta:
        model = models.RiskAssessment
        fields = '__all__'
        exclude = ['reviewed_at', 'reviewed_by']


class EventChecklistForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date'].widget.format = '%Y-%m-%d'
        for name, field in self.fields.items():
            if field.__class__ == forms.NullBooleanField:
                # Only display yes/no to user, the 'none' is only ever set in the background
                field.widget = forms.CheckboxInput()

    related_models = {
        'venue': models.Venue,
    }

    class Meta:
        model = models.EventChecklist
        fields = '__all__'
        exclude = ['reviewed_at', 'reviewed_by']


class PowerTestRecordForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if field.__class__ == forms.NullBooleanField:
                # Only display yes/no to user, the 'none' is only ever set in the background
                field.widget = forms.CheckboxInput()

    related_models = {
        'venue': models.Venue,
        'power_mic': models.Profile,
    }

    class Meta:
        model = models.PowerTestRecord
        fields = '__all__'
        exclude = ['reviewed_at', 'reviewed_by']


class EventCheckInForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['time'].initial = timezone.now()
        self.fields['role'].initial = "Crew"

    class Meta:
        model = models.EventCheckIn
        fields = '__all__'
        exclude = ['end_time']


class EditCheckInForm(forms.ModelForm):
    class Meta:
        model = models.EventCheckIn
        fields = '__all__'
