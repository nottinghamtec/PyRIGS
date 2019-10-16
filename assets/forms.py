from django import forms
from django.core.exceptions import ValidationError

from assets import models


class AssetForm(forms.ModelForm):
    class Meta:
        model = models.Asset
        fields = '__all__'


class AssetSearchForm(forms.Form):
    query = forms.CharField(required=False)
    category = forms.ModelMultipleChoiceField(models.AssetCategory.objects.all(), required=False)
    status = forms.ModelMultipleChoiceField(models.AssetStatus.objects.all(), required=False)

class SupplierForm(forms.Form):
    class Meta:
        model = models.Supplier
        fields = '__all__'
