from django.urls import path
from assets import views

urlpatterns = [
    path('', views.Index.as_view(), name='index'),
    path('assets/', views.AssetList.as_view(), name='asset_list'),
    path('assets/<int:pk>/', views.AssetDetail.as_view(), name='asset_detail'),
    path('assets/create', views.AssetCreate.as_view(), name='asset_create'),
    path('assets/<int:pk>/update', views.AssetUpdate.as_view(), name='asset_update'),
    path('assets/<int:pk>/delete', views.AssetDelete.as_view(), name='asset_delete'),
]
