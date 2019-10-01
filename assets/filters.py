import django_filters

from assets import models


class AssetFilter(django_filters.FilterSet):
    class Meta:
        model = models.Asset
        fields = ['asset_id', 'description', 'category', 'status']
