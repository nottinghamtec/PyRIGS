from django.shortcuts import render

from django.views import generic
from training import models

class ItemList(generic.ListView):
    template_name = "item_list.html"
    model = models.TrainingItem

    def get_context_data(self, **kwargs):
        context = super(ItemList, self).get_context_data(**kwargs)
        context["categories"] = models.TrainingCategory.objects.all()
        return context
