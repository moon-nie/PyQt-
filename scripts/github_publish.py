"""GitHub에 push 없이 업로드 (Git 설치 불필요).

사용법 (PowerShell):
  $env:GITHUB_TOKEN = "ghp_xxxxxxxx"   # repo 권한 있는 PAT
  python scripts/github_publish.py

토큰 발급: GitHub → Settings → Developer settings → Personal access tokens
  권한: repo (또는 Fine-grained: Contents Read and write)
"""
from __future__ import annotations

import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

OWNER = "moon-nie"
REPO = "PyQt-"
BRANCH = "main"
COMMIT_MESSAGE = "chore: add LICENSE, .gitignore, README; remove __pycache__"

ROOT = Path(__file__).resolve().parent.parent

SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "ENV",
    "__pycache__",
    ".vscode",
    ".idea",
    "node_modules",
}
SKIP_FILES = {".DS_Store", "Thumbs.db", "github_publish.py"}


def _token() -> str:
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not tok:
        print("ERROR: GITHUB_TOKEN 환경 변수가 없습니다.", file=sys.stderr)
        print("  $env:GITHUB_TOKEN = \"ghp_...\"", file=sys.stderr)
        sys.exit(1)
    return tok.strip()


def _api(method: str, path: str, data: dict | None = None) -> dict | list | None:
    url = f"https://api.github.com{path}"
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {_token()}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "gridloom-publish-script",
        },
    )
    if body is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read()
            if not raw:
                return None
            return json.loads(raw.decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        print(f"API {method} {path} → HTTP {exc.code}\n{detail}", file=sys.stderr)
        sys.exit(1)


def _collect_files() -> list[Path]:
    files: list[Path] = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if rel.name in SKIP_FILES:
            continue
        if rel.parts[0] == "scripts" and rel.name == "github_publish.py":
            continue
        files.append(path)
    return files


def _create_blob(content: bytes) -> str:
    result = _api(
        "POST",
        f"/repos/{OWNER}/{REPO}/git/blobs",
        {"content": base64.b64encode(content).decode("ascii"), "encoding": "base64"},
    )
    assert isinstance(result, dict)
    return result["sha"]


def main() -> int:
    print(f"Uploading {OWNER}/{REPO} ({BRANCH}) …")

    ref = _api("GET", f"/repos/{OWNER}/{REPO}/git/ref/heads/{BRANCH}")
    assert isinstance(ref, dict)
    parent_sha = ref["object"]["sha"]

    parent_commit = _api("GET", f"/repos/{OWNER}/{REPO}/git/commits/{parent_sha}")
    assert isinstance(parent_commit, dict)

    local_files = _collect_files()
    print(f"  local files: {len(local_files)}")

    tree_entries = []
    for i, path in enumerate(local_files, 1):
        rel = path.relative_to(ROOT).as_posix()
        content = path.read_bytes()
        blob_sha = _create_blob(content)
        tree_entries.append({"path": rel, "mode": "100644", "type": "blob", "sha": blob_sha})
        if i % 10 == 0 or i == len(local_files):
            print(f"  blobs {i}/{len(local_files)}")

    tree = _api(
        "POST",
        f"/repos/{OWNER}/{REPO}/git/trees",
        {"tree": tree_entries},
    )
    assert isinstance(tree, dict)
    new_tree_sha = tree["sha"]

    commit = _api(
        "POST",
        f"/repos/{OWNER}/{REPO}/git/commits",
        {
            "message": COMMIT_MESSAGE,
            "tree": new_tree_sha,
            "parents": [parent_sha],
        },
    )
    assert isinstance(commit, dict)
    new_commit_sha = commit["sha"]

    _api(
        "PATCH",
        f"/repos/{OWNER}/{REPO}/git/refs/heads/{BRANCH}",
        {"sha": new_commit_sha, "force": False},
    )

    _api(
        "PATCH",
        f"/repos/{OWNER}/{REPO}",
        {
            "description": "Gridloom — PyQt6 desktop tabular data workbench for CSV/Excel viewing, editing, and data wrangling.",
            "homepage": "",
        },
    )

    print(f"Done: https://github.com/{OWNER}/{REPO}/commit/{new_commit_sha}")
    print("  → __pycache__ 제거, LICENSE/.gitignore/README/sample_data 반영")
    print("  → GitHub 웹에서 Topics 추가: pyqt6, pandas, tabular-data, data-wrangling")
    return 0


if __name__ == "__main__":
    sys.exit(main())
