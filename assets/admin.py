from django.contrib import admin
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
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    ordering = ['id']


@admin.register(assets.Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ['id', 'asset_id', 'description', 'category', 'status']
    list_filter = ['is_cable', 'category']
    search_fields = ['id', 'asset_id', 'description']


@admin.register(assets.Connector)
class ConnectorAdmin(admin.ModelAdmin):
    list_display = ['id', '__str__', 'current_rating', 'voltage_rating', 'num_pins']


admin.AdminSite.site_header = 'PyAssets - TEC\'s Asset System'
admin.AdminSite.site_title = 'PyAssets Admin'
admin.AdminSite.index_title = 'System Administration'
