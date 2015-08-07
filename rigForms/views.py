from django.shortcuts import render
from django.views import generic
from rigForms import models

from django.shortcuts import get_object_or_404
from django.http.response import HttpResponseRedirect
from django.core.urlresolvers import reverse_lazy, reverse, NoReverseMatch

import RIGS

class FormCreate(generic.CreateView):
	model = models.Form
	fields = ['data']

	"""
	Whenever this view is loaded, get the schema from the url
	Expects kwarg "type_pk" to contain PK of required type
	"""
	def dispatch(self, *args, **kwargs):
		schemaType = get_object_or_404(models.Type, pk=kwargs['type_pk'])
		currentSchema = models.Schema.objects.current_schema(schemaType)

		self.schema = currentSchema

		self.event = get_object_or_404(RIGS.models.Event, pk=kwargs['event_pk'])

		return super(FormCreate, self).dispatch(*args, **kwargs)

	def get_context_data(self, **kwargs):
		context = super(FormCreate, self).get_context_data()
		
		context["object"] = {
			"schema": self.schema,
			"event": self.event,
			"data": "{}"
		}

		return context

	def form_valid(self, form):
		self.object = form.save(commit=False)
		self.object.event = self.event
		self.object.schema = self.schema
		self.object.save()
		return HttpResponseRedirect(self.get_success_url())

	def get_success_url(self):
		return reverse_lazy('update_form', kwargs={
                'pk': self.object.pk,
            })

class FormUpdate(generic.UpdateView):
	model = models.Form
	fields = ['data']

	def get_success_url(self):
		return reverse_lazy('update_form', kwargs={
                'pk': self.object.pk,
            })
