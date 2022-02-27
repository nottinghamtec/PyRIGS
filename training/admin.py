from django.contrib import admin
from training import models
from reversion.admin import VersionAdmin


admin.site.register(models.TrainingCategory, VersionAdmin)
admin.site.register(models.TrainingItem, VersionAdmin)
admin.site.register(models.TrainingLevel, VersionAdmin)
admin.site.register(models.TrainingLevelQualification, VersionAdmin)
admin.site.register(models.TrainingLevelRequirement, VersionAdmin)


@admin.register(models.TrainingItemQualification)
class TrainingItemQualificationAdmin(VersionAdmin):
    list_display = ['__str__', 'trainee']
