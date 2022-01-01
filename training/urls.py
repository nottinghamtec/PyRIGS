from django.urls import path

from django.contrib.auth.decorators import login_required
from PyRIGS.decorators import permission_required_with_403

from training import views, models
from versioning.views import VersionHistory

urlpatterns = [
    path('items/', login_required(views.ItemList.as_view()), name='item_list'),
    path('trainee/list/', login_required(views.TraineeList.as_view()), name='trainee_list'),
    path('trainee/<int:pk>/',
         permission_required_with_403('RIGS.view_profile')(views.TraineeDetail.as_view()),
         name='trainee_detail'),
    path('trainee/<int:pk>/history', permission_required_with_403('RIGS.view_profile')(VersionHistory.as_view()), name='trainee_history', kwargs={'model': models.Trainee, 'app': 'training'}), # Not picked up automatically because proxy model (I think)
    path('trainee/<int:pk>/add_qualification/', login_required(views.AddQualification.as_view()),
         name='add_qualification'),
    path('session/', login_required(views.SessionLog.as_view()), name='session_log'),
    path('levels/', login_required(views.LevelList.as_view()), name='level_list'),
    path('level/<int:pk>/', login_required(views.LevelDetail.as_view()), name='level_detail'),
    path('level/<int:pk>/add_requirement/', login_required(views.AddLevelRequirement.as_view()), name='add_requirement'),
    path('level/remove_requirement/<int:pk>/', login_required(views.RemoveRequirement.as_view()), name='remove_requirement'),
    path('trainee/<int:pk>/level/<int:level_pk>/confirm', login_required(views.ConfirmLevel.as_view()), name='confirm_level'),
    path('trainee/<int:pk>/item_record', login_required(views.TraineeItemDetail.as_view()), name='trainee_item_detail'),
]
