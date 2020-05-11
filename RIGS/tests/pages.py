from pypom import Page, Region
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver import Chrome
from django.urls import reverse
from PyRIGS.tests import regions
from PyRIGS.tests.pages import BasePage, FormPage
from selenium.common.exceptions import NoSuchElementException

class Index(BasePage):
    URL_TEMPLATE = reverse('index')


class Rigboard(BasePage):
    URL_TEMPLATE = reverse('rigboard')

    _add_item_selector = (By.CSS_SELECTOR, 'a.btn:nth-child(2)')
    _event_row_locator = (By.ID, 'event_row')

    def add(self):
        self.find_element(*self._add_item_selector).click()

    class EventListRow(Region):
        _event_number_locator = (By.ID, "event_number")
        _event_dates_locator = (By.ID, "event_dates")
        _event_details_locator = (By.ID, "event_details")
        _event_mic_locator = (By.ID, "event_mic")

        @property
        def id(self):
            return self.find_element(*self._event_number_locator).text

        @property
        def dates(self):
            return self.find_element(*self._event_dates_locator).text

        @property
        def details(self):
            return self.find_element(*self._event_details_locator).text

        @property
        def mic(self):
            return self.find_element(*self._event_mic_locator).text

    @property
    def events(self):
        return [self.EventListRow(self, i) for i in self.find_elements(*self._event_row_locator)]


class GenericList(BasePage):
    _search_selector = (By.CSS_SELECTOR, 'div.input-group:nth-child(2) > input:nth-child(1)')
    _search_go_selector = (By.ID, 'id_search')
    _add_item_selector = (By.CSS_SELECTOR, '.btn-success')

