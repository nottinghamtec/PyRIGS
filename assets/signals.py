import re
from django.db.models.signals import pre_save
from django.dispatch.dispatcher import receiver
from .models import Asset


@receiver(pre_save, sender=Asset)
def pre_save_asset(sender, instance, **kwargs):
    """Automatically fills in hidden members on database access"""
    asset_search = re.search("^([a-zA-Z0-9]*?[a-zA-Z]?)([0-9]+)$", instance.asset_id)
    if asset_search is None:
        instance.asset_id += "1"
    asset_search = re.search("^([a-zA-Z0-9]*?[a-zA-Z]?)([0-9]+)$", instance.asset_id)
    instance.asset_id_prefix = asset_search.group(1)
    instance.asset_id_number = int(asset_search.group(2))
