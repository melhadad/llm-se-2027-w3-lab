"""Pre-lab environment check. Run this BEFORE the session, not during it.

    uv run python tools/verify_env.py

It prints a report and saves the same report to outputs/setup-check-<your-name>.txt.
Commit and push that file, then submit your repo URL in Moodle. In a pair,
each partner runs this on their own machine, with their own key, and pushes
their own file.

Setup that fails in the room costs the whole room time, which is why this is
homework.

Checks, in order of how often they fail:
  1. Python >= 3.13
  2. uv-managed environment with dependencies resolved
  3. notebook kernel: ipykernel installed in this project's .venv
  4. .env exists and is NOT tracked by git
  5. exactly one model provider key present, matching LLM_MODEL
  6. the model key actually works (one tiny live call)
  7. git identity configured
  8. pre-commit hook installed (blocks committing keys)
  9. lab data present (issue snapshot and source snapshots)
"""

from __future__ import annotations

import os
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = ROOT / "outputs"

PROVIDERS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "xai": "XAI_API_KEY",
}

PASS, FAIL, WARN = "PASS", "FAIL", "WARN"
results: list[tuple[str, str, str]] = []
lines: list[str] = []


def say(text: str = "") -> None:
    print(text)
    lines.append(text)


def check(name: str, status: str, detail: str = "") -> None:
    results.append((name, status, detail))
    symbol = {PASS: "  ok  ", FAIL: " FAIL ", WARN: " warn "}[status]
    say(f"[{symbol}] {name}" + (f" - {detail}" if detail else ""))


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    path = ROOT / ".env"
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip("\"'")
    return env


def looks_placeholder(value: str) -> bool:
    return (not value) or "xxxx" in value.lower()


def git_config(key: str) -> str:
    return subprocess.run(["git", "config", key], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def main() -> int:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    say("llm-se-2027 W3 lab - environment check")
    say(f"{platform.system()} {platform.release()} | python {sys.version.split()[0]} | {stamp}\n")

    # 1. Python
    major, minor = sys.version_info[:2]
    if (major, minor) >= (3, 13):
        check("python >= 3.13", PASS, f"{major}.{minor}")
    else:
        check("python >= 3.13", FAIL, f"found {major}.{minor}; run `uv sync`")

    # 2. dependencies
    try:
        import dspy
        import pydantic  # noqa: F401

        check("dependencies importable", PASS, f"dspy {dspy.__version__}")
    except ImportError as exc:
        check("dependencies importable", FAIL, f"{exc}; run `uv sync`")

    try:
        import triage_lab  # noqa: F401

        check("lab helpers importable", PASS, "triage_lab")
    except ImportError:
        check("lab helpers importable", FAIL, "run `uv sync` in the repo folder")

    # 3. notebook kernel
    #
    # VSCode runs the notebook with the interpreter you pick as its kernel.
    # It must be this project's .venv, and that interpreter needs ipykernel.
    in_venv = Path(sys.prefix).resolve() == (ROOT / ".venv").resolve()
    try:
        import ipykernel  # noqa: F401

        has_kernel = True
    except ImportError:
        has_kernel = False
    if in_venv and has_kernel:
        check("notebook kernel", PASS, "ipykernel in .venv - pick .venv as the kernel in VSCode")
    elif not in_venv:
        check("notebook kernel", FAIL, f"not running from this repo's .venv ({sys.prefix}); use `uv run`")
    else:
        check("notebook kernel", FAIL, "ipykernel missing; run `uv sync`")

    # 4. .env present and untracked
    env = load_env()
    if not env:
        check(".env present", FAIL, "copy .env.example to .env")
    else:
        check(".env present", PASS, f"{len(env)} entries")

    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", ".env"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if tracked.returncode == 0:
        check(".env untracked", FAIL, "your .env IS TRACKED. `git rm --cached .env` now, then rotate every key in it")
    else:
        check(".env untracked", PASS)

    # 5. exactly one provider
    model = env.get("LLM_MODEL", "")
    present = [p for p, k in PROVIDERS.items() if not looks_placeholder(env.get(k, ""))]
    if not present:
        check("model provider key", FAIL, "no real key found; fill in exactly one")
    elif len(present) > 1:
        check("model provider key", WARN, f"{len(present)} keys set ({', '.join(present)}); only LLM_MODEL is used")
    else:
        check("model provider key", PASS, present[0])

    provider = model.split("/", 1)[0] if "/" in model else ""
    if model == "offline":
        check("LLM_MODEL matches key", FAIL, "LLM_MODEL=offline is for rehearsal; set a real model for this check")
    elif provider and present and provider not in present:
        check("LLM_MODEL matches key", FAIL, f"LLM_MODEL is {provider!r} but you set {present[0]!r} key")
    elif provider:
        check("LLM_MODEL matches key", PASS, model)
    else:
        check("LLM_MODEL matches key", FAIL, "LLM_MODEL missing or malformed (expected provider/model)")

    # 6. live model call, through the same code the notebook uses
    if present and provider in present:
        try:
            from triage_lab.lm import connect

            os.environ[PROVIDERS[provider]] = env[PROVIDERS[provider]]  # .env wins over the shell
            lm = connect()
            reply = lm("Reply with the single word: ready")
            text = reply[0] if isinstance(reply, list) else str(reply)
            check("live model call", PASS, str(text).strip()[:40])
        except Exception as exc:  # noqa: BLE001 - report anything, this is a smoke test
            check("live model call", FAIL, f"{type(exc).__name__}: {str(exc)[:120]}")
    else:
        check("live model call", FAIL, "skipped - fix the key first")

    # 7. git identity
    name = git_config("user.name")
    email = git_config("user.email")
    if name and email:
        check("git identity", PASS, f"{name} <{email}>")
    else:
        check("git identity", FAIL, "git config user.name / user.email")

    # 8. hook
    #
    # Same hook as W1, for the same reasons: `uv run` is the one spelling that
    # works under git on macOS, Linux and Windows (Git Bash).
    hook_body = (
        "#!/bin/sh\n"
        "# Installed by tools/verify_env.py. Blocks credential-shaped strings.\n"
        'cd "$(git rev-parse --show-toplevel)" || exit 1\n'
        "exec uv run python tools/check_secrets.py\n"
    )
    hook = ROOT / ".git" / "hooks" / "pre-commit"
    stale = hook.exists() and "exec uv run python" not in hook.read_text(encoding="utf-8")
    if hook.exists() and not stale:
        check("pre-commit hook", PASS)
    else:
        try:
            hook.parent.mkdir(parents=True, exist_ok=True)
            hook.write_text(hook_body, encoding="utf-8")
            hook.chmod(0o755)
            check("pre-commit hook", PASS, "repaired" if stale else "installed now")
        except OSError as exc:
            check("pre-commit hook", WARN, str(exc))

    # 9. lab data
    snapshot = [ROOT / "data" / "snapshot" / f"{s}.json" for s in ("train", "dev")]
    repos = [ROOT / "data" / "repos" / r for r in ("litestar", "hono", "textual")]
    missing = [p.relative_to(ROOT).as_posix() for p in snapshot + repos if not p.exists()]
    if missing:
        check("lab data present", FAIL, f"missing: {', '.join(missing)}")
    else:
        check("lab data present", PASS, "issue snapshot + 3 source snapshots")

    # verdict
    failures = [r for r in results if r[1] == FAIL]
    warnings = [r for r in results if r[1] == WARN]
    say()
    if failures:
        say(f"{len(failures)} check(s) failed:")
        for failed_name, _, detail in failures:
            say(f"  - {failed_name}: {detail}")
    elif warnings:
        say(f"All checks passed ({len(warnings)} warning(s) above, not blocking).")
    else:
        say("All checks passed.")

    slug = re.sub(r"[^a-z0-9]+", "-", (name or "unknown").lower()).strip("-") or "unknown"
    report = REPORT_DIR / f"setup-check-{slug}.txt"
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")

    rel = report.relative_to(ROOT).as_posix()
    print()
    print("=" * 62)
    print(f"Saved this report to {rel}")
    print("Commit and push it, then submit your repo URL in Moodle:")
    print(f"    git add {rel}")
    print('    git commit -m "setup check"')
    print("    git push")
    print("=" * 62)
    if failures:
        print(
            "\nPush it even though it failed, before the deadline. A failed\n"
            "report on time tells me what broke, and I can help you fix it.\n"
            "A missing one does not: there is no time to debug setup in the lab.\n"
            "Nothing in the report contains a credential."
        )
        return 1
    print("\nNothing in the report contains a credential. See you at the lab.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
