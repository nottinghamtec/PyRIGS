from pypom import Page, Region
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver import Chrome
from django.urls import reverse
from PyRIGS.tests import regions
from RIGS.tests import regions as rigs_regions
from PyRIGS.tests.pages import BasePage, FormPage
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support import expected_conditions as EC

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


class CreateEvent(FormPage):
    URL_TEMPLATE = reverse('event_create')

    _is_rig_selector = (By.ID, 'is_rig-selector')
    _bottom_save_selector = (By.XPATH, '//*[@id="main"]/form/div/div[6]/div/button')
    _submit_locator = _bottom_save_selector
    # TODO The ID is now no longer on the highest level element on the selector, annoyingly
    _person_selector_selector = (By.XPATH, '//*[@id="main"]/form/div/div[3]/div[1]/div[2]/div[1]/div/div/div[1]/div')
    _venue_selector_selector = (By.XPATH, '//*[@id="main"]/form/div/div[3]/div[1]/div[2]/div[1]/div/div/div[1]/div')
    _mic_selector_selector = (By.XPATH, '//*[@id="form-hws"]/div[7]/div[1]/div/div')

    _add_person_selector = (By.XPATH, '//a[@data-target="#id_person" and contains(@href, "add")]')
    _add_item_selector = (By.XPATH, '//button[contains(@class, "item-add")]')
    
    _event_table_selector = (By.ID, 'item-table')
    _warning_selector = (By.XPATH, '/html/body/div[1]/div[1]')

    form_items = {
        'description': (regions.TextBox, (By.ID, 'id_description')),

        'name': (regions.TextBox, (By.ID, 'id_name')),
        'start_date': (regions.DatePicker, (By.ID, 'id_start_date')),
        'start_time': (regions.TimePicker, (By.ID, 'id_start_time')),
        'end_date': (regions.DatePicker, (By.ID, 'id_start_date')),
        'end_time': (regions.TimePicker, (By.ID, 'id_start_time')),
        'access_at': (regions.DateTimePicker, (By.ID, 'id_access_at')),
        'meet_at': (regions.DateTimePicker, (By.ID, 'id_meet_at')),
        'dry_hire': (regions.CheckBox, (By.ID, 'id_dry_hire')),
        'status': (regions.SingleSelectPicker, (By.ID, 'id_status')),
        'collected_by': (regions.TextBox, (By.ID, 'id_collector')),
        'po': (regions.TextBox, (By.ID, 'id_purchase_order')),

        'notes': (regions.TextBox, (By.ID, 'id_notes'))
    }

    def select_event_type(self, type_name):
        self.find_element(By.XPATH, '//button[.="' + type_name + '"]').click()

    def item_row(self, ID):
        return rigs_regions.ItemRow(self, self.find_element(By.ID, "item-" + ID))
    
    @property
    def item_table(self):
        return self.find_element(*self._event_table_selector)
    
    @property
    def warning(self):
        return self.find_element(*self._warning_selector).text

    @property
    def is_expanded(self):
        return self.find_element(*self._bottom_save_selector).is_displayed()

    @property
    def person_selector(self):
        return regions.BootstrapSelectElement(self, self.find_element(*self._person_selector_selector))

    @property
    def venue_selector(self):
        return regions.BootstrapSelectElement(self, self.find_element(*self._venue_selector_selector))

    @property
    def mic_selector(self):
        return regions.BootstrapSelectElement(self, self.find_element(*self._mic_selector_selector))

    def add_person(self):
        self.find_element(*self._add_person_selector).click()
        return regions.Modal(self, self.driver.find_element_by_id('modal'))

    def add_event_item(self):
        self.find_element(*self._add_item_selector).click()
        element = self.driver.find_element_by_id('itemModal')
        self.wait.until(EC.visibility_of(element))
        return regions.ItemModal(self, element)

    @property
    def success(self):
        return '/create' not in self.driver.current_url
    
class DuplicateEvent(CreateEvent):
    URL_TEMPLATE = 'event/{event_id}/duplicate'
    _submit_locator = (By.XPATH, '/html/body/div[1]/form/div/div[5]/div/button')
    
    @property
    def success(self):
        return '/duplicate' not in self.driver.current_url

class GenericList(BasePage):
    _search_selector = (By.CSS_SELECTOR, 'div.input-group:nth-child(2) > input:nth-child(1)')
    _search_go_selector = (By.ID, 'id_search')
    _add_item_selector = (By.CSS_SELECTOR, '.btn-success')

