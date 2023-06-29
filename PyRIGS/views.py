import datetime
import operator
import re
import urllib.error
import urllib.parse
import urllib.request

from functools import reduce
from itertools import chain
from io import BytesIO

from PyPDF2 import PdfFileMerger, PdfFileReader
from z3c.rml import rml2pdf

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core import serializers
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy, reverse, NoReverseMatch
from django.views import generic
from django.views.decorators.clickjacking import xframe_options_exempt
from django.template.loader import get_template
from django.utils import timezone

from RIGS import models
from assets import models as asset_models
from training import models as training_models


def is_ajax(request):
    return request.headers.get('x-requested-with') == 'XMLHttpRequest'


def get_related(form, context):  # Get some other objects to include in the form. Used when there are errors but also nice and quick.
    for field, model in form.related_models.items():
        value = form[field].value()
        if value is not None and value != '':
            context[field] = model.objects.get(pk=value)


class Index(generic.TemplateView):  # Displays the current rig count along with a few other bits and pieces
    template_name = 'index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['rig_count'] = models.Event.objects.rig_count()
        context['now'] = models.Event.objects.events_in_bounds(timezone.now(), timezone.now()).exclude(status=models.Event.CANCELLED).filter(is_rig=True, dry_hire=False)
        return context


class SecureAPIRequest(generic.View):
    models = {
        'venue': models.Venue,
        'person': models.Person,
        'organisation': models.Organisation,
        'profile': models.Profile,
        'event': models.Event,
        'asset': asset_models.Asset,
        'supplier': asset_models.Supplier,
        'training_item': training_models.TrainingItem,
    }

    perms = {
        'venue': 'RIGS.view_venue',
        'person': 'RIGS.view_person',
        'organisation': 'RIGS.view_organisation',
        'profile': 'RIGS.view_profile',
        'event': None,
        'asset': None,
        'supplier': None,
        'training_item': None,
    }

    '''
    Validate the request is allowed based on user permissions.
    Raises 403 if denied.
    Potential to add API key validation at a later date.
    '''

    def __validate__(self, request, key, perm):
        if request.user.is_active:
            if request.user.is_superuser or perm is None:
                return True
            elif request.user.has_perm(perm):
                return True
        raise PermissionDenied()

    def get(self, request, model, pk=None, param=None):
        # Request permission validation things
        key = request.GET.get('apikey', None)
        perm = self.perms[model]
        self.__validate__(request, key, perm)

        # Response format where applicable
        format = request.GET.get('format', 'json')
        fields = request.GET.get('fields', None)
        if fields:
            fields = fields.split(",")
        filters = request.GET.get('filters', [])
        if filters:
            filters = filters.split(",")

        # Supply data for one record
        if pk:
            object = get_object_or_404(self.models[model], pk=pk)
            data = serializers.serialize(format, [object], fields=fields)
            return HttpResponse(data, content_type="application/" + format)

        # Supply data for autocomplete ajax request in json form
        term = request.GET.get('q', None)
        if term:
            if fields is None:  # Default to just name
                fields = ['name']

            # Build a list of Q objects for use later
            queries = []
            for part in term.split(" "):
                qs = []
                for field in fields:
                    q = Q(**{field + "__icontains": part})
                    qs.append(q)

                queries.append(reduce(operator.or_, qs))

            for f in filters:
                q = Q(**{f: True})
                queries.append(q)

            # Build the data response list
            results = []
            query = reduce(operator.and_, queries)
            objects = self.models[model].objects.filter(query)
            # Returning unactivated or unapproved users when they are elsewhere filtered out of the default queryset leads to some *very* unexpected results
            if model == "profile":
                objects = objects.filter(is_active=True, is_approved=True)
            for o in objects:
                name = o.display_name if hasattr(o, 'display_name') else o.name
                data = {
                    'pk': o.pk,
                    'value': o.pk,
                    'text': name,
                }
                try:  # See if there is a valid update URL
                    data['update'] = reverse(f"{model}_update", kwargs={'pk': o.pk})
                except NoReverseMatch:
                    pass
                results.append(data)

            # return a data response
            return JsonResponse(results, safe=False)

        start = request.GET.get('start', None)
        end = request.GET.get('end', None)

        if model == "event" and start and end:
            # Probably a calendar request
            start_datetime = datetime.datetime.strptime(start, "%Y-%m-%dT%H:%M:%S")
            end_datetime = datetime.datetime.strptime(end, "%Y-%m-%dT%H:%M:%S")

            objects = self.models[model].objects.events_in_bounds(start_datetime, end_datetime)

            results = []
            for item in objects:
                data = {
                    'pk': item.pk,
                    'title': item.name,
                    'is_rig': item.is_rig,
                    'status': str(item.get_status_display()),
                    'earliest': item.earliest_time.isoformat(),
                    'latest': item.latest_time.isoformat(),
                    'url': str(item.get_absolute_url())
                }

                results.append(data)
            return JsonResponse(results, safe=False)

        return HttpResponse(model)


class ModalURLMixin:
    def get_close_url(self, update, detail):
        if is_ajax(self.request):
            url = reverse_lazy('closemodal')
            update_url = str(reverse_lazy(update, kwargs={'pk': self.object.pk}))
            messages.info(self.request, "modalobject=" + serializers.serialize("json", [self.object]))
            messages.info(self.request, f"modalobject[0]['update_url']='{update_url}'")
        else:
            url = reverse_lazy(detail, kwargs={
                'pk': self.object.pk,
            })
        return url


class GenericListView(generic.ListView):
    template_name = 'generic_list.html'
    paginate_by = 20

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = self.model.__name__ + "s"
        if is_ajax(self.request):
            context['override'] = "base_ajax.html"
        return context

    def get_queryset(self):
        object_list = self.model.objects.search(query=self.request.GET.get('q', ""))

        orderBy = self.request.GET.get('orderBy', "name")
        if orderBy != "":
            object_list = object_list.order_by(orderBy)
        return object_list


class GenericDetailView(generic.DetailView):
    template_name = "generic_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f"{self.model.__name__} | {self.object.name}"
        if is_ajax(self.request):
            context['override'] = "base_ajax.html"
        return context


class GenericUpdateView(generic.UpdateView):
    template_name = "generic_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f"Edit {self.model.__name__}"
        if is_ajax(self.request):
            context['override'] = "base_ajax.html"
        return context


class GenericCreateView(generic.CreateView):
    template_name = "generic_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f"Create {self.model.__name__}"
        if is_ajax(self.request):
            context['override'] = "base_ajax.html"
        return context


class Search(generic.ListView):
    template_name = 'search_results.html'
    paginate_by = 20
    count = 0

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['count'] = self.count or 0
        context['query'] = self.request.GET.get('q')
        context['page_title'] = f"{context['count']} search results for <b>{context['query']}</b>"
        return context

    def get_queryset(self):
        request = self.request
        query = request.GET.get('q', None)

        if query is not None:
            event_results = models.Event.objects.search(query)
            person_results = models.Person.objects.search(query)
            organisation_results = models.Organisation.objects.search(query)
            venue_results = models.Venue.objects.search(query)
            invoice_results = models.Invoice.objects.search(query)
            asset_results = asset_models.Asset.objects.search(query)
            supplier_results = asset_models.Supplier.objects.search(query)
            trainee_results = training_models.Trainee.objects.search(query)
            training_item_results = training_models.TrainingItem.objects.search(query)

            # combine querysets
            queryset_chain = chain(
                event_results,
                person_results,
                organisation_results,
                venue_results,
                invoice_results,
                asset_results,
                supplier_results,
                trainee_results,
                training_item_results,
            )
            qs = sorted(queryset_chain,
                        key=lambda instance: instance.pk,
                        reverse=True)
            self.count = len(qs)  # since qs is actually a list
            return qs
        return models.Event.objects.none()  # just an empty queryset as default


class SearchHelp(generic.TemplateView):
    template_name = 'search_help.html'


class CloseModal(generic.TemplateView):
    """
    Called from a modal window (e.g. when an item is submitted to an event/invoice).
    May optionally also include some javascript in a success message to cause a load of
    the new information onto the page.
    """
    template_name = 'closemodal.html'

    def get_context_data(self, **kwargs):
        return {'messages': messages.get_messages(self.request)}


class OEmbedView(generic.View):
    def get(self, request, pk=None):
        embed_url = reverse(self.url_name, args=[pk])
        full_url = f"{request.scheme}://{request.META['HTTP_HOST']}{embed_url}"

        data = {
            'html': f'<iframe src="{full_url}" frameborder="0" width="100%" height="250"></iframe>',
            'version': '1.0',
            'type': 'rich',
            'height': '250'
        }

        return JsonResponse(data)


def get_info_string(user):
    user_str = f"by {user.name} " if user else ""
    time = timezone.now().strftime('%d/%m/%Y %H:%I')
    return f"[Paperwork generated {user_str}on {time}"


def render_pdf_response(template, context, append_terms):
    merger = PdfFileMerger()
    rml = template.render(context)
    buffer = rml2pdf.parseString(rml)
    merger.append(PdfFileReader(buffer))
    buffer.close()

    if append_terms:
        terms = urllib.request.urlopen(settings.TERMS_OF_HIRE_URL)
        merger.append(BytesIO(terms.read()))

    merged = BytesIO()
    merger.write(merged)

    response = HttpResponse(content_type='application/pdf')
    f = context['filename']
    response['Content-Disposition'] = f'filename="{f}"'
    response.write(merged.getvalue())
    return response


class PrintView(generic.View):
    append_terms = False

    def get_context_data(self, **kwargs):
        obj = get_object_or_404(self.model, pk=self.kwargs['pk'])
        object_name = re.sub(r'[^a-zA-Z0-9 \n\.]', '', obj.name)

        context = {
            'object': obj,
            'current_user': self.request.user,
            'object_name': object_name,
            'info_string': get_info_string(self.request.user) + f"- {obj.current_version_id}]",
        }

        return context

    def get(self, request, pk):
        return render_pdf_response(get_template(self.template_name), self.get_context_data(), self.append_terms)


class PrintListView(generic.ListView):
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['current_user'] = self.request.user
        context['info_string'] = get_info_string(self.request.user) + "]"
        return context

    def get(self, request):
        self.object_list = self.get_queryset()
        return render_pdf_response(get_template(self.template_name), self.get_context_data(), False)
