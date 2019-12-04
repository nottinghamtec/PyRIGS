from django import forms

from assets import models


class AssetForm(forms.ModelForm):
    class Meta:
        model = models.Asset
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date_sold'].widget.format = '%Y-%m-%d'
        self.fields['date_acquired'].widget.format = '%Y-%m-%d'


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
