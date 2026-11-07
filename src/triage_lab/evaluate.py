"""Run a DSPy program over a range of issues, check its output, keep score.

Every part of the lab calls `run(...)` on the same issues (dev[0:20] by
default), so the numbers are comparable from part to part. Two numbers matter:

  type accuracy   predicted issue_type == gold, over the labelled issues only
                  (unlabelled issues are run but not scored)
  valid           the output could be turned into a TriageRecord

Scores are a sanity check, not the goal of this lab.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

import dspy
from pydantic import ValidationError

from triage_lab.data import ROOT, load_extended_issues
from triage_lab.lm import model_name
from triage_lab.lm_offline import OFFLINE
from triage_lab.schema import Issue, IssueType, TriageRecord

RESULTS_PATH = ROOT / "outputs" / "results" / "w3_results.json"

_gold: dict[tuple[str, int], IssueType | None] = {}


def gold_type(issue: Issue) -> IssueType | None:
    """The gold type of an issue, looked up by repo and number (None = unlabelled)."""
    if not _gold:
        for source in ("train", "dev"):
            for extended in load_extended_issues(source):
                _gold[(extended.repo, extended.number)] = extended.gold_type
    return _gold.get((issue.repo, issue.number))


@dataclass
class Result:
    issue: Issue
    gold: IssueType | None
    predicted_type: str | None  # kept even when the record is invalid
    record: TriageRecord | None
    error: str | None
    predicted_severity: str | None = None  # shown for invalid records too
    predicted_priority: str | None = None


@dataclass
class Summary:
    issues_run: int
    issues_scored: int
    type_correct: int
    valid: int
    cost_usd: float
    lm_calls: int

    @property
    def type_accuracy(self) -> float:
        return self.type_correct / self.issues_scored if self.issues_scored else 0.0

    @property
    def valid_rate(self) -> float:
        return self.valid / self.issues_run if self.issues_run else 0.0


_parts: dict[str, tuple[Summary, list[Result]]] = {}


def to_record(issue: Issue, prediction: Any) -> TriageRecord:
    """Turn a DSPy prediction into a TriageRecord, or raise ValidationError."""
    return TriageRecord(
        issue=issue,
        issue_type=prediction.get("issue_type"),
        severity=prediction.get("severity"),
        priority=prediction.get("priority"),
        component=prediction.get("component") or [],
    )


def run(
    program: Callable[..., Any],
    issues: Sequence[Issue],
    start: int = 0,
    stop: int = 20,
    *,
    part: str | None = None,
) -> list[Result]:
    """Run `program(issue=...)` on issues[start:stop], print a table and a summary.

    Pass `part="..."` to record the result for the score table at the end of the notebook.
    """
    lm = dspy.settings.lm
    history_before = len(lm.history) if lm is not None else 0
    results: list[Result] = []
    for issue in issues[start:stop]:
        gold = gold_type(issue)
        try:
            prediction = program(issue=issue)
        except Exception as exc:  # noqa: BLE001 - a failed call is a result too
            results.append(Result(issue, gold, None, None, f"{type(exc).__name__}: {str(exc)[:80]}"))
            continue
        predicted = (prediction.get("issue_type"), prediction.get("severity"), prediction.get("priority"))
        try:
            results.append(Result(issue, gold, predicted[0], to_record(issue, prediction), None, *predicted[1:]))
        except ValidationError as exc:
            reason = exc.errors()[0]["msg"].removeprefix("Value error, ")
            results.append(Result(issue, gold, predicted[0], None, f"invalid: {reason}", *predicted[1:]))

    new_calls = lm.history[history_before:] if lm is not None else []
    cost = sum(float(call.get("cost") or 0.0) for call in new_calls)
    summary = _summarize(results, cost, len(new_calls))
    show(results)
    print(_summary_line(summary))
    if part:
        _parts[part] = (summary, results)
    return results


def _summarize(results: list[Result], cost: float, calls: int) -> Summary:
    scored = [r for r in results if r.gold is not None]
    correct = [r for r in scored if r.predicted_type == r.gold]
    valid = [r for r in results if r.record is not None]
    return Summary(len(results), len(scored), len(correct), len(valid), cost, calls)


def _summary_line(s: Summary) -> str:
    line = (
        f"\ntype accuracy {s.type_accuracy:.0%} ({s.type_correct}/{s.issues_scored} labelled issues) | "
        f"valid records {s.valid_rate:.0%} ({s.valid}/{s.issues_run}) | "
        f"{s.lm_calls} LM calls, ${s.cost_usd:.4f}"
    )
    if model_name() == OFFLINE:
        line += "\n(offline mode: fake model, these numbers mean nothing)"
    return line


def show(results: list[Result]) -> None:
    """Print one line per issue: gold type, the prediction, and the error if the record is invalid."""
    components = [", ".join(r.record.component) if r.record and r.record.component else "-" for r in results]
    width = max([len("component"), *map(len, components)])
    print(
        f"{'#':>3}  {'issue':<16} {'gold_type':<11} {'type':<13} {'severity':<9} {'priority':<9} "
        f"{'component':<{width}}  error"
    )
    for i, (r, component) in enumerate(zip(results, components)):
        name = f"{r.issue.repo}#{r.issue.number}"
        gold = r.gold or "-"
        mark = "" if r.gold in (None, r.predicted_type) else " ✗"
        predicted = f"{r.predicted_type or '?'}{mark}"
        print(
            f"{i:>3}  {name:<16} {gold:<11} {predicted:<13} "
            f"{r.predicted_severity or '-':<9} {r.predicted_priority or '-':<9} "
            f"{component:<{width}}  {r.error or '-'}"
        )


def scoreboard() -> None:
    """Print the score of every recorded part, in the order they were run."""
    print(f"{'part':<28} {'type acc':>8} {'valid':>6} {'calls':>6} {'cost $':>8}")
    for name, (s, _) in _parts.items():
        print(f"{name:<28} {s.type_accuracy:>8.0%} {s.valid_rate:>6.0%} {s.lm_calls:>6} {s.cost_usd:>8.4f}")


def save_results(path: str | None = None) -> None:
    """Write every recorded part to outputs/results/w3_results.json (commit this file)."""
    target = RESULTS_PATH if path is None else ROOT / path
    payload: dict[str, Any] = {
        "model": model_name(),
        "parts": {
            name: {
                "issues_run": s.issues_run,
                "issues_scored": s.issues_scored,
                "type_accuracy": round(s.type_accuracy, 3),
                "valid_rate": round(s.valid_rate, 3),
                "lm_calls": s.lm_calls,
                "cost_usd": round(s.cost_usd, 5),
                "issues": [
                    {
                        "repo": r.issue.repo,
                        "number": r.issue.number,
                        "gold_type": r.gold,
                        "record": r.record.model_dump(exclude={"issue"}) if r.record else None,
                        "error": r.error,
                    }
                    for r in results
                ],
            }
            for name, (s, results) in _parts.items()
        },
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {target.relative_to(ROOT)}")


# --- Part 7: optimization ---------------------------------------------------


def trainset(n: int = 20) -> list[dspy.Example]:
    """`n` labelled train issues, alternating between the repos, as DSPy examples."""
    by_repo: dict[str, list[Issue]] = {}
    for extended in load_extended_issues("train"):
        if extended.gold_type is not None:
            by_repo.setdefault(extended.repo, []).append(extended.to_issue())
    picked: list[Issue] = []
    while len(picked) < n and any(by_repo.values()):
        for queue in by_repo.values():
            if queue and len(picked) < n:
                picked.append(queue.pop(0))
    return [dspy.Example(issue=issue, gold_type=gold_type(issue)).with_inputs("issue") for issue in picked]


def triage_metric(example: dspy.Example, prediction: Any, trace: Any = None) -> bool:
    """Part 7 metric: the type is right AND the output is a valid TriageRecord."""
    if prediction.get("issue_type") != example.gold_type:
        return False
    try:
        to_record(example.issue, prediction)
    except ValidationError:
        return False
    return True
