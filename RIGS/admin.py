from django.contrib import admin
from RIGS import models, forms
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import ugettext_lazy as _
import reversion

from django.contrib.admin import helpers
from django.template.response import TemplateResponse
from django.contrib import messages 
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist

# Register your models here.
admin.site.register(models.VatRate, reversion.VersionAdmin)
admin.site.register(models.Event, reversion.VersionAdmin)
admin.site.register(models.EventItem, reversion.VersionAdmin)
admin.site.register(models.Invoice)
admin.site.register(models.Payment)

@admin.register(models.Profile)
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

@admin.register(models.Person, models.Organisation, models.Venue)
class AssociateAdmin(reversion.VersionAdmin):
    list_display = ('id', 'name','number_of_events')
    search_fields = ['id','name']

    actions = ['merge']

    def number_of_events(self,obj):
        return obj.latest_events.count()

    def merge(self, request, queryset):
        if request.POST.get('post'): # Has the user confirmed which is the master record?
            try:
                masterObjectPk = request.POST.get('master')
                masterObject = queryset.get(pk = masterObjectPk)
            except ObjectDoesNotExist:
                self.message_user(request, "An error occured. Did you select a 'master' record?",level=messages.ERROR)   
                return

            with transaction.atomic(), reversion.create_revision():
                for obj in queryset.exclude(pk = masterObjectPk):
                    events = obj.event_set.all()
                    for event in events:
                        masterObject.event_set.add(event)
                    obj.delete() 
                reversion.set_comment('Merging Objects')

            self.message_user(request, "Objects successfully merged.")
            return
        else: # Present the confirmation screen
            context = {
                'title': _("Are you sure?"),
                'queryset': queryset,
                'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
            }
            return TemplateResponse(request, 'RIGS/admin_associate_merge.html', context, current_app=self.admin_site.name)