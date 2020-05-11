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
