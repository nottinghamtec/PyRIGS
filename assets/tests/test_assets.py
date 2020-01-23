from . import pages
from urllib.parse import urlparse
from RIGS import models as rigsmodels
from PyRIGS.tests.base import BaseTest, AutoLoginTest
from assets import models
import datetime


class AssetListTests(AutoLoginTest):
    def setUp(self):
        super().setUp()
        sound = models.AssetCategory.objects.create(name="Sound")
        lighting = models.AssetCategory.objects.create(name="Lighting")

        working = models.AssetStatus.objects.create(name="Working", should_show=True)
        broken = models.AssetStatus.objects.create(name="Broken", should_show=False)

        models.Asset.objects.create(asset_id="1", description="Broken XLR", status=broken, category=sound, date_acquired=datetime.date(2020, 2, 1))
        models.Asset.objects.create(asset_id="10", description="Working Mic", status=working, category=sound, date_acquired=datetime.date(2020, 2, 1))
        models.Asset.objects.create(asset_id="2", description="A light", status=working, category=lighting, date_acquired=datetime.date(2020, 2, 1))
        models.Asset.objects.create(asset_id="C1", description="The pearl", status=broken, category=lighting, date_acquired=datetime.date(2020, 2, 1))
        self.page = pages.AssetListPage(self.driver, self.live_server_url).open()

    def test_default_statuses_applied(self):
        # Only the working stuff should be shown initially
        assetDescriptions = list(map(lambda x: x.description, self.page.assets))
        self.assertEqual(2, len(assetDescriptions))
        self.assertIn("A light", assetDescriptions)
        self.assertIn("Working Mic", assetDescriptions)

    def test_asset_order(self):
        # Only the working stuff should be shown initially
        self.page.status_selector.open()
        self.page.status_selector.set_option("Broken", True)
        self.page.status_selector.close()

        self.page.search()

        assetIDs = list(map(lambda x: x.id, self.page.assets))
        self.assertEqual("1", assetIDs[0])
        self.assertEqual("2", assetIDs[1])
        self.assertEqual("10", assetIDs[2])
        self.assertEqual("C1", assetIDs[3])
