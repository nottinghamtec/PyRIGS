# Collection of page object models for use within tests.
from pypom import Page, Region
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver import Chrome
from django.urls import reverse
from PyRIGS.tests import regions
from PyRIGS.tests.pages import BasePage, FormPage
import pdb


class AssetList(BasePage):
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


class AssetForm(FormPage):
    _purchased_from_select_locator = (By.CSS_SELECTOR, 'div#purchased-from-group>div.bootstrap-select')
    _parent_select_locator = (By.CSS_SELECTOR, 'div#parent-group>div.bootstrap-select')
    _submit_locator = (By.CLASS_NAME, 'btn-success')
    form_items = {
        'asset_id': (regions.TextBox, (By.ID, 'id_asset_id')),
        'description': (regions.TextBox, (By.ID, 'id_description')),
        'is_cable': (regions.CheckBox, (By.ID, 'id_is_cable')),
        'serial_number': (regions.TextBox, (By.ID, 'id_serial_number')),
        'comments': (regions.TextBox, (By.ID, 'id_comments')),
        'purchase_price': (regions.TextBox, (By.ID, 'id_purchase_price')),
        'salvage_value': (regions.TextBox, (By.ID, 'id_salvage_value')),
        'date_acquired': (regions.DatePicker, (By.ID, 'id_date_acquired')),
        'date_sold': (regions.DatePicker, (By.ID, 'id_date_sold')),
        'category': (regions.SingleSelectPicker, (By.ID, 'id_category')),
        'status': (regions.SingleSelectPicker, (By.ID, 'id_status')),

        'cable_type': (regions.SingleSelectPicker, (By.ID, 'id_cable_type')),
        'length': (regions.TextBox, (By.ID, 'id_length')),
        'csa': (regions.TextBox, (By.ID, 'id_csa')),
    }

    @property
    def purchased_from_selector(self):
        return regions.BootstrapSelectElement(self, self.find_element(*self._purchased_from_select_locator))

    @property
    def parent_selector(self):
        return regions.BootstrapSelectElement(self, self.find_element(*self._parent_select_locator))

    def submit(self):
        previous_errors = self.errors
        self.find_element(*self._submit_locator).click()
        self.wait.until(lambda x: self.errors != previous_errors or self.success)


class AssetEdit(AssetForm):
    URL_TEMPLATE = '/assets/asset/id/{asset_id}/edit/'

    @property
    def success(self):
        return '/edit' not in self.driver.current_url


class AssetCreate(AssetForm):
    URL_TEMPLATE = '/assets/asset/create/'

    @property
    def success(self):
        return '/create' not in self.driver.current_url


class AssetDuplicate(AssetForm):
    URL_TEMPLATE = '/assets/asset/id/{asset_id}/duplicate'

    @property
    def success(self):
        return '/duplicate' not in self.driver.current_url


class SupplierList(BasePage):
    URL_TEMPLATE = reverse('supplier_list')

    _supplier_item_locator = (By.CLASS_NAME, 'supplierRow')
    _search_text_locator = (By.ID, 'id_query')
    _go_button_locator = (By.ID, 'id_search')

    class SupplierListRow(Region):
        _name_locator = (By.CLASS_NAME, "supplierName")

        @property
        def name(self):
            return self.find_element(*self._name_locator).text

    @property
    def suppliers(self):
        return [self.SupplierListRow(self, i) for i in self.find_elements(*self._supplier_item_locator)]

    @property
    def query(self):
        return self.find_element(*self._search_text_locator).text

    def set_query(self, queryString):
        element = self.find_element(*self._search_text_locator)
        element.clear()
        element.send_keys(queryString)

    def search(self):
        self.find_element(*self._go_button_locator).click()


class SupplierForm(FormPage):
    _submit_locator = (By.CLASS_NAME, 'btn-success')
    form_items = {
        'name': (regions.TextBox, (By.ID, 'id_name')),
    }

    def submit(self):
        previous_errors = self.errors
        self.find_element(*self._submit_locator).click()
        self.wait.until(lambda x: self.errors != previous_errors or self.success)


class SupplierCreate(SupplierForm):
    URL_TEMPLATE = reverse('supplier_create')

    @property
    def success(self):
        return '/create' not in self.driver.current_url


class SupplierEdit(SupplierForm):
    # TODO This should be using reverse
    URL_TEMPLATE = '/assets/supplier/{supplier_id}/edit'

    @property
    def success(self):
        return '/edit' not in self.driver.current_url
