"""
Behave environment hooks — delegates to pytaf shared hooks.

This file exists at the repo root for backward compatibility (single-project mode).
All hook logic lives in pytaf.core.environment_hooks.
"""

from pytaf.core.environment_hooks import (  # noqa: F401
    before_all,
    after_all,
    before_scenario,
    after_scenario,
    after_step,
)
