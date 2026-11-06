from django.db import models


class RevisionAction(models.Model):
    CONVERTED = "converted"
    DELETED = "deleted"
    KINDS = [(CONVERTED, "Converted"), (DELETED, "Deleted")]

    revision = models.OneToOneField("reversion.Revision", related_name="action", on_delete=models.CASCADE)
    kind = models.CharField(max_length=16, choices=KINDS)
    name = models.TextField()
