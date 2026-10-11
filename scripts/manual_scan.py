from __future__ import annotations

from scheduler.runner import ScanRunner


def main() -> None:
    runner = ScanRunner(report_dir="reports")
    result = runner.run_once()
    print(result)
    if result.get("report_path"):
        print(f"Research artifact written to: {result['report_path']}")


if __name__ == "__main__":
    main()
