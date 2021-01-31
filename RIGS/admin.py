from django.contrib import admin
from django.contrib import messages
from django.contrib.admin import helpers
from django.contrib.auth.admin import UserAdmin
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Count
from django.forms import ModelForm
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _
from reversion import revisions as reversion
from reversion.admin import VersionAdmin

from RIGS import models
from users import forms as user_forms

# Register your models here.
admin.site.register(models.VatRate, VersionAdmin)
admin.site.register(models.Event, VersionAdmin)
admin.site.register(models.EventItem, VersionAdmin)
admin.site.register(models.Invoice, VersionAdmin)


def approve_user(modeladmin, request, queryset):
    queryset.update(is_approved=True)


approve_user.short_description = "Approve selected users"


@admin.register(models.Profile)
class ProfileAdmin(UserAdmin):
    # Don't know how to add 'is_approved' whilst preserving the default list...
    list_filter = ('is_approved', 'is_active', 'is_staff', 'is_superuser', 'groups')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {
            'fields': ('first_name', 'last_name', 'email', 'initials', 'phone')}),
        (_('Permissions'), {'fields': ('is_approved', 'is_active', 'is_staff', 'is_superuser',
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
    form = user_forms.ProfileChangeForm
    add_form = user_forms.ProfileCreationForm
    actions = [approve_user]


class AssociateAdmin(VersionAdmin):
    list_display = ('id', 'name', 'number_of_events')
    search_fields = ['id', 'name']
    list_display_links = ['id', 'name']
    actions = ['merge']

    merge_fields = ['name']

    def get_queryset(self, request):
        return super(AssociateAdmin, self).get_queryset(request).annotate(event_count=Count('event'))

    def number_of_events(self, obj):
        return obj.latest_events.count()

    number_of_events.admin_order_field = 'event_count'

    def merge(self, request, queryset):
        if request.POST.get('post'):  # Has the user confirmed which is the master record?
            try:
                masterObjectPk = request.POST.get('master')
                masterObject = queryset.get(pk=masterObjectPk)
            except ObjectDoesNotExist:
                self.message_user(request, "An error occured. Did you select a 'master' record?", level=messages.ERROR)
                return

            with transaction.atomic(), reversion.create_revision():
                for obj in queryset.exclude(pk=masterObjectPk):
                    events = obj.event_set.all()
                    for event in events:
                        masterObject.event_set.add(event)
                    obj.delete()
                reversion.set_comment('Merging Objects')

            self.message_user(request, "Objects successfully merged.")
            return
        else:  # Present the confirmation screen

            class TempForm(ModelForm):
                class Meta:
                    model = queryset.model
                    fields = self.merge_fields

            forms = []
            for obj in queryset:
                forms.append(TempForm(instance=obj))

            context = {
                'title': _("Are you sure?"),
                'queryset': queryset,
                'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
                'forms': forms
            }
            return TemplateResponse(request, 'admin_associate_merge.html', context)


@admin.register(models.Person)
class PersonAdmin(AssociateAdmin):
    list_display = ('id', 'name', 'phone', 'email', 'number_of_events')
    merge_fields = ['name', 'phone', 'email', 'address', 'notes']


@admin.register(models.Venue)
class VenueAdmin(AssociateAdmin):
    list_display = ('id', 'name', 'phone', 'email', 'number_of_events')
    merge_fields = ['name', 'phone', 'email', 'address', 'notes', 'three_phase_available']


@admin.register(models.Organisation)
class OrganisationAdmin(AssociateAdmin):
    list_display = ('id', 'name', 'phone', 'email', 'number_of_events')
    merge_fields = ['name', 'phone', 'email', 'address', 'notes', 'union_account']


@admin.register(models.RiskAssessment)
class RiskAssessmentAdmin(VersionAdmin):
    list_display = ('id', 'event', 'reviewed_at', 'reviewed_by')


@admin.register(models.EventChecklist)
class EventChecklistAdmin(VersionAdmin):
    list_display = ('id', 'event', 'reviewed_at', 'reviewed_by')
