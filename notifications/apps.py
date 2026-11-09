from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    name = "notifications"

    def ready(self):
        import notifications.signals  # noqa: F401 (registers signal handlers)
