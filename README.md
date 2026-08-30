# Limina AI — Python SDK & CI/CD Regression Gate

[![PyPI Version](https://img.shields.io/pypi/v/limina-ai.svg)](https://pypi.org/project/limina-ai/)
[![GitHub Action](https://img.shields.io/badge/GitHub_Action-v1-blue.svg)](https://github.com/Limina-AI/limina-python/actions)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python Versions](https://img.shields.io/pypi/pyversions/limina-ai.svg)](https://pypi.org/project/limina-ai/)

> Local evaluation, agent observability, and CI/CD regression testing for AI agents.
> Run fast, deterministic evaluations without sending every test to a third-party LLM judge.

## Why Limina?

Evaluating AI agents with a generative LLM judge introduces three major bottlenecks in production CI/CD pipelines:
1. **Flaky assertions:** Probabilistic judges return non-deterministic scores on identical test cases (~80% consistency).
2. **High latency:** Generative judges add 6–10 seconds per test case, stalling pull request pipelines.
3. **Double token costs:** Paying model API fees twice—once for the agent execution, and once for the evaluation judge.

Limina formalizes execution transcripts into a **State-Space DAG** and runs calibrated Cross-Encoder Natural Language Inference (NLI) models locally on CPU:
- **$0 Third-Party Judge API Cost:** Runs entirely on local CPU with zero third-party judge token bills.
- **Low-Latency Execution:** 1.6x to 6x measured speedups compared to generative judges across our beta test setups.
- **100% Deterministic:** Same input + same context = exact same assertion verdict every single run.
- **Automated CI/CD Gating:** Automatically comments on Pull Requests and blocks merges (`exit code 1`) if a prompt tweak breaks previously passing scenarios.

## Benchmark Results (Week 1 Private Beta)

Mean results across 175+ unique evaluation test cases contributed by beta testers, including real agent workloads and synthetic failure fixtures:

| Metric | At Start of Beta | After 1 Week (Now) | Mean Live LLM Judge |
| :--- | :--- | :--- | :--- |
| **Factual Accuracy** | 83.0% | **98.0% ↗** | ~87.8% |
| **Failure Recall** | 72.5% | **100.0% ↗ (43/43 caught)** | ~87.3% |
| **F1-Score** | 0.70 | **0.963 ↗** | ~0.86 |
| **Mean Latency** | 3.8s | **1.6x to 6x faster\*** | ~8.03s |
| **Consistency** | 100% (Deterministic) | **100% (Deterministic)** | ~80% (Scores fluctuate) |
| **Evaluation Cost** | **$0.00** | **$0.00 (Local CPU)** | Paying token fees per eval |

*\* Results are aggregated from our Week 1 private beta evaluation dataset across 175+ unique evaluation test cases. LLM judge results are aggregated means across the live judge configurations used during beta testing. Speedup factor depends on agent complexity, tool execution duration, and context length.*


## Quickstart

### 1. Install SDK
```bash
pip install limina-ai
```

### 2. Set API Key
```bash
export LIMINA_API_KEY="limina_live_..."
```

### 3. Trace Your Agent
Wrap your agent functions with `@monitor.trace` and `@monitor.trace_tool`. Limina captures execution duration, tool payloads, and state transitions without altering your business logic:

```python
from limina import LiminaMonitor
from openai import OpenAI

client = OpenAI()
monitor = LiminaMonitor(export_html=True)

@monitor.trace_tool(tool_name="database_policy_lookup")
def query_policy(order_id: str):
    return {"max_return_days": 14, "allow_cash": False}

@monitor.trace(session_id="session_order_check")
def support_agent(user_query: str):
    policy = query_policy("ORD-101")
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": user_query}]
    )
    return response.choices[0].message.content

# Execute agent
response = support_agent("Can I return an item after 30 days?")

# Flush pending background trace uploads
monitor.flush()
```

## CI/CD Gating with GitHub Actions

Add automated prompt regression gating to your CI pipeline in your repository workflow (`.github/workflows/limina.yml`):

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
      - uses: Limina-AI/limina-python@v1
        with:
          api-key: ${{ secrets.LIMINA_API_KEY }}
          baseline: 'tests/eval_datasets/baseline_golden.json'
          candidate: 'tests/eval_datasets/candidate_patch.json'
          fail-on-regression: 'true'
          github-token: ${{ secrets.GITHUB_TOKEN }}
```

When a regression occurs, `limina-action` posts a 4-quadrant state matrix directly on the PR and exits with `code 1`:

```text
### [Limina AI] Regression Report
Gate Status: BLOCKED (REGRESSION_DETECTED)

| Metric | Baseline | Candidate | Delta |
| :--- | :--- | :--- | :--- |
| Factual Accuracy | 100.0% | 50.0% | -50.0% |
| Mean Latency | 120.0ms | 120.0ms | +0.0ms |

- Fixed Scenarios: 0
- New Regressions: 1 (test_warranty_check)

Recommendation: DO NOT SHIP: 1 previously passing scenario broke after prompt patch.
```

## 4-Quadrant Regression Comparator

Compare a **Baseline Golden Dataset** against a **Candidate Prompt** locally or in test suites:

```python
from limina import LiminaMonitor

monitor = LiminaMonitor()

# Compares datasets across Fixed, New Regressions, Persistent, and Stable Passing
diff_report = monitor.compare(
    baseline_logs="tests/baseline.json",
    candidate_logs="tests/candidate.json",
    fail_on_regression=True  # Raises RuntimeError on detected regressions (blocks CI merge)
)

analysis = diff_report["regression_analysis"]
print(f"Verdict     : {analysis['verdict']} (Gate: {analysis['ci_gate_status']})")
print(f"Delta Acc   : {analysis['metrics']['delta_accuracy_percentage']:+0.1f}%")
print(f"Regressions : {analysis['breakdown']['new_regressions_count']}")
```

## Advanced Diagnostics & Features

### 1. Standalone Visual HTML Reports (`export_html=True`)
Generate an interactive, single-file HTML report (`report.html`) on local disk without opening the cloud dashboard. It contains an animated State-Space DAG canvas, latency flamegraphs, and the side-by-side NLI Truth Mirror (Tool Premise vs. Agent Claim):

```python
from limina import LiminaMonitor

# Saves 'report.html' locally on every evaluation
monitor = LiminaMonitor(export_html=True)

# Run evaluations...
monitor.evaluate_logs("logs/agent_transcript.json")
```

### 2. Adversarial Red-Teaming & Fuzzing (`run_stress_test=True`)
Evaluate agent stability under adversarial conditions. Injects stochastic QWERTY keyboard typos, character perturbations, and system override jailbreaks to calculate drift deltas and robustness scores:

```python
from limina import LiminaMonitor

monitor = LiminaMonitor()

# Runs adversarial perturbation test suite
report = monitor.evaluate_logs("dataset.json", run_stress_test=True)

summary = report["executive_summary"]
print(f"Robustness Health: {summary['health_rating']} (Score: {summary['success_rate_percentage']}%)")
```

## Supported Integrations & Log Formats

`LogAdapter` automatically standardizes third-party agent transcripts into State-Space DAGs:

```python
from limina import LogAdapter

# 1. From OpenAI Tool-Calling Transcripts
trajectories = LogAdapter.from_openai(openai_messages, session_id="eval_01")

# 2. From LangSmith / LangChain Run Trees
trajectories = LogAdapter.from_langsmith(langsmith_run_dict)

# 3. Auto-detect any structure (JSON file path, list of dicts, or generic traces)
trajectories = LogAdapter.auto_convert("logs/production_traces.json")
```

## Code Examples

Explore ready-to-run scripts in our repository:

```text
examples/
├── basic_tracing.py       # Basic sync/async agent tracing with @monitor.trace
├── openai_agent.py        # OpenAI tool-calling agent with live context grounding
├── langsmith_adapter.py   # Ingesting LangSmith & LangChain run trees into Limina DAGs
├── regression_diff.py     # Comparing baseline vs. candidate prompt datasets
└── github_action/         # CI/CD regression gating workflow template
```

## Troubleshooting & Common Questions

#### 1. Why are my traces not appearing in the dashboard?
Trace uploads execute asynchronously on a background thread pool to avoid adding latency to host agent functions. Call `monitor.flush()` before your application process exits to ensure all queued traces are dispatched.

#### 2. Does Limina support asynchronous (`async def`) agent functions?
Yes. The `@monitor.trace` and `@monitor.trace_tool` decorators natively support both synchronous (`def`) and asynchronous (`async def`) functions using thread-safe context propagation.

#### 3. How does `fail_on_regression=True` work in CI/CD?
When enabled, `monitor.compare` inspects the 4-quadrant delta. If any previously passing scenario breaks (`new_regressions_count > 0`), it raises a `RuntimeError` and triggers `sys.exit(1)`, causing GitHub Actions or pytest to fail the build.

## Security, Privacy & Data Governance

- **Strict Zero Data Retention (ZDR):** Conversation transcripts and tool outputs are processed ephemerally in volatile memory (RAM) and are never persisted to disk.
- **Zero Foundation Model Training (ZMT):** Customer prompts, system instructions, and evaluation data are never used to train or fine-tune AI models.
- **Cryptographic Key Isolation:** API secret keys are stored strictly as irreversible SHA-256 cryptographic hashes.
- **Enterprise On-Premise:** Air-gapped self-hosted Docker container deployment available on request for enterprise tiers.

## License

Distributed under the [Apache-2.0 License](LICENSE).