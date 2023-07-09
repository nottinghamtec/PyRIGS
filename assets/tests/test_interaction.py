import time
import datetime
import pytest

from django.utils import timezone
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

from PyRIGS.tests.base import AutoLoginTest, screenshot_failure_cls, assert_times_almost_equal
from PyRIGS.tests.pages import animation_is_finished
from assets import models
from . import pages


@screenshot_failure_cls
class TestAssetList(AutoLoginTest):
    def setUp(self):
        super().setUp()
        sound = models.AssetCategory.objects.create(name="Sound")
        lighting = models.AssetCategory.objects.create(name="Lighting")

        working = models.AssetStatus.objects.create(name="Working", should_show=True)
        broken = models.AssetStatus.objects.create(name="Broken", should_show=False)

        models.Asset.objects.create(asset_id="1", description="Broken XLR", status=broken, category=sound,
                                    date_acquired=datetime.date(2020, 2, 1))
        models.Asset.objects.create(asset_id="10", description="Working Mic", status=working, category=sound,
                                    date_acquired=datetime.date(2020, 2, 1))
        models.Asset.objects.create(asset_id="2", description="A light", status=working, category=lighting,
                                    date_acquired=datetime.date(2020, 2, 1))
        models.Asset.objects.create(asset_id="C1", description="The pearl", status=broken, category=lighting,
                                    date_acquired=datetime.date(2020, 2, 1))
        self.page = pages.AssetList(self.driver, self.live_server_url).open()

    def test_default_statuses_applied(self):
        # Only the working stuff should be shown initially
        asset_descriptions = list(map(lambda x: x.description, self.page.assets))
        self.assertEqual(2, len(asset_descriptions))
        self.assertIn("A light", asset_descriptions)
        self.assertIn("Working Mic", asset_descriptions)

    def test_asset_order(self):
        # Only the working stuff should be shown initially
        self.page.status_selector.open()
        self.page.status_selector.set_option("Broken", True)
        self.page.status_selector.close()

        self.page.search()

        asset_ids = list(map(lambda x: x.id, self.page.assets))
        self.assertEqual("1", asset_ids[0])
        self.assertEqual("2", asset_ids[1])
        self.assertEqual("10", asset_ids[2])
        self.assertEqual("C1", asset_ids[3])


@pytest.mark.xfail(reason="Fails on CI for unknown reason", raises=AssertionError)
def test_search(logged_in_browser, admin_user, live_server, test_asset, test_asset_2, category, status, cable_type):
    page = pages.AssetList(logged_in_browser.driver, live_server.url).open()
    page.set_query(test_asset.asset_id)
    page.search()
    assert len(page.assets) == 1
    assert page.assets[0].description == test_asset.description
    assert page.assets[0].id == test_asset.asset_id

    page.set_query(test_asset.description)
    page.search()
    assert len(page.assets) == 1
    assert page.assets[0].description == test_asset.description

    page.set_query("Random string")
    page.search()
    assert len(page.assets) == 0

    page.set_query("")
    page.search()
    # Only working stuff shown by default
    assert len(page.assets) == 1

    page.status_selector.toggle()
    assert page.status_selector.is_open
    page.status_selector.select_all()
    page.status_selector.toggle()
    assert not page.status_selector.is_open
    page.filter()
    assert len(page.assets) == 2

    page.category_selector.toggle()
    assert page.category_selector.is_open
    page.category_selector.set_option(category.name, True)
    page.category_selector.close()
    assert not page.category_selector.is_open
    page.filter()
    assert len(page.assets) == 2


def test_cable_create(logged_in_browser, admin_user, live_server, test_asset, category, status, cable_type):
    page = pages.AssetCreate(logged_in_browser.driver, live_server.url).open()
    wait = WebDriverWait(logged_in_browser.driver, 20)
    page.description = str(cable_type)
    page.category = category.name
    page.status = status.name
    page.serial_number = "MELON-MELON-MELON"
    page.comments = "You might need that"
    page.replacement_cost = "666"
    page.is_cable = True

    assert logged_in_browser.driver.find_element(By.ID, 'cable-table').is_displayed()
    wait.until(animation_is_finished())
    page.cable_type = str(cable_type)
    page.length = 10
    page.csa = "1.5"

    page.submit()
    assert page.success


def test_asset_edit(logged_in_browser, admin_user, live_server, test_asset):
    page = pages.AssetEdit(logged_in_browser.driver, live_server.url, asset_id=test_asset.asset_id).open()

    assert logged_in_browser.driver.find_element(By.ID, 'id_asset_id').get_attribute('readonly') is not None

    new_description = "Big Shelf"
    page.description = new_description

    page.submit()
    assert page.success

    assert models.Asset.objects.get(asset_id=test_asset.asset_id).description == new_description


def test_asset_duplicate(logged_in_browser, admin_user, live_server, test_asset):
    page = pages.AssetDuplicate(logged_in_browser.driver, live_server.url, asset_id=test_asset.asset_id).open()

    assert test_asset.asset_id != page.asset_id
    assert test_asset.description == page.description
    assert test_asset.status.name == page.status
    assert test_asset.category.name == page.category
    assert test_asset.date_acquired == page.date_acquired.date()

    page.submit()
    assert page.success
    assert models.Asset.objects.last().description == test_asset.description


@screenshot_failure_cls
class TestAssetForm(AutoLoginTest):
    def setUp(self):
        super().setUp()
        self.category = models.AssetCategory.objects.create(name="Health & Safety")
        self.status = models.AssetStatus.objects.create(name="O.K.", should_show=True)
        self.supplier = models.Supplier.objects.create(name="Fullmetal Heavy Industry")
        self.parent = models.Asset.objects.create(asset_id="9000", description="Shelf", status=self.status,
                                                  category=self.category, date_acquired=datetime.date(2000, 1, 1))
        self.connector = models.Connector.objects.create(description="IEC", current_rating=10, voltage_rating=240,
                                                         num_pins=3)
        self.cable_type = models.CableType.objects.create(plug=self.connector, socket=self.connector, circuits=1,
                                                          cores=3)
        self.page = pages.AssetCreate(self.driver, self.live_server_url).open()

    def test_asset_create(self):
        # Test that ID is automatically assigned and properly incremented
        # self.assertIn(self.page.asset_id, "9001") FIXME

        self.page.remove_all_required()
        self.page.asset_id = "XX$X"
        self.page.submit()
        self.assertFalse(self.page.success)
        self.assertIn("An Asset ID can only consist of letters and numbers, with a final number",
                      self.page.errors["Asset id"])
        self.assertIn("This field is required.", self.page.errors["Description"])

        self.page.open()

        self.page.description = desc = "Bodge Lead"
        self.page.category = cat = "Health & Safety"
        self.page.status = status = "O.K."
        self.page.serial_number = sn = "0124567890-SAUSAGE"
        self.page.comments = comments = "This is actually a sledgehammer, not a cable..."

        self.page.purchase_price = "12.99"
        self.page.replacement_cost = "99.12"
        self.page.date_acquired = acquired = datetime.date(2020, 5, 2)
        self.page.purchased_from_selector.toggle()
        self.assertTrue(self.page.purchased_from_selector.is_open)
        self.page.purchased_from_selector.search(self.supplier.name[:-8])
        self.page.purchased_from_selector.set_option(self.supplier.name, True)

        self.page.parent_selector.toggle()
        self.assertTrue(self.page.parent_selector.is_open)
        option = self.parent.asset_id
        self.page.parent_selector.search(option)
        time.sleep(2)  # Slow down for javascript
        # self.page.parent_selector.set_option(option, True)
        # self.assertTrue(self.page.parent_selector.options[0].selected)
        self.page.parent_selector.toggle()

        self.assertFalse(self.driver.find_element(By.ID, 'cable-table').is_displayed())

        self.page.submit()
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


def test_audit_search(logged_in_browser, live_server, test_asset):
    page = pages.AssetAuditList(logged_in_browser.driver, live_server.url).open()
    # Check that a failed search works
    page.set_query("NOTFOUND")
    page.search()
    assert not logged_in_browser.find_by_id('modal').visible
    logged_in_browser.driver.implicitly_wait(4)
    assert logged_in_browser.is_text_present("Asset with that ID does not exist!")


def test_audit_success(logged_in_browser, admin_user, live_server, test_asset):
    page = pages.AssetAuditList(logged_in_browser.driver, live_server.url).open()
    wait = WebDriverWait(logged_in_browser.driver, 20)
    page.set_query(test_asset.asset_id)
    page.search()
    wait.until(ec.visibility_of_element_located((By.ID, 'modal')))
    # Now do it properly
    page.modal.description = new_desc = "A BIG hammer"
    page.modal.submit()
    logged_in_browser.driver.implicitly_wait(4)
    wait.until(animation_is_finished())
    submit_time = timezone.now()
    # Check data is correct
    test_asset.refresh_from_db()
    assert test_asset.description in new_desc
    # Make sure audit 'log' was filled out
    assert admin_user.initials == test_asset.last_audited_by.initials
    assert_times_almost_equal(submit_time, test_asset.last_audited_at)
    # Check we've removed it from the 'needing audit' list
    assert test_asset.asset_id not in page.assets


@screenshot_failure_cls
class TestAssetAudit(AutoLoginTest):
    def setUp(self):
        super().setUp()
        self.category = models.AssetCategory.objects.create(name="Haulage")
        self.status = models.AssetStatus.objects.create(name="Probably Fine", should_show=True)
        self.supplier = models.Supplier.objects.create(name="The Bazaar")
        self.connector = models.Connector.objects.create(description="Trailer Socket", current_rating=1,
                                                         voltage_rating=40, num_pins=13)
        models.Asset.objects.create(asset_id="1", description="Trailer Cable", status=self.status,
                                    category=self.category, date_acquired=datetime.date(2020, 2, 1), replacement_cost=10)
        models.Asset.objects.create(asset_id="11", description="Trailerboard", status=self.status,
                                    category=self.category, date_acquired=datetime.date(2020, 2, 1), replacement_cost=10)
        models.Asset.objects.create(asset_id="111", description="Erms", status=self.status, category=self.category,
                                    date_acquired=datetime.date(2020, 2, 1), replacement_cost=10)
        self.asset = models.Asset.objects.create(asset_id="1111", description="A hammer", status=self.status,
                                                 category=self.category,
                                                 date_acquired=datetime.date(2020, 2, 1), replacement_cost=10)
        self.page = pages.AssetAuditList(self.driver, self.live_server_url).open()
        self.wait = WebDriverWait(self.driver, 20)

    def test_audit_fail(self):
        self.page.set_query(self.asset.asset_id)
        self.page.search()
        self.wait.until(ec.visibility_of_element_located((By.ID, 'modal')))
        # Do it wrong on purpose to check error display
        self.page.modal.remove_all_required()
        self.page.modal.description = ""
        self.page.modal.submit()
        self.wait.until(animation_is_finished())
        self.driver.implicitly_wait(4)
        self.assertIn("This field is required.", self.page.modal.errors["Description"])

    def test_audit_list(self):
        self.assertEqual(models.Asset.objects.filter(last_audited_at=None).count(), len(self.page.assets))
        asset_row = self.page.assets[0]
        self.driver.find_element(By.XPATH, "//a[contains(@class,'btn') and contains(., 'Audit')]").click()
        self.wait.until(ec.visibility_of_element_located((By.ID, 'modal')))
        self.assertEqual(self.page.modal.asset_id, asset_row.id)
        self.page.modal.close()
        self.assertFalse(self.driver.find_element(By.ID, 'modal').is_displayed())
        # Make sure audit log was NOT filled out
        audited = models.Asset.objects.get(asset_id=asset_row.id)
        assert audited.last_audited_by is None
