from pypom import Region
from selenium.webdriver.common.by import By

from PyRIGS.tests.regions import TextBox, Modal, SimpleMDETextArea


class Header(Region):
    def find_link(self, link_text):
        return self.driver.find_element(By.PARTIAL_LINK_TEXT, link_text)


class ItemRow(Region):
    _name_locator = (By.XPATH, '//span[@class="name"]')
    _description_locator = (By.XPATH, '//div[@class="item-description"]')
    _price_locator = (By.XPATH, '//span[@class="cost"]')
    _quantity_locator = (By.XPATH, '//td[@class="quantity"]')
    _subtotal_locator = (By.XPATH, '//span[@class="sub-total"]')

    @property
    def name(self):
        return self.find_element(*self._name_locator).text

    @property
    def description(self):
        return self.find_element(*self._description_locator).text

    @property
    def price(self):
        return self.find_element(*self._price_locator).text

    @property
    def quantity(self):
        return self.find_element(*self._quantity_locator).text

    @property
    def subtotal(self):
        return self.find_element(*self._subtotal_locator).text


class ItemModal(Modal):
    _header_selector = (By.TAG_NAME, 'h4')

    form_items = {
        'name': (TextBox, (By.ID, 'item_name')),
        'description': (SimpleMDETextArea, (By.ID, 'item_description')),
        'quantity': (TextBox, (By.ID, 'item_quantity')),
        'price': (TextBox, (By.ID, 'item_cost'))
    }
