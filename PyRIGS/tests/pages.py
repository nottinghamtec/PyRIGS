from pypom import Page
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By

from PyRIGS.tests import regions


class BasePage(Page):
    form_items = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __getattr__(self, name):
        if name in self.form_items:
            element = self.form_items[name]
            form_element = element[0](self, self.find_element(*element[1]))
            return form_element.value
        else:
            return super().__getattribute__(name)

    def __setattr__(self, name, value):
        if name in self.form_items:
            element = self.form_items[name]
            form_element = element[0](self, self.find_element(*element[1]))
            form_element.set_value(value)
        else:
            self.__dict__[name] = value


class FormPage(BasePage):
    _errors_selector = (By.CLASS_NAME, "alert-danger")
    _submit_locator = (By.XPATH, "//button[@type='submit' and contains(., 'Save')]")

    def remove_all_required(self):
        self.driver.execute_script(
            "Array.from(document.getElementsByTagName(\"input\")).forEach(function (el, ind, arr) { el.removeAttribute(\"required\")});")
        self.driver.execute_script(
            "Array.from(document.getElementsByTagName(\"select\")).forEach(function (el, ind, arr) { el.removeAttribute(\"required\")});")

    def submit(self):
        previous_errors = self.errors
        submit = self.find_element(*self._submit_locator)
        ActionChains(self.driver).move_to_element(submit).perform()
        submit.click()
        self.wait.until(animation_is_finished())
        self.wait.until(lambda x: self.errors != previous_errors or self.success)

    @property
    def errors(self):
        try:
            error_page = regions.ErrorPage(self, self.find_element(*self._errors_selector))
            return error_page.errors
        except NoSuchElementException:
            return None


class LoginPage(BasePage):
    URL_TEMPLATE = '/user/login'

    _username_locator = (By.ID, 'id_username')
    _password_locator = (By.ID, 'id_password')
    _submit_locator = (By.ID, 'id_submit')
    _error_locator = (By.CSS_SELECTOR, '.errorlist>li')

    def login(self, username, password):
        username_element = self.find_element(*self._username_locator)
        username_element.clear()
        username_element.send_keys(username)

        password_element = self.find_element(*self._password_locator)
        password_element.clear()
        password_element.send_keys(password)

        self.find_element(*self._submit_locator).click()


class animation_is_finished():
    def __call__(self, driver):
        number_animating = driver.execute_script('return $(":animated").length')
        finished = number_animating == 0
        if finished:
            import time
            time.sleep(0.1)
        return finished
