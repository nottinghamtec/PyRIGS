from django.urls import path
from assets import views

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
]
