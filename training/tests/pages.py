from django.urls import reverse
from pypom import Region
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from PyRIGS.tests import regions
from PyRIGS.tests.pages import BasePage, FormPage

class TraineeDetail(BasePage):
    URL_TEMPLATE = 'trainee/{pk}'

    _name_selector = (By.XPATH, '//h2')

    @property
    def page_name(self):
        return self.find_element(*self._name_selector).text
