from django import forms
from django.db.models import Q

from assets import models


class AssetForm(forms.ModelForm):
    related_models = {
        'asset': models.Asset,
        'supplier': models.Supplier
    }

    class Meta:
        model = models.Asset
        fields = '__all__'
        exclude = ['asset_id_prefix', 'asset_id_number', 'last_audited_at', 'last_audited_by']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date_sold'].widget.format = '%Y-%m-%d'
        self.fields['date_acquired'].widget.format = '%Y-%m-%d'


class AssetAuditForm(AssetForm):
    class Meta(AssetForm.Meta):
        # Prevents assets losing existing data that isn't included in the audit form
        exclude = ['asset_id_prefix', 'asset_id_number', 'last_audited_at', 'last_audited_by',
                   'parent', 'purchased_from', 'purchase_price', 'comments']


class AssetSearchForm(forms.Form):
    q = forms.CharField(required=False)
    category = forms.ModelMultipleChoiceField(models.AssetCategory.objects.all(), required=False)
    status = forms.ModelMultipleChoiceField(models.AssetStatus.objects.all(), required=False)
    is_cable = forms.BooleanField(required=False)
    cable_type = forms.ModelMultipleChoiceField(models.CableType.objects.all(), required=False)
    date_acquired = forms.DateField(required=False)


class SupplierForm(forms.ModelForm):
    class Meta:
        model = models.Supplier
        fields = '__all__'


class CableTypeForm(forms.ModelForm):
    class Meta:
        model = models.CableType
        fields = '__all__'
