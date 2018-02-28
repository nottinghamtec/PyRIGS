from django.contrib import admin
from assets import models as assets

@admin.register(assets.AssetCategory)
class AssetCategoryAdmin(admin.ModelAdmin):
    pass


@admin.register(assets.AssetStatus)
class AssetStatusAdmin(admin.ModelAdmin):
    pass


@admin.register(assets.Supplier)
class SupplierAdmin(admin.ModelAdmin):
    pass


@admin.register(assets.Collection)
class CollectionAdmin(admin.ModelAdmin):
    pass


@admin.register(assets.Asset)
class AssetAdmin(admin.ModelAdmin):
    pass
