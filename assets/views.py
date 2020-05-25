import datetime

import simplejson
from assets import forms, models
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core import serializers
from django.db.models import Q
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import generic
from django.views.decorators.csrf import csrf_exempt
from versioning import versioning
from PyRIGS.views import GenericListView


@method_decorator(csrf_exempt, name='dispatch')
class AssetList(LoginRequiredMixin, generic.ListView):
    model = models.Asset
    template_name = 'asset_list.html'
    paginate_by = 40
    ordering = ['-pk']
    hide_hidden_status = True

    def get_initial(self):
        initial = {'status': models.AssetStatus.objects.filter(should_show=True)}
        return initial

    def get_queryset(self):
        if self.request.method == 'POST':
            self.form = forms.AssetSearchForm(data=self.request.POST)
        elif self.request.method == 'GET' and len(self.request.GET) > 0:
            self.form = forms.AssetSearchForm(data=self.request.GET)
        else:
            self.form = forms.AssetSearchForm(data=self.get_initial())
        form = self.form
        if not form.is_valid():
            return self.model.objects.none()

        # TODO Feedback to user when search fails
        query_string = form.cleaned_data['query'] or ""
        if len(query_string) == 0:
            queryset = self.model.objects.all()
        elif len(query_string) >= 3:
            queryset = self.model.objects.filter(
                Q(asset_id__exact=query_string) | Q(description__icontains=query_string) | Q(serial_number__exact=query_string))
        else:
            queryset = self.model.objects.filter(Q(asset_id__exact=query_string))

        if form.cleaned_data['category']:
            queryset = queryset.filter(category__in=form.cleaned_data['category'])

        if len(form.cleaned_data['status']) > 0:
            queryset = queryset.filter(status__in=form.cleaned_data['status'])
        elif self.hide_hidden_status:
            queryset = queryset.filter(
                status__in=models.AssetStatus.objects.filter(should_show=True))

        return queryset

    def get_context_data(self, **kwargs):
        context = super(AssetList, self).get_context_data(**kwargs)
        context["form"] = self.form

        context["categories"] = models.AssetCategory.objects.all()

        context["statuses"] = models.AssetStatus.objects.all()
        return context


class AssetSearch(AssetList):
    hide_hidden_status = False

    def render_to_response(self, context, **response_kwargs):
        result = []

        for asset in context["object_list"]:
            result.append({"id": asset.pk, "label": (asset.asset_id + " | " + asset.description)})

        return JsonResponse(result, safe=False)


class AssetIDUrlMixin:
    def get_object(self, queryset=None):
        pk = self.kwargs.get(self.pk_url_kwarg)
        queryset = models.Asset.objects.filter(asset_id=pk)
        try:
            # Get the single item from the filtered queryset
            obj = queryset.get()
        except queryset.model.DoesNotExist:
            raise Http404("No assets found matching the query")
        return obj


class AssetDetail(LoginRequiredMixin, AssetIDUrlMixin, generic.DetailView):
    model = models.Asset
    template_name = 'asset_detail.html'


class AssetEdit(LoginRequiredMixin, AssetIDUrlMixin, generic.UpdateView):
    template_name = 'asset_form.html'
    model = models.Asset
    form_class = forms.AssetForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["edit"] = True
        context["connectors"] = models.Connector.objects.all()

        return context

    def get_success_url(self):
        if self.request.is_ajax():
            url = reverse_lazy('closemodal')
            update_url = str(reverse_lazy('asset_update', kwargs={'pk': self.object.pk}))
            messages.info(self.request, "modalobject=" + serializers.serialize("json", [self.object]))
            messages.info(self.request, "modalobject[0]['update_url']='" + update_url + "'")
        else:
            url = reverse_lazy('asset_detail', kwargs={'pk': self.object.asset_id, })
        return url


class AssetCreate(LoginRequiredMixin, generic.CreateView):
    template_name = 'asset_form.html'
    model = models.Asset
    form_class = forms.AssetForm

    def get_context_data(self, **kwargs):
        context = super(AssetCreate, self).get_context_data(**kwargs)
        context["create"] = True
        context["connectors"] = models.Connector.objects.all()

        return context

    def get_initial(self, *args, **kwargs):
        initial = super().get_initial(*args, **kwargs)
        initial["asset_id"] = models.Asset.get_available_asset_id()
        return initial

    def get_success_url(self):
        return reverse("asset_detail", kwargs={"pk": self.object.asset_id})


class DuplicateMixin:
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.pk = None
        return self.render_to_response(self.get_context_data())


class AssetDuplicate(DuplicateMixin, AssetIDUrlMixin, AssetCreate):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["create"] = None
        context["duplicate"] = True
        context['previous_asset_id'] = self.get_object().asset_id
        return context


class AssetOembed(generic.View):
    model = models.Asset

    def get(self, request, pk=None):
        embed_url = reverse('asset_embed', args=[pk])
        full_url = "{0}://{1}{2}".format(request.scheme, request.META['HTTP_HOST'], embed_url)

        data = {
            'html': '<iframe src="{0}" frameborder="0" width="100%" height="250"></iframe>'.format(full_url),
            'version': '1.0',
            'type': 'rich',
            'height': '250'
        }

        json = simplejson.JSONEncoderForHTML().encode(data)
        return HttpResponse(json, content_type="application/json")


class AssetEmbed(AssetDetail):
    template_name = 'asset_embed.html'


@method_decorator(csrf_exempt, name='dispatch')
class AssetAuditList(AssetList):
    template_name = 'asset_audit_list.html'
    hide_hidden_status = False

    # TODO Refresh this when the modal is submitted
    def get_queryset(self):
        self.form = forms.AssetSearchForm(data={})
        return self.model.objects.filter(Q(last_audited_at__isnull=True))


class AssetAudit(AssetEdit):
    template_name = 'asset_audit.html'
    form_class = forms.AssetAuditForm

    def get_success_url(self):
        # TODO For some reason this doesn't stick when done in form_valid??
        asset = self.get_object()
        asset.last_audited_by = self.request.user
        asset.last_audited_at = timezone.now()
        asset.save()
        return super().get_success_url()


class SupplierList(GenericListView):
    model = models.Supplier
    template_name = 'supplier_list.html'
    ordering = ['name']


class SupplierSearch(SupplierList):
    hide_hidden_status = False

    def render_to_response(self, context, **response_kwargs):
        result = []

        for supplier in context["object_list"]:
            result.append({"id": supplier.pk, "name": supplier.name})
        return JsonResponse(result, safe=False)


class SupplierDetail(generic.DetailView):
    model = models.Supplier
    template_name = 'supplier_detail.html'


class SupplierCreate(generic.CreateView):
    model = models.Supplier
    form_class = forms.SupplierForm
    template_name = 'supplier_update.html'


class SupplierUpdate(generic.UpdateView):
    model = models.Supplier
    form_class = forms.SupplierForm
    template_name = 'supplier_update.html'


class SupplierVersionHistory(versioning.VersionHistory):
    template_name = "asset_version_history.html"


class AssetVersionHistory(versioning.VersionHistory):
    template_name = "version_history.html"

    def get_object(self, **kwargs):
        return get_object_or_404(models.Asset, asset_id=self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        context = super(AssetVersionHistory, self).get_context_data(**kwargs)
        context['object'] = self.get_object()
        context['id'] = self.get_object().asset_id
        context['override'] = 'base_assets.html'

        return context


class ActivityTable(versioning.ActivityTable):
    model = versioning.RIGSVersion
    template_name = "activity_table.html"
    paginate_by = 25

    def get_queryset(self):
        versions = versioning.RIGSVersion.objects.get_for_multiple_models(
            [models.Asset, models.Supplier])
        return versions

    def get_context_data(self, **kwargs):
        context = super(ActivityTable, self).get_context_data(**kwargs)
        context['override'] = 'base_assets.html'
        context['title'] = 'Asset Database'

        return context


class CableTypeList(generic.ListView):
    model = models.CableType
    template_name = 'cable_type_list.html'
    paginate_by = 40
    # ordering = ['__str__']


class CableTypeDetail(generic.DetailView):
    model = models.CableType
    template_name = 'cable_type_form.html'


class CableTypeCreate(generic.CreateView):
    model = models.CableType
    template_name = "cable_type_form.html"
    form_class = forms.CableTypeForm

    def get_context_data(self, **kwargs):
        context = super(CableTypeCreate, self).get_context_data(**kwargs)
        context["create"] = True

        return context

    def get_success_url(self):
        return reverse("cable_type_detail", kwargs={"pk": self.object.pk})


class CableTypeUpdate(generic.UpdateView):
    model = models.CableType
    template_name = "cable_type_form.html"
    form_class = forms.CableTypeForm

    def get_context_data(self, **kwargs):
        context = super(CableTypeUpdate, self).get_context_data(**kwargs)
        context["edit"] = True

        return context

    def get_success_url(self):
        return reverse("cable_type_detail", kwargs={"pk": self.object.pk})
