"""Safe access to the source snapshots in data/repos/.

The tools you build in the notebook let the model choose a repo and a path.
The model's choice can be steered by issue text, which is untrusted (W1, and
again in W8). So every path the model gives goes through `source_dir`, which
keeps it inside the snapshot: no absolute paths, no `..`, no symlinks out.
The snapshot is read-only and nothing here runs a shell.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from triage_lab.data import ROOT

__all__ = ["RepoName", "SOURCE_SUFFIXES", "cap", "entries", "source_dir"]

REPOS_DIR = ROOT / "data" / "repos"

# The repos the tools accept. A Literal, so the model can only pick a real one.
RepoName = Literal["litestar", "hono", "textual"]

# Each project keeps its own layout, so the paths match what GitHub shows.
SOURCE_ROOTS: dict[str, str] = {
    "litestar": "litestar/litestar",
    "hono": "hono/src",
    "textual": "textual/src/textual",
}

SOURCE_SUFFIXES = (".py", ".ts", ".tsx")


def source_dir(repo: str, path: str = "") -> Path:
    """Return the folder `path` inside `repo`'s source, or raise ValueError."""
    if repo not in SOURCE_ROOTS:
        raise ValueError(f"unknown repo {repo!r}; choose one of {sorted(SOURCE_ROOTS)}")
    root = (REPOS_DIR / SOURCE_ROOTS[repo]).resolve()
    clean = path.strip().strip("/")
    if Path(clean).is_absolute() or ".." in Path(clean).parts:
        raise ValueError(f"path must be relative and inside the repo: {path!r}")
    target = (root / clean).resolve()
    if not target.is_relative_to(root):
        raise ValueError(f"path leaves the repo: {path!r}")
    if not target.is_dir():
        raise ValueError(f"no such folder in {repo}: {path!r}")
    return target


def entries(folder: Path) -> list[str]:
    """Sub-folders (with a trailing '/') and source files of one folder, sorted.

    Skips hidden entries, caches and __init__.py, which say nothing about
    components.
    """
    names: list[str] = []
    for child in sorted(folder.iterdir()):
        if child.name.startswith((".", "__")):
            continue
        if child.is_dir():
            names.append(child.name + "/")
        elif child.suffix in SOURCE_SUFFIXES:
            names.append(child.name)
    return names


def cap(items: list[str], max_results: int) -> list[str]:
    """Keep at most `max_results` items and say how many were cut."""
    if len(items) <= max_results:
        return items
    return items[:max_results] + [f"... and {len(items) - max_results} more"]
