"""Convert a run directory into leap-finetune VLM SFT JSONL (stub)."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    raise SystemExit(
        "prepare_finetune.py is a stub. TODO: emit leap-finetune-format JSONL "
        "(train.jsonl, test.jsonl) referencing rgb_t1, swir_t1, rgb_t0, swir_t0 "
        "with the SYSTEM_PROMPT/USER_TEXT_TEMPLATE as the input and "
        "annotation.json as the assistant output."
    )


if __name__ == "__main__":
    main()
