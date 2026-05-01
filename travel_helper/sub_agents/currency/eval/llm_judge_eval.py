import argparse
import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

from travel_helper.sub_agents.currency.agent import root_agent as currency_agent


@dataclass
class AgentRunResult:
    response_text: str
    tool_calls: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run LLM-as-a-Judge evaluation for the currency sub-agent."
    )
    parser.add_argument(
        "--evalset_path",
        default="travel_helper/sub_agents/currency/eval/test.evalset.json",
        help="Path to the eval set JSON file.",
    )
    parser.add_argument(
        "--config_path",
        default="travel_helper/sub_agents/currency/eval/llm_judge_config.json",
        help="Path to LLM judge configuration JSON file.",
    )
    parser.add_argument(
        "--output_path",
        default="travel_helper/sub_agents/currency/eval/llm_judge_results.json",
        help="Where to write the final evaluation report.",
    )
    parser.add_argument(
        "--judge_model",
        default=None,
        help="Optional override for the judge model.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def extract_text(content_obj: dict[str, Any] | None) -> str:
    if not content_obj:
        return ""
    parts = content_obj.get("parts", [])
    texts = [p.get("text", "") for p in parts if p.get("text")]
    return "\n".join(texts).strip()


def extract_expected_tools(conversation_turn: dict[str, Any]) -> list[str]:
    tools = (
        conversation_turn.get("intermediate_data", {})
        .get("tool_uses", [])
    )
    names = [tool.get("name", "") for tool in tools if tool.get("name")]
    return sorted(set(names))


def parse_judge_response(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```json", "").replace("```", "").strip()
    return json.loads(cleaned)


def weighted_score(scores: dict[str, float], dimensions: dict[str, Any]) -> float:
    total = 0.0
    for name, definition in dimensions.items():
        total += float(scores.get(name, 0.0)) * float(definition.get("weight", 0.0))
    return round(total, 4)


async def run_agent_for_prompt(runner: Runner, user_id: str, session_id: str, prompt: str) -> AgentRunResult:
    content = Content(role="user", parts=[Part(text=prompt)])
    response_text = ""
    tool_calls: list[str] = []

    async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.function_call and part.function_call.name:
                    tool_calls.append(part.function_call.name)
                if event.is_final_response() and part.text:
                    response_text += part.text

        if event.is_final_response():
            break

    return AgentRunResult(response_text=response_text.strip(), tool_calls=tool_calls)


def build_judge_prompt(
    user_prompt: str,
    expected_response: str,
    actual_response: str,
    expected_tools: list[str],
    actual_tools: list[str],
    config: dict[str, Any],
) -> str:
    dimensions = config["dimensions"]
    return f"""
You are an expert evaluator for an AI currency conversion assistant.
Score the assistant using the rubric below. Each dimension score must be a float in [0.0, 1.0].

Rubric dimensions and weights:
{json.dumps(dimensions, indent=2)}

Context:
- User request: {user_prompt}
- Expected response (reference): {expected_response}
- Actual response: {actual_response}
- Expected tool calls: {expected_tools}
- Actual tool calls: {actual_tools}

Evaluation policy:
1) Prefer factual correctness and user intent completion.
2) Penalize missing `convert_currency` call if conversion was attempted.
3) Penalize invented rates when data is unavailable.
4) Accept small wording differences if meaning and format are compliant.
5) If output is malformed or ambiguous, reduce format_compliance.

Return ONLY strict JSON in this schema:
{{
  "dimension_scores": {{
    "task_fulfillment": <float 0..1>,
    "tool_usage": <float 0..1>,
    "format_compliance": <float 0..1>,
    "safety_and_honesty": <float 0..1>
  }},
  "rationale": "<short explanation>",
  "issues": ["<issue1>", "<issue2>"]
}}
""".strip()


async def run() -> None:
    load_dotenv()
    args = parse_args()

    evalset_path = Path(args.evalset_path)
    config_path = Path(args.config_path)
    output_path = Path(args.output_path)

    evalset = load_json(evalset_path)
    config = load_json(config_path)
    judge_model = args.judge_model or config["judge_model"]
    pass_threshold = float(config["pass_threshold"])

    client = genai.Client()
    session_service = InMemorySessionService()
    runner = Runner(
        agent=currency_agent,
        app_name="currency_llm_judge_eval",
        session_service=session_service,
    )

    case_results: list[dict[str, Any]] = []
    for idx, case in enumerate(evalset.get("eval_cases", [])):
        eval_id = case.get("eval_id", f"case_{idx}")
        turn = case.get("conversation", [{}])[0]
        user_prompt = extract_text(turn.get("user_content"))
        expected_response = extract_text(turn.get("final_response"))
        expected_tools = extract_expected_tools(turn)

        user_id = f"judge_user_{idx}"
        session_id = f"judge_session_{idx}"
        await session_service.create_session(
            app_name="currency_llm_judge_eval",
            user_id=user_id,
            session_id=session_id,
        )
        run_result = await run_agent_for_prompt(runner, user_id, session_id, user_prompt)

        prompt = build_judge_prompt(
            user_prompt=user_prompt,
            expected_response=expected_response,
            actual_response=run_result.response_text,
            expected_tools=expected_tools,
            actual_tools=run_result.tool_calls,
            config=config,
        )

        response = client.models.generate_content(
            model=judge_model,
            contents=prompt,
        )
        judge_json = parse_judge_response(response.text or "{}")
        dim_scores = judge_json.get("dimension_scores", {})
        overall = weighted_score(dim_scores, config["dimensions"])
        passed = overall >= pass_threshold

        case_results.append(
            {
                "eval_id": eval_id,
                "user_prompt": user_prompt,
                "expected_response": expected_response,
                "actual_response": run_result.response_text,
                "expected_tools": expected_tools,
                "actual_tools": run_result.tool_calls,
                "judge_model": judge_model,
                "judge_result": judge_json,
                "overall_score": overall,
                "pass_threshold": pass_threshold,
                "verdict": "pass" if passed else "fail",
            }
        )

    avg_score = round(
        sum(float(item["overall_score"]) for item in case_results) / max(len(case_results), 1),
        4,
    )
    pass_rate = round(
        sum(1 for item in case_results if item["verdict"] == "pass") / max(len(case_results), 1),
        4,
    )

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "eval_set_id": evalset.get("eval_set_id"),
        "judge_model": judge_model,
        "pass_threshold": pass_threshold,
        "summary": {
            "total_cases": len(case_results),
            "avg_score": avg_score,
            "pass_rate": pass_rate,
        },
        "cases": case_results,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(json.dumps(report["summary"], indent=2))
    print(f"Detailed report written to: {output_path}")


if __name__ == "__main__":
    asyncio.run(run())
