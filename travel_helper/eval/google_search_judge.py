"""
LLM-as-judge evaluation for `travel_helper.agents.google_search`.

The google_search_agent takes a destination city + traveler nationality and must
return three fixed sections: ENTRY REQUIREMENTS, AIRPORT TO CITY CENTER, and a
numbered TOURIST ATTRACTIONS list. This module scores that output two ways:

  1. Deterministic structural checks (required headers present, attraction count).
  2. A separate Gemini "judge" agent that scores the output against a rubric
     (nationality-specific entry advice, completeness, factual plausibility, ...).

Both the agent under test and the judge make real Vertex AI / Gemini calls, so the
pytest suite that uses this module is skipped unless TRAVEL_HELPER_RUN_LLM_EVAL is set
(see test_google_search_judge.py).
"""

from __future__ import annotations

import asyncio
import json
import re
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from dotenv import load_dotenv

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

from travel_helper.agents.google_search import root_agent as google_search_agent

# Load Vertex AI config (GOOGLE_GENAI_USE_VERTEXAI / project / location) from .env,
# matching travel_helper_runner and the API gateway. Existing env vars win.
load_dotenv()

_APP_NAME = "google_search_judge_eval"
_USER_ID = "eval_user"

# Section headers the agent is instructed to emit (case-insensitive match).
REQUIRED_SECTIONS = (
    "ENTRY REQUIREMENTS",
    "AIRPORT TO CITY CENTER",
    "TOURIST ATTRACTIONS",
)

# Counts lines that look like a numbered list item, e.g. "1. Foo" or "2) Bar".
_NUMBERED_RE = re.compile(r"^\s*\d+[.)]\s+\S", re.MULTILINE)


class JudgeVerdict(BaseModel):
    """Rubric scores returned by the judge agent (each 1=poor .. 5=excellent)."""

    nationality_specific: int = Field(
        ge=1, le=5,
        description="Is the entry/visa advice tailored to the traveler's stated nationality/passport?",
    )
    entry_completeness: int = Field(
        ge=1, le=5,
        description="Does ENTRY REQUIREMENTS state visa yes/no, max stay, and how to apply?",
    )
    airport_usefulness: int = Field(
        ge=1, le=5,
        description="Does AIRPORT TO CITY CENTER give concrete options, approx cost, and travel time?",
    )
    attractions_quality: int = Field(
        ge=1, le=5,
        description="Are the listed attractions real, well-known, and relevant to the destination?",
    )
    factual_plausibility: int = Field(
        ge=1, le=5,
        description="Is the answer free of obvious hallucinations, contradictions, or wrong-country facts?",
    )
    overall: int = Field(
        ge=1, le=5,
        description="Overall usefulness of this output as pre-trip research.",
    )
    reasoning: str = Field(
        description="One or two sentences justifying the scores; cite the weakest dimension.",
    )


_JUDGE_INSTRUCTION = """
You are a strict evaluation judge for a travel-research agent.

You will receive JSON with: `destination`, `nationality`, and `output` (the agent's
answer). The agent was asked to return three sections — ENTRY REQUIREMENTS,
AIRPORT TO CITY CENTER, and a numbered TOURIST ATTRACTIONS list — for a traveler of
the given nationality going to the given destination.

Score each rubric dimension from 1 (poor) to 5 (excellent):
- nationality_specific: entry advice must reflect THIS nationality's rules (e.g. visa
  vs visa-free, eTA). Generic advice that ignores the passport scores low.
- entry_completeness: visa needed yes/no, maximum stay, and how to apply.
- airport_usefulness: named transport options, approximate cost, and travel time.
- attractions_quality: real, relevant landmarks for the destination (not invented or
  from the wrong city).
- factual_plausibility: penalize hallucinations, contradictions, or facts about the
  wrong country.
- overall: holistic usefulness as pre-trip research.

Be calibrated and critical: reserve 5 for genuinely excellent answers, and use 1-2
when a dimension is missing or wrong. Judge only what is present in `output`; do not
reward formatting alone. Return your scores in the required structured format.
"""

# Judge has no tools/sub-agents; output_schema forces structured JSON and (per ADK)
# disables agent transfer automatically.
judge_agent = Agent(
    name="google_search_judge",
    model="gemini-2.5-flash",
    description="Scores google_search_agent travel-research output against a rubric.",
    instruction=_JUDGE_INSTRUCTION,
    output_schema=JudgeVerdict,
)


@dataclass(frozen=True)
class StructuralReport:
    missing_sections: list[str]
    attraction_count: int

    @property
    def ok(self) -> bool:
        return not self.missing_sections


@dataclass(frozen=True)
class CaseResult:
    destination: str
    nationality: str
    output: str
    structural: StructuralReport
    verdict: JudgeVerdict


async def _run_agent_text(agent: Agent, prompt: str) -> str:
    """Run an ADK agent for a single turn and return the final response text."""
    session_service = InMemorySessionService()
    session_id = f"s_{uuid.uuid4().hex}"
    await session_service.create_session(
        app_name=_APP_NAME, user_id=_USER_ID, session_id=session_id
    )
    runner = Runner(
        agent=agent, app_name=_APP_NAME, session_service=session_service
    )
    content = Content(role="user", parts=[Part(text=prompt)])

    final_text = ""
    async for event in runner.run_async(
        user_id=_USER_ID, session_id=session_id, new_message=content
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_text = "".join(p.text or "" for p in event.content.parts)
            break
    return final_text.strip()


async def run_google_search_agent(destination: str, nationality: str) -> str:
    """Invoke the agent under test exactly as the root travel_helper agent does."""
    prompt = f"destination: {destination}, nationality: {nationality}"
    return await _run_agent_text(google_search_agent, prompt)


def structural_report(output: str) -> StructuralReport:
    """Deterministic checks: required headers present and numbered-attraction count."""
    upper = output.upper()
    missing = [s for s in REQUIRED_SECTIONS if s not in upper]
    attraction_count = len(_NUMBERED_RE.findall(output))
    return StructuralReport(missing_sections=missing, attraction_count=attraction_count)


async def judge_output(destination: str, nationality: str, output: str) -> JudgeVerdict:
    """Ask the judge agent to score one agent output; returns a validated verdict."""
    prompt = json.dumps(
        {"destination": destination, "nationality": nationality, "output": output},
        ensure_ascii=False,
    )
    text = await _run_agent_text(judge_agent, prompt)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"Judge did not return valid JSON for {destination!r}/{nationality!r}: {text!r}"
        ) from e
    return JudgeVerdict(**data)


def evaluate_case(destination: str, nationality: str) -> CaseResult:
    """Run the agent, structural checks, and the judge for one (destination, nationality)."""

    async def _run() -> tuple[str, StructuralReport, JudgeVerdict]:
        output = await run_google_search_agent(destination, nationality)
        if not output:
            raise RuntimeError(
                f"google_search_agent returned empty output for "
                f"{destination!r}/{nationality!r}"
            )
        structural = structural_report(output)
        verdict = await judge_output(destination, nationality, output)
        return output, structural, verdict

    output, structural, verdict = asyncio.run(_run())
    return CaseResult(
        destination=destination,
        nationality=nationality,
        output=output,
        structural=structural,
        verdict=verdict,
    )


def append_result(path: Path, case_id: str, result: CaseResult, passed: bool | None = None) -> None:
    """Append one case result into a pretty-printed JSON array file (human-readable).

    Read-modify-write keeps the whole file valid JSON after every case; the suite runs
    serially, so this is safe. Parent dirs are created as needed.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "case_id": case_id,
        "destination": result.destination,
        "nationality": result.nationality,
        "passed": passed,
        "structural": asdict(result.structural),
        "verdict": result.verdict.model_dump(),
        "output": result.output,
    }

    results: list = []
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(existing, list):
                results = existing
        except json.JSONDecodeError:
            pass  # corrupt/partial file — start fresh rather than crash the run
    results.append(record)

    path.write_text(
        json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
