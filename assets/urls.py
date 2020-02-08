from django.conf.urls import url
from django.urls import path
from assets import views, models
from RIGS import versioning

from django.contrib.auth.decorators import login_required
from django.views.decorators.clickjacking import xframe_options_exempt
from PyRIGS.decorators import has_oembed, permission_required_with_403

urlpatterns = [
    path('', views.AssetList.as_view(), name='asset_index'),
    path('asset/list/', views.AssetList.as_view(), name='asset_list'),
    # Lazy way to enable the oembed redirect...
    path('asset/id/<str:pk>/', has_oembed(oembed_view="asset_oembed")(views.AssetDetail.as_view()), name='asset_detail'),
    path('asset/create/', permission_required_with_403('assets.add_asset')
         (views.AssetCreate.as_view()), name='asset_create'),
    path('asset/id/<str:pk>/edit/', permission_required_with_403('assets.change_asset')
         (views.AssetEdit.as_view()), name='asset_update'),
    path('asset/id/<str:pk>/duplicate/', permission_required_with_403('assets.add_asset')
         (views.AssetDuplicate.as_view()), name='asset_duplicate'),
    path('asset/id/<str:pk>/history/', permission_required_with_403('assets.view_asset')(views.AssetVersionHistory.as_view()),
         name='asset_history', kwargs={'model': models.Asset}),
    path('activity', permission_required_with_403('assets.view_asset')
         (views.ActivityTable.as_view()), name='asset_activity_table'),

    path('asset/search/', views.AssetSearch.as_view(), name='asset_search_json'),
    path('asset/id/<str:pk>/embed/',
         xframe_options_exempt(
                               login_required(login_url='/user/login/embed/')(views.AssetEmbed.as_view())),
         name='asset_embed'),
    path('asset/id/<str:pk>/oembed_json/',
         views.AssetOembed.as_view(),
         name='asset_oembed'),

    path('supplier/list', views.SupplierList.as_view(), name='supplier_list'),
    path('supplier/<int:pk>', views.SupplierDetail.as_view(), name='supplier_detail'),
    path('supplier/create', permission_required_with_403('assets.add_supplier')
         (views.SupplierCreate.as_view()), name='supplier_create'),
    path('supplier/<int:pk>/edit', permission_required_with_403('assets.change_supplier')
         (views.SupplierUpdate.as_view()), name='supplier_update'),
    path('supplier/<str:pk>/history/', views.SupplierVersionHistory.as_view(),
         name='supplier_history', kwargs={'model': models.Supplier}),

    path('supplier/search/', views.SupplierSearch.as_view(), name='supplier_search_json'),
]
