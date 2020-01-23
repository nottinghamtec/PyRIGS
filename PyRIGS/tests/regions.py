from pypom import Region
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait


def parse_bool_from_string(string):
    # Used to convert from attribute strings to boolean values, written after I found this:
    # >>> bool("false")
    # True
    if string == "true":
        return True
    else:
        return False


class BootstrapSelectElement(Region):
    _main_button_locator = (By.CSS_SELECTOR, 'button.dropdown-toggle')
    _option_box_locator = (By.CSS_SELECTOR, 'ul.dropdown-menu')
    _option_locator = (By.CSS_SELECTOR, 'ul.dropdown-menu.inner>li>a[role=option]')
    _select_all_locator = (By.CLASS_NAME, 'bs-select-all')
    _deselect_all_locator = (By.CLASS_NAME, 'bs-deselect-all')

    @property
    def is_open(self):
        return parse_bool_from_string(self.find_element(*self._main_button_locator).get_attribute("aria-expanded"))

    def toggle(self):
        original_state = self.is_open
        return self.find_element(*self._main_button_locator).click()
        option_box = self.find_element(*self._option_box_locator)
        if original_state:
            self.wait.until(expected_conditions.invisibility_of_element_located(option_box))
        else:
            self.wait.until(expected_conditions.visibility_of_element_located(option_box))

    def open(self):
        if not self.is_open:
            self.toggle()

    def close(self):
        if self.is_open:
            self.toggle()

    def select_all(self):
        self.find_element(*self._select_all_locator).click()

    def deselect_all(self):
        self.find_element(*self._deselect_all_locator).click()

    @property
    def options(self):
        options = list(self.find_elements(*self._option_locator))
        return [self.BootstrapSelectOption(self, i) for i in options]

    def set_option(self, name, selected):
        options = (x for x in self.options if x.name == name)
        for option in options:
            option.set_selected(selected)

    class BootstrapSelectOption(Region):
        _text_locator = (By.CLASS_NAME, 'text')

        @property
        def selected(self):
            return parse_bool_from_string(self.root.get_attribute("aria-selected"))

        def toggle(self):
            self.root.click()

        def set_selected(self, selected):
            if self.selected != selected:
                self.toggle()

        @property
        def name(self):
            return self.find_element(*self._text_locator).text
