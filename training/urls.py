from django.urls import path

from django.contrib.auth.decorators import login_required
from PyRIGS.decorators import permission_required_with_403

from training import views

urlpatterns = [
    path('items/', views.ItemList.as_view(), name='item_list'),

    path('trainee/list/', views.TraineeList.as_view(), name='trainee_list'),
    path('trainee/', login_required(views.TraineeDetail.as_view()), name='trainee_detail'),
    path('trainee/<int:pk>/',
         permission_required_with_403('RIGS.view_profile')(views.TraineeDetail.as_view()),
         name='trainee_detail'),
    path('trainee/<int:pk>/edit/', views.AddQualification.as_view(),
         name='edit_record'),
    path('session/', views.SessionLog.as_view(), name='session_log'),
    path('level/<int:pk>/', views.LevelDetail.as_view(), name='level_detail'),
    path('level/<int:pk>/add_requirement/', views.AddLevelRequirement.as_view(), name='add_requirement'),
    path('level/remove_requirement/<int:pk>/', views.RemoveRequirement.as_view(), name='remove_requirement'),
    path('trainee/<int:pk>/level/<int:level_pk>/confirm', views.ConfirmLevel.as_view(), name='confirm_level'),
]
