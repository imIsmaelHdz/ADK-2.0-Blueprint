# Travel Helper — assistant response guard evaluation

Automated checks for [`assistant_response_guard.py`](../assistant_response_guard.py): pure string helpers and Guardrails-backed `AssistantResponseGuardService.apply` behavior.

## Prerequisites

From the repository root:

```shell
pip install -r requirements.txt pytest
```

`guardrails-ai` is in `requirements.txt`. Cases that call Guardrails are **skipped** if the package is not installed.

## Run tests

```shell
pytest travel_helper/eval/test_assistant_response_guard.py -v
```

## Evaluation cases (JSON)

Structured expectations live in [`assistant_response_guard_cases.json`](assistant_response_guard_cases.json). Each entry is one `apply()` scenario: `input`, `banned_terms`, and `expected` output after emoji and optional vocabulary fixes.

Add rows to that file when you want new regression cases; `test_service_apply_matches_eval_cases` parametrizes over them.

## LLM-as-judge: google_search agent

[`test_google_search_judge.py`](test_google_search_judge.py) evaluates the
[`google_search`](../agents/google_search.py) sub-agent end-to-end. For each
`(destination, nationality)` case it:

1. Runs the agent and applies **deterministic** structural checks (required section
   headers present, numbered attraction count) via
   [`google_search_judge.py`](google_search_judge.py).
2. Asks a separate Gemini **judge agent** (`output_schema=JudgeVerdict`) to score the
   output 1–5 on: nationality-specific entry advice, entry completeness, airport
   usefulness, attractions quality, factual plausibility, and overall usefulness.

Both the agent under test and the judge make **real Vertex AI calls**, so the suite is
**skipped unless `TRAVEL_HELPER_RUN_LLM_EVAL` is set** (needs the same ADC + Vertex
config as running the agent — see [setup.md](../../setup.md)).

```shell
TRAVEL_HELPER_RUN_LLM_EVAL=1 pytest travel_helper/eval/test_google_search_judge.py -v -s
```

Cases and per-dimension thresholds live in
[`google_search_judge_cases.json`](google_search_judge_cases.json); a case may override
any default threshold. Use `-s` to print each case's scores and the judge's reasoning.

## Related

- ADK agent eval flows (LLM + tools): see [Evaluate Agents](../docs/evaluate_agents.md).
