from django.contrib import admin

from notifications import models


@admin.register(models.Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["title", "recipient", "kind", "created_at", "delivered_at", "read_at"]
    list_filter = ["kind"]
    search_fields = ["title", "body", "recipient__first_name", "recipient__last_name", "recipient__username"]
    list_select_related = ["recipient"]
    date_hierarchy = "created_at"


@admin.register(models.PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ["user", "user_agent", "created_at"]
    search_fields = ["user__username", "user_agent"]
    list_select_related = ["user"]
