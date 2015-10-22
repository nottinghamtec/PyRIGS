from django.contrib import admin
from training import models

# Register your models here.
admin.site.register(models.TrainingCategory)
admin.site.register(models.TrainingItem)
admin.site.register(models.TrainingRecord)
admin.site.register(models.TrainingLevelRecord)
