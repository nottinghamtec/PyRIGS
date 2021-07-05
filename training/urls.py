from django.urls import path

from django.contrib.auth.decorators import login_required
from PyRIGS.decorators import permission_required_with_403

from training import views

urlpatterns = [
    path('items/', views.ItemList.as_view(), name='item_list'),

    path('trainee/', login_required(views.TraineeDetail.as_view()), name='trainee_detail'),
    path('trainee/<int:pk>/',
         permission_required_with_403('RIGS.view_profile')(views.TraineeDetail.as_view()),
         name='trainee_detail'),
    path('session/', views.SessionLog.as_view(), name='session_log'),
]
