from django.shortcuts import render
from django.views import generic
from django.urls import reverse_lazy
from assets import models, forms


class Index(generic.TemplateView):
    template_name = 'index.html'


class AssetList(generic.ListView):
    model = models.Asset
    template_name = 'assets/asset_list.html'


class AssetDetail(generic.DetailView):
    model = models.Asset
    template_name = 'assets/asset_detail.html'


class AssetCreate(generic.CreateView):
    model = models.Asset
    fields = '__all__'
    template_name = 'assets/asset_form.html'
    # success_url = reverse_lazy('asset_list')


class AssetUpdate(generic.UpdateView):
    model = models.Asset
    fields = '__all__'
    template_name = 'assets/asset_form.html'


class AssetDelete(generic.DeleteView):
    model = models.Asset
    template_name = 'confirm_delete.html'
    success_url = reverse_lazy('asset_list')
