from django.urls import path

from django.contrib.auth.decorators import login_required
from training.decorators import has_perm_or_supervisor

from training import views, models
from versioning.views import VersionHistory

urlpatterns = [
    path('items/', login_required(views.ItemList.as_view()), name='item_list'),
    path('trainee/list/', login_required(views.TraineeList.as_view()), name='trainee_list'),
    path('trainee/<int:pk>/',
         has_perm_or_supervisor('RIGS.view_profile')(views.TraineeDetail.as_view()),
         name='trainee_detail'),
    path('trainee/<int:pk>/history', has_perm_or_supervisor('RIGS.view_profile')(VersionHistory.as_view()), name='trainee_history', kwargs={'model': models.Trainee, 'app': 'training'}),  # Not picked up automatically because proxy model (I think)
    path('trainee/<int:pk>/add_qualification/', has_perm_or_supervisor('training.add_trainingitemqualification')(views.AddQualification.as_view()),
         name='add_qualification'),
    path('trainee/edit_qualification/<int:pk>/', has_perm_or_supervisor('training.change_trainingitemqualification')(views.EditQualification.as_view()),
         name='edit_qualification'),

    path('levels/', login_required(views.LevelList.as_view()), name='level_list'),
    path('level/<int:pk>/', login_required(views.LevelDetail.as_view()), name='level_detail'),
    path('level/<int:pk>/user/<int:u>/', login_required(views.LevelDetail.as_view()), name='level_detail'),
    path('level/<int:pk>/add_requirement/', login_required(views.AddLevelRequirement.as_view()), name='add_requirement'),
    path('level/remove_requirement/<int:pk>/', login_required(views.RemoveRequirement.as_view()), name='remove_requirement'),

    path('trainee/<int:pk>/level/<int:level_pk>/confirm', login_required(views.ConfirmLevel.as_view()), name='confirm_level'),
    path('trainee/<int:pk>/item_record', login_required(views.TraineeItemDetail.as_view()), name='trainee_item_detail'),
]
