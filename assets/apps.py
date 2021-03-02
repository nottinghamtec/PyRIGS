from django.apps import AppConfig


class AssetsAppConfig(AppConfig):
    name = 'assets'

    def ready(self):
        import assets.signals
