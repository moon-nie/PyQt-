"""Gridloom QA smoke tests 일괄 실행."""
from __future__ import annotations

import subprocess
import sys
import os
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent
    project_root = root.parent
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root) + os.pathsep + env.get("PYTHONPATH", "")
    scripts = [
        "qa_operations_smoke.py",
        "qa_analysis_smoke.py",
        "qa_analysis_panel_smoke.py",
        "qa_mainwindow_smoke.py",
        "qa_loader_smoke.py",
        "qa_viewer_smoke.py",
        "grid_smoke.py",
    ]
    failed: list[str] = []
    for name in scripts:
        path = root / name
        print(f"--- {name} ---")
        result = subprocess.run([sys.executable, str(path)], cwd=project_root, env=env)
        if result.returncode != 0:
            failed.append(name)
    if failed:
        print(f"FAILED: {', '.join(failed)}")
        return 1
    print("run_all_qa: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
