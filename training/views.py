from django.shortcuts import render
from django.views import generic
from training import models

# Create your views here.


class TrainingRecordDetailView(generic.DetailView):
    model = models.TrainingRecord
