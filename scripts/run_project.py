"""
Run a pytaf project by name.

Usage:
    python scripts/run_project.py <project>  [behave args...]
    python scripts/run_project.py example
    python scripts/run_project.py myapp      --tags=@smoke
    python scripts/run_project.py myapp      -f pretty

The script changes into ``projects/<project>/`` and runs Behave with the
framework root on PYTHONPATH so that ``import pytaf`` works everywhere.
"""

import os
import subprocess
import sys
from pathlib import Path


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    projects_dir = repo_root / "projects"

    if len(sys.argv) < 2:
        available = sorted(
            p.name
            for p in projects_dir.iterdir()
            if p.is_dir() and (p / "features").exists()
        ) if projects_dir.exists() else []
        print("Usage: python scripts/run_project.py <project> [behave args...]")
        print(f"Available projects: {', '.join(available) or '(none)'}")
        sys.exit(1)

    project_name = sys.argv[1]
    project_dir = projects_dir / project_name

    if not project_dir.exists():
        print(f"Project not found: {project_dir}")
        sys.exit(1)
    if not (project_dir / "features").exists():
        print(f"No features/ directory in {project_dir}")
        sys.exit(1)

    behave_args = sys.argv[2:]
    env = {**os.environ, "PYTHONPATH": str(repo_root)}

    result = subprocess.run(
        [sys.executable, "-m", "behave"] + behave_args,
        cwd=str(project_dir),
        env=env,
    )
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
