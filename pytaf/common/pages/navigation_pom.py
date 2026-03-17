"""
NavigationPOM - navigation helpers (Vibium edition).
"""

import logging

from vibium.sync_api.page import Page

from pytaf.core.base_page import BasePage
from pytaf.utils.config.config_reader import ConfigReader

logger = logging.getLogger(__name__)


class NavigationPOM(BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self._base_url = ConfigReader.get("base.url", "")

    def navigate_to(self, link: str) -> None:
        if link.startswith("http://") or link.startswith("https://"):
            self.page.go(link)
        else:
            url = self._base_url.rstrip("/") + "/" + link.lstrip("/")
            self.page.go(url)
        logger.debug("Navigated to: %s", link)

    def wait_for(self, seconds: int) -> None:
        self.page.wait(seconds * 1000)
