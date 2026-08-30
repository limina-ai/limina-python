#!/usr/bin/env python
# coding: utf-8

import os
from limina import LiminaMonitor

# Initialize monitor; export_html=True writes an interactive report.html on disk
monitor = LiminaMonitor(export_html=True)

@monitor.trace_tool(tool_name="database_policy_lookup")
def query_refund_policy(order_id: str):
    # Simulated database lookup
    return {
        "order_id": order_id,
        "max_return_days": 14,
        "cash_refund_allowed": False,
        "item_category": "electronics"
    }

@monitor.trace(session_id="order_refund_check", description="Customer support refund triage")
def customer_support_agent(user_query: str):
    policy = query_refund_policy("ORD-9821")
    
    # Formulate compliant agent response based on retrieved facts
    return (
        f"Order {policy['order_id']} is eligible for return within our "
        f"{policy['max_return_days']}-day return window. Store credit will be issued."
    )

if __name__ == "__main__":
    print("[limina] Running basic agent tracing...")
    response = customer_support_agent("Can I return order #9821 for a cash refund?")
    print(f"[agent]: {response}")
    
    # Flush background thread queue and generate report.html
    monitor.flush()
    print("[limina] Tracing complete. Open 'report.html' in your browser to inspect the DAG.")