"""
Reusable Behave environment hooks for pytaf.

This module contains all lifecycle hook logic so that multiple projects
can share the same framework.  Each project's ``features/environment.py``
imports these hooks — Behave discovers them by name.

Usage (in a project's features/environment.py):

    import sys
    from pathlib import Path

    _FRAMEWORK_ROOT = Path(__file__).resolve().parents[3]   # adjust depth
    if str(_FRAMEWORK_ROOT) not in sys.path:
        sys.path.insert(0, str(_FRAMEWORK_ROOT))

    from pytaf.core.environment_hooks import (          # noqa: F401
        before_all, after_all,
        before_scenario, after_scenario,
        after_step,
    )
"""

import logging
import os
import re
import shutil
import time
from datetime import datetime
from pathlib import Path

import allure
from dotenv import load_dotenv

from pytaf.core.browser_manager import BrowserManager
from pytaf.utils.config.config_reader import ConfigReader
from pytaf.utils.context.scenario_context import ScenarioContext
from pytaf.utils.api import evidence_writer
from pytaf.core.base_page import reset_screenshot_counter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("pytaf.environment")


# ------------------------------------------------------------------
# Suite-level setup / teardown
# ------------------------------------------------------------------

def before_all(context):
    # Load .env from the working directory (project root)
    load_dotenv()

    report_name = ConfigReader.get("report.name", "pytaf")
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    report_dir = os.path.join("test-reports", f"{report_name}_{timestamp}")
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

    # Spreadsheet tag support
    # @test_<name>     → run rows where test == <name>
    # @testfile_<name> → run all tests in <name>.xlsx
    for tag in scenario.tags:
        if tag.startswith("testfile_"):
            context.scenario_ctx.set("spreadsheet_tag", tag[9:])
            context.scenario_ctx.set("spreadsheet_mode", "all")
        elif tag.startswith("test_"):
            context.scenario_ctx.set("spreadsheet_tag", tag[5:])
            context.scenario_ctx.set("spreadsheet_mode", "test")

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
        from pytaf.common.pages.login_pom import LoginPOM
        LoginPOM(context.page).log_out()
    except Exception as exc:
        logger.warning("Logout attempt failed: %s", exc)


def _cleanup_old_reports(current_report_dir: str) -> None:
    base = Path("test-reports")
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
