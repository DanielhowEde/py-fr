"""
LoginPOM - Page Object for the login page (Vibium edition).

config.properties keys (all optional):
    login.username.selector     CSS/XPath locator for the username field
    login.password.selector     CSS/XPath locator for the password field
    login.button.selector       CSS/XPath locator for the login button
    login.logout.selector       CSS/XPath locator for the logout link/button
    base.url                    Navigated to before entering credentials
"""

import logging
import time

from vibium.sync_api.page import Page

from pytaf.core.base_page import BasePage
from pytaf.utils.config.config_reader import ConfigReader
from pytaf.utils.credentials.credential_store import CredentialStore

logger = logging.getLogger(__name__)


class LoginPOM(BasePage):
    USERNAME_SELECTOR = ConfigReader.get("login.username.selector", "[name='username'],[name='email']")
    PASSWORD_SELECTOR = ConfigReader.get("login.password.selector", "[name='password'],[type='password']")
    LOGIN_BUTTON_SELECTOR = ConfigReader.get("login.button.selector", "[type='submit']")
    LOGOUT_SELECTOR = ConfigReader.get("login.logout.selector", "[data-testid='logout'],#logout,.logout")

    def __init__(self, page: Page) -> None:
        super().__init__(page)

    def enter_username(self, username: str) -> None:
        self.enter_text_in_field(self.USERNAME_SELECTOR, username)

    def enter_password(self, password: str) -> None:
        self.enter_text_in_field(self.PASSWORD_SELECTOR, password)

    def click_login_button(self) -> None:
        self.click_element_by_locator(self.LOGIN_BUTTON_SELECTOR)

    def login_as_user(self, alias: str) -> None:
        username, password = self._resolve_credentials(alias)
        base_url = ConfigReader.get("base.url", "")
        if base_url:
            self.page.go(base_url)
        self.enter_username(username)
        self.enter_password(password)
        self.click_login_button()

    def login_to_site(self, alias: str) -> None:
        self.login_as_user(alias)

    def log_out(self) -> None:
        try:
            self.click_element_by_locator(self.LOGOUT_SELECTOR)
            logger.info("Logged out successfully")
        except Exception as exc:
            logger.warning("Logout element not found or failed: %s", exc)

    def _resolve_credentials(self, alias: str) -> tuple[str, str]:
        return CredentialStore.get(alias)
