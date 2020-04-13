from django import forms

from assets import models
from django.db.models import Q


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


# Needed to prevent assets losing parent data on audit
class AssetAuditForm(AssetForm):
    class Meta(AssetForm.Meta):
        # TODO Inherit exlcusions from superclass
        exclude = ['asset_id_prefix', 'asset_id_number', 'last_audited_at', 'last_audited_by', 'parent']


class AssetSearchForm(forms.Form):
    query = forms.CharField(required=False)
    category = forms.ModelMultipleChoiceField(models.AssetCategory.objects.all(), required=False)
    status = forms.ModelMultipleChoiceField(models.AssetStatus.objects.all(), required=False)


class SupplierForm(forms.ModelForm):
    class Meta:
        model = models.Supplier
        fields = '__all__'


class SupplierSearchForm(forms.Form):
    query = forms.CharField(required=False)


class CableTypeForm(forms.ModelForm):
    class Meta:
        model = models.CableType
        fields = '__all__'

    def clean(self):
        form_data = self.cleaned_data
        queryset = models.CableType.objects.filter(Q(plug=form_data['plug']) & Q(socket=form_data['socket']) & Q(circuits=form_data['circuits']) & Q(cores=form_data['cores']))
        # Being identical to itself shouldn't count...
        if queryset.exists() and self.instance.pk != queryset[0].pk:
            raise forms.ValidationError("A cable type that exactly matches this one already exists, please use that instead.", code="notunique")
        return form_data
