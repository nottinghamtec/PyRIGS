import reversion
from django.contrib import admin
from django.contrib import messages
from django.contrib.admin import helpers
from django.contrib.auth.admin import UserAdmin
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Count
from django.forms import ModelForm
from django.template.response import TemplateResponse
from django.utils.translation import ugettext_lazy as _

from RIGS import models, forms

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


class AssociateAdmin(reversion.VersionAdmin):
    list_display = ('id', 'name', 'number_of_events')
    search_fields = ['id', 'name']
    list_display_links = ['id', 'name']
    actions = ['merge']

    merge_fields = ['name']

    def get_queryset(self, request):
        return super(AssociateAdmin, self).get_queryset(
            request).annotate(event_count=Count('event'))

    def number_of_events(self, obj):
        return obj.latest_events.count()

    number_of_events.admin_order_field = 'event_count'

    def merge(self, request, queryset):
        if request.POST.get(
            'post'):  # Has the user confirmed which is the master record?
            try:
                masterObjectPk = request.POST.get('master')
                masterObject = queryset.get(pk=masterObjectPk)
            except ObjectDoesNotExist:
                self.message_user(
                    request,
                    "An error occured. Did you select a 'master' record?",
                    level=messages.ERROR)
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
            return TemplateResponse(request, 'RIGS/admin_associate_merge.html', context,
                                    current_app=self.admin_site.name)


@admin.register(models.Person)
class PersonAdmin(AssociateAdmin):
    list_display = ('id', 'name', 'phone', 'email', 'number_of_events')
    merge_fields = ['name', 'phone', 'email', 'address', 'notes']


@admin.register(models.Venue)
class VenueAdmin(AssociateAdmin):
    list_display = ('id', 'name', 'phone', 'email', 'number_of_events')
    merge_fields = [
        'name',
        'phone',
        'email',
        'address',
        'notes',
        'three_phase_available']


@admin.register(models.Organisation)
class OrganisationAdmin(AssociateAdmin):
    list_display = ('id', 'name', 'phone', 'email', 'number_of_events')
    merge_fields = [
        'name',
        'phone',
        'email',
        'address',
        'notes',
        'union_account']
