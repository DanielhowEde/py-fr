"""
Behave environment hooks for this project.

Adds the framework root to sys.path so pytaf is importable, then
re-exports all lifecycle hooks from the shared module.
"""

import sys
from pathlib import Path

# Framework root is two levels above this project folder
# projects/example/features/environment.py  →  repo root
_FRAMEWORK_ROOT = Path(__file__).resolve().parents[3]
if str(_FRAMEWORK_ROOT) not in sys.path:
    sys.path.insert(0, str(_FRAMEWORK_ROOT))

from pytaf.core.environment_hooks import (  # noqa: F401, E402
    before_all,
    after_all,
    before_scenario,
    after_scenario,
    after_step,
)
