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
from django.db import IntegrityError
from reversion import revisions as reversion
from reversion.admin import VersionAdmin

from RIGS import models
from users import forms as user_forms


admin.site.register(models.VatRate, VersionAdmin)
admin.site.register(models.Event, VersionAdmin)
admin.site.register(models.EventItem, VersionAdmin)
admin.site.register(models.Invoice, VersionAdmin)


class AssociateAdmin(VersionAdmin):
    search_fields = ['id', 'name']
    list_display_links = ['id', 'name']
    actions = ['merge']

    def get_queryset(self, request):
        return super(AssociateAdmin, self).get_queryset(request).annotate(event_count=Count('event'))

    def number_of_events(self, obj):
        return obj.latest_events.count()

    number_of_events.admin_order_field = 'event_count'

    def merge(self, request, queryset):
        if request.POST.get('post'):  # Has the user confirmed which is the master record?
            try:
                master_object_pk = request.POST.get('master')
                master_object = queryset.get(pk=master_object_pk)
            except ObjectDoesNotExist:
                self.message_user(request, "An error occured. Did you select a 'master' record?", level=messages.ERROR)
                return

            with transaction.atomic(), reversion.create_revision():
                for obj in queryset.exclude(pk=master_object_pk):
                    # If we're merging profiles, merge their training information
                    if hasattr(obj, 'event_mic'):
                        events = obj.event_mic.all()
                        for event in events:
                            master_object.event_mic.add(event)
                        for qual in obj.qualifications_obtained.all():
                            try:
                                with transaction.atomic():
                                    master_object.qualifications_obtained.add(qual)
                            except IntegrityError:
                                existing_qual = master_object.qualifications_obtained.get(item=qual.item, depth=qual.depth)
                                existing_qual.notes += qual.notes
                                existing_qual.save()
                        for level in obj.level_qualifications.all():
                            try:
                                with transaction.atomic():
                                    master_object.level_qualifications.add(level)
                            except IntegrityError:
                                continue  # Exists, oh well
                    else:
                        events = obj.event_set.all()
                        for event in events:
                            master_object.event_set.add(event)
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


@admin.register(models.Profile)
class ProfileAdmin(UserAdmin, AssociateAdmin):
    list_display = ('username', 'name', 'is_approved', 'is_staff', 'is_superuser', 'is_supervisor', 'number_of_events')
    list_display_links = ['username']
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
    actions = ['approve_user', 'merge']

    merge_fields = ['username', 'first_name', 'last_name', 'initials', 'email', 'phone', 'is_supervisor']

    def approve_user(modeladmin, request, queryset):
        queryset.update(is_approved=True)


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
