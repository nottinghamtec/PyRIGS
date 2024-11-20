from django.urls import reverse
from pypom import Region
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from PyRIGS.tests import regions
from PyRIGS.tests.pages import BasePage, FormPage
from RIGS.tests import regions as rigs_regions


class Index(BasePage):
    URL_TEMPLATE = reverse('index')


class Rigboard(BasePage):
    URL_TEMPLATE = reverse('rigboard')

    _add_item_selector = (By.XPATH, "//a[contains(@class,'btn-primary') and contains(., 'New')]")
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


class EventDetail(BasePage):
    URL_TEMPLATE = 'event/{event_id}'

    # TODO Refactor into regions to match template fragmentation
    _event_name_selector = (By.XPATH, '//h2')
    _person_panel_selector = (By.XPATH, '//div[contains(text(), "Person Details")]/..')
    _name_selector = (By.XPATH, '//dt[text()="Person"]/following-sibling::dd[1]')
    _email_selector = (By.XPATH, '//dt[text()="Email"]/following-sibling::dd[1]')
    _phone_selector = (By.XPATH, '//dt[text()="Phone Number"]/following-sibling::dd[1]')
    _event_table_selector = (By.ID, 'item-table')

    @property
    def event_name(self):
        return self.find_element(*self._event_name_selector).text

    @property
    def name(self):
        return self.find_element(*self._person_panel_selector).find_element(*self._name_selector).text

    @property
    def email(self):
        return self.find_element(*self._person_panel_selector).find_element(*self._email_selector).text

    @property
    def phone(self):
        return self.find_element(*self._person_panel_selector).find_element(*self._phone_selector).text

    @property
    def item_table(self):
        return self.find_element(*self._event_table_selector)


class CreateEvent(FormPage):
    URL_TEMPLATE = reverse('event_create')

    _is_rig_selector = (By.ID, 'is_rig-selector')
    _submit_locator = (By.XPATH, "//button[@type='submit' and contains(., 'Save')]")
    _person_selector_selector = (By.XPATH, '//*[@id="id_person"]/..')
    _venue_selector_selector = (By.XPATH, '//*[@id="id_venue"]/..')
    _mic_selector_selector = (By.XPATH, '//*[@id="form-hws"]/div[7]/div[1]/div/div')

    _add_person_selector = (By.XPATH, '//a[@data-target="#id_person" and contains(@href, "add")]')
    _add_item_selector = (By.XPATH, '//button[contains(@class, "item-add")]')

    _event_table_selector = (By.ID, 'item-table')
    _warning_selector = (By.XPATH, '/html/body/div[1]/div[1]')

    form_items = {
        'description': (regions.SimpleMDETextArea, (By.ID, 'id_description')),

        'name': (regions.TextBox, (By.ID, 'id_name')),
        'start_date': (regions.DatePicker, (By.ID, 'id_start_date')),
        'start_time': (regions.TimePicker, (By.ID, 'id_start_time')),
        'end_date': (regions.DatePicker, (By.ID, 'id_end_date')),
        'end_time': (regions.TimePicker, (By.ID, 'id_end_time')),
        'access_at': (regions.DateTimePicker, (By.ID, 'id_access_at')),
        'meet_at': (regions.DateTimePicker, (By.ID, 'id_meet_at')),
        'dry_hire': (regions.CheckBox, (By.ID, 'id_dry_hire')),
        'status': (regions.SingleSelectPicker, (By.ID, 'id_status')),
        'collected_by': (regions.TextBox, (By.ID, 'id_collector')),
        'po': (regions.TextBox, (By.ID, 'id_purchase_order')),

        'notes': (regions.SimpleMDETextArea, (By.ID, 'id_notes'))
    }

    def select_event_type(self, type_name):
        self.find_element(By.XPATH, f'//button[.="{type_name}"]').click()

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
        return self.find_element(*self._submit_locator).is_displayed()

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
        return regions.Modal(self, self.driver.find_element(By.ID, 'modal'))

    def add_event_item(self):
        self.find_element(*self._add_item_selector).click()
        element = self.driver.find_element(By.ID, 'itemModal')
        self.wait.until(EC.visibility_of(element))
        return rigs_regions.ItemModal(self, element)

    @property
    def success(self):
        return '/create' not in self.driver.current_url


class DuplicateEvent(CreateEvent):
    URL_TEMPLATE = 'event/{event_id}/duplicate'

    @property
    def success(self):
        return '/duplicate' not in self.driver.current_url


class EditEvent(CreateEvent):
    URL_TEMPLATE = 'event/{event_id}/edit'

    @property
    def success(self):
        return '/edit' not in self.driver.current_url


class CreateRiskAssessment(FormPage):
    URL_TEMPLATE = 'event/{event_id}/ra/'

    _submit_locator = (By.XPATH, "//button[@type='submit' and contains(., 'Save')]")
    _power_mic_selector = (By.CSS_SELECTOR, ".bootstrap-select")

    form_items = {
        'nonstandard_equipment': (regions.RadioSelect, (By.ID, 'id_nonstandard_equipment')),
        'nonstandard_use': (regions.RadioSelect, (By.ID, 'id_nonstandard_use')),
        'contractors': (regions.RadioSelect, (By.ID, 'id_contractors')),
        'other_companies': (regions.RadioSelect, (By.ID, 'id_other_companies')),
        'crew_fatigue': (regions.RadioSelect, (By.ID, 'id_crew_fatigue')),
        'general_notes': (regions.TextBox, (By.ID, 'id_general_notes')),
        'big_power': (regions.RadioSelect, (By.ID, 'id_big_power')),
        'outside': (regions.RadioSelect, (By.ID, 'id_outside')),
        'generators': (regions.RadioSelect, (By.ID, 'id_generators')),
        'other_companies_power': (regions.RadioSelect, (By.ID, 'id_other_companies_power')),
        'nonstandard_equipment_power': (regions.RadioSelect, (By.ID, 'id_nonstandard_equipment_power')),
        'multiple_electrical_environments': (regions.RadioSelect, (By.ID, 'id_multiple_electrical_environments')),
        'power_notes': (regions.TextBox, (By.ID, 'id_power_notes')),
        'noise_monitoring': (regions.RadioSelect, (By.ID, 'id_noise_monitoring')),
        'sound_notes': (regions.TextBox, (By.ID, 'id_sound_notes')),
        'known_venue': (regions.RadioSelect, (By.ID, 'id_known_venue')),
        'safe_loading': (regions.RadioSelect, (By.ID, 'id_safe_loading')),
        'safe_storage': (regions.RadioSelect, (By.ID, 'id_safe_storage')),
        'area_outside_of_control': (regions.RadioSelect, (By.ID, 'id_area_outside_of_control')),
        'barrier_required': (regions.RadioSelect, (By.ID, 'id_barrier_required')),
        'nonstandard_emergency_procedure': (regions.RadioSelect, (By.ID, 'id_nonstandard_emergency_procedure')),
        'special_structures': (regions.RadioSelect, (By.ID, 'id_special_structures')),
        'persons_responsible_structures': (regions.TextBox, (By.ID, 'id_persons_responsible_structures')),
        'suspended_structures': (regions.RadioSelect, (By.ID, 'id_suspended_structures')),
        'supervisor_consulted': (regions.CheckBox, (By.ID, 'id_supervisor_consulted')),
        'rigging_plan': (regions.TextBox, (By.ID, 'id_rigging_plan')),
        'parking_and_access': (regions.RadioSelect, (By.ID, 'id_parking_and_access')),
    }

    @property
    def power_mic(self):
        return regions.BootstrapSelectElement(self, self.find_element(*self._power_mic_selector))

    @property
    def success(self):
        return '/event/ra' in self.driver.current_url


class EditRiskAssessment(CreateRiskAssessment):
    URL_TEMPLATE = 'event/ra/{pk}/edit'

    @property
    def success(self):
        return '/edit' not in self.driver.current_url


class CreateEventChecklist(FormPage):
    URL_TEMPLATE = 'event/{event_id}/checklist'

    _submit_locator = (By.XPATH, "//button[@type='submit' and contains(., 'Save')]")

    form_items = {
        'safe_parking': (regions.CheckBox, (By.ID, 'id_safe_parking')),
        'safe_packing': (regions.CheckBox, (By.ID, 'id_safe_packing')),
        'exits': (regions.CheckBox, (By.ID, 'id_exits')),
        'trip_hazard': (regions.CheckBox, (By.ID, 'id_trip_hazard')),
        'warning_signs': (regions.CheckBox, (By.ID, 'id_warning_signs')),
        'ear_plugs': (regions.CheckBox, (By.ID, 'id_ear_plugs')),
        'hs_location': (regions.TextBox, (By.ID, 'id_hs_location')),
        'extinguishers_location': (regions.TextBox, (By.ID, 'id_extinguishers_location')),
    }

    @property
    def success(self):
        return '{event_id}' not in self.driver.current_url


class CreatePowerTestRecord(FormPage):
    URL_TEMPLATE = 'event/{event_id}/power'

    _submit_locator = (By.XPATH, "//button[@type='submit' and contains(., 'Save')]")
    _power_mic_selector = (By.XPATH, "//div[select[@id='id_power_mic']]")

    form_items = {
        'rcds': (regions.CheckBox, (By.ID, 'id_rcds')),
        'supply_test': (regions.CheckBox, (By.ID, 'id_supply_test')),
        'earthing': (regions.CheckBox, (By.ID, 'id_earthing')),
        'pat': (regions.CheckBox, (By.ID, 'id_pat')),
        'source_rcd': (regions.CheckBox, (By.ID, 'id_source_rcd')),
        'labelling': (regions.CheckBox, (By.ID, 'id_labelling')),
        'fd_voltage_l1': (regions.TextBox, (By.ID, 'id_fd_voltage_l1')),
        'fd_voltage_l2': (regions.TextBox, (By.ID, 'id_fd_voltage_l2')),
        'fd_voltage_l3': (regions.TextBox, (By.ID, 'id_fd_voltage_l3')),
        'fd_phase_rotation': (regions.CheckBox, (By.ID, 'id_fd_phase_rotation')),
        'fd_earth_fault': (regions.TextBox, (By.ID, 'id_fd_earth_fault')),
        'fd_pssc': (regions.TextBox, (By.ID, 'id_fd_pssc')),
        'w1_description': (regions.TextBox, (By.ID, 'id_w1_description')),
        'w1_polarity': (regions.CheckBox, (By.ID, 'id_w1_polarity')),
        'w1_voltage': (regions.TextBox, (By.ID, 'id_w1_voltage')),
        'w1_earth_fault': (regions.TextBox, (By.ID, 'id_w1_earth_fault')),
    }

    @property
    def power_mic(self):
        return regions.BootstrapSelectElement(self, self.find_element(*self._power_mic_selector))

    @property
    def success(self):
        return '{event_id}' not in self.driver.current_url


class EditEventChecklist(CreateEventChecklist):
    URL_TEMPLATE = '/event/checklist/{pk}/edit'

    @property
    def success(self):
        return 'edit' not in self.driver.current_url


class GenericList(BasePage):
    _search_selector = (By.CSS_SELECTOR, 'div.input-group:nth-child(2) > input:nth-child(1)')
    _search_go_selector = (By.ID, 'id_search')
    _add_item_selector = (By.CSS_SELECTOR, '.btn-success')


class UserPage(BasePage):
    URL_TEMPLATE = 'user/'

    _api_key_selector = (By.ID, 'api-key')
    _cal_url_selector = (By.ID, 'cal-url')
    _generation_button_selector = (By.LINK_TEXT, 'Generate API Key')

    @property
    def api_key(self):
        return self.find_element(*self._api_key_selector).text

    @property
    def cal_url(self):
        return self.find_element(*self._cal_url_selector).text

    def toggle_filter(self, type_name):
        self.find_element(By.XPATH, "//input[@value='" + type_name + "']").click()

    def generate_key(self):
        self.find_element(*self._generation_button_selector).click()


class CalendarPage(BasePage):
    URL_TEMPLATE = 'rigboard/calendar'

    _go_locator = (By.ID, 'go-to-date-button')

    _today_selector = (By.ID, 'today-button')

    _prev_selector = (By.ID, 'prev-button')
    _next_selector = (By.ID, 'next-button')

    _month_selector = (By.ID, 'month-button')
    _week_selector = (By.ID, 'week-button')
    _day_selector = (By.ID, 'day-button')

    def go(self):
        return self.find_element(*self._go_locator).click()

    @property
    def target_date(self):
        return regions.DatePicker(self, self.find_element(By.ID, 'go-to-date-input'))

    def today(self):
        return self.find_element(*self._today_selector).click()

    def prev(self):
        return self.find_element(*self._prev_selector).click()

    def next(self):
        return self.find_element(*self._next_selector).click()

    def month(self):
        return self.find_element(*self._month_selector).click()

    def week(self):
        return self.find_element(*self._week_selector).click()

    def day(self):
        return self.find_element(*self._day_selector).click()
