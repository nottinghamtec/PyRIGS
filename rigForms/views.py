from django.shortcuts import render
from django.views import generic
from rigForms import models

from django.shortcuts import get_object_or_404
from django.http.response import HttpResponseRedirect
from django.core.urlresolvers import reverse_lazy, reverse, NoReverseMatch
from django.db.models import Q

import json
from collections import OrderedDict
from z3c.rml import rml2pdf
from django.template.loader import get_template
from django.template import RequestContext
import cStringIO as StringIO
import re
import copy


from django.http import HttpResponse

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
		context["edit"] = True

		return context

	def form_valid(self, form):
		self.object = form.save(commit=False)
		self.object.event = self.event
		self.object.schema = self.schema
		self.object.save()
		return HttpResponseRedirect(self.get_success_url())

	def get_success_url(self):
		return reverse_lazy('form_detail', kwargs={
                'pk': self.object.pk,
            })

class FormDetail(generic.DetailView):
	model = models.Form
	template_name = 'rigForms/form_form.html'

	def get_success_url(self):
		return reverse_lazy('update_form', kwargs={
                'pk': self.object.pk,
            })

	def get_context_data(self, **kwargs):
		context = super(FormDetail, self).get_context_data()
		
		context["edit"] = False

		return context

class FormUpdate(generic.UpdateView):
	model = models.Form
	fields = ['data']

	def get_success_url(self):
		return reverse_lazy('form_detail', kwargs={
                'pk': self.object.pk,
            })

	def get_context_data(self, **kwargs):
		context = super(FormUpdate, self).get_context_data()
		
		context["edit"] = True

		return context

class FormList(generic.ListView):
	model = models.Form

	def get_queryset(self):
		event = get_object_or_404(RIGS.models.Event,pk=self.kwargs["event_pk"])
		object_list = self.model.objects.filter(Q(event=event))

		return object_list

	def get_context_data(self):
		context = super(FormList, self).get_context_data()
		context['event'] = get_object_or_404(RIGS.models.Event,pk=self.kwargs["event_pk"])

		context['formTypes'] = models.Type.objects.filter(Q(active=True))

		return context

class FormPrint(generic.TemplateView):
	indentBy = 20

	def _render_array(self, field, value, current_indent):
		# Render all the child form bits first
		children=[]

		try:
			numberOfChildren = len(value)
		
			for key,item in enumerate(value):
				# Append the item number onto the item title
				thisField = copy.deepcopy(field["items"])
				thisField["title"] = thisField.get("title","Item") + " " + str(key+1)

				children.append(self._render_field_item(thisField,item,current_indent+self.indentBy))
		except TypeError:
			numberOfChildren = 0

		template = get_template('rigForms/print/render-array.xml')
		context = {
			'field': field,
			'children': children,
			'currentIndent':current_indent
		}
		return template.render(context)

	def _render_object(self, field, value, current_indent):
		# Render all the child form bits first
		children = self._render_field(field["properties"], value, current_indent + self.indentBy)
		
		template = get_template('rigForms/print/render-object.xml')
		context = {
			'field': field,
			'children': children,
			'currentIndent':current_indent
		}
		return template.render(context)

	def _render_string(self, field, value, current_indent):
		template = get_template('rigForms/print/render-string.xml')
		context = {
			'field': field,
			'currentIndent':current_indent,
			'value':value
		}
		return template.render(context)

	def _render_boolean(self, field, value, current_indent):
		template = get_template('rigForms/print/render-boolean.xml')
		context = {
			'field': field,
			'currentIndent':current_indent,
			'value':value
		}
		return template.render(context)

	def _render_field_item(self, field, value, current_indent):
		renderFunctions = {
			"object": self._render_object,
			"string": self._render_string,
			"number": self._render_string,
			"integer": self._render_string,
			"array": self._render_array,
			"boolean": self._render_boolean,

			#error values:
			"unknown": lambda: "<h4>(Field type unknown: " + str(key) + ": " + str(field) + ")</h4>",
			"notype": lambda: "<h4>(No field type: " + str(key) + ": " + str(field) + ")</h4>",
			"notOD": lambda: "<h4>(Not an OrderedDict: " + str(key) + ": " + str(field) + ")</h4>",
		}

		result = ""
		if type(field) is OrderedDict:
			fieldType = field.get("type","notype")
			func = renderFunctions.get(fieldType, renderFunctions["unknown"])
			result += func(field, value, current_indent)
		else:
			result += renderFunctions["notOD"]()

		return result

	def _render_field(self, parentField, parentValue, current_indent):
		result = ""
		for (key,field) in parentField.items():
			try:
				value = parentValue.get(key,None)
			except AttributeError: # if parentValue is None
				value = None
			result += self._render_field_item(field, value, current_indent)
			
		return result

	def get(self, request, pk):
		form = get_object_or_404(models.Form, pk=pk)

		jsonSchema = json.loads(form.schema.schema, object_pairs_hook=OrderedDict)
		jsonData = json.loads(form.data, object_pairs_hook=OrderedDict)

		formData = self._render_field(jsonSchema["properties"], jsonData, 0)

		# For development return the raw string
		# response = HttpResponse()
		# response.write(pdfData)
		# return response

		template = get_template('rigForms/form_print.xml')

		context = RequestContext(request, {
			'fonts': {
				'opensans': {
					'regular': 'RIGS/static/fonts/OPENSANS-REGULAR.TTF',
					'bold': 'RIGS/static/fonts/OPENSANS-BOLD.TTF',
				}
			},
			'formData':formData,
			'form':form
		})

		rml = template.render(context)
		buffer = StringIO.StringIO()

		buffer = rml2pdf.parseString(rml)

		pdfData = buffer.read()

		# escapedEventName = re.sub('[^a-zA-Z0-9 \n\.]', '', object.name)

		response = HttpResponse(content_type='application/pdf')
		response['Content-Disposition'] = "filename=Form.pdf"
		response.write(pdfData)
		return response