from django.contrib import admin

from badges import models


@admin.register(models.BadgeAward)
class BadgeAwardAdmin(admin.ModelAdmin):
    list_display = ["profile", "slug", "awarded_at", "created_at", "email", "emailed_at"]
    list_filter = ["email", "slug"]
    search_fields = ["profile__first_name", "profile__last_name", "profile__username", "slug"]
    list_select_related = ["profile"]
    date_hierarchy = "awarded_at"


@admin.register(models.BadgeSettings)
class BadgeSettingsAdmin(admin.ModelAdmin):
    list_display = ["__str__", "badges_live", "badges_superusers", "tech_rider_live", "tech_rider_superusers"]

    def has_add_permission(self, request):
        return not models.BadgeSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
