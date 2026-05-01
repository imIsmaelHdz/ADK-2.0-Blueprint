# Currency Agent Evaluation

This folder now supports two evaluation approaches:

1. Built-in metric-based ADK eval (`tool_trajectory_avg_score` and `response_match_score`).
2. A custom **LLM-as-a-Judge** framework with rubric-based scoring.

Use the built-in metrics for fast regression checks and use LLM Judge for richer quality assessment (format, honesty, and intent fulfillment).

---

## LLM-as-a-Judge framework

### What it evaluates

The judge scores each eval case across weighted dimensions:

- `task_fulfillment`: did the response satisfy the conversion request?
- `tool_usage`: did the agent use `convert_currency` correctly?
- `format_compliance`: did it follow the expected response format/fallback?
- `safety_and_honesty`: did it avoid inventing unavailable rates?

Config is defined in `llm_judge_config.json`.

### Files

- `llm_judge_eval.py`: runs the eval cases, executes the currency agent, and asks an LLM to grade each case.
- `llm_judge_config.json`: model, threshold, rubric dimensions, and weights.
- `llm_judge_results.json`: generated report (created after execution).

### Run

From the repository root:

```shell
python -m travel_helper.sub_agents.currency.eval.llm_judge_eval \
  --evalset_path travel_helper/sub_agents/currency/eval/test.evalset.json \
  --config_path travel_helper/sub_agents/currency/eval/llm_judge_config.json \
  --output_path travel_helper/sub_agents/currency/eval/llm_judge_results.json
```

Optional model override:

```shell
python -m travel_helper.sub_agents.currency.eval.llm_judge_eval --judge_model gemini-2.5-pro
```

Expected output:

- Console summary with `total_cases`, `avg_score`, `pass_rate`.
- Detailed per-case report in `llm_judge_results.json`.

### How scoring works

For each eval case:

1. Read user prompt + reference response + expected tool trajectory from the eval set.
2. Re-run the `currency_agent` on the same prompt.
3. Capture final response and actual tool calls.
4. Send both expected and actual outputs to the judge LLM using the rubric.
5. Compute weighted overall score and pass/fail from `pass_threshold`.

---

## Existing metric-based ADK eval

The currency agent converts from one currency to another using the `convert_currency` tool.

To make sure it uses the `convert_currency` tool, we can use the `tool_trajectory_avg_score` metric and its response
can be evaluated with `response_match_score` metric.

## Evaluation set

First, let's create a couple of reference user sessions and save as evaluation cases. You can create this manually but using the 
`adk web` tool is the easiest. 

Inside the [sub_agents](../../../sub_agents) folder, start the `adk web`: 

```shell
adk web
```

Select the `currency` agent.


### Evaluation case 1

For the first evaluation case, type `Convert British Pounds to US Dollars`. 

You should see a call to `convert_currency` tool and get a response like this: 

```shell
1 British Pounds (GBP) = 1.3497 US Dollars (USD)
```

Save this as an evaluation case in a new evaluation set:

1. Go to `Eval` tab.
2. Select `Create Evaluation Set` and give it a name `test`. This creates a `test.evalset.json` file.
3. Click on the `test` eval set, select `Add current session to greeter`, and give the eval case a name `case_gbp_usd`. 

At this point, you should have eval case `case_gbp_usd` added to the eval set `test.evalset.json`.

### Evaluation case 2

Before you continue, refresh the browser page for `adk web` tool, so you get a fresh session that we can save as an 
evaluation case.

For the second evaluation case, let's use a negative case. The `convert_currency` tool does not know about United Arab 
Emirates Dirham. Type `Convert British Pounds to UAE Dirhams`. 

You should see a call to `convert_currency` tool and get a response like this: 

```shell
I'm sorry, I cannot convert from GBP to AED
```

Save this as an evaluation case in a new evaluation set with `case_gbp_aed` name like before:

At this point, you should have another eval case `case_gbp_aed` added to the eval set `test.evalset.json`.

## Evaluation criteria

Next, define the evaluation criteria in a configuration file. In this case, we want to see if the response
is similar to the reference response in the eval set and we also want to make sure the `convert_currency` tool is used. 

Define a `test_config.json` file as follows:

```json
{
  "criteria": {
    "tool_trajectory_avg_score": 1.0,
    "response_match_score": 0.8
  }
}
```

`tool_trajectory_avg_score` metric compares the agent's actual tool usage during the evaluation against the expected tool 
usage. Each matching tool usage step receives a score of 1, while a mismatch receives a score of 0. 
The final score is the average of these matches, representing the accuracy of the tool usage trajectory.

`response_match_score` metric compares the agent's response to the expected response using the ROUGE similarity metric.

## Run evaluation

Time to run evaluation. 

Inside the [sub_agents](../../../sub_agents) folder:

```shell
adk eval currency \
  currency/eval/test.evalset.json \
  --config_file_path currency/eval/test_config.json \
  --print_detailed_results
```

You should get a response like this:

```shell
Using evaluation criteria: {'tool_trajectory_avg_score': 1.0, 'response_match_score': 0.8}
Running Eval: currency:case_gbp_usd
Warning: there are non-text parts in the response: ['function_call'], returning concatenated text result from text parts. Check the full candidates.content.parts accessor to get the full model response.
Computing metrics with a total of 1 Vertex Gen AI Evaluation Service API requests.
All 1 metric requests are successfully computed.
Evaluation Took:0.623047833039891 seconds
Result: ✅ Passed

Running Eval: currency:case_gbp_aed
Warning: there are non-text parts in the response: ['function_call'], returning concatenated text result from text parts. Check the full candidates.content.parts accessor to get the full model response.
HTTP error occurred: 404 Client Error: Not Found for url: https://api.frankfurter.dev/v1/latest?base=GBP&symbols=AED
Computing metrics with a total of 1 Vertex Gen AI Evaluation Service API requests.
All 1 metric requests are successfully computed.
Evaluation Took:0.6156062500085682 seconds
Result: ✅ Passed
```