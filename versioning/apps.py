from django.apps import AppConfig


class VersioningConfig(AppConfig):
    name = "versioning"

    def ready(self):
        from django.db.models.signals import pre_delete
        from reversion import signals as reversion_signals

        from versioning.versioning import get_models, record_deleted_object, revision_committed

        reversion_signals.post_revision_commit.connect(revision_committed)
        for model in get_models():
            pre_delete.connect(record_deleted_object, sender=model)
