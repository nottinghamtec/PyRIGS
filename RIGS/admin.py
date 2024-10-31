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
admin.site.register(models.EventCheckIn)


@transaction.atomic()  # Copied from django-extensions. GenericForeignKey support removed as unnecessary.
def merge_model_instances(primary_object, alias_objects):
    """
    Merge several model instances into one, the `primary_object`.
    Use this function to merge model objects and migrate all of the related
    fields from the alias objects the primary object.
    """

    # get related fields
    related_fields = list(filter(
        lambda x: x.is_relation is True,
        primary_object._meta.get_fields()))

    many_to_many_fields = list(filter(
        lambda x: x.many_to_many is True, related_fields))

    related_fields = list(filter(
        lambda x: x.many_to_many is False, related_fields))

    # Loop through all alias objects and migrate their references to the
    # primary object
    deleted_objects = []
    deleted_objects_count = 0
    for alias_object in alias_objects:
        # Migrate all foreign key references from alias object to primary
        # object.
        for many_to_many_field in many_to_many_fields:
            alias_varname = many_to_many_field.name
            related_objects = getattr(alias_object, alias_varname)
            for obj in related_objects.all():
                try:
                    # Handle regular M2M relationships.
                    getattr(alias_object, alias_varname).remove(obj)
                    getattr(primary_object, alias_varname).add(obj)
                except AttributeError:
                    # Handle M2M relationships with a 'through' model.
                    # This does not delete the 'through model.
                    # TODO: Allow the user to delete a duplicate 'through' model.
                    through_model = getattr(alias_object, alias_varname).through
                    kwargs = {
                        many_to_many_field.m2m_reverse_field_name(): obj,
                        many_to_many_field.m2m_field_name(): alias_object,
                    }
                    through_model_instances = through_model.objects.filter(**kwargs)
                    for instance in through_model_instances:
                        # Re-attach the through model to the primary_object
                        setattr(
                            instance,
                            many_to_many_field.m2m_field_name(),
                            primary_object)
                        instance.save()
                        # TODO: Here, try to delete duplicate instances that are
                        # disallowed by a unique_together constraint

        for related_field in related_fields:
            if related_field.one_to_many:
                with transaction.atomic():
                    try:
                        alias_varname = related_field.get_accessor_name()
                        related_objects = getattr(alias_object, alias_varname)
                        for obj in related_objects.all():
                            field_name = related_field.field.name
                            setattr(obj, field_name, primary_object)
                            obj.save()
                    except IntegrityError:
                        pass  # Skip to avoid integrity error from unique_together
            elif related_field.one_to_one or related_field.many_to_one:
                alias_varname = related_field.name
                if hasattr(alias_object, alias_varname):
                    related_object = getattr(alias_object, alias_varname)
                    primary_related_object = getattr(primary_object, alias_varname)
                    if primary_related_object is None:
                        setattr(primary_object, alias_varname, related_object)
                        primary_object.save()
                    elif related_field.one_to_one:
                        related_object.delete()

        if alias_object.id:
            deleted_objects += [alias_object]
            alias_object.delete()
            deleted_objects_count += 1

    return primary_object, deleted_objects, deleted_objects_count


class AssociateAdmin(VersionAdmin):
    search_fields = ['id', 'name']
    list_display_links = ['id', 'name']
    actions = ['merge']

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(event_count=Count('event'))

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

            primary_object, deleted_objects, deleted_objects_count = merge_model_instances(master_object, queryset.exclude(pk=master_object_pk).all())
            reversion.set_comment('Merging Objects')
            self.message_user(request, f"Objects successfully merged. {deleted_objects_count} old objects deleted.")
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
    list_display = ('username', 'name', 'is_approved', 'is_superuser', 'is_supervisor', 'number_of_events', 'last_login', 'date_joined')
    list_display_links = ['username']
    list_filter = UserAdmin.list_filter + ('is_approved', 'date_joined')
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


@admin.register(models.PowerTestRecord)
class EventChecklistAdmin(VersionAdmin):
    list_display = ('id', 'event', 'reviewed_at', 'reviewed_by')
