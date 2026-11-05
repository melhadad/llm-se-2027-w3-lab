"""Tests for the provided helpers. All offline: no key, no network."""

from __future__ import annotations

from typing import Literal

import dspy
import pytest
from pydantic import ValidationError

from triage_lab.data import load_extended_issues, load_issues
from triage_lab.evaluate import gold_type, run, trainset, triage_metric
from triage_lab.lm_offline import OfflineLM
from triage_lab.repos import cap, entries, source_dir
from triage_lab.schema import MAX_BODY_CHARS, Issue, TriageRecord

ISSUE = Issue(repo="hono", number=1, title="t", body="b", author_association="NONE", labels=[])


# --- record ----------------------------------------------------------------


def test_record_accepts_valid_combinations() -> None:
    TriageRecord(issue=ISSUE, issue_type="bug", severity="high", component=["router/"])
    TriageRecord(issue=ISSUE, issue_type="enhancement", priority="low")
    TriageRecord(issue=ISSUE, issue_type="other")


@pytest.mark.parametrize(
    "fields",
    [
        {"issue_type": "bug"},
        {"issue_type": "bug", "severity": "high", "priority": "low"},
        {"issue_type": "enhancement", "severity": "high"},
        {"issue_type": "enhancement"},
        {"issue_type": "other", "priority": "low"},
        {"issue_type": "Bug", "severity": "high"},
        {"issue_type": "bug", "severity": "High"},
    ],
)
def test_record_rejects_invalid_combinations(fields: dict[str, str]) -> None:
    with pytest.raises(ValidationError):
        TriageRecord(issue=ISSUE, **fields)  # type: ignore[arg-type]


# --- data ------------------------------------------------------------------


def test_test_issues_are_sealed() -> None:
    with pytest.raises(ValueError):
        load_issues("test")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        load_extended_issues("test")  # type: ignore[arg-type]


def test_issue_counts_and_mapped_types() -> None:
    assert len(load_issues("train")) == 720
    dev = load_extended_issues("dev")
    assert len(dev) == 240
    assert {i.gold_type for i in dev} <= {"bug", "enhancement", "other", None}


def test_issue_hides_hindsight_and_gold_fields_and_truncates() -> None:
    issues = load_issues("dev")
    assert set(Issue.model_fields) == {"repo", "number", "title", "body", "author_association", "labels"}
    assert all(type(i) is Issue for i in issues)
    assert max(len(i.body) for i in issues) <= MAX_BODY_CHARS + 20


def test_gold_lookup_matches_extended_issues() -> None:
    extended = load_extended_issues("dev")[1]
    assert gold_type(extended.to_issue()) == extended.gold_type


# --- repos -----------------------------------------------------------------


def test_source_dir_lists_modules() -> None:
    assert "dto/" in entries(source_dir("litestar"))
    assert "middleware/" in entries(source_dir("hono"))
    assert "widgets/" in entries(source_dir("textual"))
    assert entries(source_dir("hono", "middleware"))


@pytest.mark.parametrize("path", ["..", "../..", "/etc", "dto/../../..", "no-such-folder"])
def test_source_dir_stays_inside_snapshot(path: str) -> None:
    with pytest.raises(ValueError):
        source_dir("litestar", path)


def test_unknown_repo_rejected() -> None:
    with pytest.raises(ValueError):
        source_dir("django")


def test_cap_reports_what_was_cut() -> None:
    assert cap(["a", "b", "c"], 2) == ["a", "b", "... and 1 more"]
    assert cap(["a"], 2) == ["a"]


# --- offline end to end ----------------------------------------------------


class TriageIssue(dspy.Signature):
    """Triage a GitHub issue."""

    issue: Issue = dspy.InputField()
    issue_type: Literal["bug", "enhancement", "other"] = dspy.OutputField()
    severity: Literal["low", "medium", "high", "critical"] | None = dspy.OutputField()
    priority: Literal["low", "medium", "high"] | None = dspy.OutputField()
    component: list[str] = dspy.OutputField()


@pytest.fixture(autouse=True)
def offline() -> None:
    dspy.configure(lm=OfflineLM())


def test_offline_one_call_program_runs() -> None:
    results = run(dspy.Predict(TriageIssue), load_issues("dev"), 0, 5)
    assert len(results) == 5
    assert all(r.record is not None for r in results)
    assert [r.predicted_type for r in results][1] == "enhancement"


def list_components(repo: Literal["litestar", "hono", "textual"]) -> list[str]:
    """List the top-level modules of a repo."""
    return entries(source_dir(repo))


class AssessBug(dspy.Signature):
    """Assess a bug."""

    issue: Issue = dspy.InputField()
    severity: Literal["low", "medium", "high", "critical"] = dspy.OutputField()
    component: list[str] = dspy.OutputField()


def test_offline_react_calls_the_tool() -> None:
    agent = dspy.ReAct(AssessBug, tools=[list_components], max_iters=3)
    prediction = agent(issue=ISSUE.model_copy(update={"repo": "litestar", "title": "crash in dto"}))
    assert prediction.severity == "medium"
    assert prediction.trajectory["tool_name_0"] == "list_components"
    assert "dto/" in str(prediction.trajectory["observation_0"])


def test_offline_bootstrap_fewshot_compiles() -> None:
    optimizer = dspy.BootstrapFewShot(metric=triage_metric, max_bootstrapped_demos=2, max_labeled_demos=0)
    compiled = optimizer.compile(dspy.Predict(TriageIssue), trainset=trainset(6))
    assert len(compiled.demos) <= 2
