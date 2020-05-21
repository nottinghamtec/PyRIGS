from pypom import Region
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.select import Select
import datetime


class Header(Region):
    def find_link(self, link_text):
        return self.driver.find_element_by_partial_link_text(link_text)


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
