# Limina AI — Python SDK

[![PyPI Version](https://img.shields.io/pypi/v/limina-ai.svg)](https://pypi.org/project/limina-ai/)
[![GitHub Action](https://img.shields.io/badge/GitHub_Action-v1-blue.svg)](https://github.com/Limina-ai/limina-python/actions)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python Versions](https://img.shields.io/pypi/pyversions/limina-ai.svg)](https://pypi.org/project/limina-ai/)

> Local evaluation, agent observability, and CI/CD regression testing for AI agents.
> Run deterministic evaluations without sending every evaluation to a third-party LLM judge.

Limina is a Python SDK for tracing, evaluating, comparing, and regression-testing
multi-turn AI agent workloads.

It provides:

- Real-time agent and tool tracing
- Historical transcript evaluation
- Baseline vs. candidate regression comparison
- CI/CD regression gating
- State-Space DAG diagnostics
- Adversarial stress testing
- Standalone interactive HTML reports
- OpenAI and LangSmith / LangChain log adapters
- Configurable evaluation profiles and policies

## Table of Contents

- [Installation](#installation)
- [Quickstart](#quickstart)
- [Core Concepts](#core-concepts)
- [Tracing](#tracing)
- [Tool Tracing](#tool-tracing)
- [Historical Log Evaluation](#historical-log-evaluation)
- [Regression Comparison](#regression-comparison)
- [CI/CD Gating](#cicd-gating)
- [Adversarial Stress Testing](#adversarial-stress-testing)
- [Standalone HTML Reports](#standalone-html-reports)
- [Profiles and Policy Configuration](#profiles-and-policy-configuration)
- [Log Adapters](#log-adapters)
- [Output Format](#output-format)
- [Async Support](#async-support)
- [API Reference](#api-reference)
- [Troubleshooting](#troubleshooting)
- [Privacy and Security](#privacy-and-security)
- [Examples](#examples)
- [Benchmark Context](#benchmark-context)
- [License](#license)

# Installation

Install the latest published package:

```bash
pip install limina-ai
```

Or install the development version directly from GitHub:

```bash
pip install git+https://github.com/limina-ai/limina-python.git
```

Set your API key through the environment:

```bash
export LIMINA_API_KEY="limina_live_..."
```

You can also pass the API key directly when initializing `LiminaMonitor`.

# Quickstart

## 1. Create a monitor

```python
from limina import LiminaMonitor

monitor = LiminaMonitor()
```

To also generate a standalone local HTML report:

```python
monitor = LiminaMonitor(export_html=True)
```

## 2. Trace an agent

Wrap your agent function with `@monitor.trace`:

```python
from limina import LiminaMonitor
from openai import OpenAI

client = OpenAI()
monitor = LiminaMonitor(export_html=True)

@monitor.trace(session_id="session_order_check")
def support_agent(user_query: str):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": user_query
            }
        ]
    )

    return response.choices[0].message.content

response = support_agent("Can I return an item after 30 days?")

monitor.flush()
```

Limina captures agent execution telemetry and dispatches trace data
asynchronously.

Call `monitor.flush()` before application shutdown to ensure queued trace
uploads have completed.

# Core Concepts

Limina is organized around four main workflows:

### Observe

Trace multi-turn agent execution, state transitions, tool calls, execution
duration, and structured payloads.

### Evaluate

Evaluate existing transcripts and structured agent logs using the Limina
evaluation engine.

### Compare

Compare a baseline dataset against a candidate dataset and classify outcomes
into four categories:

- Fixed Scenarios
- New Regressions
- Persistent Failures
- Stable Passing

### Gate

Use regression results inside CI/CD and fail builds when previously passing
scenarios regress.

# Tracing

## Agent tracing

Use `@monitor.trace` to trace agent execution:

```python
from limina import LiminaMonitor

monitor = LiminaMonitor()

@monitor.trace(
    session_id="session_001",
    description="Support Agent Run"
)
def support_agent(user_input: str):
    return "Our return policy is 14 days."

support_agent("Can I return my order after 30 days?")

monitor.flush()
```

The trace decorator captures execution duration, state transitions, user
inputs, and agent generations.

Trace uploads are dispatched asynchronously.

# Tool Tracing

Use `@monitor.trace_tool` to instrument deterministic tools, database lookups,
or API clients:

```python
from limina import LiminaMonitor

monitor = LiminaMonitor()

@monitor.trace_tool(tool_name="database_policy_lookup")
def query_policy(order_id: str):
    return {
        "max_return_days": 14,
        "allow_cash": False
    }

@monitor.trace(session_id="session_order_check")
def support_agent(user_input: str):
    policy = query_policy("ORD-101")

    return f"Return window: {policy['max_return_days']} days."

support_agent("I want a refund.")

monitor.flush()
```

Tool tracing records structured inputs / outputs and measures tool execution
latency.

# Historical Log Evaluation

`evaluate_logs()` accepts supported historical agent data and can operate on
local JSON files, in-memory structures, and supported transcript formats.

## Evaluate an in-memory OpenAI transcript

```python
from limina import LiminaMonitor

monitor = LiminaMonitor()

openai_messages = [
    {
        "role": "user",
        "content": "Can I return an item after 45 days?"
    },
    {
        "role": "tool",
        "content": "{\"max_days\": 14, \"cash_refund\": false}"
    },
    {
        "role": "assistant",
        "content": "Returns are strictly limited to 14 days."
    }
]

report = monitor.evaluate_logs(openai_messages)

print(
    report["executive_summary"]["health_rating"]
)
```

## Evaluate a local JSON file

```python
report = monitor.evaluate_logs(
    "logs/production_traces.json"
)

print(report["executive_summary"])
```

# Regression Comparison

When changing prompts, models, or agent logic, compare a known-good baseline
against a candidate dataset.

```python
from limina import LiminaMonitor

monitor = LiminaMonitor()

diff_report = monitor.compare(
    baseline_logs="tests/baseline.json",
    candidate_logs="tests/candidate.json",
    fail_on_regression=True
)

analysis = diff_report["regression_analysis"]

print(
    f"Verdict: {analysis['verdict']}"
)

print(
    f"Gate: {analysis['ci_gate_status']}"
)

print(
    f"Delta Accuracy: "
    f"{analysis['metrics']['delta_accuracy_percentage']:+0.1f}%"
)

print(
    f"Regressions: "
    f"{analysis['breakdown']['new_regressions_count']}"
)
```

## Regression categories

### Fixed Scenarios

Previously failing scenarios that now pass.

### New Regressions

Previously passing scenarios that fail after the change.

### Persistent Failures

Scenarios that fail in both baseline and candidate.

### Stable Passing

Scenarios that pass in both versions.

# CI/CD Gating

Limina can be used as a CI gate so a regression causes the build to fail.

Create a workflow such as:

`.github/workflows/limina.yml`

```yaml
name: Limina AI Regression Gate

on: [pull_request]

permissions:
  pull-requests: write
  contents: read

jobs:
  regression-gate:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: limina-ai/limina-python@v1
        with:
          api-key: ${{ secrets.LIMINA_API_KEY }}
          baseline: 'tests/eval_datasets/baseline_golden.json'
          candidate: 'tests/eval_datasets/candidate_patch.json'
          fail-on-regression: 'true'
          github-token: ${{ secrets.GITHUB_TOKEN }}
```

When a regression is detected, the action can publish a regression report to
the pull request and fail the job with exit code `1`.

Example report:

```text
### [Limina AI] Regression Report

Gate Status: BLOCKED (REGRESSION_DETECTED)

| Metric | Baseline | Candidate | Delta |
| :--- | :--- | :--- | :--- |
| Factual Accuracy | 100.0% | 50.0% | -50.0% |
| Mean Latency | 120.0ms | 120.0ms | +0.0ms |

- Fixed Scenarios: 0
- New Regressions: 1 (test_warranty_check)

Recommendation:
DO NOT SHIP: 1 previously passing scenario broke after prompt patch.
```

# Adversarial Stress Testing

Enable adversarial testing through:

```python
report = monitor.evaluate_logs(
    "dataset.json",
    run_stress_test=True
)
```

The stress-testing suite includes:

- QWERTY keyboard typos
- Character perturbations
- System override / jailbreak-style prompt injection

Example:

```python
summary = report["executive_summary"]

print(
    f"Robustness Health: "
    f"{summary['health_rating']}"
)

print(
    f"Score: "
    f"{summary['success_rate_percentage']}%"
)
```

# Standalone HTML Reports

Enable local report generation with:

```python
monitor = LiminaMonitor(
    export_html=True
)
```

Then evaluate a dataset:

```python
monitor.evaluate_logs(
    "logs/agent_transcript.json"
)
```

Limina generates a standalone `report.html` file locally.

The report can include:

- Interactive State-Space DAG visualization
- Execution / latency visualization
- Tool premise vs. agent claim inspection
- Diagnostic output

The report can be opened locally without relying on the cloud dashboard.

# Profiles and Policy Configuration

Limina supports predefined evaluation profiles:

- `standard`
- `banking`
- `healthcare`
- `customer_support`
- `creative`

Initialize with a profile:

```python
monitor = LiminaMonitor(
    profile="banking"
)
```

Or switch profiles at runtime:

```python
monitor.set_profile("healthcare")
```

## `limina.yaml`

Use a `limina.yaml` file to define project-level evaluation settings.

Example:

```yaml
strictness_profile: "banking"

max_sentences: 14

max_tool_latency_ms: 2000.0

custom_rules:
  forbidden_words:
    - "competitorxyz"
    - "guaranteed profit"

  required_words:
    - "terms apply"
```

# Log Adapters

Limina includes a `LogAdapter` for standardizing supported third-party agent
transcripts into Limina trajectory structures.

## OpenAI

```python
from limina import LogAdapter

trajectories = LogAdapter.from_openai(
    openai_messages,
    session_id="eval_01"
)
```

## LangSmith / LangChain

```python
trajectories = LogAdapter.from_langsmith(
    langsmith_run_dict
)
```

## Automatic conversion

```python
trajectories = LogAdapter.auto_convert(
    "logs/production_traces.json"
)
```

Supported automatic conversion inputs include compatible JSON file paths,
lists, dictionaries, OpenAI message structures, and LangSmith-compatible run
data.

# Output Format

Evaluation and comparison methods return JSON-serializable Python dictionaries.

## Executive summary

```json
{
  "executive_summary": {
    "health_rating": "A",
    "success_rate_percentage": 100.0,
    "most_vulnerable_component": "NONE",
    "total_nodes": 3,
    "errors_detected": 0
  }
}
```

## Regression analysis

```json
{
  "regression_analysis": {
    "verdict": "IMPROVED",
    "ci_gate_status": "PASSED",
    "metrics": {
      "baseline_accuracy": 50.0,
      "candidate_accuracy": 100.0,
      "delta_accuracy_percentage": 50.0,
      "baseline_latency_ms": 190.0,
      "candidate_latency_ms": 185.0,
      "delta_latency_ms": -5.0,
      "delta_tokens": 15,
      "delta_cost_usd": 0.000045
    },
    "breakdown": {
      "fixed_count": 1,
      "new_regressions_count": 0,
      "persistent_failures_count": 0,
      "stable_passing_count": 1
    }
  }
}
```

# Async Support

`@monitor.trace` and `@monitor.trace_tool` support both synchronous and
asynchronous functions.

### Synchronous

```python
@monitor.trace()
def agent(...):
    ...
```

### Asynchronous

```python
@monitor.trace()
async def agent(...):
    ...
```

The same applies to tool tracing:

```python
@monitor.trace_tool("my_tool")
async def tool(...):
    ...
```

Because trace dispatch is asynchronous, call:

```python
monitor.flush()
```

before application shutdown to wait for pending trace uploads.

---

# API Reference

## `LiminaMonitor`

Primary SDK entry point.

### Initialization

```python
LiminaMonitor(
    api_key: Optional[str] = None,
    profile: str = "standard",
    export_html: bool = False,
    host: Optional[str] = None
)
```

### `trace()`

Decorator for agent execution functions.

```python
@monitor.trace(
    session_id="session_001",
    description="Support Agent"
)
def agent(...):
    ...
```

### `trace_tool()`

Decorator for tools and external calls.

```python
@monitor.trace_tool(
    tool_name="database_lookup"
)
def lookup(...):
    ...
```

### `evaluate()`

Evaluate pre-structured trajectory data.

```python
monitor.evaluate(payload)
```

### `evaluate_logs()`

Evaluate supported historical logs, transcripts, files, or in-memory
structures.

```python
monitor.evaluate_logs(
    input_data,
    source="auto"
)
```

### `compare()`

Compare baseline and candidate datasets.

```python
monitor.compare(
    baseline_logs,
    candidate_logs,
    source="auto",
    fail_on_regression=False
)
```

### `set_profile()`

Change the active profile:

```python
monitor.set_profile("healthcare")
```

### `flush()`

Wait for pending background trace dispatch to complete:

```python
monitor.flush()
```

# Troubleshooting

## Traces are not appearing

Trace uploads run asynchronously.

Before the process exits:

```python
monitor.flush()
```

This ensures pending trace uploads have completed.

## Async agents

Both synchronous and asynchronous agent functions are supported:

```python
@monitor.trace()
async def agent(...):
    ...
```

## CI build is not failing on regressions

Make sure:

```python
fail_on_regression=True
```

is enabled.

When a previously passing scenario becomes a regression, the comparator
raises a `RuntimeError`, allowing CI systems such as GitHub Actions or pytest
to fail the build.

# Examples

The repository contains example scripts for common workflows:

```text
examples/
├── basic_tracing.py
├── openai_agent.py
├── langsmith_adapter.py
├── regression_diff.py
└── github_action/
```

These examples cover:

- Agent tracing
- OpenAI tool-calling
- LangSmith / LangChain ingestion
- Baseline vs. candidate regression comparison
- GitHub Actions CI/CD gating

# Privacy and Security

Limina documents the following security properties:

### Zero Data Retention

Conversation transcripts and tool outputs are processed ephemerally in memory
and are not persisted to disk.

### No Foundation Model Training

Customer prompts, system instructions, and evaluation data are not used to
train or fine-tune AI models.

### API Key Isolation

API secret keys are stored as irreversible SHA-256 hashes.

### Enterprise On-Premise

Air-gapped self-hosted Docker deployment is available on request for
enterprise tiers.

# Benchmark Context

The Week 1 private beta benchmark was based on:

- 175+ unique evaluation test cases
- Tester-contributed datasets
- Real agent workloads
- Synthetic failure fixtures
- Repeated evaluation runs
- Aggregated live LLM judge configurations

The reported Week 1 results were:

| Metric | Start of Beta | After Week 1 | Mean Live LLM Judge |
| :--- | ---: | ---: | ---: |
| Factual Accuracy | 83.0% | **98.0%** | ~87.8% |
| Failure Recall | 72.5% | **100.0% (43/43)** | ~87.3% |
| F1-Score | 0.70 | **0.963** | ~0.86 |
| Mean Latency | 3.8s | **1.6x–6x faster** | ~8.03s |
| Consistency | 100% | **100%** | ~80% |
| Evaluation Cost | $0.00 | **$0.00 local CPU** | Token-based cost |

These figures are private-beta measurements rather than universal performance
guarantees. Speedup depends on agent complexity, tool execution duration, and
context length.

# License

Distributed under the
[Apache-2.0 License](LICENSE).
