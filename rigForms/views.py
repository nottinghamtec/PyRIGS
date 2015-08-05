from django.shortcuts import render
from django.views import generic
from rigForms import models

class FormCreate(generic.CreateView):
	model = models.Form
	fields = ['data']

	"""
	Expects kwarg "type_pk" to contain PK of required type
	"""
	def get_context_data(self, **kwargs):
		context = super(FormCreate, self).get_context_data(**kwargs)
		schemaType = get_object_or_404(models.Type,kwargs["type_pk"])
		currentSchema = models.Schema.objects.current_schema(schemaType)

		context["type"] = schemaType
		context["schema"] = currentSchema

		return context
