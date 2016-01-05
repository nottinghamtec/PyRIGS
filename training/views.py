from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.shortcuts import render
from django.views import generic
from training import models


# Create your views here.


class UserTrainingRecordView(generic.DetailView):
    model = get_user_model()
    template_name = 'training/profile_detail.html'

    def get_context_data(self, **kwargs):
        context = super(UserTrainingRecordView, self).get_context_data(**kwargs)
        context['categories'] = models.TrainingCategory.objects.all()
        return context


class SelfUserTrainingRecordView(UserTrainingRecordView):
    template_name = 'training/index.html'

    def get_queryset(self):
        pk = self.request.user.id
        self.kwargs['pk'] = pk

        return self.model.objects.filter(pk=pk)


class TrainingCategoryItemListView(generic.ListView):
    model = models.TrainingCategory
    template_name = 'training/trainingcategory_item_list.html'
