__author__ = 'Ghost'
from django import forms
from django.utils import formats
from django.conf import settings
from django.core import serializers
import simplejson

from RIGS import models


# Events Shit
class EventForm(forms.ModelForm):
    datetime_input_formats = formats.get_format_lazy("DATETIME_INPUT_FORMATS") + settings.DATETIME_INPUT_FORMATS
    meet_at = forms.DateTimeField(input_formats=datetime_input_formats, required=False)
    access_at = forms.DateTimeField(input_formats=datetime_input_formats, required=False)
    name = forms.CharField(min_length=3)

    items_json = forms.CharField()

    items = {}

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

    def process_items_json(self, event=None):
        data = simplejson.loads(self.cleaned_data['items_json'])
        items = {}
        for key in data:
            pk = int(key)
            items[pk] = self._get_or_initialise_item(pk, data[key]['fields'], event)

        return items

    def _get_or_initialise_item(self, pk, data, event):
        if (pk < 0):
            item = models.EventItem()
        else:
            item = models.EventItem.objects.get(pk=pk)

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
        fields = ['is_rig', 'name', 'venue', 'start_date', 'start_time', 'end_date',
                  'end_time', 'meet_at', 'access_at', 'description', 'notes', 'mic',
                  'person', 'organisation', 'dry_hire', 'based_on']