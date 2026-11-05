"""Connect DSPy to your model, from the settings in .env file (LLM_MODEL = <model name> or offline)."""

from __future__ import annotations

import os

import dspy
from dotenv import dotenv_values

from triage_lab.data import ROOT
from triage_lab.lm_offline import OFFLINE, OfflineLM


def connect() -> dspy.BaseLM:
    """Create the LM named by LLM_MODEL and make it DSPy's default."""
    model = model_name()
    if not model:
        raise RuntimeError("LLM_MODEL is not set: copy .env.example to .env and fill it in")
    lm: dspy.BaseLM
    if model != OFFLINE:
        # Values every provider accepts. OpenAI's reasoning models (gpt-5*,
        # o3, o4) require exactly temperature=1.0 and max_tokens >= 16000.
        # max_tokens is a ceiling, not a cost: you pay for what is generated.
        lm = dspy.LM(model, temperature=1.0, max_tokens=16000)
    else:
        lm = OfflineLM()
    dspy.configure(lm=lm)
    return lm


def model_name() -> str:
    """LLM_MODEL from .env, read fresh each time (edit .env, rerun the cell).

    The provider keys in .env are put into the environment, where LiteLLM
    finds them. They win over an old key exported in your shell.
    """
    values = dotenv_values(ROOT / ".env")
    for key, value in values.items():
        if key.endswith("_API_KEY") and value:
            os.environ[key] = value
    return (values.get("LLM_MODEL") or "").strip()
