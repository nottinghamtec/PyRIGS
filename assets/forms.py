import hashlib

from django import forms
from django.conf import settings

from assets import models
from assets.sss import SSSParseError, parse_sss


class AssetForm(forms.ModelForm):
    related_models = {"asset": models.Asset, "supplier": models.Supplier}

    class Meta:
        model = models.Asset
        fields = "__all__"
        exclude = ["asset_id_prefix", "asset_id_number", "last_audited_at", "last_audited_by"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["date_sold"].widget.format = "%Y-%m-%d"
        self.fields["date_acquired"].widget.format = "%Y-%m-%d"


class AssetAuditForm(AssetForm):
    class Meta(AssetForm.Meta):
        # Prevents assets losing existing data that isn't included in the audit form
        exclude = [
            "asset_id_prefix",
            "asset_id_number",
            "last_audited_at",
            "last_audited_by",
            "parent",
            "purchased_from",
            "purchase_price",
            "comments",
        ]


class AssetSearchForm(forms.Form):
    ORDER_CHOICES = [
        ("", "Sort: Asset ID"),
        ("description", "Sort: Description"),
        ("-date_acquired", "Sort: Newest acquired"),
        ("date_acquired", "Sort: Oldest acquired"),
        ("audit", "Sort: Longest since audit"),
        ("pat_due", "Sort: PAT due soonest"),
    ]

    q = forms.CharField(required=False)
    category = forms.ModelMultipleChoiceField(models.AssetCategory.objects.all(), required=False)
    status = forms.ModelMultipleChoiceField(models.AssetStatus.objects.all(), required=False)
    supplier = forms.ModelMultipleChoiceField(models.Supplier.objects.all(), required=False)
    is_cable = forms.BooleanField(required=False)
    cable_type = forms.ModelMultipleChoiceField(models.CableType.objects.all(), required=False)
    acquired_from = forms.DateField(required=False)
    acquired_to = forms.DateField(required=False)
    audit_status = forms.ChoiceField(
        required=False,
        choices=[
            ("", "Any audit status"),
            ("audited", "Audited"),
            ("never", "Never audited"),
            ("stale", "Audited over a year ago"),
        ],
    )
    pat_status = forms.ChoiceField(
        required=False,
        choices=[
            ("", "Any PAT status"),
            ("needs", "Needs PAT (overdue)"),
            ("failed", "Failed last PAT"),
            ("in_date", "PAT in date"),
            ("never", "Never PAT tested"),
        ],
    )
    collection = forms.ChoiceField(
        required=False,
        choices=[
            ("", "Any collection status"),
            ("top", "Not in a collection"),
            ("child", "In a collection"),
            ("parent", "Is a collection"),
        ],
    )
    order = forms.ChoiceField(required=False, choices=ORDER_CHOICES)

    def clean(self):
        cleaned_data = super().clean()
        start, end = cleaned_data.get("acquired_from"), cleaned_data.get("acquired_to")
        if start and end and start > end:
            self.add_error("acquired_to", "The end date can't be before the start date")
        return cleaned_data


class SupplierForm(forms.ModelForm):
    class Meta:
        model = models.Supplier
        fields = "__all__"


class CableTypeForm(forms.ModelForm):
    class Meta:
        model = models.CableType
        fields = "__all__"


class PATUploadForm(forms.Form):
    file = forms.FileField(help_text="A .sss file exported from the Seaward PAT tester software")

    def clean_file(self):
        upload = self.cleaned_data["file"]
        if not upload.name.lower().endswith(".sss"):
            raise forms.ValidationError("Please upload a .sss file")
        if upload.size > settings.PAT_MAX_UPLOAD_BYTES:
            raise forms.ValidationError("That file is too large to be a PAT results file")
        self.content = upload.read()
        self.sha256 = hashlib.sha256(self.content).hexdigest()
        self.existing_batch = models.PATTestBatch.objects.filter(sha256=self.sha256).first()
        if self.existing_batch:
            raise forms.ValidationError("That exact file has already been uploaded")
        try:
            self.parsed = parse_sss(self.content)
        except SSSParseError as e:
            raise forms.ValidationError(f"Couldn't read that file: {e}") from None
        return upload


class PATBatchDeleteForm(forms.Form):
    reason = forms.CharField(
        max_length=500,
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="This is kept in the audit trail, so say why these results are being removed",
    )

    def clean_reason(self):
        return " ".join(self.cleaned_data["reason"].split())


class PATResultSuppressForm(forms.Form):
    reason = forms.CharField(
        max_length=500,
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="This is kept in the asset's history, so say why this result shouldn't count, "
        "such as which asset it really belongs to",
    )

    def clean_reason(self):
        return " ".join(self.cleaned_data["reason"].split())
