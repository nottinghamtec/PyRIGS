from django.contrib.auth.decorators import login_required
from django.urls import path, register_converter
from django.views.decorators.clickjacking import xframe_options_exempt

from PyRIGS.decorators import has_oembed, permission_required_with_403
from PyRIGS.views import OEmbedView
from . import views, converters

register_converter(converters.AssetIDConverter, 'asset')
register_converter(converters.ListConverter, 'list')

urlpatterns = [
    path('', login_required(views.AssetList.as_view()), name='asset_index'),
    path('asset/list/', login_required(views.AssetList.as_view()), name='asset_list'),
    path('asset/id/<asset:pk>/', has_oembed(oembed_view="asset_oembed")(views.AssetDetail.as_view()), name='asset_detail'),
    path('asset/create/', permission_required_with_403('assets.add_asset')
         (views.AssetCreate.as_view()), name='asset_create'),
    path('asset/id/<asset:pk>/edit/', permission_required_with_403('assets.change_asset')
         (views.AssetEdit.as_view()), name='asset_update'),
    path('asset/id/<asset:pk>/duplicate/', permission_required_with_403('assets.add_asset')
         (views.AssetDuplicate.as_view()), name='asset_duplicate'),
    path('asset/id/<asset:pk>/label', login_required(views.GenerateLabel.as_view()), name='generate_label'),
    path('asset/<list:ids>/list/label', views.GenerateLabels.as_view(), name='generate_labels'),

    path('cables/list/', login_required(views.CableList.as_view()), name='cable_list'),
    path('cabletype/list/', login_required(views.CableTypeList.as_view()), name='cable_type_list'),
    path('cabletype/create/', permission_required_with_403('assets.add_cable_type')(views.CableTypeCreate.as_view()), name='cable_type_create'),
    path('cabletype/<int:pk>/update/', permission_required_with_403('assets.change_cable_type')(views.CableTypeUpdate.as_view()), name='cable_type_update'),
    path('cabletype/<int:pk>/detail/', login_required(views.CableTypeDetail.as_view()), name='cable_type_detail'),

    path('asset/id/<str:pk>/embed/',
         xframe_options_exempt(
             login_required(login_url='/user/login/embed/')(views.AssetEmbed.as_view())),
         name='asset_embed'),
    path('asset/id/<str:pk>/oembed_json/', views.AssetOEmbed.as_view(), name='asset_oembed'),

    path('asset/audit/', permission_required_with_403('assets.change_asset')(views.AssetAuditList.as_view()), name='asset_audit_list'),
    path('asset/id/<str:pk>/audit/', permission_required_with_403('assets.change_asset')(views.AssetAudit.as_view()), name='asset_audit'),

    path('supplier/list/', login_required(views.SupplierList.as_view()), name='supplier_list'),
    path('supplier/<int:pk>/', login_required(views.SupplierDetail.as_view()), name='supplier_detail'),
    path('supplier/create/', permission_required_with_403('assets.add_supplier')
         (views.SupplierCreate.as_view()), name='supplier_create'),
    path('supplier/<int:pk>/edit/', permission_required_with_403('assets.change_supplier')
         (views.SupplierUpdate.as_view()), name='supplier_update'),
]
