from __future__ import annotations

from pathlib import Path


def ensure_project_dirs() -> None:
    root = Path(__file__).resolve().parents[1]
    for rel_path in [
        "data/raw",
        "data/providers",
        "tests",
        "scripts",
    ]:
        (root / rel_path).mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    ensure_project_dirs()
    print("Project directories ensured.")
