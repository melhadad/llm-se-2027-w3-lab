"""The contracts between the model and the rest of the code.

  Issue           what the model sees about an issue (the input)
  ExtendedIssue   every field of the snapshot, including the gold labels
                  (never shown to the model)
  TriageRecord    an Issue plus the triage the model produced (the output)

Whatever a DSPy program returns, it only counts once it has been turned into a
`TriageRecord`. If that fails, the output is invalid, however plausible it
looks.

VOCABULARY
----------
One concept, one name (the W1 lesson):

  issue_type  bug | enhancement | other. Only bugs and enhancements are
              triaged. Documentation, questions and meta issues are "other".
  severity    how bad a BUG is. Bugs only.
  priority    how much an ENHANCEMENT matters. Enhancements only.
  component   the parts of the code base the issue is about (module folders
              or files of the repo). May be empty.

Severity and priority are separate concepts with separate values. Nothing in
this package calls severity "priority", or the other way round.

How this differs from W1's TriageRecord (Exercise B): W1 had five issue types
and a severity for every issue. Schemas are design decisions; this one is ours
for W3.
"""

from __future__ import annotations

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, model_validator

IssueType = Literal["bug", "enhancement", "other"]
Severity = Literal["low", "medium", "high", "critical"]
Priority = Literal["low", "medium", "high"]

# Long bodies cost tokens and rarely change the answer.
MAX_BODY_CHARS = 1500


class Issue(BaseModel):
    """An issue as it reaches triage: only the fields the model may see.

    The labels are the ones in the snapshot, which means the final labels:
    some were added by maintainers after the issue was opened.
    """

    repo: str  # litestar, hono or textual
    number: int
    title: str
    body: str
    author_association: str  # the author's relation to the repo, e.g. MEMBER, NONE
    labels: list[str]


class ExtendedIssue(Issue):
    """Every field of the snapshot JSON.

    The extra fields are hindsight (state, closed_at and comments only exist
    after triage) or answers (gold_*). The model never sees them.
    """

    state: str
    created_at: str
    closed_at: str | None
    comments: int
    url: str
    gold_type: IssueType | None  # None = unlabelled, not scored
    gold_component: str | None
    gold_has_reproduction_steps: bool | None
    gold_severity: Severity | None
    gold_duplicate_candidate: int | None

    def to_issue(self) -> Issue:
        """The projection the model sees, with the body cut to MAX_BODY_CHARS."""
        body = self.body
        if len(body) > MAX_BODY_CHARS:
            body = body[:MAX_BODY_CHARS] + "\n[... truncated]"
        fields = self.model_dump(include=set(Issue.model_fields))
        return Issue(**{**fields, "body": body})


class TriageRecord(BaseModel):
    """One triaged issue: the issue, and the triage of it."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    issue: Issue
    issue_type: IssueType
    severity: Severity | None = None
    priority: Priority | None = None
    component: list[str] = []

    @model_validator(mode="after")
    def _fields_match_type(self) -> Self:
        if self.issue_type == "bug":
            if self.severity is None:
                raise ValueError("a bug needs a severity")
            if self.priority is not None:
                raise ValueError("a bug has a severity, not a priority")
        elif self.issue_type == "enhancement":
            if self.priority is None:
                raise ValueError("an enhancement needs a priority")
            if self.severity is not None:
                raise ValueError("an enhancement has a priority, not a severity")
        elif self.severity is not None or self.priority is not None:
            raise ValueError("'other' issues are not triaged: no severity, no priority")
        return self
