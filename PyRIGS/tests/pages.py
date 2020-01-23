from pypom import Page
from selenium.webdriver.common.by import By


class BasePage(Page):
    _user_locator = (By.CSS_SELECTOR, "#user>a")


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
