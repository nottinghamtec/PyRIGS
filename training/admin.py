from django.contrib import admin
from training import models
from reversion.admin import VersionAdmin


admin.site.register(models.TrainingCategory, VersionAdmin)
admin.site.register(models.TrainingLevel, VersionAdmin)
admin.site.register(models.TrainingLevelQualification, VersionAdmin)
admin.site.register(models.TrainingLevelRequirement, VersionAdmin)


@admin.register(models.TrainingItemQualification)
class TrainingItemQualificationAdmin(VersionAdmin):
    list_display = ["item", "depth", "trainee", "supervisor", "date"]
    list_filter = ["depth", "date", "item__category"]
    search_fields = [
        "item__name",
        "trainee__first_name",
        "trainee__last_name",
    ]
    list_select_related = ["item", "item__category", "trainee", "supervisor"]
    date_hierarchy = "date"
    ordering = ["-date"]


@admin.register(models.TrainingItem)
class TrainingItemAdmin(VersionAdmin):
    list_display = ["__str__", "category", "active", "technician_can_train"]
    list_filter = ["category", "active", "technician_can_train"]
