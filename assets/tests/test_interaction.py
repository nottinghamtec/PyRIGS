from . import pages
from django.core.management import call_command
from django.test import TestCase
from assets import models
from django.test.utils import override_settings
from django.urls import reverse
from urllib.parse import urlparse
from RIGS import models as rigsmodels
from PyRIGS.tests.base import BaseTest, AutoLoginTest, screenshot_failure_cls
from assets import models, urls
from reversion import revisions as reversion
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from PyRIGS.tests.base import animation_is_finished
import datetime
from django.utils import timezone
from selenium.webdriver.common.action_chains import ActionChains
from django.test import tag


@screenshot_failure_cls
class TestAssetList(AutoLoginTest):
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
        self.page = pages.AssetList(self.driver, self.live_server_url).open()

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

    def test_search(self):
        self.page.set_query("10")
        self.page.search()
        self.assertTrue(len(self.page.assets) == 1)
        self.assertEqual("Working Mic", self.page.assets[0].description)
        self.assertEqual("10", self.page.assets[0].id)

        self.page.set_query("light")
        self.page.search()
        self.assertTrue(len(self.page.assets) == 1)
        self.assertEqual("A light", self.page.assets[0].description)

        self.page.set_query("Random string")
        self.page.search()
        self.assertTrue(len(self.page.assets) == 0)

        self.page.set_query("")
        self.page.search()
        # Only working stuff shown by default
        self.assertTrue(len(self.page.assets) == 2)

        self.page.status_selector.toggle()
        self.assertTrue(self.page.status_selector.is_open)
        self.page.status_selector.select_all()
        self.page.status_selector.toggle()
        self.assertFalse(self.page.status_selector.is_open)
        self.page.search()
        self.assertTrue(len(self.page.assets) == 4)

        self.page.category_selector.toggle()
        self.assertTrue(self.page.category_selector.is_open)
        self.page.category_selector.set_option("Sound", True)
        self.page.category_selector.close()
        self.assertFalse(self.page.category_selector.is_open)
        self.page.search()
        self.assertTrue(len(self.page.assets) == 2)
        assetIDs = list(map(lambda x: x.id, self.page.assets))
        self.assertEqual("1", assetIDs[0])
        self.assertEqual("10", assetIDs[1])


@screenshot_failure_cls
class TestAssetForm(AutoLoginTest):
    def setUp(self):
        super().setUp()
        self.category = models.AssetCategory.objects.create(name="Health & Safety")
        self.status = models.AssetStatus.objects.create(name="O.K.", should_show=True)
        self.supplier = models.Supplier.objects.create(name="Fullmetal Heavy Industry")
        self.parent = models.Asset.objects.create(asset_id="9000", description="Shelf", status=self.status, category=self.category, date_acquired=datetime.date(2000, 1, 1))
        self.connector = models.Connector.objects.create(description="IEC", current_rating=10, voltage_rating=240, num_pins=3)
        self.cable_type = models.CableType.objects.create(plug=self.connector, socket=self.connector, circuits=1, cores=3)
        self.wait = WebDriverWait(self.driver, 5)
        self.page = pages.AssetCreate(self.driver, self.live_server_url).open()

    def test_asset_create(self):
        # Test that ID is automatically assigned and properly incremented
        self.assertIn(self.page.asset_id, "9001")

        self.page.remove_all_required()
        self.page.asset_id = "XX$X"
        self.page.submit()
        self.assertFalse(self.page.success)
        self.assertIn("An Asset ID can only consist of letters and numbers, with a final number", self.page.errors["Asset id"])
        self.assertIn("This field is required.", self.page.errors["Description"])

        self.page.open()

        self.page.description = desc = "Bodge Lead"
        self.page.category = cat = "Health & Safety"
        self.page.status = status = "O.K."
        self.page.serial_number = sn = "0124567890-SAUSAGE"
        self.page.comments = comments = "This is actually a sledgehammer, not a cable..."

        self.page.purchased_from_selector.toggle()
        self.assertTrue(self.page.purchased_from_selector.is_open)
        self.page.purchased_from_selector.search(self.supplier.name[:-8])
        self.page.purchased_from_selector.set_option(self.supplier.name, True)
        self.page.purchase_price = "12.99"
        self.page.salvage_value = "99.12"
        self.page.date_acquired = acquired = datetime.date(2020, 5, 2)

        self.page.parent_selector.toggle()
        self.assertTrue(self.page.parent_selector.is_open)
        self.page.parent_selector.search(self.parent.asset_id)
        # Needed here but not earlier for whatever reason
        self.driver.implicitly_wait(1)
        self.page.parent_selector.set_option(self.parent.asset_id + " | " + self.parent.description, True)
        self.assertTrue(self.page.parent_selector.options[0].selected)
        self.page.parent_selector.toggle()

        self.assertFalse(self.driver.find_element_by_id('cable-table').is_displayed())

        self.page.submit()
        self.wait.until(animation_is_finished())
        self.assertTrue(self.page.success)
        # Check that data is right
        asset = models.Asset.objects.get(asset_id="9001")
        self.assertEqual(asset.description, desc)
        self.assertEqual(asset.category.name, cat)
        self.assertEqual(asset.status.name, status)
        self.assertEqual(asset.serial_number, sn)
        self.assertEqual(asset.comments, comments)
        # This one is important as it defaults to today's date
        self.assertEqual(asset.date_acquired, acquired)

    def test_cable_create(self):
        self.page.description = "IEC -> IEC"
        self.page.category = "Health & Safety"
        self.page.status = "O.K."
        self.page.serial_number = "MELON-MELON-MELON"
        self.page.comments = "You might need that"
        self.page.is_cable = True

        self.assertTrue(self.driver.find_element_by_id('cable-table').is_displayed())
        self.wait.until(animation_is_finished())
        self.page.cable_type = "IEC → IEC"
        self.page.socket = "IEC"
        self.page.length = 10
        self.page.csa = "1.5"

        self.page.submit()
        self.assertTrue(self.page.success)

    def test_asset_edit(self):
        self.page = pages.AssetEdit(self.driver, self.live_server_url, asset_id=self.parent.asset_id).open()

        self.assertTrue(self.driver.find_element_by_id('id_asset_id').get_attribute('readonly') is not None)

        new_description = "Big Shelf"
        self.page.description = new_description

        self.page.submit()
        self.assertTrue(self.page.success)

        self.assertEqual(models.Asset.objects.get(asset_id=self.parent.asset_id).description, new_description)

    def test_asset_duplicate(self):
        self.page = pages.AssetDuplicate(self.driver, self.live_server_url, asset_id=self.parent.asset_id).open()

        self.assertNotEqual(self.parent.asset_id, self.page.asset_id)
        self.assertEqual(self.parent.description, self.page.description)
        self.assertEqual(self.parent.status.name, self.page.status)
        self.assertEqual(self.parent.category.name, self.page.category)
        self.assertEqual(self.parent.date_acquired, self.page.date_acquired.date())

        self.page.submit()
        self.assertTrue(self.page.success)
        self.assertEqual(models.Asset.objects.last().description, self.parent.description)


@screenshot_failure_cls
class TestSupplierList(AutoLoginTest):
    def setUp(self):
        super().setUp()
        models.Supplier.objects.create(name="Fullmetal Heavy Industry")
        models.Supplier.objects.create(name="Acme.")
        models.Supplier.objects.create(name="TEC PA & Lighting")
        models.Supplier.objects.create(name="Caterpillar Inc.")
        models.Supplier.objects.create(name="N.E.R.D")
        models.Supplier.objects.create(name="Khumalo")
        models.Supplier.objects.create(name="1984 Incorporated")
        self.page = pages.SupplierList(self.driver, self.live_server_url).open()

    # Should be sorted alphabetically
    def test_order(self):
        names = list(map(lambda x: x.name, self.page.suppliers))
        self.assertEqual("1984 Incorporated", names[0])
        self.assertEqual("Acme.", names[1])
        self.assertEqual("Caterpillar Inc.", names[2])
        self.assertEqual("Fullmetal Heavy Industry", names[3])
        self.assertEqual("Khumalo", names[4])
        self.assertEqual("N.E.R.D", names[5])
        self.assertEqual("TEC PA & Lighting", names[6])

    def test_search(self):
        self.page.set_query("TEC")
        self.page.search()

        self.assertTrue(len(self.page.suppliers) == 1)
        self.assertEqual("TEC PA & Lighting", self.page.suppliers[0].name)

        self.page.set_query("")
        self.page.search()
        self.assertTrue(len(self.page.suppliers) == 7)

        self.page.set_query("This is not a supplier")
        self.page.search()
        self.assertTrue(len(self.page.suppliers) == 0)


@screenshot_failure_cls
class TestSupplierCreateAndEdit(AutoLoginTest):
    def setUp(self):
        super().setUp()
        self.supplier = models.Supplier.objects.create(name="Fullmetal Heavy Industry")

    def test_supplier_create(self):
        self.page = pages.SupplierCreate(self.driver, self.live_server_url).open()

        self.page.remove_all_required()
        self.page.submit()
        self.assertFalse(self.page.success)
        self.assertIn("This field is required.", self.page.errors["Name"])

        self.page.name = "Optican Health Supplies"
        self.page.submit()
        self.assertTrue(self.page.success)

    def test_supplier_edit(self):
        self.page = pages.SupplierEdit(self.driver, self.live_server_url, supplier_id=self.supplier.pk).open()

        self.assertEqual("Fullmetal Heavy Industry", self.page.name)
        new_name = "Cyberdyne Systems"
        self.page.name = new_name
        self.page.submit()
        self.assertTrue(self.page.success)


@screenshot_failure_cls
class TestAssetAudit(AutoLoginTest):
    def setUp(self):
        super().setUp()
        self.category = models.AssetCategory.objects.create(name="Haulage")
        self.status = models.AssetStatus.objects.create(name="Probably Fine", should_show=True)
        self.supplier = models.Supplier.objects.create(name="The Bazaar")
        self.connector = models.Connector.objects.create(description="Trailer Socket", current_rating=1, voltage_rating=40, num_pins=13)
        models.Asset.objects.create(asset_id="1", description="Trailer Cable", status=self.status, category=self.category, date_acquired=datetime.date(2020, 2, 1))
        models.Asset.objects.create(asset_id="11", description="Trailerboard", status=self.status, category=self.category, date_acquired=datetime.date(2020, 2, 1))
        models.Asset.objects.create(asset_id="111", description="Erms", status=self.status, category=self.category, date_acquired=datetime.date(2020, 2, 1))
        models.Asset.objects.create(asset_id="1111", description="A hammer", status=self.status, category=self.category, date_acquired=datetime.date(2020, 2, 1))
        self.page = pages.AssetAuditList(self.driver, self.live_server_url).open()
        self.wait = WebDriverWait(self.driver, 20)

    def test_audit_process(self):
        asset_id = "1111"
        self.page.set_query(asset_id)
        self.page.search()
        self.wait.until(EC.visibility_of_element_located((By.ID, 'modal')))
        # Do it wrong on purpose to check error display
        self.page.modal.remove_all_required()
        self.page.modal.description = ""
        self.page.modal.submit()
        self.wait.until(animation_is_finished())
        self.wait.until(EC.visibility_of_element_located((By.ID, 'modal')))
        self.assertIn("This field is required.", self.page.modal.errors["Description"])
        # Now do it properly
        self.page.modal.description = new_desc = "A BIG hammer"
        self.page.modal.submit()
        submit_time = timezone.now()
        self.wait.until(EC.invisibility_of_element_located((By.ID, 'modal')))
        self.assertFalse(self.driver.find_element_by_id('modal').is_displayed())

        # Check data is correct
        audited = models.Asset.objects.get(asset_id=asset_id)
        self.assertEqual(audited.description, new_desc)
        # Make sure audit 'log' was filled out
        self.assertEqual(self.profile.initials, audited.last_audited_by.initials)
        self.assertEqual(submit_time.replace(microsecond=0), audited.last_audited_at.replace(microsecond=0))
        # Check we've removed it from the 'needing audit' list
        self.assertNotIn(asset_id, self.page.assets)

    def test_audit_list(self):
        self.assertEqual(len(models.Asset.objects.filter(last_audited_at=None)), len(self.page.assets))

        asset_row = self.page.assets[0]
        self.driver.find_element(By.XPATH, "//a[contains(@class,'btn') and contains(., 'Audit')]").click()
        self.wait.until(EC.visibility_of_element_located((By.ID, 'modal')))
        self.assertEqual(self.page.modal.asset_id, asset_row.id)
        self.page.modal.close()
        self.wait.until(EC.invisibility_of_element_located((By.ID, 'modal')))
        self.assertFalse(self.driver.find_element_by_id('modal').is_displayed())
        # Make sure audit log was NOT filled out
        audited = models.Asset.objects.get(asset_id=asset_row.id)
        self.assertEqual(None, audited.last_audited_by)

    def test_audit_search(self):
        # Check that a failed search works
        self.page.set_query("NOTFOUND")
        self.page.search()
        self.wait.until(animation_is_finished())
        self.assertFalse(self.driver.find_element_by_id('modal').is_displayed())
        self.assertIn("Asset with that ID does not exist!", self.page.error.text)
