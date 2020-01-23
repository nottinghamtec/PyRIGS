# Collection of page object models for use within tests.
from pypom import Page, Region
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from django.urls import reverse
from PyRIGS.tests import regions
from PyRIGS.tests.pages import BasePage
import pdb


class AssetListPage(BasePage):
    URL_TEMPLATE = '/assets/asset/list'

    _asset_item_locator = (By.CLASS_NAME, 'assetRow')
    _search_text_locator = (By.ID, 'id_query')
    _status_select_locator = (By.CSS_SELECTOR, 'div#status-group>div.bootstrap-select')
    _category_select_locator = (By.CSS_SELECTOR, 'div#category-group>div.bootstrap-select')
    _go_button_locator = (By.ID, 'filter-submit')

    class AssetListRow(Region):
        _asset_id_locator = (By.CLASS_NAME, "assetID")
        _asset_description_locator = (By.CLASS_NAME, "assetDesc")
        _asset_category_locator = (By.CLASS_NAME, "assetCategory")
        _asset_status_locator = (By.CLASS_NAME, "assetStatus")

        @property
        def id(self):
            return self.find_element(*self._asset_id_locator).text

        @property
        def description(self):
            return self.find_element(*self._asset_description_locator).text

        @property
        def category(self):
            return self.find_element(*self._asset_category_locator).text

        @property
        def status(self):
            return self.find_element(*self._asset_status_locator).text

    @property
    def assets(self):
        return [self.AssetListRow(self, i) for i in self.find_elements(*self._asset_item_locator)]

    @property
    def query(self):
        return self.find_element(*self._search_text_locator).text

    def set_query(self, queryString):
        element = self.find_element(*self._search_text_locator)
        element.clear()
        element.send_keys(queryString)

    def search(self):
        self.find_element(*self._go_button_locator).click()

    @property
    def status_selector(self):
        return regions.BootstrapSelectElement(self, self.find_element(*self._status_select_locator))

    @property
    def category_selector(self):
        return regions.BootstrapSelectElement(self, self.find_element(*self._category_select_locator))
