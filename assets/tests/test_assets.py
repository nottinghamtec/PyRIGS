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


class AssetCreateTests(AutoLoginTest):
    def setUp(self):
        super().setUp()
        self.category = models.AssetCategory.objects.create(name="Health & Safety")
        self.status = models.AssetStatus.objects.create(name="O.K.", should_show=True)
        self.supplier = models.Supplier.objects.create(name="Fullmetal Heavy Industry")
        self.parent = models.Asset.objects.create(asset_id="9000", description="Shelf", status=self.status, category=self.category, date_acquired=datetime.date(2000, 1, 1))
        self.page = pages.AssetCreate(self.driver, self.live_server_url).open()

    def test_asset_form(self):
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
        self.driver.implicitly_wait(3)
        # self.page.parent_selector.set_option(self.parent.asset_id + " | " + self.parent.description, True)
        # Need to explicitly close as we haven't selected anything to trigger the auto close
        self.page.parent_selector.search(Keys.ESCAPE)
        self.assertFalse(self.page.parent_selector.is_open)
        self.assertTrue(self.page.parent_selector.options[0].selected)

        self.assertFalse(self.driver.find_element_by_id('cable-table').is_displayed())

        self.page.submit()
        self.assertTrue(self.page.success)

class TestSampleDataGenerator(TestCase):
    @override_settings(DEBUG=True)
    def test_generate_sample_data(self):
        # Run the management command and check there are no exceptions
        call_command('generateSampleAssetsData')

        # Check there are lots
        self.assertTrue(models.Asset.objects.all().count() > 50)
        self.assertTrue(models.Supplier.objects.all().count() > 50)

    def test_production_exception(self):
        from django.core.management.base import CommandError

        self.assertRaisesRegex(CommandError, ".*production", call_command, 'generateSampleAssetsData')


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
