"""Load the issue snapshot.

The issues come from snapshot (data/snapshot/). They are divided into three sources:

  dev    every score you see in this lab
  train  examples for one-shot and for the optimizer (Part 3, Part 7)
  test   SEALED. Not loaded here, not opened, not tuned against. It is used
         later in the course, and its only value is that nobody has seen it.

SECURITY: issue text's come from public repos, and are written by strangers on the internet. It should be treated as data,
not LLM instructions.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from triage_lab.schema import ExtendedIssue, Issue

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_DIR = ROOT / "data" / "snapshot"

Source = Literal["train", "dev"]


def load_issues(source: Source) -> list[Issue]:
    """The issues of data/snapshot/<source>.json as the model sees them, in file order."""
    return [issue.to_issue() for issue in load_extended_issues(source)]


def load_extended_issues(source: Source) -> list[ExtendedIssue]:
    """The issues of data/snapshot/<source>.json with every field, in file order."""
    if source not in ("train", "dev"):
        raise ValueError(f"source must be 'train' or 'dev', not {source!r} (test is sealed)")
    path = SNAPSHOT_DIR / f"{source}.json"
    return [ExtendedIssue(**raw) for raw in json.loads(path.read_text(encoding="utf-8"))]
