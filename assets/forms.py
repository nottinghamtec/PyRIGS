from django import forms

from assets import models


class AssetForm(forms.ModelForm):
    class Meta:
        model = models.Asset
        fields = '__all__'


class SupplierForm(forms.ModelForm):
    class Meta:
        model = models.Supplier
        fields = '__all__'
