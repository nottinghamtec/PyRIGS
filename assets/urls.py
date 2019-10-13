from django.urls import path, include
from rest_framework import routers
from assets import views, api

from PyRIGS.decorators import permission_required_with_403

router = routers.DefaultRouter()
router.register(r'api/assets', api.AssetViewSet)

urlpatterns = [
    path('', views.AssetList.as_view(), name='index'),
    path('asset/list/', views.AssetList.as_view(), name='asset_list'),
    path('asset/<int:pk>/', views.AssetDetail.as_view(), name='asset_detail'),
    path('asset/create/', permission_required_with_403('assets.create_asset')(views.AssetCreate.as_view()), name='asset_create'),
    path('asset/<int:pk>/edit/', permission_required_with_403('assets.change_asset')(views.AssetEdit.as_view()), name='asset_update'),
    path('asset/<int:pk>/duplicate/', permission_required_with_403('assets.create_asset')(views.AssetDuplicate.as_view()), name='asset_duplicate'),
    path('asset/delete/', permission_required_with_403('assets.delete_asset')(views.asset_delete), name='ajax_asset_delete'),

    path('asset/search/', views.AssetSearch.as_view(), name='asset_search_json'),

    path('supplier/list', views.SupplierList.as_view(), name='supplier_list'),
    path('supplier/<int:pk>', views.SupplierDetail.as_view(), name='supplier_detail'),
    path('supplier/create', permission_required_with_403('assets.create_supplier')(views.SupplierCreate.as_view()), name='supplier_create'),
    path('supplier/<int:pk>/edit', permission_required_with_403('assets.edit_supplier')(views.SupplierUpdate.as_view()), name='supplier_update'),

    path('', include(router.urls)),
]

