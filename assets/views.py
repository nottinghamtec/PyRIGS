from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, QueryDict
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
        if len(query) >= 3:
            return self.model.objects.filter(Q(asset_id__exact=query) | Q(description__icontains=query))
        elif query != "":
            return self.model.objects.filter(Q(asset_id__exact=query))
        else:
            cat = self.request.GET.get('cat', "")
            status = self.request.GET.get('status', "")
            if cat != "None":
                return self.model.objects.filter(category__name__exact=cat)
            elif status != "None":
                return self.model.objects.filter(status__name__exact=status)
            else:
                return self.model.objects.all()
    
    def get_context_data(self, **kwargs):
        context = super(AssetList, self).get_context_data(**kwargs)
        context["search_name"] = self.request.GET.get('query', "")
        context["categories"] = models.AssetCategory.objects.all()
        context["statuses"] = models.AssetStatus.objects.all()
        return context;

class AssetDetail(LoginRequiredMixin, generic.DetailView):
    model = models.Asset
    template_name = 'asset_update.html'


# class AssetCreate(LoginRequiredMixin, generic.TemplateView):
#     fields = '__all__'
#     template_name = 'asset_update.html'
#     # success_url = reverse_lazy('asset_list')

class AssetEdit(LoginRequiredMixin, generic.UpdateView):
    template_name = 'asset_update.html'
    model = models.Asset
    form_class = forms.AssetForm

    def get_context_data(self, **kwargs):
        context = super(AssetEdit, self).get_context_data(**kwargs)
        if self.kwargs:
            context['object'] = get_object_or_404(models.Asset, pk=self.kwargs['pk'])
        context['form'] = forms.AssetForm
        # context['asset_names'] = models.Asset.objects.values_list('asset_id', 'description').order_by('-date_acquired')[]

        if self.request.GET.get('duplicate'):
            context['duplicate'] = True
            context['previous_asset_id'] = context['object'].asset_id
            context['previous_asset_pk'] = context['object'].pk
            context['object'].pk = 0
            context['object'].asset_id = ''
            context['object'].serial_number = ''
        else:
            context['edit'] = True

        return context

    def get_success_url(self):
        return reverse("asset_detail", kwargs={"pk":self.object.id})

class AssetCreate(LoginRequiredMixin, generic.CreateView):
    template_name = 'asset_update.html'
    model = models.Asset
    form_class = forms.AssetForm

    def get_context_data(self, **kwargs):
        context = super(AssetCreate, self).get_context_data(**kwargs)
        context["create"] = True
        return context

@login_required()
def asset_update(request):
    context = dict()

    if request.method == 'POST' and request.is_ajax():
        defaults = QueryDict(request.POST['form'].encode('ASCII')).dict()
        defaults.pop('csrfmiddlewaretoken')

        asset_pk = int(defaults.pop('id'))

        if defaults['date_acquired']:
            defaults['date_acquired'] = parser.parse(defaults.pop('date_acquired'))
        else:
            defaults['date_acquired'] = None

        if defaults['date_sold']:
            defaults['date_sold'] = parser.parse(defaults.pop('date_sold'))
        else:
            defaults['date_sold'] = None

        # if defaults['parent']:
        #     defaults['parent'] = models.Asset.objects.get(asset_id=defaults.pop('parent'))

        form = forms.AssetForm(defaults)
        context['valid'] = form.is_valid()
        context['errors'] = form.errors.as_json()

        if asset_pk == 0:
            asset = models.Asset.objects.create(**form.cleaned_data)
        else:
            asset, created = models.Asset.objects.update_or_create(pk=asset_pk, defaults=form.cleaned_data)

        context['url'] = reverse('asset_detail', args=[asset.pk])

        return HttpResponse(json.dumps(context), content_type='application/json')


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
