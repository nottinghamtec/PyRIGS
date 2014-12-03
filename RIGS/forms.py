__author__ = 'Ghost'
from django import forms
from django.utils import formats
from RIGS import models
from django.conf import settings

# Events Shit
class EventForm(forms.ModelForm):
    datetime_input_formats = formats.get_format_lazy("DATETIME_INPUT_FORMATS") + settings.DATETIME_INPUT_FORMATS
    meet_at = forms.DateTimeField(input_formats=datetime_input_formats, required=False)
    access_at = forms.DateTimeField(input_formats=datetime_input_formats, required=False)
    name = forms.CharField(min_length=3)
    class Meta:
        model = models.Event
        fields = ['is_rig', 'name', 'venue', 'start_date', 'start_time', 'end_date',
                  'end_time', 'meet_at', 'access_at', 'description', 'notes', 'mic',
                  'person', 'organisation', 'dry_hire', 'based_on']