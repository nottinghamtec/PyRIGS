from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, QueryDict, JsonResponse
from django.core import serializers
from django.views import generic
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy, reverse
from django.db.models import Q
import datetime
from dateutil import parser
# import json
import simplejson as json
from assets import models, forms

class AssetList(LoginRequiredMixin, generic.ListView):
    model = models.Asset
    template_name = 'asset_list.html'
    paginate_by = 40
    ordering = ['-pk']
        
    def get_queryset(self):
        #TODO Feedback to user when search fails
        query = self.request.GET.get('query', "")
        if len(query) == 0:
            queryset = self.model.objects.all()
        elif len(query) >= 3:
            queryset = self.model.objects.filter(Q(asset_id__exact=query) | Q(description__icontains=query))
        else:
            queryset = self.model.objects.filter(Q(asset_id__exact=query))
        
        cat = self.request.GET.get('cat', "")
        status = self.request.GET.get('status', "")
        if cat != "":
            queryset = queryset.filter(category__name__exact=cat)
        if status != "":
            queryset = queryset.filter(status__name__exact=status)

        return queryset
    
    def get_context_data(self, **kwargs):
        context = super(AssetList, self).get_context_data(**kwargs)
        context["search_name"] = self.request.GET.get('query', "")

        context["categories"] = models.AssetCategory.objects.all()
        context["category_select"] = self.request.GET.get('cat', "")

        context["statuses"] = models.AssetStatus.objects.all()
        context["status_select"] = self.request.GET.get('status', "")
        return context

class AssetSearch(AssetList):
    def render_to_response(self, context, **response_kwargs):
        result = []

        for asset in context["object_list"]:
            result.append({"id":asset.pk, "label":(asset.asset_id + " | " + asset.description)})
        
        return JsonResponse(result, safe=False)

class AssetDetail(LoginRequiredMixin, generic.DetailView):
    model = models.Asset
    template_name = 'asset_update.html'

class AssetEdit(LoginRequiredMixin, generic.UpdateView):
    template_name = 'asset_update.html'
    model = models.Asset
    form_class = forms.AssetForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['edit'] = True
        context["connectors"] = models.Connector.objects.all()

        return context

    def get_success_url(self):
        return reverse("asset_detail", kwargs={"pk":self.object.id})

class AssetCreate(LoginRequiredMixin, generic.CreateView):
    template_name = 'asset_create.html'
    model = models.Asset
    form_class = forms.AssetForm

    def get_context_data(self, **kwargs):
        context = super(AssetCreate, self).get_context_data(**kwargs)
        
        context["create"] = True
        context["connectors"] = models.Connector.objects.all()

        return context
    
    def get_success_url(self):
        return reverse("asset_detail", kwargs={"pk":self.object.id})

class DuplicateMixin:
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.pk = None
        return self.render_to_response(self.get_context_data())

class AssetDuplicate(DuplicateMixin, AssetCreate):
    model = models.Asset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["create"] = None
        context["duplicate"] = True
        context['previous_asset_id'] = self.get_object().asset_id
        context["previous_asset_pk"] = self.kwargs.get(self.pk_url_kwarg)
        return context

@login_required()
def asset_delete(request):
    context = dict()
    if request.method == 'POST' and request.is_ajax():
        asset = get_object_or_404(models.Asset, pk=request.POST.get('asset_id', None))
        asset.delete()

        context['url'] = reverse('asset_list')

        return HttpResponse(json.dumps(context), content_type='application/json')

class SupplierList(generic.ListView):
    model = models.Supplier
    template_name = 'supplier_list.html'
    paginate_by = 40
    ordering = ['name']


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
