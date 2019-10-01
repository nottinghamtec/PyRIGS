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


class Login(auth_views.LoginView):
    template_name = 'registration/login.html'


class Logout(auth_views.LogoutView):
    template_name = 'registration/logout.html'


class PasswordChange(auth_views.PasswordChangeView):
    template_name = 'registration/password_change.html'

    def get_success_url(self):
        return reverse_lazy('profile_detail', kwargs={'pk': self.request.user.id})

class AssetList(LoginRequiredMixin, generic.ListView):
    model = models.Asset
    template_name = 'asset_list.html'
    paginate_by = 40
    ordering = ['-pk']


class AssetDetail(LoginRequiredMixin, generic.DetailView):
    model = models.Asset
    template_name = 'asset_update.html'


# class AssetCreate(LoginRequiredMixin, generic.TemplateView):
#     fields = '__all__'
#     template_name = 'asset_update.html'
#     # success_url = reverse_lazy('asset_list')


class AssetEdit(LoginRequiredMixin, generic.TemplateView):
    template_name = 'asset_update.html'

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


@login_required()
def asset_filter(request):
    context = dict()

    if request.method == 'POST' and request.is_ajax():
        defaults = QueryDict(request.POST['form'].encode('ASCII')).dict()
        defaults.pop('csrfmiddlewaretoken')

        context['object_list'] = models.Asset.objects.filter(
            Q(pk__icontains=defaults.get('asset_id')) |
            Q(asset_id__icontains=defaults.get('asset_id'))
        )

        if request.POST.get('sender', None) == 'asset_update':
            return render(request, template_name='asset_update_search_results.html', context=context)
        else:
            return render(request, template_name='asset_list_table_body.html', context=context)


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
