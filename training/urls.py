from django.urls import path

from training import views

urlpatterns = [
    path('items/', views.ItemList.as_view(), name='item_list'),
]
