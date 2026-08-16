# Limina AI — Python Monitor SDK

[![PyPI version](https://badge.fury.io/py/limina-monitor.svg)](https://badge.fury.io/py/limina-monitor)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

Lightweight Python client SDK for local-first, deterministic AI Agent evaluation, multi-turn trajectory monitoring, and automated prompt remediation.

---

## Installation

```bash
pip install limina-monitor
```

---

## Quickstart

No API key or cloud registration required. Limina evaluates multi-turn agent traces locally on your machine by default:

```python
from limina import LiminaMonitor

# 1. Initialize local monitor with a domain profile (zero configuration required)
limina = LiminaMonitor(profile="banking")

# 2. Trace external tool/database execution
@limina.trace_tool(tool_name="sql_database")
def query_database(user_id: str):
    return {"status": "active", "cash_refund_limit_days": 14}

# 3. Trace top-level AI agent function
@limina.trace(session_id="customer_run_1", description="Support Agent Test")
def my_agent(user_prompt: str):
    user_info = query_database("usr_101")
    return "Refund processed."

if __name__ == "__main__":
    response = my_agent("Can I get a refund for an item bought 30 days ago?")
    print(response)
```

> **Optional Cloud Dashboard Sync:** If you want to sync your traces to your team's central web dashboard on Limina AI, provide your organization API key: `LiminaMonitor(api_key="your_api_key")`.

## What You Get

When you trace your agent, Limina generates:

1. **Terminal Diagnostics:** Instant health score ratings (`[A]` to `[F]`), latency tracking, and token cost estimations.
2. **Interactive HTML Artifact (`report.html`):** A standalone visual DAG inspector you can open in any browser to inspect the execution graph, node latencies, and side-by-side failure diffs.
3. **Self-Healing Prompt Patches:** Automated `git diff` suggestions to fix detected RAG hallucinations or policy violations directly in your codebase.


## Built-In Domain Profiles

You can select a pre-configured strictness profile directly in Python:

```python
# 1. Banking & Fintech (0.5x Z-Score tolerance, strict 2000ms tool latency, mandatory disclaimers)
limina = LiminaMonitor(profile="banking")

# 2. Healthcare & HIPAA (0.6x tolerance, strict PHI/PII leak scanning, medical grounding)
limina = LiminaMonitor(profile="healthcare")

# 3. Customer Support (1.0x tolerance, strict sentence count limit, brand safety filters)
limina = LiminaMonitor(profile="customer_support")

# 4. Creative & Storytelling (1.5x relaxed tolerance for high variance outputs)
limina = LiminaMonitor(profile="creative")
```


## Universal Log Adapter (OpenAI & LangSmith Ingestion)

Evaluate historical logs from OpenAI API, LangSmith, or LangChain without rewriting your log formats:

```python
from limina import LiminaMonitor, LogAdapter

limina = LiminaMonitor(profile="banking")

# 1. Evaluate historical JSON logs directly
report = limina.evaluate_logs("path/to/historical_logs.json")

# 2. Convert raw OpenAI ChatCompletion message history
raw_openai_messages = [
    {"role": "user", "content": "Check order status"},
    {"role": "assistant", "tool_calls": [{"function": {"name": "get_order", "arguments": "{\"id\": \"123\"}"}}]},
    {"role": "tool", "content": "{\"status\": \"shipped\"}"},
    {"role": "assistant", "content": "Your order has been shipped."}
]
trajectory_dag = LogAdapter.from_openai(raw_openai_messages)
report = limina.evaluate_logs([trajectory_dag])
```

## SDK Reference & Methods

### 1. `@limina.trace(session_id, description)`
Wraps top-level AI agent functions to capture input prompts, final outputs, and execution duration.
* `session_id` *(str, optional)*: Unique identifier for the conversation trace (default: `"default_session"`).
* `description` *(str, optional)*: Short description of the scenario or test case.

```python
@limina.trace(session_id="checkout_flow_01", description="Refund Request Test")
def run_agent(prompt: str):
    return "Agent response..."
```

### 2. `@limina.trace_tool(tool_name)`
Wraps database queries, API calls, or RAG retrieval tools executed by your agent.
* `tool_name` *(str, optional)*: Name of the external tool (default: `"custom_tool"`).

```python
@limina.trace_tool(tool_name="database_sql_query")
def fetch_user_orders(user_id: str):
    return {"order_id": "12345", "status": "shipped"}
```


### 3. `limina.evaluate_logs(input_data)`
Evaluates an entire historical JSON log file or a list of converted trajectories.
* `input_data` *(str | list)*: Path to `.json` file or list of trajectory dictionaries.
* **Returns**: A structured evaluation report dictionary.

```python
report = limina.evaluate_logs("my_agent_logs.json")
print("Health Rating:", report["executive_summary"]["health_rating"])
```


## Performance & Privacy

The `limina-monitor` SDK evaluates trace graphs in non-blocking daemon background threads, adding **0ms latency** to your production application. If network errors occur, the SDK fails silently to ensure your host application remains unaffected in production.


## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.