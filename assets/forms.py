from django import forms
from django.core.exceptions import ValidationError

from assets import models


class AssetForm(forms.ModelForm):
    class Meta:
        model = models.Asset
        fields = '__all__'
    
    def __init__(self, *args, **kwargs): 
        super(AssetForm, self).__init__(*args, **kwargs)                       
        self.fields['asset_id'].disabled = True #You should not be able to change the asset ID, either in update or create

    def clean_date_sold(self):
        if self.cleaned_data["date_sold"] and self.cleaned_data["date_acquired"] > self.cleaned_data["date_sold"]:
            raise ValidationError("Cannot sell an item before it is acquired")
        return self.cleaned_data["date_sold"]

class SupplierForm(forms.ModelForm):
    class Meta:
        model = models.Supplier
        fields = '__all__'
