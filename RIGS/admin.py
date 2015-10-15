from django.contrib import admin
from RIGS import models, forms
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import ugettext_lazy as _
import reversion

# Register your models here.
admin.site.register(models.Person, reversion.VersionAdmin)
admin.site.register(models.Organisation, reversion.VersionAdmin)
admin.site.register(models.VatRate, reversion.VersionAdmin)
admin.site.register(models.Venue, reversion.VersionAdmin)
admin.site.register(models.Event, reversion.VersionAdmin)
admin.site.register(models.EventItem, reversion.VersionAdmin)
admin.site.register(models.Invoice)
admin.site.register(models.Payment)

class ProfileAdmin(UserAdmin):
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {
         'fields': ('first_name', 'last_name', 'email', 'initials', 'phone')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser',
                                       'groups', 'user_permissions')}),
        (_('Important dates'), {
         'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2'),
        }),
    )
    form = forms.ProfileChangeForm
    add_form = forms.ProfileCreationForm

admin.site.register(models.Profile, ProfileAdmin)
