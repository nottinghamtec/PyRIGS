from django.urls import path, include
from rest_framework import routers
from assets import views, api

router = routers.DefaultRouter()
router.register(r'api/assets', api.AssetViewSet)

urlpatterns = [
    # path('', views.Index.as_view(), name='index'),
    path('', views.AssetList.as_view(), name='index'),
    path('asset/list/', views.AssetList.as_view(), name='asset_list'),
    path('asset/<int:pk>/', views.AssetDetail.as_view(), name='asset_detail'),
    path('asset/create/', views.AssetEdit.as_view(), name='asset_create'),
    path('asset/<int:pk>/edit/', views.AssetEdit.as_view(), name='asset_update'),
    path('asset/delete/', views.asset_delete, name='ajax_asset_delete'),
    path('asset/filter/', views.asset_filter, name='ajax_asset_filter'),
    path('asset/update/', views.asset_update, name='ajax_asset_update'),

    path('supplier/list', views.SupplierList.as_view(), name='supplier_list'),
    path('supplier/<int:pk>', views.SupplierDetail.as_view(), name='supplier_detail'),
    path('supplier/create', views.SupplierCreate.as_view(), name='supplier_create'),
    path('supplier/<int:pk>/edit', views.SupplierUpdate.as_view(), name='supplier_update'),

    path('', include(router.urls)),
]

