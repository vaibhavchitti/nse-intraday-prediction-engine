from __future__ import annotations

from pathlib import Path


def ensure_project_dirs() -> None:
    for directory in [
        "data",
        "data/providers",
        "tests",
        "scripts",
    ]:
        Path(directory).mkdir(parents=True, exist_ok=True)
