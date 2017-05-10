__author__ = 'Ghost'
from django import forms
from django.utils import formats
from django.conf import settings
from django.core import serializers
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AuthenticationForm, PasswordResetForm
from registration.forms import RegistrationFormUniqueEmail
from captcha.fields import ReCaptchaField
import simplejson

from RIGS import models


# Registration
class ProfileRegistrationFormUniqueEmail(RegistrationFormUniqueEmail):
    captcha = ReCaptchaField()

    class Meta:
        model = models.Profile
        fields = ('username', 'email', 'first_name', 'last_name', 'initials', 'phone')

    def clean_initials(self):
        """
        Validate that the supplied initials are unique.
        """
        if models.Profile.objects.filter(initials__iexact=self.cleaned_data['initials']):
            raise forms.ValidationError("These initials are already in use. Please supply different initials.")
        return self.cleaned_data['initials']

    def clean_first_name(self):
        if self.cleaned_data["first_name"].strip() == '':
            raise ValidationError("First name is required.")
        return self.cleaned_data["first_name"]

    def clean_last_name(self):
        if self.cleaned_data["last_name"].strip() == '':
            raise ValidationError("Last name is required.")
        return self.cleaned_data["last_name"]


# Login form
class PasswordReset(PasswordResetForm):
    captcha = ReCaptchaField(label='Captcha')


class ProfileCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = models.Profile


class ProfileChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = models.Profile


# Events Shit
class EventForm(forms.ModelForm):
    datetime_input_formats = formats.get_format_lazy("DATETIME_INPUT_FORMATS") + settings.DATETIME_INPUT_FORMATS
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
                  'collector', 'purchase_order']
