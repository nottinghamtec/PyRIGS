from django.shortcuts import render

from django.views import generic
from training import models

from users import views

class ItemList(generic.ListView):
    template_name = "item_list.html"
    model = models.TrainingItem

    def get_context_data(self, **kwargs):
        context = super(ItemList, self).get_context_data(**kwargs)
        context["page_title"] = "Training Items"
        context["categories"] = models.TrainingCategory.objects.all()    
        return context


class TraineeDetail(views.ProfileDetail):
    template_name = "trainee_detail.html"
    model = models.Trainee

    def get_context_data(self, **kwargs):
        context = super(TraineeDetail, self).get_context_data(**kwargs)
        context["page_title"] = "{}'s Training Record".format(self.object)
        context["categories"] = models.TrainingCategory.objects.all() 
        choices = models.TrainingItemQualification.CHOICES
        context["depths"] = choices
        for i in [x for x,_ in choices]:
            context[str(i)] = self.object.get_records_of_depth(i)
        return context
        
