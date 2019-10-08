from django import forms
from django.core.exceptions import ValidationError

from assets import models


class AssetForm(forms.ModelForm):
    

    def clean_date_sold(self):
        if self.cleaned_data["date_sold"] and self.cleaned_data["date_acquired"] > self.cleaned_data["date_sold"]:
            raise ValidationError("Cannot sell an item before it is acquired")
        return self.cleaned_data["date_sold"]
    
    class Meta:
        model = models.Asset
        fields = '__all__'
        widgets = {
            'is_cable' : forms.CheckboxInput()
        }

class CableForm(AssetForm):
    class Meta(AssetForm.Meta):
        model = models.Cable

class SupplierForm(forms.Form):
    class Meta:
        model = models.Supplier
        fields = '__all__'
