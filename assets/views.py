from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views import generic
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.urls import reverse
from django.db.models import Q
from assets import models, forms


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
            queryset = self.model.objects.filter(Q(asset_id__exact=query_string) | Q(description__icontains=query_string))
        else:
            queryset = self.model.objects.filter(Q(asset_id__exact=query_string))

        if form.cleaned_data['category']:
            queryset = queryset.filter(category__in=form.cleaned_data['category'])

        if len(form.cleaned_data['status']) > 0:
            queryset = queryset.filter(status__in=form.cleaned_data['status'])
        elif self.hide_hidden_status:
            queryset = queryset.filter(status__in=models.AssetStatus.objects.filter(should_show=True))

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
            raise Http404(_("No %(verbose_name)s found matching the query") %
                          {'verbose_name': queryset.model._meta.verbose_name})
        return obj


class AssetDetail(LoginRequiredMixin, AssetIDUrlMixin, generic.DetailView):
    model = models.Asset
    template_name = 'asset_update.html'


class AssetEdit(LoginRequiredMixin, AssetIDUrlMixin, generic.UpdateView):
    template_name = 'asset_update.html'
    model = models.Asset
    form_class = forms.AssetForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['edit'] = True
        context["connectors"] = models.Connector.objects.all()

        return context

    def get_success_url(self):
        return reverse("asset_detail", kwargs={"pk": self.object.asset_id})


class AssetCreate(LoginRequiredMixin, generic.CreateView):
    template_name = 'asset_create.html'
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
    model = models.Asset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["create"] = None
        context["duplicate"] = True
        context['previous_asset_id'] = self.get_object().asset_id
        return context


class SupplierList(generic.ListView):
    model = models.Supplier
    template_name = 'supplier_list.html'
    paginate_by = 40
    ordering = ['name']

    def get_queryset(self):
        if self.request.method == 'POST':
            self.form = forms.SupplierSearchForm(data=self.request.POST)
        elif self.request.method == 'GET':
            self.form = forms.SupplierSearchForm(data=self.request.GET)
        else:
            self.form = forms.SupplierSearchForm(data={})
        form = self.form
        if not form.is_valid():
            return self.model.objects.none()

        query_string = form.cleaned_data['query'] or ""
        if len(query_string) == 0:
            queryset = self.model.objects.all()
        else:
            queryset = self.model.objects.filter(Q(name__icontains=query_string))

        return queryset

    def get_context_data(self, **kwargs):
        context = super(SupplierList, self).get_context_data(**kwargs)
        context["form"] = self.form
        return context


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
