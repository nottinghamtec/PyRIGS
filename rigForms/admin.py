from django.contrib import admin

from rigForms import models

import reversion

# Register your models here.
admin.site.register(models.Type, reversion.VersionAdmin)
admin.site.register(models.Schema, reversion.VersionAdmin)
admin.site.register(models.Form, reversion.VersionAdmin)