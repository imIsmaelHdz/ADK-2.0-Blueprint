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

## Related

- ADK agent eval flows (LLM + tools): see [Evaluate Agents](../docs/evaluate_agents.md) and sub-agent folders such as [`greeter/eval`](../sub_agents/greeter/eval).
