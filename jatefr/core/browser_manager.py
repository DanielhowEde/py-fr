"""
BrowserManager - singleton Vibium browser lifecycle manager.

Replaces driver_manager.py (Selenium) with Vibium.

Usage:
    from jatefr.core.browser_manager import BrowserManager

    bro  = BrowserManager.get_browser()
    page = BrowserManager.get_page()
    BrowserManager.stop()
"""

import threading
import logging

from vibium import browser as vib_browser
from vibium.sync_api.browser import Browser
from vibium.sync_api.page import Page

from jatefr.utils.config.config_reader import ConfigReader

logger = logging.getLogger(__name__)


class BrowserManager:
    _browser: Browser | None = None
    _page: Page | None = None
    _lock = threading.Lock()

    @classmethod
    def get_browser(cls) -> Browser:
        if cls._browser is None:
            with cls._lock:
                if cls._browser is None:
                    headless = ConfigReader.get_bool("headless", False)
                    connect_url = ConfigReader.get("vibium.connect.url", "")
                    cls._browser = vib_browser.start(
                        url=connect_url or None,
                        headless=headless,
                    )
                    logger.info("Vibium browser started (headless=%s)", headless)
        return cls._browser

    @classmethod
    def get_page(cls) -> Page:
        if cls._page is None:
            with cls._lock:
                if cls._page is None:
                    cls._page = cls.get_browser().page()
        return cls._page

    @classmethod
    def new_page(cls) -> Page:
        """Open a fresh tab (useful for multi-page scenarios)."""
        return cls.get_browser().new_page()

    @classmethod
    def stop(cls) -> None:
        with cls._lock:
            if cls._browser is not None:
                try:
                    cls._browser.stop()
                    logger.info("Vibium browser stopped")
                except Exception as exc:
                    logger.error("Failed to stop browser: %s", exc)
                finally:
                    cls._browser = None
                    cls._page = None

    # ------------------------------------------------------------------
    # Back-compat alias — environment.py calls quit_driver()
    # ------------------------------------------------------------------
    @classmethod
    def quit_driver(cls) -> None:
        cls.stop()
