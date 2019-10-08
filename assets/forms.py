from django import forms
from django.core.exceptions import ValidationError
import re

from assets import models


class AssetForm(forms.ModelForm):
    
    
    class Meta:
        model = models.Asset
        fields = '__all__'
        widgets = {
            'is_cable' : forms.CheckboxInput()
        }

    def clean_date_sold(self):
        if self.cleaned_data["date_sold"] and self.cleaned_data["date_acquired"] > self.cleaned_data["date_sold"]:
            raise ValidationError("Cannot sell an item before it is acquired")
        return self.cleaned_data["date_sold"]
    
    def clean_asset_id(self):
        # If the asset ID has been changed
        if self.instance.asset_id and self.instance.asset_id == self.cleaned_data["asset_id"]: #If the item was not changed
            return self.cleaned_data["asset_id"]
        else:
            if re.search("^[a-zA-Z0-9]+$", self.cleaned_data["asset_id"]) == None:
                raise ValidationError("An Asset ID can only consist of letters and numbers")
            return self.cleaned_data["asset_id"]

    def clean_purchase_price(self):
        purchase_price = self.cleaned_data["purchase_price"]
        if purchase_price and purchase_price < 0:
            raise ValidationError("A price cannot be negative")
        return purchase_price

    def clean_salvage_value(self):
        salvage_value = self.cleaned_data["salvage_value"]
        if salvage_value and salvage_value < 0:
            raise ValidationError("A price cannot be negative")
        return salvage_value


class CableForm(AssetForm):
    class Meta(AssetForm.Meta):
        model = models.Cable

    def clean_length(self):
        length = self.cleaned_data["length"]
        if length <= 0:
            raise ValidationError("The length of a cable must be more than 0")
        return length

    def clean_csa(self):
        csa = self.cleaned_data["csa"]
        if csa <= 0:
            raise ValidationError("The CSA of a cable must be more than 0")
        return csa

    def clean_circuits(self):
        circuits = self.cleaned_data["circuits"]
        if circuits <= 0:
            raise ValidationError("There must be at least one circuit")
        return circuits
    
    def clean_cores(self):
        cores = self.cleaned_data["cores"]
        if cores <= 0:
            raise ValidationError("There must be at least one core")
        return cores

class SupplierForm(forms.Form):
    class Meta:
        model = models.Supplier
        fields = '__all__'
