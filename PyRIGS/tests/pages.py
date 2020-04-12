from pypom import Page, Region
from selenium.webdriver.common.by import By
from selenium.webdriver import Chrome
from selenium.common.exceptions import NoSuchElementException


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

    def remove_all_required(self):
        self.driver.execute_script(
            "Array.from(document.getElementsByTagName(\"input\")).forEach(function (el, ind, arr) { el.removeAttribute(\"required\")});")
        self.driver.execute_script(
            "Array.from(document.getElementsByTagName(\"select\")).forEach(function (el, ind, arr) { el.removeAttribute(\"required\")});")

    @property
    def errors(self):
        try:
            error_page = self.ErrorPage(self, self.find_element(*self._errors_selector))
            return error_page.errors
        except NoSuchElementException:
            return None

    class ErrorPage(Region):
        _error_item_selector = (By.CSS_SELECTOR, "dl>span")

        class ErrorItem(Region):
            _field_selector = (By.CSS_SELECTOR, "dt")
            _error_selector = (By.CSS_SELECTOR, "dd>ul>li")

            @property
            def field_name(self):
                return self.find_element(*self._field_selector).text

            @property
            def errors(self):
                return [x.text for x in self.find_elements(*self._error_selector)]

        @property
        def errors(self):
            error_items = [self.ErrorItem(self, x) for x in self.find_elements(*self._error_item_selector)]
            errors = {}
            for error in error_items:
                errors[error.field_name] = error.errors
            return errors


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
