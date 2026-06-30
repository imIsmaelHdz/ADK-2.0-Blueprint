"""
LLM-as-judge tests for `travel_helper.agents.google_search`.

These make REAL Vertex AI / Gemini calls (the agent under test *and* the judge), so
they are skipped unless TRAVEL_HELPER_RUN_LLM_EVAL is set. Requires ADC + Vertex
configuration the same as running the agent (see setup.md).

Run from the repository root:

    TRAVEL_HELPER_RUN_LLM_EVAL=1 pytest travel_helper/eval/test_google_search_judge.py -v -s

Cases and thresholds live in google_search_judge_cases.json.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

_EVAL_DIR = Path(__file__).resolve().parent
_CASES_PATH = _EVAL_DIR / "google_search_judge_cases.json"

# One results file per pytest session (this module imports once). Override the path
# with TRAVEL_HELPER_EVAL_OUTPUT; default lands under eval/results/ (git-ignored).
_RUN_TS = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
_RESULTS_PATH = Path(
    os.environ.get(
        "TRAVEL_HELPER_EVAL_OUTPUT",
        _EVAL_DIR / "results" / f"google_search_judge_{_RUN_TS}.json",
    )
)

requires_llm_eval = pytest.mark.skipif(
    not os.environ.get("TRAVEL_HELPER_RUN_LLM_EVAL"),
    reason="Set TRAVEL_HELPER_RUN_LLM_EVAL=1 to run live LLM-as-judge eval (real Vertex AI calls)",
)


def _load() -> tuple[dict, list[dict]]:
    data = json.loads(_CASES_PATH.read_text(encoding="utf-8"))
    return data.get("defaults", {}), data["cases"]


_DEFAULTS, _CASES = _load()


def _threshold(case: dict, key: str) -> int:
    return int(case.get(key, _DEFAULTS.get(key, 3)))


@requires_llm_eval
@pytest.mark.parametrize("case", _CASES, ids=[c["id"] for c in _CASES])
def test_google_search_meets_rubric(case):
    # Imported lazily so the whole eval dir still collects when ADK/Vertex deps or
    # credentials are unavailable and this suite is skipped.
    from travel_helper.eval.google_search_judge import append_result, evaluate_case

    result = evaluate_case(case["destination"], case["nationality"])
    verdict = result.verdict

    # Compute pass/fail up front so the persisted record reflects the assertions below.
    passed = (
        not result.structural.missing_sections
        and result.structural.attraction_count >= _threshold(case, "min_attractions")
        and verdict.overall >= _threshold(case, "min_overall")
        and verdict.nationality_specific >= _threshold(case, "min_nationality_specific")
        and verdict.factual_plausibility >= _threshold(case, "min_factual_plausibility")
    )
    append_result(_RESULTS_PATH, case["id"], result, passed=passed)
    print(f"\n  → wrote result to {_RESULTS_PATH}")

    # Surface scores when run with -s; helps triage a regression without re-running.
    print(
        f"\n[{case['id']}] attractions={result.structural.attraction_count} "
        f"overall={verdict.overall} nationality={verdict.nationality_specific} "
        f"entry={verdict.entry_completeness} airport={verdict.airport_usefulness} "
        f"attractions_q={verdict.attractions_quality} factual={verdict.factual_plausibility}\n"
        f"  judge: {verdict.reasoning}"
    )

    # 1) Deterministic structure: all required headers present, enough attractions.
    assert not result.structural.missing_sections, (
        f"missing sections: {result.structural.missing_sections}"
    )
    min_attractions = _threshold(case, "min_attractions")
    assert result.structural.attraction_count >= min_attractions, (
        f"only {result.structural.attraction_count} numbered attractions "
        f"(expected >= {min_attractions})"
    )

    # 2) LLM-judge rubric thresholds.
    assert verdict.overall >= _threshold(case, "min_overall"), (
        f"overall {verdict.overall} below threshold: {verdict.reasoning}"
    )
    assert verdict.nationality_specific >= _threshold(case, "min_nationality_specific"), (
        f"nationality_specific {verdict.nationality_specific} below threshold: {verdict.reasoning}"
    )
    assert verdict.factual_plausibility >= _threshold(case, "min_factual_plausibility"), (
        f"factual_plausibility {verdict.factual_plausibility} below threshold: {verdict.reasoning}"
    )
