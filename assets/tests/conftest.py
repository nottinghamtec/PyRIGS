import pytest
from assets import models
import datetime


@pytest.fixture
def test_cable(db):
    category = models.AssetCategory.objects.create(name="Sound")
    status = models.AssetStatus.objects.create(name="Broken", should_show=True)
    connector = models.Connector.objects.create(description="16A IEC", current_rating=16, voltage_rating=240, num_pins=3)
    cable_type = models.CableType.objects.create(circuits=11, cores=3, plug=connector, socket=connector)
    return models.Asset.objects.create(asset_id="666", description="125A -> Jack", comments="The cable from Hell...", status=status, category=category, date_acquired=datetime.date(2006, 6, 6), is_cable=True, cable_type=cable_type, length=10, csa="1.5")


@pytest.fixture
def test_asset(db):
    working = models.AssetStatus.objects.create(name="Working", should_show=True)
    lighting = models.AssetCategory.objects.create(name="Lighting")
    asset = models.Asset.objects.create(asset_id="1991", description="Spaceflower", status=working, category=lighting, date_acquired=datetime.date(1991, 12, 26))
    return asset
