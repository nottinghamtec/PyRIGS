from django.urls import reverse
from pypom import Region
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from PyRIGS.tests import regions
from PyRIGS.tests.pages import BasePage, FormPage


class TraineeDetail(BasePage):
    URL_TEMPLATE = 'training/trainee/{pk}'

    _name_selector = (By.XPATH, '//h2')

    @property
    def page_name(self):
        return self.find_element(*self._name_selector).text


class AddQualification(FormPage):
    URL_TEMPLATE = 'training/trainee/{pk}/add_qualification/'

    _item_selector = (By.XPATH, '//div[1]/form/div[1]/div')
    _supervisor_selector = (By.XPATH, '//div[1]/form/div[3]/div')

    form_items = {
        'depth': (regions.SingleSelectPicker, (By.ID, 'id_depth')),
        'date': (regions.DatePicker, (By.ID, 'id_date')),
        'notes': (regions.TextBox, (By.ID, 'id_notes')),
    }

    @property
    def item_selector(self):
        return regions.BootstrapSelectElement(self, self.find_element(*self._item_selector))

    @property
    def supervisor_selector(self):
        return regions.BootstrapSelectElement(self, self.find_element(*self._supervisor_selector))

    @property
    def success(self):
        return 'add' not in self.driver.current_url


class SessionLog(FormPage):
    URL_TEMPLATE = 'training/session_log'

    _supervisor_selector = (By.CSS_SELECTOR, 'div#supervisor_group>div.bootstrap-select')
    _trainees_selector = (By.CSS_SELECTOR, 'div#trainees_group>div.bootstrap-select')
    _training_started_selector = (By.XPATH, '//div[1]/div/div/form/div[4]/div')
    _training_complete_selector = (By.XPATH, '//div[1]/div/div/form/div[4]/div')
    _competency_assessed_selector = (By.XPATH, '//div[1]/div/div/form/div[5]/div')

    form_items = {
        'date': (regions.DatePicker, (By.ID, 'id_date')),
        'notes': (regions.TextBox, (By.ID, 'id_notes')),
    }

    @property
    def supervisor_selector(self):
        return regions.BootstrapSelectElement(self, self.find_element(*self._supervisor_selector))

    @property
    def trainees_selector(self):
        return regions.BootstrapSelectElement(self, self.find_element(*self._trainees_selector))

    @property
    def training_started_selector(self):
        return regions.BootstrapSelectElement(self, self.find_element(*self._training_started_selector))

    @property
    def training_complete_selector(self):
        return regions.BootstrapSelectElement(self, self.find_element(*self._training_complete_selector))

    @property
    def competency_assessed_selector(self):
        return regions.BootstrapSelectElement(self, self.find_element(*self._competency_assessed_selector))

    @property
    def success(self):
        return 'log' not in self.driver.current_url
