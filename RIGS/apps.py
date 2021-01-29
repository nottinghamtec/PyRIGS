from django.apps import AppConfig


class RIGSAppConfig(AppConfig):
    name = 'RIGS'

    def ready(self):
        import RIGS.signals
