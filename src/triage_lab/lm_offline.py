"""Offline mode: a fake model, for rehearsals and for when your provider is down.

    LLM_MODEL=offline     in .env (no key, no network, no cost)

`OfflineLM` returns fixed, valid answers for any DSPy signature, so every
cell of the notebook runs. Its scores mean nothing.

You do not need to read this file for the lab.
"""

from __future__ import annotations

import json
import re
from typing import Any

from dspy.utils import DummyLM
from dspy.utils.dummies import dotdict

OFFLINE = "offline"

_OUTPUT_FIELD = re.compile(r"^\d+\. `(\w+)` \((.+?)\):", re.MULTILINE)


class OfflineLM(DummyLM):
    """A fake model that answers any DSPy signature without a network call.

    It reads the output fields and their types from DSPy's prompt and fills
    each one with a fixed valid value: the type follows the issue's labels,
    severity (bugs) and priority (enhancements) are "medium", components are
    empty. Under ReAct it calls the first tool once, then finishes.
    Deterministic and free.
    """

    def __init__(self) -> None:
        super().__init__(answers=[])
        self.model = OFFLINE

    def forward(self, prompt: str | None = None, messages: list[dict[str, Any]] | None = None, **kwargs: Any) -> Any:
        messages = messages or [{"role": "user", "content": prompt or ""}]
        system = next((m["content"] for m in messages if m["role"] == "system"), "")
        last = str(messages[-1]["content"])
        fields = _OUTPUT_FIELD.findall(system.split("Your output fields are:", 1)[-1].split("All interactions", 1)[0])
        if fields:
            names = [name for name, _ in fields]
            issue_type = _type_from_labels(last) if "issue_type" in names else None
            answer = {name: self._value(name, kind, system, last, issue_type) for name, kind in fields}
            content = self._format_answer_fields(answer)
        else:
            content = "ready"
        message = dotdict(content=content, tool_calls=None)
        return dotdict(
            choices=[dotdict(message=message, finish_reason="stop")],
            usage=dotdict(prompt_tokens=0, completion_tokens=0, total_tokens=0),
            model=OFFLINE,
        )

    def _value(self, name: str, kind: str, system: str, last: str, issue_type: str | None) -> Any:
        options = re.findall(r"'([^']*)'", kind) if "Literal[" in kind else []
        if name == "next_tool_name":
            tools = [o for o in options if o != "finish"]
            return tools[0] if tools and "observation_0" not in last else "finish"
        if name == "next_tool_args":
            match = re.search(r'"repo":\s*"(\w+)"', last)
            repo = match.group(1) if match else "litestar"
            return {"repo": repo} if "observation_0" not in last and "repo" in system else {}
        if name == "issue_type" and issue_type is not None:
            return issue_type
        if issue_type is not None and "NoneType" in kind:
            # One call that fills everything: only the field that fits the type.
            if (name == "severity" and issue_type != "bug") or (name == "priority" and issue_type != "enhancement"):
                return None
        if options:
            return "medium" if "medium" in options else options[0]
        if kind.startswith("list"):
            return []
        if kind.startswith("dict"):
            return {}
        if kind in ("bool",):
            return False
        if kind in ("int", "float"):
            return 0
        return "offline answer"


def _type_from_labels(text: str) -> str:
    """Read the labels from the issue's JSON in the prompt."""
    match = re.search(r'"labels":\s*(\[.*?\])', text)
    labels = [label.lower() for label in json.loads(match.group(1))] if match else []
    if any("bug" in label and "not bug" not in label for label in labels):
        return "bug"
    if any("enhancement" in label or "feature" in label for label in labels):
        return "enhancement"
    return "other"
