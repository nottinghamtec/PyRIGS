import base64
import datetime
from io import BytesIO

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core import serializers
from django.core.paginator import Paginator
from django.db.models import Exists, F, OuterRef, Q, Subquery, Sum
from django.http import FileResponse, HttpResponse
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import generic
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import get_template

from pypdf import PdfReader, PdfWriter
from PIL import Image, ImageDraw, ImageFont, ImageOps
from barcode import Code39
from barcode.writer import ImageWriter
from PyRIGS.pdf import render_rml

from PyRIGS.views import (
    GenericListView,
    GenericDetailView,
    GenericUpdateView,
    GenericCreateView,
    ModalURLMixin,
    is_ajax,
    OEmbedView,
)
from assets import forms, models, pat
from assets.sss import SSSParseError


def latest_pat(field):
    latest = models.PATTestRecord.objects.filter(asset=OuterRef("pk")).order_by("-tested_at")
    return Subquery(latest.values(field)[:1])


class AssetList(LoginRequiredMixin, generic.ListView):
    model = models.Asset
    template_name = "asset_list.html"
    paginate_by = 40
    hide_hidden_status = True
    advanced_filters = {
        "audit_status",
        "supplier",
        "collection",
        "acquired_from",
        "acquired_to",
        "is_cable",
        "cable_type",
    }

    def get_initial(self):
        initial = {"status": models.AssetStatus.objects.filter(should_show=True)}
        return initial

    def get_queryset(self):
        if self.request.method == "GET" and len(self.request.GET) > 0:
            self.form = forms.AssetSearchForm(data=self.request.GET)
        else:
            self.form = forms.AssetSearchForm(data=self.get_initial())
        form = self.form
        if not form.is_valid():
            return self.model.objects.none()
        data = form.cleaned_data

        # TODO Feedback to user when search fails
        query_string = data["q"] or ""
        queryset = models.Asset.objects.search(query=query_string).annotate(
            pat_last_tested=latest_pat("tested_at"),
            pat_last_passed=latest_pat("passed"),
            pat_next_due=latest_pat("next_full_test_date"),
        )

        if data["is_cable"]:
            queryset = queryset.filter(is_cable=True)

        if data["acquired_from"]:
            queryset = queryset.filter(date_acquired__gte=data["acquired_from"])
        if data["acquired_to"]:
            queryset = queryset.filter(date_acquired__lte=data["acquired_to"])

        audit_status = data["audit_status"]
        if audit_status == "audited":
            queryset = queryset.filter(last_audited_at__isnull=False)
        elif audit_status == "never":
            queryset = queryset.filter(last_audited_at__isnull=True)
        elif audit_status == "stale":
            queryset = queryset.filter(last_audited_at__lt=timezone.now() - datetime.timedelta(days=365))

        queryset = self.filter_pat(queryset, data["pat_status"])

        collection = data["collection"]
        if collection == "top":
            queryset = queryset.filter(parent__isnull=True)
        elif collection == "child":
            queryset = queryset.filter(parent__isnull=False)
        elif collection == "parent":
            queryset = queryset.filter(Exists(models.Asset.objects.filter(parent=OuterRef("pk"))))

        if data["category"]:
            queryset = queryset.filter(category__in=data["category"])

        if data["supplier"]:
            queryset = queryset.filter(purchased_from__in=data["supplier"])

        if len(data["status"]) > 0:
            queryset = queryset.filter(status__in=data["status"])
        elif self.hide_hidden_status:
            queryset = queryset.filter(status__in=models.AssetStatus.objects.filter(should_show=True))

        queryset = self.order(queryset, data["order"])
        return queryset.select_related("category", "status", "cable_type__plug", "cable_type__socket")

    @staticmethod
    def filter_pat(queryset, pat_status):
        today = timezone.localdate()
        failed = Q(pat_last_passed=False)
        tested = Q(pat_last_tested__isnull=False)
        if pat_status == "needs":
            # Only things that have been tested before: never-tested assets may not need a PAT at all
            return queryset.filter(tested, pat_next_due__lt=today).exclude(failed)
        if pat_status == "failed":
            return queryset.filter(failed)
        if pat_status == "in_date":
            return queryset.filter(tested).exclude(failed).exclude(pat_next_due__lt=today)
        if pat_status == "never":
            return queryset.filter(pat_last_tested__isnull=True)
        return queryset

    @staticmethod
    def order(queryset, order):
        orderings = {
            "description": ["description"],
            "-date_acquired": ["-date_acquired"],
            "date_acquired": ["date_acquired"],
            "audit": [F("last_audited_at").asc(nulls_first=True)],
            "pat_due": [F("pat_next_due").asc(nulls_last=True)],
        }
        if order not in orderings:
            return queryset
        return queryset.order_by(*orderings[order], "asset_id_prefix", "asset_id_number")

    def remove_filter_url(self, key, value=None):
        params = self.request.GET.copy()
        params.pop("page", None)
        if value is None:
            params.pop(key, None)
        else:
            remaining = [v for v in params.getlist(key) if v != str(value)]
            if remaining:
                params.setlist(key, remaining)
            else:
                params.pop(key, None)
        query = params.urlencode()
        return f"{self.request.path}?{query}" if query else self.request.path

    def get_active_filters(self):
        if not self.request.GET or not self.form.is_valid():
            return []
        data = self.form.cleaned_data
        chips = []

        def add(key, label, value=None):
            chips.append(
                {
                    "key": key,
                    "label": label,
                    "url": self.remove_filter_url(key, value),
                    "advanced": key in self.advanced_filters,
                }
            )

        if data["q"]:
            add("q", f"Search: {data['q']}")
        for key, title in [
            ("category", "Category"),
            ("status", "Status"),
            ("supplier", "Supplier"),
            ("cable_type", "Cable type"),
        ]:
            for obj in data[key]:
                add(key, f"{title}: {obj}", obj.pk)
        if data["is_cable"]:
            add("is_cable", "Only cables")
        if data["acquired_from"]:
            add("acquired_from", f"Acquired from {data['acquired_from']:%d/%m/%Y}")
        if data["acquired_to"]:
            add("acquired_to", f"Acquired until {data['acquired_to']:%d/%m/%Y}")
        for key in ("audit_status", "pat_status", "collection"):
            if data[key]:
                add(key, dict(self.form.fields[key].choices)[data[key]])
        return chips

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = self.form
        context["active_filters"] = self.get_active_filters()
        context["advanced_count"] = sum(chip["advanced"] for chip in context["active_filters"])
        context["advanced_open"] = context["advanced_count"] > 0
        context["show_pat"] = True
        context["categories"] = models.AssetCategory.objects.all()
        context["statuses"] = models.AssetStatus.objects.all()
        context["page_title"] = "Asset List"
        return context


class CableList(AssetList):
    template_name = "cable_list.html"
    paginator = None

    def get_queryset(self):
        queryset = super().get_queryset().filter(is_cable=True)

        if self.form.cleaned_data["cable_type"]:
            queryset = queryset.filter(cable_type__in=self.form.cleaned_data["cable_type"])

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Cable List"
        context["total_length"] = self.get_queryset().aggregate(Sum("length"))["length__sum"]
        return context


class AssetIDUrlMixin:
    def get_object(self, queryset=None):
        pk = self.kwargs.get(self.pk_url_kwarg)
        return get_object_or_404(models.Asset, asset_id=pk)


class AssetDetail(LoginRequiredMixin, AssetIDUrlMixin, generic.DetailView):
    model = models.Asset
    template_name = "asset_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = f"Asset {self.object.display_id}"
        pat_tests = list(self.object.pat_tests.all()[:5])
        context["pat_tests"] = pat_tests
        context["pat_status"] = models.PATTestRecord.status_for(pat_tests[0] if pat_tests else None)
        context["pat_status_label"] = models.PATTestRecord.STATUS_LABELS[context["pat_status"]]
        return context


class AssetEdit(LoginRequiredMixin, AssetIDUrlMixin, generic.UpdateView):
    template_name = "asset_form.html"
    model = models.Asset
    form_class = forms.AssetForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["edit"] = True
        context["connectors"] = models.Connector.objects.all()
        context["page_title"] = f"Edit Asset: {self.object.display_id}"
        return context

    def get_success_url(self):
        if is_ajax(self.request):
            url = reverse_lazy("closemodal")
            update_url = str(reverse_lazy("asset_update", kwargs={"pk": self.object.pk}))
            messages.info(self.request, "modalobject=" + serializers.serialize("json", [self.object]))
            messages.info(self.request, "modalobject[0]['update_url']='" + update_url + "'")
        else:
            url = reverse_lazy(
                "asset_detail",
                kwargs={
                    "pk": self.object.asset_id,
                },
            )
        return url


class AssetCreate(LoginRequiredMixin, generic.CreateView):
    template_name = "asset_form.html"
    model = models.Asset
    form_class = forms.AssetForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["create"] = True
        context["connectors"] = models.Connector.objects.all()
        context["page_title"] = "Create Asset"
        return context

    def get_initial(self, *args, **kwargs):
        initial = super().get_initial(*args, **kwargs)
        initial["asset_id"] = models.get_available_asset_id()
        return initial

    def get_success_url(self):
        return reverse("asset_detail", kwargs={"pk": self.object.asset_id})


class AssetRemoveParent(LoginRequiredMixin, AssetIDUrlMixin, generic.View):
    http_method_names = ["post"]
    pk_url_kwarg = "pk"

    def post(self, request, *args, **kwargs):
        asset = self.get_object()
        parent = asset.parent
        asset.parent = None
        asset.save()
        messages.success(
            request, f"Removed {asset.asset_id} from {parent.asset_id}" if parent else "No parent to remove"
        )
        return redirect(parent.get_absolute_url() if parent else asset.get_absolute_url())


class DuplicateMixin:
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.pk = None
        return self.render_to_response(self.get_context_data())


class AssetDuplicate(DuplicateMixin, AssetIDUrlMixin, AssetCreate):
    def get_initial(self, *args, **kwargs):
        initial = super().get_initial(*args, **kwargs)
        initial["asset_id"] = models.get_available_asset_id()
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["create"] = None
        context["duplicate"] = True
        old_id = self.get_object().asset_id
        context["previous_asset_id"] = old_id
        context["page_title"] = f"Duplication of Asset: {old_id}"
        return context


class AssetEmbed(AssetDetail):
    template_name = "asset_embed.html"


class AssetOEmbed(OEmbedView):
    model = models.Asset
    url_name = "asset_embed"


class AssetAuditList(AssetList):
    template_name = "asset_audit_list.html"
    hide_hidden_status = True

    # TODO Refresh this when the modal is submitted
    def get_queryset(self):
        self.form = forms.AssetSearchForm(data=self.request.GET)
        return self.model.objects.filter(Q(last_audited_at__isnull=True)).select_related("category", "status")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Asset Audit List"
        return context


class AssetAudit(AssetEdit):
    template_name = "asset_audit.html"
    form_class = forms.AssetAuditForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = f"Audit Asset: {self.object.display_id}"
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
    ordering = ["name"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["create"] = "supplier_create"
        context["edit"] = "supplier_update"
        context["can_edit"] = self.request.user.has_perm("assets.change_supplier")
        context["detail"] = "supplier_detail"
        if is_ajax(self.request):
            context["override"] = "base_ajax.html"
        else:
            context["override"] = "base_assets.html"
        return context


class SupplierDetail(GenericDetailView):
    model = models.Supplier

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["history_link"] = "supplier_history"
        context["update_link"] = "supplier_update"
        context["detail_link"] = "supplier_detail"
        context["associated"] = "partials/associated_assets.html"
        context["associated2"] = ""
        show_all = self.request.GET.get("all") == "1"
        assets = self.object.assets.select_related("category", "status")
        if not show_all:
            assets = assets.filter(status__should_show=True)
        paginator = Paginator(assets, 20)
        page_obj = paginator.get_page(self.request.GET.get("page"))
        context["show_all"] = show_all
        context["paginator"] = paginator
        context["page_obj"] = page_obj
        context["is_paginated"] = page_obj.has_other_pages()
        context["object_list"] = page_obj.object_list
        if is_ajax(self.request):
            context["override"] = "base_ajax.html"
        else:
            context["override"] = "base_assets.html"
        context["can_edit"] = self.request.user.has_perm("assets.change_supplier")
        return context


class SupplierCreate(GenericCreateView, ModalURLMixin):
    model = models.Supplier
    form_class = forms.SupplierForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if is_ajax(self.request):
            context["override"] = "base_ajax.html"
        else:
            context["override"] = "base_assets.html"
        return context

    def get_success_url(self):
        return self.get_close_url("supplier_update", "supplier_detail")


class SupplierUpdate(GenericUpdateView, ModalURLMixin):
    model = models.Supplier
    form_class = forms.SupplierForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if is_ajax(self.request):
            context["override"] = "base_ajax.html"
        else:
            context["override"] = "base_assets.html"
        return context

    def get_success_url(self):
        return self.get_close_url("supplier_update", "supplier_detail")


class CableTypeList(generic.ListView):
    model = models.CableType
    template_name = "cable_type_list.html"
    paginate_by = 40

    def get_queryset(self):
        return self.model.objects.select_related("plug", "socket")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Cable Type List"
        return context


class CableTypeDetail(generic.DetailView):
    model = models.CableType
    template_name = "cable_type_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = f"Cable Type {self.object}"
        return context


class CableTypeCreate(generic.CreateView):
    model = models.CableType
    template_name = "cable_type_form.html"
    form_class = forms.CableTypeForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
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
        context = super().get_context_data(**kwargs)
        context["edit"] = True
        context["page_title"] = f"Edit Cable Type {self.object}"
        return context

    def get_success_url(self):
        return reverse("cable_type_detail", kwargs={"pk": self.object.pk})


def generate_label(pk):
    black = (0, 0, 0)
    white = (255, 255, 255)
    size = (700, 200)
    font_size = 22
    font = ImageFont.truetype("static/fonts/OpenSans-Regular.tff", font_size)
    heavy_font = ImageFont.truetype("static/fonts/OpenSans-Bold.tff", font_size + 13)
    obj = get_object_or_404(models.Asset, asset_id=pk)

    asset_id = f"Asset: {obj.asset_id}"
    if obj.is_cable:
        length = f"Length: {obj.length}m"
        csa = f"CSA: {obj.csa}mm²"

    image = Image.new("RGB", size, white)
    image = ImageOps.expand(image, border=(5, 5, 5, 5), fill=black)
    logo = Image.open("static/imgs/square_logo.png")
    draw = ImageDraw.Draw(image)

    draw.text((300, 0), asset_id, fill=black, font=heavy_font)
    if obj.is_cable:
        y = 140
        draw.text((210, y), length, fill=black, font=font)
        if obj.csa:
            draw.text((365, y), csa, fill=black, font=font)
    draw.text((210, size[1] - font_size - 8), "TEC PA & Lighting (0115) 84 68720", fill=black, font=font)

    barcode = Code39(str(obj.asset_id), writer=ImageWriter())

    logo_size = (200, 200)
    image.paste(logo.resize(logo_size, Image.LANCZOS), box=(5, 5))
    barcode_image = barcode.render(writer_options={"quiet_zone": 0, "write_text": False})
    width, height = barcode_image.size
    image.paste(barcode_image.crop((0, 0, width, 100)), (int(((size[0] + logo_size[0]) - width) / 2), 40))

    return image


class GenerateLabel(generic.View):  # TODO Caching
    def get(self, request, pk):
        response = HttpResponse(content_type="image/png")
        generate_label(pk).save(response, "PNG")
        return response


class GenerateLabels(generic.View):
    def get(self, request, ids):
        response = HttpResponse(content_type="application/pdf")
        template = get_template("labels_print.xml")

        images = []

        for asset_id in ids:
            image = generate_label(asset_id)
            in_mem_file = BytesIO()
            image.save(in_mem_file, format="PNG")
            # reset file pointer to start
            in_mem_file.seek(0)
            img_bytes = in_mem_file.read()

            base64_encoded_result_bytes = base64.b64encode(img_bytes)
            base64_encoded_result_str = base64_encoded_result_bytes.decode("ascii")
            images.append((get_object_or_404(models.Asset, asset_id=asset_id), base64_encoded_result_str))

        name = f"Asset Label Sheet generated at {timezone.now()}"

        context = {
            "images0": images[::3],
            "images1": images[1::3],
            "images2": images[2::3],
            # 'images3': images[3::4],
            "filename": name,
        }
        merger = PdfWriter()

        rml = template.render(context)
        buffer = render_rml(rml)
        merger.append(PdfReader(buffer))
        buffer.close()

        merged = BytesIO()
        merger.write(merged)

        response["Content-Disposition"] = f'filename="{name}"'
        response.write(merged.getvalue())
        return response


class PATUpload(generic.FormView):
    template_name = "pat_upload.html"
    form_class = forms.PATUploadForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Upload PAT Results"
        return context

    def form_valid(self, form):
        summary = pat.import_sss(
            form.parsed, form.content, form.cleaned_data["file"].name, form.sha256, self.request.user
        )
        report_pat_import(self.request, summary)
        if summary.batch is None:
            messages.warning(self.request, "Nothing was imported and the file wasn't stored")
            return redirect("pat_upload")
        return redirect("pat_batch_detail", pk=summary.batch.pk)


def report_pat_import(request, summary):
    if summary.imported:
        messages.success(request, f"Imported {len(summary.imported)} PAT results")
    if summary.replaced:
        messages.success(request, f"Replaced {len(summary.replaced)} existing results with the version in this file")
    if summary.duplicates:
        messages.info(request, f"Skipped {len(summary.duplicates)} results that were already recorded")
    if summary.conflicts:
        messages.warning(
            request,
            f"{len(summary.conflicts)} results have the same asset and time as ones already recorded but a "
            "different outcome. They weren't imported; review them below.",
        )
    if summary.unmatched:
        advice = (
            "create them, then use Re-match on this page" if summary.batch else "create them and upload the file again"
        )
        messages.warning(
            request,
            f"{len(set(summary.unmatched))} asset IDs in the file don't exist in RIGS and were skipped; {advice}",
        )


class PATBatchReprocess(generic.View):
    def post(self, request, pk):
        batch = get_object_or_404(models.PATTestBatch, pk=pk)
        accept = request.POST.get("accept") or None
        if accept and accept not in {conflict["key"] for conflict in batch.conflicts}:
            messages.error(request, "That conflict no longer exists")
            return redirect("pat_batch_detail", pk=batch.pk)
        try:
            summary = pat.reprocess(batch, request.user, accept)
        except SSSParseError:
            messages.error(request, "The stored file could no longer be read")
            return redirect("pat_batch_detail", pk=batch.pk)
        report_pat_import(request, summary)
        if not (summary.imported or summary.replaced):
            messages.info(request, "Nothing new to import")
        return redirect("pat_batch_detail", pk=batch.pk)


class PATBatchList(generic.ListView):
    model = models.PATTestBatch
    template_name = "pat_batch_list.html"
    paginate_by = 40

    def get_queryset(self):
        return super().get_queryset().select_related("uploaded_by")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "PAT Uploads"
        return context


class PATBatchDetail(generic.DetailView):
    model = models.PATTestBatch
    template_name = "pat_batch_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = f"PAT Upload {self.object.original_filename}"
        context["records"] = self.object.records.select_related("asset")
        return context


class PATBatchDownload(generic.View):
    def get(self, request, pk):
        batch = get_object_or_404(models.PATTestBatch, pk=pk)
        return FileResponse(batch.file.open("rb"), as_attachment=True, filename=batch.original_filename)


class PATBatchDelete(generic.FormView):
    template_name = "pat_batch_confirm_delete.html"
    form_class = forms.PATBatchDeleteForm

    def dispatch(self, request, *args, **kwargs):
        self.batch = get_object_or_404(models.PATTestBatch, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        records = self.batch.records.all()
        affected = models.Asset.objects.filter(pat_tests__batch=self.batch).distinct()
        # assets with results from other uploads go back to their latest remaining result; these would have none
        untested = affected.exclude(pat_tests__in=models.PATTestRecord.objects.exclude(batch=self.batch))
        context.update(
            {
                "page_title": f"Delete PAT upload {self.batch.original_filename}",
                "batch": self.batch,
                "record_count": records.count(),
                "asset_count": affected.count(),
                "untested_assets": list(untested.order_by("asset_id_prefix", "asset_id_number")[:30]),
                "untested_count": untested.count(),
            }
        )
        context["more_count"] = context["untested_count"] - len(context["untested_assets"])
        return context

    def form_valid(self, form):
        name = self.batch.original_filename
        count = pat.delete_batch(self.batch, self.request.user, form.cleaned_data["reason"])
        messages.success(self.request, f"Deleted {name} and its {count} results")
        return redirect("pat_batch_list")
