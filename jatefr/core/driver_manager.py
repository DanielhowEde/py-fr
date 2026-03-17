"""
Compatibility shim — re-exports BrowserManager as DriverManager.
Import from browser_manager directly for new code.
"""
from jatefr.core.browser_manager import BrowserManager as DriverManager  # noqa: F401
