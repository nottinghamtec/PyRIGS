from django.contrib import admin
from training import models
from reversion.admin import VersionAdmin

admin.site.register(models.Trainee, VersionAdmin)
admin.site.register(models.TechnicalAssistant, VersionAdmin)
admin.site.register(models.Technician, VersionAdmin)
admin.site.register(models.Supervisor, VersionAdmin)
admin.site.register(models.Department, VersionAdmin)
