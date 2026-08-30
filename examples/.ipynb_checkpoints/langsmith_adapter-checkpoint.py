#!/usr/bin/env python
# coding: utf-8

from limina import LiminaMonitor, LogAdapter

monitor = LiminaMonitor()

# Mock LangSmith / LangChain Run Tree dump
sample_langsmith_dump = {
    "id": "langsmith_trace_001",
    "name": "Customer Support Retrieval Chain",
    "run_type": "chain",
    "inputs": {"input": "What is the return policy for electronics?"},
    "child_runs": [
        {
            "name": "KnowledgeBaseRetriever",
            "run_type": "tool",
            "outputs": {"policy": "Electronics can be returned within 14 days with original receipt."},
            "latency_ms": 120.0
        }
    ],
    "outputs": {"output": "Electronics are eligible for return within 14 days with original receipt."}
}

if __name__ == "__main__":
    print("[limina] Converting LangSmith run tree into State-Space DAG...")
    dag = LogAdapter.from_langsmith(sample_langsmith_dump)
    
    print(f"[limina] Parsed {len(dag['nodes'])} nodes and {len(dag['edges'])} edges.")
    print("[limina] Evaluating factual grounding...")
    
    report = monitor.evaluate([dag])
    summary = report.get("executive_summary", {})
    
    print(f"[limina] Result: Health [{summary.get('health_rating', 'N/A')}] — {summary.get('success_rate_percentage', 0.0):.1f}% pass rate.")