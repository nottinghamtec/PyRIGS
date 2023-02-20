from django.urls import path

from django.contrib.auth.decorators import login_required
from training.decorators import is_supervisor

from training import views, models
from versioning.views import VersionHistory

urlpatterns = [
    path('items/', login_required(views.ItemList.as_view()), name='item_list'),
    path('items/export/', login_required(views.ItemListExport.as_view()), name='item_list_export'),
    path('item/<int:pk>/qualified_users/', login_required(views.ItemQualifications.as_view()), name='item_qualification'),

    path('trainee/list/', login_required(views.TraineeList.as_view()), name='trainee_list'),
    path('trainee/<int:pk>/', login_required(views.TraineeDetail.as_view()),
         name='trainee_detail'),
    path('trainee/<int:pk>/history', login_required(VersionHistory.as_view()), name='trainee_history', kwargs={'model': models.Trainee, 'app': 'training'}),  # Not picked up automatically because proxy model (I think)
    path('trainee/<int:pk>/add_qualification/', is_supervisor()(views.AddQualification.as_view()),
         name='add_qualification'),
    path('trainee/edit_qualification/<int:pk>/', is_supervisor()(views.EditQualification.as_view()),
         name='edit_qualification'),

    path('levels/', login_required(views.LevelList.as_view()), name='level_list'),
    path('level/<int:pk>/', login_required(views.LevelDetail.as_view()), name='level_detail'),
    path('level/<int:pk>/user/<int:u>/', login_required(views.LevelDetail.as_view()), name='level_detail'),
    path('level/<int:pk>/add_requirement/', is_supervisor()(views.AddLevelRequirement.as_view()), name='add_requirement'),
    path('level/remove_requirement/<int:pk>/', is_supervisor()(views.RemoveRequirement.as_view()), name='remove_requirement'),

    path('trainee/<int:pk>/level/<int:level_pk>/confirm', is_supervisor()(views.ConfirmLevel.as_view()), name='confirm_level'),
    path('trainee/<int:pk>/item_record', login_required(views.TraineeItemDetail.as_view()), name='trainee_item_detail'),

    path('session_log', is_supervisor()(views.SessionLog.as_view()), name='session_log'),
]
