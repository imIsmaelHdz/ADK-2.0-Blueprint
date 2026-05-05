"""
Optional assistant-response guard for travel_helper (Guardrails AI).

Toggle with environment variable (default: off). The flag is read on each model
response; unset it or set to 0/false to skip Guardrails without code changes.

    TRAVEL_HELPER_GUARDRAILS_ENABLED=1   # enable
    TRAVEL_HELPER_GUARDRAILS_ENABLED=0   # disable (same as unset)

Optional comma-separated lowercase phrases to strip on failure (case-insensitive):

    TRAVEL_HELPER_GUARDRAILS_BANNED_TERMS=foo,bar

Requires: pip install guardrails-ai (see requirements.txt).
When enabled but the package is missing, validation is skipped and a warning is logged.
"""

from __future__ import annotations

import logging
import os
import re
import threading
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from google.adk.agents.callback_context import CallbackContext
    from google.adk.models.llm_response import LlmResponse

logger = logging.getLogger(__name__)

_ENV_ENABLED = "TRAVEL_HELPER_GUARDRAILS_ENABLED"
_ENV_BANNED = "TRAVEL_HELPER_GUARDRAILS_BANNED_TERMS"

_EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "]+",
    flags=re.UNICODE,
)


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _env_banned_terms() -> frozenset[str]:
    raw = os.environ.get(_ENV_BANNED, "")
    out = {t.strip().lower() for t in raw.split(",") if t.strip()}
    return frozenset(out)


def strip_emojis(text: str) -> str:
    cleaned = _EMOJI_RE.sub("", text)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned.strip()


def strip_banned_terms(text: str, banned: frozenset[str]) -> str:
    out = text
    for term in banned:
        if not term:
            continue
        out = re.sub(re.escape(term), "", out, flags=re.IGNORECASE)
    return " ".join(out.split())


def _register_travel_validators(banned: frozenset[str]):
    from guardrails import Guard
    from guardrails.validator_base import register_validator, Validator
    from guardrails_ai.types import FailResult, PassResult, ValidationResult

    @register_validator(name="travel_helper_no_emoji", data_type="string")
    class TravelHelperNoEmoji(Validator):
        def _validate(self, value: str, metadata: dict) -> ValidationResult:
            if _EMOJI_RE.search(value):
                return FailResult(error_message="Emoji characters are not allowed.")
            return PassResult()

    def on_emoji_fail(value, fail_result):
        return strip_emojis(value)

    validators: list = [TravelHelperNoEmoji(on_fail=on_emoji_fail)]

    if banned:

        @register_validator(name="travel_helper_banned_terms", data_type="string")
        class TravelHelperBannedTerms(Validator):
            def _validate(self, value: str, metadata: dict) -> ValidationResult:
                lower = value.lower()
                for term in banned:
                    if term and term in lower:
                        return FailResult(
                            error_message="Disallowed vocabulary detected."
                        )
                return PassResult()

        def on_banned_fail(value, fail_result):
            return strip_banned_terms(value, banned)

        validators.append(
            TravelHelperBannedTerms(on_fail=on_banned_fail),
        )

    return Guard.for_string(
        validators=validators,
        name="travel_helper_assistant_response_guard",
        description="Sanitize travel_helper assistant replies (emoji / optional terms).",
    )


@dataclass
class AssistantResponseGuardService:
    """Feature-flagged Guardrails wrapper; safe no-op when disabled or unavailable."""

    enabled: bool
    banned_terms: frozenset[str]
    _import_error: Optional[str] = None
    _guard_cache: Any = field(default=None, repr=False, init=False)

    @classmethod
    def from_env(cls) -> AssistantResponseGuardService:
        want = _env_flag(_ENV_ENABLED, default=False)
        banned = _env_banned_terms()
        if not want:
            return cls(enabled=False, banned_terms=banned, _import_error=None)

        try:
            import guardrails  # noqa: F401
        except ImportError as e:
            logger.warning(
                "TRAVEL_HELPER_GUARDRAILS_ENABLED is set but guardrails-ai is not "
                "installed (%s). Install guardrails-ai or unset the env var.",
                e,
            )
            return cls(enabled=False, banned_terms=banned, _import_error=str(e))

        return cls(enabled=True, banned_terms=banned, _import_error=None)

    def is_enabled(self) -> bool:
        return self.enabled

    def _guard(self):
        if self._guard_cache is None:
            self._guard_cache = _register_travel_validators(self.banned_terms)
        return self._guard_cache

    def apply(self, text: str) -> str:
        if not self.enabled or not text:
            return text
        guard = self._guard()
        outcome = guard.parse(text)
        if outcome.validated_output is not None:
            return str(outcome.validated_output)
        logger.warning(
            "Guardrails validation did not return validated_output; using raw text."
        )
        return outcome.raw_llm_output if outcome.raw_llm_output is not None else text


_runtime_lock = threading.Lock()
_runtime_service: Optional[AssistantResponseGuardService] = None
_runtime_banned: Optional[frozenset[str]] = None


def _get_runtime_service() -> Optional[AssistantResponseGuardService]:
    """Lazily build Guardrails when TRAVEL_HELPER_GUARDRAILS_ENABLED is set (checked each call)."""
    global _runtime_service, _runtime_banned

    if not _env_flag(_ENV_ENABLED, default=False):
        return None

    banned = _env_banned_terms()
    with _runtime_lock:
        if _runtime_service is not None and _runtime_banned == banned:
            return _runtime_service

        try:
            import guardrails  # noqa: F401
        except ImportError as e:
            logger.warning(
                "TRAVEL_HELPER_GUARDRAILS_ENABLED is set but guardrails-ai is not "
                "installed (%s). Install guardrails-ai or unset the env var.",
                e,
            )
            _runtime_service = None
            _runtime_banned = None
            return None

        _runtime_service = AssistantResponseGuardService(
            enabled=True, banned_terms=banned
        )
        _runtime_banned = banned
        return _runtime_service


def travel_helper_after_model_callback(
    callback_context: "CallbackContext",
    llm_response: "LlmResponse",
) -> Optional["LlmResponse"]:
    """ADK hook: sanitize model text when Guardrails is enabled via env."""
    service = _get_runtime_service()
    if service is None:
        return None

    from google.genai.types import Content, Part

    content = llm_response.content
    if not content or not content.parts:
        return None

    changed = False
    new_parts = []
    for part in content.parts:
        if part.text is not None:
            updated = service.apply(part.text)
            if updated != part.text:
                changed = True
            new_parts.append(Part(text=updated))
        else:
            new_parts.append(part)

    if not changed:
        return None

    new_content = Content(role=content.role, parts=new_parts)
    return llm_response.model_copy(update={"content": new_content})


def travel_helper_assistant_response_guard_enabled() -> bool:
    """True when the env flag is on (package may still be missing at runtime)."""
    return _env_flag(_ENV_ENABLED, default=False)
