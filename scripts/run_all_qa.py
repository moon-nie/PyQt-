"""Gridloom QA smoke tests 일괄 실행."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent
    scripts = [
        "qa_operations_smoke.py",
        "qa_loader_smoke.py",
        "grid_smoke.py",
    ]
    failed: list[str] = []
    for name in scripts:
        path = root / name
        print(f"--- {name} ---")
        result = subprocess.run([sys.executable, str(path)], cwd=root.parent)
        if result.returncode != 0:
            failed.append(name)
    if failed:
        print(f"FAILED: {', '.join(failed)}")
        return 1
    print("run_all_qa: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
