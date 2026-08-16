# Limina AI — Python Monitor SDK

[![PyPI version](https://badge.fury.io/py/limina-monitor.svg)](https://badge.fury.io/py/limina-monitor)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

Lightweight Python client SDK for streaming multi-turn AI Agent execution traces to Limina AI.

---

## Installation

```bash
pip install limina-monitor
```

## Quickstart

You can test the SDK immediately using our public sandbox key (`limina_test_key_999`):

```python
from limina import LiminaMonitor

# 1. Initialize client (Use the sandbox key or your private organization key)
limina = LiminaMonitor(api_key="limina_test_key_999",export_html = True)

# 2. Trace external tool/database execution
@limina.trace_tool(tool_name="sql_database")
def query_database(user_id: str):
    return {"status": "active", "plan": "pro"}

# 3. Trace top-level AI agent function
@limina.trace(session_id="customer_run_1", description="Support Agent Test")
def my_agent(user_prompt: str):
    user_info = query_database("usr_101")
    return f"User plan is {user_info['plan']}."

if __name__ == "__main__":
    response = my_agent("What is my current subscription plan?")
    print(response)
```

> **Note on Beta API Keys:** The public sandbox key connects to our shared demo workspace. To request a dedicated private API key for your team or organization, send a DM on [LinkedIn](https://www.linkedin.com/in/lucianblidar/) or open an issue on this repository.

## What You Get

When you trace your agent, Limina generates:

1. **Terminal Diagnostics:** Instant health score ratings (`[A]` to `[F]`), latency tracking, and token cost estimations.
2. **Interactive HTML Artifact (`report.html`):** A standalone visual DAG inspector you can open in any browser to inspect the execution graph and side-by-side failure diffs.
3. **Self-Healing Prompt Patches:** Automated `git diff` suggestions to fix detected RAG hallucinations or policy violations directly in your codebase.

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

### 3. `limina.evaluate_logs(file_path)`
Evaluates an entire historical JSON log file containing multiple conversation trajectories.
* `file_path` *(str)*: Path to the `.json` log file.
* **Returns**: A structured evaluation report dictionary.

```python
# Evaluate historical chat logs at once:
report = limina.evaluate_logs("path/to/historical_logs.json")
print("Health Rating:", report["executive_summary"]["health_rating"])
```

## Performance & Privacy

The `limina-monitor` SDK streams trace graphs in non-blocking daemon background threads, adding **0ms latency** to your production application. If network errors occur, the SDK fails silently to ensure your host application remains unaffected in production.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
