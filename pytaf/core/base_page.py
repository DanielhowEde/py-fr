"""
BasePage - UI interaction helpers built on Vibium.

Replaces the Selenium-based implementation with Vibium's Page/Element API.
All methods preserve the same names as the Java original so existing Gherkin
step definitions continue to work without changes.

Locator rules (same convention as before):
    Strings starting with // or (//  → XPath  → page.find(xpath=locator)
    Everything else                  → CSS     → page.find(locator)
"""

import logging
import re
from datetime import datetime
from pathlib import Path

from vibium.sync_api.page import Page
from vibium.sync_api.element import Element

from pytaf.utils.config.config_reader import ConfigReader

logger = logging.getLogger(__name__)

_screenshot_counter = 0


def reset_screenshot_counter() -> None:
    global _screenshot_counter
    _screenshot_counter = 0


class BasePage:
    def __init__(self, page: Page) -> None:
        self.page = page
        # Vibium timeouts are in milliseconds
        self.timeout_ms = ConfigReader.get_int("timeout", 10) * 1000

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find(self, locator: str) -> Element:
        if locator.startswith("//") or locator.startswith("(//"):
            return self.page.find(xpath=locator, timeout=self.timeout_ms)
        return self.page.find(locator, timeout=self.timeout_ms)

    def _find_all(self, locator: str) -> list[Element]:
        if locator.startswith("//") or locator.startswith("(//"):
            return self.page.find_all(xpath=locator, timeout=self.timeout_ms)
        return self.page.find_all(locator, timeout=self.timeout_ms)

    # ------------------------------------------------------------------
    # Click
    # ------------------------------------------------------------------

    def click_element_by_locator(self, locator: str) -> None:
        self._find(locator).click(timeout=self.timeout_ms)
        logger.debug("Clicked: %s", locator)

    def double_click_element(self, locator: str) -> None:
        self._find(locator).dblclick(timeout=self.timeout_ms)

    def right_click_element(self, locator: str) -> None:
        self._find(locator).dispatch_event("contextmenu")

    # ------------------------------------------------------------------
    # Text input
    # ------------------------------------------------------------------

    def enter_text_in_field(self, locator: str, text: str) -> None:
        """Clear then fill a field (Vibium fill = clear + type)."""
        self._find(locator).fill(text, timeout=self.timeout_ms)

    def clear_text_field(self, locator: str) -> None:
        self._find(locator).clear(timeout=self.timeout_ms)

    def get_input_field_value(self, locator: str) -> str:
        return self._find(locator).value() or ""

    # ------------------------------------------------------------------
    # Dropdowns
    # ------------------------------------------------------------------

    def select_dropdown_option_by_text(self, locator: str, value: str) -> None:
        self._find(locator).select_option(value, timeout=self.timeout_ms)

    def select_option_from_dynamic_list(
        self, input_locator: str, list_items_locator: str, value_to_select: str
    ) -> None:
        self.enter_text_in_field(input_locator, value_to_select)
        items = self._find_all(list_items_locator)
        for item in items:
            if item.text().strip() == value_to_select:
                item.click()
                return
        raise ValueError(f"Option '{value_to_select}' not found in dynamic list")

    # ------------------------------------------------------------------
    # Checkbox
    # ------------------------------------------------------------------

    def set_checkbox_checked_state(self, locator: str, should_be_checked: bool) -> None:
        el = self._find(locator)
        if should_be_checked:
            el.check(timeout=self.timeout_ms)
        else:
            el.uncheck(timeout=self.timeout_ms)

    # ------------------------------------------------------------------
    # Visibility checks
    # ------------------------------------------------------------------

    def is_element_visible(self, locator: str) -> bool:
        try:
            el = self._find(locator)
            return el.is_visible()
        except Exception:
            return False

    def wait_until_element_visible(self, locator: str, should_be_visible: bool = True) -> None:
        state = "visible" if should_be_visible else "hidden"
        self._find(locator).wait_until(state, timeout=self.timeout_ms)

    def wait_until_text_appears(self, locator: str, expected_text: str) -> None:
        """Poll until element text matches expected."""
        import time
        deadline = time.time() + self.timeout_ms / 1000
        while time.time() < deadline:
            try:
                if expected_text in self._find(locator).text():
                    return
            except Exception:
                pass
            time.sleep(0.5)
        raise TimeoutError(f"Text '{expected_text}' did not appear in '{locator}'")

    # ------------------------------------------------------------------
    # Text retrieval
    # ------------------------------------------------------------------

    def get_text_from_element(self, locator: str) -> str:
        return self._find(locator).text()

    def get_tooltip_from_element(self, locator: str) -> str:
        return self._find(locator).attr("title") or ""

    # ------------------------------------------------------------------
    # Toast / Modal
    # ------------------------------------------------------------------

    def get_toast_popup_message(self, toast_locator: str) -> str:
        return self.get_text_from_element(toast_locator)

    def focus_on_modal(self, modal_locator: str) -> None:
        self._find(modal_locator).scroll_into_view(timeout=self.timeout_ms)

    def close_modal_window(self, close_button_locator: str) -> None:
        self.click_element_by_locator(close_button_locator)

    # ------------------------------------------------------------------
    # JS Alerts / Dialogs
    # ------------------------------------------------------------------

    def handle_java_script_alert(self, action: str, input_text: str = "") -> None:
        """Register a one-shot dialog handler for the next alert/confirm/prompt.

        Call this BEFORE the action that triggers the dialog.
        action: 'accept' | 'dismiss' | 'input'
        """
        if action.lower() in ("accept", "input"):
            self.page.on_dialog("accept")
        else:
            self.page.on_dialog("dismiss")

    # ------------------------------------------------------------------
    # Scroll / Hover / Highlight
    # ------------------------------------------------------------------

    def scroll_to_element_by_locator(self, locator: str) -> None:
        self._find(locator).scroll_into_view(timeout=self.timeout_ms)

    def scroll_to_web_element(self, element: Element) -> None:
        element.scroll_into_view()

    def hover_on_element(self, locator: str) -> None:
        self._find(locator).hover(timeout=self.timeout_ms)

    def highlight_element_border(self, locator: str) -> None:
        safe = locator.replace("'", "\\'")
        self.page.evaluate(
            f"document.querySelector('{safe}').style.border='3px solid red'"
        )

    # ------------------------------------------------------------------
    # Screenshots
    # ------------------------------------------------------------------

    def capture_screenshot(self, screenshot_name: str) -> str:
        global _screenshot_counter
        _screenshot_counter += 1
        screenshots_dir = Path("screenshots")
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        safe_name = re.sub(r"[^a-zA-Z0-9_\-]", "_", screenshot_name)
        ts = datetime.now().strftime("%H%M%S_%f")[:10]
        filename = screenshots_dir / f"{_screenshot_counter:03d}_{safe_name}_{ts}.png"
        png_bytes = self.page.screenshot()
        filename.write_bytes(png_bytes)
        logger.info("Screenshot saved: %s", filename)
        return str(filename)
