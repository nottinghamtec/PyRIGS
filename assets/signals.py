import re
from django.db.models.signals import pre_save
from django.dispatch.dispatcher import receiver
from .models import Asset


def split_asset_id(asset_id):
    """Automatically fills in hidden members on database access"""
    asset_search = re.search("^([a-zA-Z0-9]*?[a-zA-Z]?)([0-9]+)$", asset_id)
    return asset_search


@receiver(pre_save, sender=Asset)
def pre_save_asset(sender, instance, **kwargs):
    asset_search = split_asset_id(instance.asset_id)
    if asset_search is None:
        instance.asset_id += "1"
    asset_search = split_asset_id(instance.asset_id)
    instance.asset_id_prefix = asset_search.group(1)
    instance.asset_id_number = int(asset_search.group(2))
