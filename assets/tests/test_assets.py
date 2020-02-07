from . import pages
from django.core.management import call_command
from django.test import TestCase
from assets import models
from django.test.utils import override_settings
from django.urls import reverse
from urllib.parse import urlparse
from RIGS import models as rigsmodels
from PyRIGS.tests.base import BaseTest, AutoLoginTest
from assets import models
from reversion import revisions as reversion
from selenium.webdriver.common.keys import Keys
import datetime


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


class TestAssetForm(AutoLoginTest):
    def setUp(self):
        super().setUp()
        self.category = models.AssetCategory.objects.create(name="Health & Safety")
        self.status = models.AssetStatus.objects.create(name="O.K.", should_show=True)
        self.supplier = models.Supplier.objects.create(name="Fullmetal Heavy Industry")
        self.parent = models.Asset.objects.create(asset_id="9000", description="Shelf", status=self.status, category=self.category, date_acquired=datetime.date(2000, 1, 1))
        self.connector = models.Connector.objects.create(description="IEC", current_rating=10, voltage_rating=240, num_pins=3)
        self.page = pages.AssetCreate(self.driver, self.live_server_url).open()

    def test_asset_create(self):
        # Test that ID is automatically assigned and properly incremented
        self.assertIn(self.page.asset_id, "9001")

        self.page.description = "Bodge Lead"
        self.page.category = "Health & Safety"
        self.page.status = "O.K."
        self.page.serial_number = "0124567890-SAUSAGE"
        self.page.comments = "This is actually a sledgehammer, not a cable..."

        self.page.purchased_from_selector.toggle()
        self.assertTrue(self.page.purchased_from_selector.is_open)
        self.page.purchased_from_selector.search(self.supplier.name[:-8])
        self.page.purchased_from_selector.set_option(self.supplier.name, True)
        self.assertFalse(self.page.purchased_from_selector.is_open)
        self.page.purchase_price = "12.99"
        self.page.salvage_value = "99.12"
        self.date_acquired = "05022020"

        self.page.parent_selector.toggle()
        self.assertTrue(self.page.parent_selector.is_open)
        # Searching it by ID autoselects it
        self.page.parent_selector.search(self.parent.asset_id)
        # Needed here but not earlier for whatever reason
        self.driver.implicitly_wait(1)
        # self.page.parent_selector.set_option(self.parent.asset_id + " | " + self.parent.description, True)
        # Need to explicitly close as we haven't selected anything to trigger the auto close
        self.page.parent_selector.search(Keys.ESCAPE)
        self.assertFalse(self.page.parent_selector.is_open)
        self.assertTrue(self.page.parent_selector.options[0].selected)

        self.assertFalse(self.driver.find_element_by_id('cable-table').is_displayed())

        self.page.submit()
        self.assertTrue(self.page.success)

    def test_cable_create(self):
        self.page.description = "IEC -> IEC"
        self.page.category = "Health & Safety"
        self.page.status = "O.K."
        self.page.serial_number = "MELON-MELON-MELON"
        self.page.comments = "You might need that"
        self.page.is_cable = True

        self.assertTrue(self.driver.find_element_by_id('cable-table').is_displayed())
        self.page.plug = "IEC"
        self.page.socket = "IEC"
        self.page.length = 10
        self.page.csa = "1.5"
        self.page.circuits = 1
        self.page.cores = 3

        self.page.submit()
        self.assertTrue(self.page.success)

    def test_asset_edit(self):
        self.page = pages.AssetEdit(self.driver, self.live_server_url, asset_id="9000").open()

        self.assertTrue(self.driver.find_element_by_id('id_asset_id').get_attribute('readonly') is not None)

        new_description = "Big Shelf"
        self.page.description = new_description

        self.page.submit()
        self.assertTrue(self.page.success)

        self.assertEqual(models.Asset.objects.get(asset_id="9000").description, new_description)


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


class TestSupplierCreateAndEdit(AutoLoginTest):
    def setUp(self):
        super().setUp()
        self.supplier = models.Supplier.objects.create(name="Fullmetal Heavy Industry")

    def test_supplier_create(self):
        self.page = pages.SupplierCreate(self.driver, self.live_server_url).open()

        self.page.name = "Optican Health Supplies"
        self.page.submit()
        self.assertTrue(self.page.success)

    def test_supplier_edit(self):
        self.page = pages.SupplierEdit(self.driver, self.live_server_url, supplier_id=self.supplier.pk).open()

        self.assertEquals("Fullmetal Heavy Industry", self.page.name)
        new_name = "Cyberdyne Systems"
        self.page.name = new_name
        self.page.submit()
        self.assertTrue(self.page.success)


class TestSupplierValidation(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.profile = rigsmodels.Profile.objects.create(username="SupplierValidationTest", email="SVT@test.com", is_superuser=True, is_active=True, is_staff=True)
        cls.supplier = models.Supplier.objects.create(name="Gadgetron Corporation")

    def setUp(self):
        self.profile.set_password('testuser')
        self.profile.save()
        self.assertTrue(self.client.login(username=self.profile.username, password='testuser'))

    def test_create(self):
        url = reverse('supplier_create')
        response = self.client.post(url)
        self.assertFormError(response, 'form', 'name', 'This field is required.')

    def test_edit(self):
        url = reverse('supplier_update', kwargs={'pk': self.supplier.pk})
        response = self.client.post(url, {'name': ""})
        self.assertFormError(response, 'form', 'name', 'This field is required.')


# @tag('slow') TODO: req. Django 3.0
class TestAccessLevels(TestCase):
    @override_settings(DEBUG=True)
    def setUp(self):
        super().setUp()
        # Shortcut to create the levels - bonus side effect of testing the command (hopefully) matches production
        call_command('generateSampleData')

    def test_basic_access(self):
        self.assertTrue(self.client.login(username="basic", password="basic"))

        url = reverse('asset_list')
        response = self.client.get(url)
        # Check edit and duplicate buttons not shown in list
        self.assertNotContains(response, 'Edit')
        self.assertNotContains(response, 'Duplicate')

        url = reverse('asset_detail', kwargs={'pk': "9000"})
        response = self.client.get(url)
        self.assertNotContains(response, 'Purchase Details')
        self.assertNotContains(response, 'View Revision History')

        request_url = reverse('asset_update', kwargs={'pk': "9000"})
        response = self.client.get(request_url, follow=True)
        self.assertEqual(response.status_code, 403)

        request_url = reverse('asset_duplicate', kwargs={'pk': "9000"})
        response = self.client.get(request_url, follow=True)
        self.assertEqual(response.status_code, 403)

        request_url = reverse('asset_history', kwargs={'pk': "9000"})
        response = self.client.get(request_url, follow=True)
        self.assertEqual(response.status_code, 403)

        request_url = reverse('supplier_create')
        response = self.client.get(request_url, follow=True)
        self.assertEqual(response.status_code, 403)

        request_url = reverse('supplier_update', kwargs={'pk': "1"})
        response = self.client.get(request_url, follow=True)
        self.assertEqual(response.status_code, 403)

    def test_keyholder_access(self):
        self.assertTrue(self.client.login(username="keyholder", password="keyholder"))

        url = reverse('asset_list')
        response = self.client.get(url)
        # Check edit and duplicate buttons shown in list
        self.assertContains(response, 'Edit')
        self.assertContains(response, 'Duplicate')

        url = reverse('asset_detail', kwargs={'pk': "9000"})
        response = self.client.get(url)
        self.assertContains(response, 'Purchase Details')
        self.assertContains(response, 'View Revision History')

    # def test_finance_access(self): Level not used in assets currently


class TestFormValidation(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.profile = rigsmodels.Profile.objects.create(username="AssetCreateValidationTest", email="acvt@test.com", is_superuser=True, is_active=True, is_staff=True)
        cls.category = models.AssetCategory.objects.create(name="Sound")
        cls.status = models.AssetStatus.objects.create(name="Broken", should_show=True)
        cls.asset = models.Asset.objects.create(asset_id="9999", description="The Office", status=cls.status, category=cls.category, date_acquired=datetime.date(2018, 6, 15))
        cls.connector = models.Connector.objects.create(description="16A IEC", current_rating=16, voltage_rating=240, num_pins=3)
        cls.cable_asset = models.Asset.objects.create(asset_id="666", description="125A -> Jack", comments="The cable from Hell...", status=cls.status, category=cls.category, date_acquired=datetime.date(2006, 6, 6), is_cable=True, plug=cls.connector, socket=cls.connector, length=10, csa="1.5", circuits=1, cores=3)

    def setUp(self):
        self.profile.set_password('testuser')
        self.profile.save()
        self.assertTrue(self.client.login(username=self.profile.username, password='testuser'))

    def test_asset_create(self):
        url = reverse('asset_create')
        response = self.client.post(url, {'date_sold': '2000-01-01', 'date_acquired': '2020-01-01', 'purchase_price': '-30', 'salvage_value': '-30'})
        self.assertFormError(response, 'form', 'asset_id', 'This field is required.')
        self.assertFormError(response, 'form', 'description', 'This field is required.')
        self.assertFormError(response, 'form', 'status', 'This field is required.')
        self.assertFormError(response, 'form', 'category', 'This field is required.')

        self.assertFormError(response, 'form', 'date_sold', 'Cannot sell an item before it is acquired')
        self.assertFormError(response, 'form', 'purchase_price', 'A price cannot be negative')
        self.assertFormError(response, 'form', 'salvage_value', 'A price cannot be negative')

    def test_cable_create(self):
        url = reverse('asset_create')
        response = self.client.post(url, {'asset_id': 'X$%A', 'is_cable': True})
        self.assertFormError(response, 'form', 'asset_id', 'An Asset ID can only consist of letters and numbers, with a final number')

        self.assertFormError(response, 'form', 'plug', 'A cable must have a plug')
        self.assertFormError(response, 'form', 'socket', 'A cable must have a socket')
        self.assertFormError(response, 'form', 'length', 'The length of a cable must be more than 0')
        self.assertFormError(response, 'form', 'csa', 'The CSA of a cable must be more than 0')
        self.assertFormError(response, 'form', 'circuits', 'There must be at least one circuit in a cable')
        self.assertFormError(response, 'form', 'cores', 'There must be at least one core in a cable')

    # Given that validation is done at model level it *shouldn't* need retesting...gonna do it anyway!
    def test_asset_edit(self):
        url = reverse('asset_update', kwargs={'pk': self.asset.asset_id})
        response = self.client.post(url, {'date_sold': '2000-12-01', 'date_acquired': '2020-12-01', 'purchase_price': '-50', 'salvage_value': '-50', 'description': "", 'status': "", 'category': ""})
        # self.assertFormError(response, 'form', 'asset_id', 'This field is required.')
        self.assertFormError(response, 'form', 'description', 'This field is required.')
        self.assertFormError(response, 'form', 'status', 'This field is required.')
        self.assertFormError(response, 'form', 'category', 'This field is required.')

        self.assertFormError(response, 'form', 'date_sold', 'Cannot sell an item before it is acquired')
        self.assertFormError(response, 'form', 'purchase_price', 'A price cannot be negative')
        self.assertFormError(response, 'form', 'salvage_value', 'A price cannot be negative')

    def test_cable_edit(self):
        url = reverse('asset_update', kwargs={'pk': self.cable_asset.asset_id})
        # TODO Why do I have to send is_cable=True here?
        response = self.client.post(url, {'is_cable': True, 'length': -3, 'csa': -3, 'circuits': -4, 'cores': -8})

        # Can't figure out how to select the 'none' option...
        # self.assertFormError(response, 'form', 'plug', 'A cable must have a plug')
        # self.assertFormError(response, 'form', 'socket', 'A cable must have a socket')
        self.assertFormError(response, 'form', 'length', 'The length of a cable must be more than 0')
        self.assertFormError(response, 'form', 'csa', 'The CSA of a cable must be more than 0')
        self.assertFormError(response, 'form', 'circuits', 'There must be at least one circuit in a cable')
        self.assertFormError(response, 'form', 'cores', 'There must be at least one core in a cable')


class TestSampleDataGenerator(TestCase):
    @override_settings(DEBUG=True)
    def test_generate_sample_data(self):
        # Run the management command and check there are no exceptions
        call_command('generateSampleAssetsData')

        # Check there are lots
        self.assertTrue(models.Asset.objects.all().count() > 50)
        self.assertTrue(models.Supplier.objects.all().count() > 50)

    @override_settings(DEBUG=True)
    def test_delete_sample_data(self):
        call_command('deleteSampleData')

        self.assertTrue(models.Asset.objects.all().count() == 0)
        self.assertTrue(models.Supplier.objects.all().count() == 0)

    def test_production_exception(self):
        from django.core.management.base import CommandError

        self.assertRaisesRegex(CommandError, ".*production", call_command, 'generateSampleAssetsData')
        self.assertRaisesRegex(CommandError, ".*production", call_command, 'deleteSampleData')


class TestVersioningViews(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.profile = rigsmodels.Profile.objects.create(username="VersionTest", email="version@test.com", is_superuser=True, is_active=True, is_staff=True)

        working = models.AssetStatus.objects.create(name="Working", should_show=True)
        broken = models.AssetStatus.objects.create(name="Broken", should_show=False)
        general = models.AssetCategory.objects.create(name="General")
        lighting = models.AssetCategory.objects.create(name="Lighting")

        cls.assets = {}

        with reversion.create_revision():
            reversion.set_user(cls.profile)
            cls.assets[1] = models.Asset.objects.create(asset_id="1991", description="Spaceflower", status=broken, category=lighting, date_acquired=datetime.date(1991, 12, 26))

        with reversion.create_revision():
            reversion.set_user(cls.profile)
            cls.assets[2] = models.Asset.objects.create(asset_id="0001", description="Virgil", status=working, category=lighting, date_acquired=datetime.date(2015, 1, 1))

        with reversion.create_revision():
            reversion.set_user(cls.profile)
            cls.assets[1].status = working
            cls.assets[1].save()

    def setUp(self):
        self.profile.set_password('testuser')
        self.profile.save()
        self.assertTrue(self.client.login(username=self.profile.username, password='testuser'))

    def test_history_loads_successfully(self):
        request_url = reverse('asset_history', kwargs={'pk': self.assets[1].asset_id})

        response = self.client.get(request_url, follow=True)
        self.assertEqual(response.status_code, 200)

    def test_activity_table_loads_successfully(self):
        request_url = reverse('asset_activity_table')

        response = self.client.get(request_url, follow=True)
        self.assertEqual(response.status_code, 200)


class TestEmbeddedViews(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.profile = rigsmodels.Profile.objects.create(username="EmbeddedViewsTest", email="embedded@test.com", is_superuser=True, is_active=True, is_staff=True)

        working = models.AssetStatus.objects.create(name="Working", should_show=True)
        lighting = models.AssetCategory.objects.create(name="Lighting")

        cls.assets = {
            1: models.Asset.objects.create(asset_id="1991", description="Spaceflower", status=working, category=lighting, date_acquired=datetime.date(1991, 12, 26))
        }

    def setUp(self):
        self.profile.set_password('testuser')
        self.profile.save()

    def testLoginRedirect(self):
        request_url = reverse('asset_embed', kwargs={'pk': self.assets[1].asset_id})
        expected_url = "{0}?next={1}".format(reverse('login_embed'), request_url)

        # Request the page and check it redirects
        response = self.client.get(request_url, follow=True)
        self.assertRedirects(response, expected_url, status_code=302, target_status_code=200)

        # Now login
        self.assertTrue(self.client.login(username=self.profile.username, password='testuser'))

        # And check that it no longer redirects
        response = self.client.get(request_url, follow=True)
        self.assertEqual(len(response.redirect_chain), 0)

    def testLoginCookieWarning(self):
        login_url = reverse('login_embed')
        response = self.client.post(login_url, follow=True)
        self.assertContains(response, "Cookies do not seem to be enabled")

    def testXFrameHeaders(self):
        asset_url = reverse('asset_embed', kwargs={'pk': self.assets[1].asset_id})
        login_url = reverse('login_embed')

        self.assertTrue(self.client.login(username=self.profile.username, password='testuser'))

        response = self.client.get(asset_url, follow=True)
        with self.assertRaises(KeyError):
            response._headers["X-Frame-Options"]

        response = self.client.get(login_url, follow=True)
        with self.assertRaises(KeyError):
            response._headers["X-Frame-Options"]

    def testOEmbed(self):
        asset_url = reverse('asset_detail', kwargs={'pk': self.assets[1].asset_id})
        asset_embed_url = reverse('asset_embed', kwargs={'pk': self.assets[1].asset_id})
        oembed_url = reverse('asset_oembed', kwargs={'pk': self.assets[1].asset_id})

        alt_oembed_url = reverse('asset_oembed', kwargs={'pk': 999})
        alt_asset_embed_url = reverse('asset_embed', kwargs={'pk': 999})

        # Test the meta tag is in place
        response = self.client.get(asset_url, follow=True, HTTP_HOST='example.com')
        self.assertContains(response, '<link rel="alternate" type="application/json+oembed"')
        self.assertContains(response, oembed_url)

        # Test that the JSON exists
        response = self.client.get(oembed_url, follow=True, HTTP_HOST='example.com')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, asset_embed_url)

        # Should also work for non-existant
        response = self.client.get(alt_oembed_url, follow=True, HTTP_HOST='example.com')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, alt_asset_embed_url)
