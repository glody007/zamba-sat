"""List sample directories missing annotation.json.

Used by Claude (in this conversation) to find which samples still need to
be labeled. Print one absolute path per line; pipe into a workflow as needed.

Usage:
    uv run scripts/label_pending.py [run_name]
    # If no run_name is given, uses the most recent run.
"""

from __future__ import annotations

import sys
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "runs"


def latest_run() -> Path:
    runs = sorted([p for p in DATA_DIR.iterdir() if p.is_dir()])
    if not runs:
        raise SystemExit(f"no runs found in {DATA_DIR}")
    return runs[-1]


def main() -> None:
    if len(sys.argv) > 1:
        run_dir = DATA_DIR / sys.argv[1]
    else:
        run_dir = latest_run()
    if not run_dir.exists():
        raise SystemExit(f"run dir not found: {run_dir}")

    pending: list[Path] = []
    for meta in sorted(run_dir.rglob("metadata.json")):
        sample_dir = meta.parent
        if (sample_dir / "annotation.json").exists():
            continue
        pending.append(sample_dir)

    print(f"# run: {run_dir.name}")
    print(f"# pending: {len(pending)}")
    for p in pending:
        print(p)


if __name__ == "__main__":
    main()
