from datetime import datetime

import simplejson
from django import forms
from django.conf import settings
from django.core import serializers
from django.utils import timezone
from reversion import revisions as reversion

from RIGS import models

# Override the django form defaults to use the HTML date/time/datetime UI elements
forms.DateField.widget = forms.DateInput(attrs={'type': 'date'})
forms.TimeField.widget = forms.TimeInput(attrs={'type': 'time'}, format='%H:%M')
forms.DateTimeField.widget = forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%d %H:%M')


# Events Shit
class EventForm(forms.ModelForm):
    datetime_input_formats = list(settings.DATETIME_INPUT_FORMATS)
    meet_at = forms.DateTimeField(input_formats=datetime_input_formats, required=False)
    access_at = forms.DateTimeField(input_formats=datetime_input_formats, required=False)

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
        super(EventForm, self).__init__(*args, **kwargs)

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
        return super(EventForm, self).clean()

    def save(self, commit=True):
        m = super(EventForm, self).save(commit=False)

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
                  'purchase_order', 'collector']


class BaseClientEventAuthorisationForm(forms.ModelForm):
    tos = forms.BooleanField(required=True, label="Terms of hire")
    name = forms.CharField(label="Your Name")

    def clean(self):
        if self.cleaned_data.get('amount') != self.instance.event.total:
            self.add_error('amount', 'The amount authorised must equal the total for the event (inc VAT).')
        return super(BaseClientEventAuthorisationForm, self).clean()

    class Meta:
        abstract = True


class InternalClientEventAuthorisationForm(BaseClientEventAuthorisationForm):
    def __init__(self, **kwargs):
        super(InternalClientEventAuthorisationForm, self).__init__(**kwargs)
        self.fields['uni_id'].required = True
        self.fields['account_code'].required = True

    class Meta:
        model = models.EventAuthorisation
        fields = ('tos', 'name', 'amount', 'uni_id', 'account_code')


class EventAuthorisationRequestForm(forms.Form):
    email = forms.EmailField(required=True, label='Authoriser Email')


class EventRiskAssessmentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(EventRiskAssessmentForm, self).__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if str(name) == 'supervisor_consulted':
                field.widget = forms.CheckboxInput()
            elif field.__class__ == forms.BooleanField:
                field.widget = forms.RadioSelect(choices=[
                    (True, 'Yes'),
                    (False, 'No')
                ], attrs={'class': 'custom-control-input', 'required': 'true'})

    def clean(self):
        # Check expected values
        unexpected_values = []
        for field, value in models.RiskAssessment.expected_values.items():
            if self.cleaned_data.get(field) != value:
                unexpected_values.append("<li>{}</li>".format(self._meta.model._meta.get_field(field).help_text))
        if len(unexpected_values) > 0 and not self.cleaned_data.get('supervisor_consulted'):
            raise forms.ValidationError("Your answers to these questions: <ul>{}</ul> require consulting with a supervisor.".format(''.join([str(elem) for elem in unexpected_values])), code='unusual_answers')
        return super(EventRiskAssessmentForm, self).clean()

    class Meta:
        model = models.RiskAssessment
        fields = '__all__'
        exclude = ['reviewed_at', 'reviewed_by']


class EventChecklistForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(EventChecklistForm, self).__init__(*args, **kwargs)
        self.fields['date'].widget.format = '%Y-%m-%d'
        for name, field in self.fields.items():
            if field.__class__ == forms.NullBooleanField:
                # Only display yes/no to user, the 'none' is only ever set in the background
                field.widget = forms.CheckboxInput()
    # Parsed from incoming form data by clean, then saved into models when the form is saved
    items = {}

    related_models = {
        'venue': models.Venue,
        'power_mic': models.Profile,
    }

    # Two possible formats
    def parsedatetime(self, date_string):
        try:
            return timezone.make_aware(datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%S'))
        except ValueError:
            return timezone.make_aware(datetime.strptime(date_string, '%Y-%m-%dT%H:%M'))

    # There's probably a thousand better ways to do this, but this one is mine
    def clean(self):
        vehicles = {key: val for key, val in self.data.items()
                    if key.startswith('vehicle')}
        for key in vehicles:
            pk = int(key.split('_')[1])
            driver_key = 'driver_' + str(pk)
            if(self.data[driver_key] == ''):
                raise forms.ValidationError('Add a driver to vehicle ' + str(pk), code='vehicle_mismatch')
            else:
                try:
                    item = models.EventChecklistVehicle.objects.get(pk=pk)
                except models.EventChecklistVehicle.DoesNotExist:
                    item = models.EventChecklistVehicle()

                item.vehicle = vehicles['vehicle_' + str(pk)]
                item.driver = models.Profile.objects.get(pk=self.data[driver_key])
                item.full_clean('checklist')

                # item does not have a database pk yet as it isn't saved
                self.items['v' + str(pk)] = item

        crewmembers = {key: val for key, val in self.data.items()
                       if key.startswith('crewmember')}
        other_fields = ['start', 'role', 'end']
        for key in crewmembers:
            pk = int(key.split('_')[1])

            for field in other_fields:
                value = self.data['{}_{}'.format(field, pk)]
                if value == '':
                    raise forms.ValidationError('Add a {} to crewmember {}'.format(field, pk), code='{}_mismatch'.format(field))

            try:
                item = models.EventChecklistCrew.objects.get(pk=pk)
            except models.EventChecklistCrew.DoesNotExist:
                item = models.EventChecklistCrew()

            item.crewmember = models.Profile.objects.get(pk=self.data['crewmember_' + str(pk)])
            item.start = self.parsedatetime(self.data['start_' + str(pk)])
            item.role = self.data['role_' + str(pk)]
            item.end = self.parsedatetime(self.data['end_' + str(pk)])
            item.full_clean('checklist')

            # item does not have a database pk yet as it isn't saved
            self.items['c' + str(pk)] = item

        return super(EventChecklistForm, self).clean()

    def save(self, commit=True):
        checklist = super(EventChecklistForm, self).save(commit=False)
        if (commit):
            # Remove all existing, to be recreated from the form
            checklist.vehicles.all().delete()
            checklist.crew.all().delete()
            checklist.save()

            for key in self.items:
                item = self.items[key]
                reversion.add_to_revision(item)
                # finish and save new database items
                item.checklist = checklist
                item.full_clean()
                item.save()

        self.items.clear()

        return checklist

    class Meta:
        model = models.EventChecklist
        fields = '__all__'
        exclude = ['reviewed_at', 'reviewed_by']
