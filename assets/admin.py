from django.contrib import admin
from reversion.admin import VersionAdmin

from assets import models as assets


@admin.register(assets.AssetCategory)
class AssetCategoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    ordering = ['id']


@admin.register(assets.AssetStatus)
class AssetStatusAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    ordering = ['id']


@admin.register(assets.Supplier)
class SupplierAdmin(VersionAdmin):
    list_display = ['id', 'name']
    ordering = ['id']


@admin.register(assets.Asset)
class AssetAdmin(VersionAdmin):
    list_display = ['id', 'asset_id', 'description', 'category', 'status']
    list_filter = ['is_cable', 'category', 'status']
    search_fields = ['id', 'asset_id', 'description']


@admin.register(assets.CableType)
class CableTypeAdmin(admin.ModelAdmin):
    list_display = ['id', '__str__', 'plug', 'socket', 'cores', 'circuits']


@admin.register(assets.Connector)
class ConnectorAdmin(admin.ModelAdmin):
    list_display = ['id', '__str__', 'current_rating', 'voltage_rating', 'num_pins']
