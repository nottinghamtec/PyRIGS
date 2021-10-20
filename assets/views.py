import simplejson
import random
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core import serializers
from django.db.models import Q
from django.http import Http404, HttpResponse, JsonResponse
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import generic
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404

from PIL import Image, ImageDraw, ImageFont
from barcode import Code39
from barcode.writer import ImageWriter

from PyRIGS.views import GenericListView, GenericDetailView, GenericUpdateView, GenericCreateView, ModalURLMixin, \
    is_ajax, OEmbedView
from assets import forms, models
from assets.models import get_available_asset_id


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
        if self.request.method == 'GET' and len(self.request.GET) > 0:
            self.form = forms.AssetSearchForm(data=self.request.GET)
        else:
            self.form = forms.AssetSearchForm(data=self.get_initial())
        form = self.form
        if not form.is_valid():
            return self.model.objects.none()

        # TODO Feedback to user when search fails
        query_string = form.cleaned_data['q'] or ""
        if len(query_string) == 0:
            queryset = self.model.objects.all()
        elif len(query_string) >= 3:
            queryset = self.model.objects.filter(
                Q(asset_id__exact=query_string.upper()) | Q(description__icontains=query_string) | Q(serial_number__exact=query_string))
        else:
            queryset = self.model.objects.filter(Q(asset_id__exact=query_string.upper()))

        if form.cleaned_data['category']:
            queryset = queryset.filter(category__in=form.cleaned_data['category'])

        if len(form.cleaned_data['status']) > 0:
            queryset = queryset.filter(status__in=form.cleaned_data['status'])
        elif self.hide_hidden_status:
            queryset = queryset.filter(
                status__in=models.AssetStatus.objects.filter(should_show=True))

        return queryset.select_related('category', 'status')

    def get_context_data(self, **kwargs):
        context = super(AssetList, self).get_context_data(**kwargs)
        context["form"] = self.form
        if hasattr(self.form, 'cleaned_data'):
            context["category_filters"] = self.form.cleaned_data.get('category')
            context["status_filters"] = self.form.cleaned_data.get('status')
        context["categories"] = models.AssetCategory.objects.all()
        context["statuses"] = models.AssetStatus.objects.all()
        context["page_title"] = "Asset List"
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Asset {}".format(self.object.display_id)
        return context


class AssetEdit(LoginRequiredMixin, AssetIDUrlMixin, generic.UpdateView):
    template_name = 'asset_form.html'
    model = models.Asset
    form_class = forms.AssetForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["edit"] = True
        context["connectors"] = models.Connector.objects.all()
        context["page_title"] = "Edit Asset: {}".format(self.object.display_id)
        return context

    def get_success_url(self):
        if is_ajax(self.request):
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
        context["page_title"] = "Create Asset"
        return context

    def get_initial(self, *args, **kwargs):
        initial = super().get_initial(*args, **kwargs)
        initial["asset_id"] = get_available_asset_id()
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
        context["page_title"] = "Duplication of Asset: {}".format(context['previous_asset_id'])
        return context


class AssetEmbed(AssetDetail):
    template_name = 'asset_embed.html'


class AssetOEmbed(OEmbedView):
    model = models.Asset
    url_name = 'asset_embed'


class AssetAuditList(AssetList):
    template_name = 'asset_audit_list.html'
    hide_hidden_status = False

    # TODO Refresh this when the modal is submitted
    def get_queryset(self):
        self.form = forms.AssetSearchForm(data=self.request.GET)
        return self.model.objects.filter(Q(last_audited_at__isnull=True)).select_related('category', 'status')

    def get_context_data(self, **kwargs):
        context = super(AssetAuditList, self).get_context_data(**kwargs)
        context['page_title'] = "Asset Audit List"
        return context


class AssetAudit(AssetEdit):
    template_name = 'asset_audit.html'
    form_class = forms.AssetAuditForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Audit Asset: {}".format(self.object.display_id)
        return context

    def get_success_url(self):
        # TODO For some reason this doesn't stick when done in form_valid??
        asset = self.get_object()
        asset.last_audited_by = self.request.user
        asset.last_audited_at = timezone.now()
        asset.save()
        return super().get_success_url()


class SupplierList(GenericListView):
    model = models.Supplier
    ordering = ['name']

    def get_context_data(self, **kwargs):
        context = super(SupplierList, self).get_context_data(**kwargs)
        context['create'] = 'supplier_create'
        context['edit'] = 'supplier_update'
        context['can_edit'] = self.request.user.has_perm('assets.change_supplier')
        context['detail'] = 'supplier_detail'
        if is_ajax(self.request):
            context['override'] = "base_ajax.html"
        else:
            context['override'] = 'base_assets.html'
        return context


class SupplierSearch(SupplierList):
    hide_hidden_status = False

    def render_to_response(self, context, **response_kwargs):
        result = []

        for supplier in context["object_list"]:
            result.append({"id": supplier.pk, "name": supplier.name})
        return JsonResponse(result, safe=False)


class SupplierDetail(GenericDetailView):
    model = models.Supplier

    def get_context_data(self, **kwargs):
        context = super(SupplierDetail, self).get_context_data(**kwargs)
        context['history_link'] = 'supplier_history'
        context['update_link'] = 'supplier_update'
        context['detail_link'] = 'supplier_detail'
        context['associated'] = 'partials/associated_assets.html'
        context['associated2'] = ''
        if is_ajax(self.request):
            context['override'] = "base_ajax.html"
        else:
            context['override'] = 'base_assets.html'
        context['can_edit'] = self.request.user.has_perm('assets.change_supplier')
        return context


class SupplierCreate(GenericCreateView, ModalURLMixin):
    model = models.Supplier
    form_class = forms.SupplierForm

    def get_context_data(self, **kwargs):
        context = super(SupplierCreate, self).get_context_data(**kwargs)
        if is_ajax(self.request):
            context['override'] = "base_ajax.html"
        else:
            context['override'] = 'base_assets.html'
        return context

    def get_success_url(self):
        return self.get_close_url('supplier_update', 'supplier_detail')


class SupplierUpdate(GenericUpdateView, ModalURLMixin):
    model = models.Supplier
    form_class = forms.SupplierForm

    def get_context_data(self, **kwargs):
        context = super(SupplierUpdate, self).get_context_data(**kwargs)
        if is_ajax(self.request):
            context['override'] = "base_ajax.html"
        else:
            context['override'] = 'base_assets.html'
        return context

    def get_success_url(self):
        return self.get_close_url('supplier_update', 'supplier_detail')


class CableTypeList(generic.ListView):
    model = models.CableType
    template_name = 'cable_type_list.html'
    paginate_by = 40

    def get_queryset(self):
        return self.model.objects.select_related('plug', 'socket')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Cable Type List"
        return context


class CableTypeDetail(generic.DetailView):
    model = models.CableType
    template_name = 'cable_type_detail.html'

    def get_context_data(self, **kwargs):
        context = super(CableTypeDetail, self).get_context_data(**kwargs)
        context["page_title"] = "Cable Type {}".format(str(self.object))
        return context


class CableTypeCreate(generic.CreateView):
    model = models.CableType
    template_name = "cable_type_form.html"
    form_class = forms.CableTypeForm

    def get_context_data(self, **kwargs):
        context = super(CableTypeCreate, self).get_context_data(**kwargs)
        context["create"] = True
        context["page_title"] = "Create Cable Type"

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
        context["page_title"] = "Edit Cable Type"

        return context

    def get_success_url(self):
        return reverse("cable_type_detail", kwargs={"pk": self.object.pk})


class GenerateLabel(generic.View):
    def get(self, request, pk):
        black = (0, 0, 0)
        white = (255, 255, 255)
        size = (700, 200)
        font = ImageFont.truetype("static/fonts/OpenSans-Regular.tff", 20)
        obj = get_object_or_404(models.Asset, asset_id=pk)

        asset_id = "Asset: {}".format(obj.asset_id)
        length = "Length: {}m".format(obj.length)
        csa = "CSA: {}mm²".format(obj.csa)

        image = Image.new("RGB", size, white)
        logo = Image.open("static/imgs/square_logo.png")
        draw = ImageDraw.Draw(image)

        draw.text((210, 140), asset_id, fill=black, font=font)
        draw.text((210, 170), length, fill=black, font=font)
        draw.text((350, 170), csa, fill=black, font=font)
        draw.multiline_text((500, 140), "TEC PA & Lighting\n(0115) 84 68720", fill=black, font=font)

        barcode = Code39(str(obj.asset_id), writer=ImageWriter())

        logo_size = (200, 200)
        image.paste(logo.resize(logo_size, Image.ANTIALIAS))
        barcode_image = barcode.render(writer_options={"quiet_zone": 0, "write_text": False})
        width, height = barcode_image.size
        image.paste(barcode_image.crop((0, 0, width, 135)), (int(((size[0] + logo_size[0]) - width) / 2), 0))

        response = HttpResponse(content_type="image/png")
        image.save(response, "PNG")
        return response
