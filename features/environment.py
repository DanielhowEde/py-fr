"""
Behave environment hooks — lifecycle management for jatefr (Vibium edition).

Browser lifecycle:
  before_all    → start Vibium browser, create report directory
  before_scenario → open fresh page, create ScenarioContext
  after_step    → screenshot attached to Allure
  after_scenario → screenshot, attempt logout on failure, close page
  after_all     → stop browser, clean old reports

Environment variables / config.properties keys:
  base.url          Base URL of the system under test
  headless          true | false (default false)
  vibium.connect.url  Remote BiDi URL (optional; blank = launch locally)
  report.name       Name prefix for the test-reports directory
  timeout           Element wait timeout in seconds (default 10)
"""

import logging
import os
import re
import shutil
import time
from datetime import datetime
from pathlib import Path

import allure
from vibium import browser as vib_browser

from jatefr.core.browser_manager import BrowserManager
from jatefr.utils.config.config_reader import ConfigReader
from jatefr.utils.context.scenario_context import ScenarioContext
from jatefr.utils.api import evidence_writer
from jatefr.core.base_page import reset_screenshot_counter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("jatefr.environment")


# ------------------------------------------------------------------
# Suite-level setup / teardown
# ------------------------------------------------------------------

def before_all(context):
    report_name = ConfigReader.get("report.name", "jatefr")
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    report_dir = os.path.join("..", "test-reports", f"{report_name}_{timestamp}")
    Path(report_dir).mkdir(parents=True, exist_ok=True)
    context.report_dir = report_dir
    evidence_writer.set_report_dir(report_dir)
    logger.info("Reports directory: %s", Path(report_dir).resolve())

    # Start the shared browser for the whole suite
    BrowserManager.get_browser()


def after_all(context):
    BrowserManager.stop()
    _cleanup_old_reports(getattr(context, "report_dir", ""))
    logger.info("Suite complete — browser stopped")


# ------------------------------------------------------------------
# Scenario-level setup / teardown
# ------------------------------------------------------------------

def before_scenario(context, scenario):
    context.scenario_ctx = ScenarioContext()
    reset_screenshot_counter()

    # Each scenario gets a fresh page (new tab)
    context.bro = BrowserManager.get_browser()
    context.page = context.bro.new_page()

    # Set viewport to 1920×1080
    context.page.set_viewport({"width": 1920, "height": 1080})

    # @Data_ tag support (mirrors Java @Data_ spreadsheet logic)
    for tag in scenario.tags:
        if tag.startswith("Data_"):
            context.scenario_ctx.set("spreadsheet_tag", tag[5:])

    logger.info(">>> Scenario: %s", scenario.name)


def after_scenario(context, scenario):
    _attach_screenshot(context, f"{scenario.name} — final")

    if scenario.status == "failed":
        logger.warning("FAILED: %s", scenario.name)
        _attempt_logout(context)
    else:
        logger.info("PASSED: %s", scenario.name)

    try:
        context.page.close()
    except Exception as exc:
        logger.warning("Could not close page: %s", exc)


# ------------------------------------------------------------------
# Step-level screenshot (mirrors @AfterStep)
# ------------------------------------------------------------------

def after_step(context, step):
    if not hasattr(context, "page"):
        return
    try:
        png = context.page.screenshot()
        step_label = f"{step.keyword} {step.name}"
        allure.attach(png, name=step_label, attachment_type=allure.attachment_type.PNG)
        if step.status == "failed":
            allure.attach(
                png,
                name=f"FAILURE — {step_label}",
                attachment_type=allure.attachment_type.PNG,
            )
    except Exception as exc:
        logger.warning("Could not capture step screenshot: %s", exc)


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def _attach_screenshot(context, label: str) -> None:
    if not hasattr(context, "page"):
        return
    try:
        png = context.page.screenshot()
        allure.attach(png, name=label, attachment_type=allure.attachment_type.PNG)
    except Exception as exc:
        logger.warning("Could not capture screenshot '%s': %s", label, exc)


def _attempt_logout(context) -> None:
    if not hasattr(context, "page"):
        return
    logout_sel = ConfigReader.get("login.logout.selector", "")
    if not logout_sel:
        return
    try:
        from jatefr.common.pages.login_pom import LoginPOM
        LoginPOM(context.page).log_out()
    except Exception as exc:
        logger.warning("Logout attempt failed: %s", exc)


def _cleanup_old_reports(current_report_dir: str) -> None:
    base = Path("..") / "test-reports"
    if not base.exists():
        return
    pattern = re.compile(r".+_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}$")
    two_days = 2 * 24 * 60 * 60
    now = time.time()
    for d in base.iterdir():
        if not d.is_dir() or not pattern.match(d.name):
            continue
        if current_report_dir and str(d.resolve()) == str(Path(current_report_dir).resolve()):
            continue
        if now - d.stat().st_mtime > two_days:
            try:
                shutil.rmtree(d)
                logger.info("Deleted old report dir: %s", d.name)
            except Exception as exc:
                logger.warning("Could not delete %s: %s", d, exc)
