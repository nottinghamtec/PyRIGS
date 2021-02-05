import pytest
from assets import models
import datetime


@pytest.fixture
def category(db):
    return models.AssetCategory.objects.create(name="Sound")


@pytest.fixture
def status(db):
    return models.AssetStatus.objects.create(name="Broken", should_show=True)


@pytest.fixture
def test_cable(db, category, status):
    connector = models.Connector.objects.create(description="16A IEC", current_rating=16, voltage_rating=240, num_pins=3)
    cable_type = models.CableType.objects.create(circuits=11, cores=3, plug=connector, socket=connector)
    return models.Asset.objects.create(asset_id="9666", description="125A -> Jack", comments="The cable from Hell...", status=status, category=category, date_acquired=datetime.date(2006, 6, 6), is_cable=True, cable_type=cable_type, length=10, csa="1.5")


@pytest.fixture
def test_asset(db, category, status):
    asset = models.Asset.objects.create(asset_id="91991", description="Spaceflower", status=status, category=category, date_acquired=datetime.date(1991, 12, 26))
    return asset
