# Limina AI — Python SDK

The deterministic diagnostic, state-space DAG reconstruction, adversarial stress-testing, and automated prompt-patching engine for multi-turn AI Agents.

## Installation

Install the official package via pip:

```bash
pip install limina-ai
```

Or install the development build directly from source:

```bash
pip install git+https://github.com/YOUR_GITHUB_USERNAME/limina-python.git
```

## Quickstart

### 1. Real-Time Agent Tracing

Use decorators to monitor agent state transitions, tool execution latency, and policy violations:

```python
from limina import LiminaMonitor

# Initialize client with optional industry profile ('standard', 'banking', 'healthcare', 'customer_support', 'creative')
monitor = LiminaMonitor(
    api_key="YOUR_LIMINA_API_KEY",
    space_id="sdawdsdw/limina-engine",
    profile="standard"
)

# Trace tool execution
@monitor.trace_tool(tool_name="database_policy_lookup")
def query_db(query: str):
    return {"max_refund_days": 14, "allow_cash": False}

# Trace root agent session
@monitor.trace(session_id="session_101", description="Support Agent Run")
def support_agent(user_input: str):
    policy = query_db(user_input)
    return "Your cash refund has been issued."

# Execute
response = support_agent("Requesting refund for order #992.")

# Flush pending asynchronous traces before application shutdown
monitor.flush()
```

## Industry Domain Profiles

Limina provides specialized strictness profiles designed for regulated and high-stakes agentic workloads:

| Profile | Strictness Multiplier | Max Tool Latency | Compliance Focus |
| :--- | :--- | :--- | :--- |
| `standard` | 1.0x | 4000ms | General-purpose agent validation & hallucination checks. |
| `banking` | 0.5x (Zero Tolerance) | 2000ms | Enforces financial disclaimers; flags unauthorized promises. |
| `healthcare` | 0.6x | 2500ms | Verifies medical advice boundaries and mandatory disclaimers. |
| `customer_support` | 1.0x | 3000ms | Brand safety, profanity filtering, competitor name censorship. |
| `creative` | 1.5x (Relaxed) | 6000ms | Higher semantic tolerance for exploratory and generative agents. |

### Setting Profiles in Python

```python
# At initialization:
monitor = LiminaMonitor(api_key="YOUR_KEY", profile="banking")

# Or at runtime:
monitor.set_profile("healthcare")
```

## Historical Log & JSON File Evaluation

`evaluate_logs()` natively accepts local file paths (`.json`), raw Python lists, or individual log dictionaries:

```python
from limina import LiminaMonitor

monitor = LiminaMonitor(api_key="YOUR_LIMINA_API_KEY")

# 1. Evaluate directly from a local JSON file
report_from_file = monitor.evaluate_logs("logs/production_traces.json")
print(report_from_file["executive_summary"])

# 2. Evaluate from in-memory OpenAI transcripts
openai_messages = [
    {"role": "user", "content": "Can I return an item after 30 days?"},
    {"role": "assistant", "content": "Yes, our policy covers returns up to 60 days."}
]

report_from_memory = monitor.evaluate_logs(openai_messages)
print(report_from_memory["narrative_report"])  # Automated Git Diff prompt patch
```


## Privacy, Security & Data Governance

Limina AI is engineered with a strict privacy-first architecture:

* **Zero Data Retention:** Customer conversation logs, user prompts, and tool outputs are processed ephemerally in volatile memory during evaluation and are not retained on disk.
* **No Model Training:** Customer data is never stored, aggregated, or used to train, fine-tune, or improve proprietary or foundation models.
* **Cryptographic Key Isolation:** API keys are never stored in plaintext. All authentication checks rely on irreversible SHA-256 cryptographic hashes.
* **Non-Blocking Runtime:** Tracing decorators run asynchronously on background threads to prevent latency overhead on host agents.


## License

Distributed under the Apache-2.0 License.