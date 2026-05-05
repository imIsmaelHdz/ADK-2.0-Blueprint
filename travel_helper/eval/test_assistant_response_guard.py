"""
Evaluation-style tests for `travel_helper.assistant_response_guard`.

Run from repository root:

    pip install -r requirements.txt pytest
    pytest travel_helper/eval/test_assistant_response_guard.py -v

Pure helpers (`strip_emojis`, `strip_banned_terms`) always run.
Guardrails-backed `AssistantResponseGuardService.apply` cases are skipped if
`guardrails-ai` is not installed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from travel_helper.assistant_response_guard import (
    AssistantResponseGuardService,
    strip_banned_terms,
    strip_emojis,
    travel_helper_after_model_callback,
    travel_helper_assistant_response_guard_enabled,
)

_CASES_PATH = Path(__file__).resolve().parent / "assistant_response_guard_cases.json"

try:
    import guardrails  # noqa: F401

    HAS_GUARDRAILS = True
except ImportError:
    HAS_GUARDRAILS = False

requires_guardrails = pytest.mark.skipif(
    not HAS_GUARDRAILS,
    reason="guardrails-ai is not installed (pip install guardrails-ai)",
)


def _load_json_cases():
    data = json.loads(_CASES_PATH.read_text(encoding="utf-8"))
    return data["cases"]


@pytest.mark.parametrize(
    "text, expected",
    [
        ("no emoji", "no emoji"),
        ("Hi \U0001f600", "Hi"),
        ("A \u2708\ufe0f B", "A B"),
    ],
)
def test_strip_emojis(text, expected):
    assert strip_emojis(text) == expected


@pytest.mark.parametrize(
    "text, banned, expected",
    [
        ("hello", frozenset(), "hello"),
        ("hello BAD secret", frozenset({"bad"}), "hello secret"),
        ("FooBar fooBAR", frozenset({"foobar"}), ""),
    ],
)
def test_strip_banned_terms(text, banned, expected):
    assert strip_banned_terms(text, banned) == expected


@pytest.mark.parametrize("case", _load_json_cases(), ids=lambda c: c["id"])
@requires_guardrails
def test_service_apply_matches_eval_cases(case):
    banned = frozenset(case["banned_terms"])
    service = AssistantResponseGuardService(enabled=True, banned_terms=banned)
    assert service.apply(case["input"]) == case["expected"]


@requires_guardrails
def test_service_apply_disabled_passthrough():
    service = AssistantResponseGuardService(enabled=False, banned_terms=frozenset())
    assert service.apply("Hello \U0001f600") == "Hello \U0001f600"


@requires_guardrails
def test_after_model_callback_strips_emoji_when_env_enabled(monkeypatch):
    import travel_helper.assistant_response_guard as guard_mod

    monkeypatch.setenv("TRAVEL_HELPER_GUARDRAILS_ENABLED", "1")
    monkeypatch.delenv("TRAVEL_HELPER_GUARDRAILS_BANNED_TERMS", raising=False)
    with guard_mod._runtime_lock:
        guard_mod._runtime_service = None
        guard_mod._runtime_banned = None

    from google.adk.models.llm_response import LlmResponse
    from google.genai.types import Content, Part

    original = LlmResponse(
        content=Content(role="model", parts=[Part(text="Go to CDG \U0001f6e3")])
    )
    updated = travel_helper_after_model_callback(None, original)
    assert updated is not None
    assert updated.content.parts[0].text == "Go to CDG"


def test_assistant_response_guard_enabled_reads_env(monkeypatch):
    monkeypatch.delenv("TRAVEL_HELPER_GUARDRAILS_ENABLED", raising=False)
    assert travel_helper_assistant_response_guard_enabled() is False
    monkeypatch.setenv("TRAVEL_HELPER_GUARDRAILS_ENABLED", "1")
    assert travel_helper_assistant_response_guard_enabled() is True
