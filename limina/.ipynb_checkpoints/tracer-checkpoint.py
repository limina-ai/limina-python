import functools
import time
import json
import os
import threading
from typing import Optional, Callable, Any, Dict, List, Union

_active_session_context = threading.local()

class LiminaMonitor:
    """
    Local-First Python SDK for deterministic AI Agent evaluation and trajectory tracing.
    """
    _instance = None

    def __init__(self, api_key: str = "limina_local_dev", profile: str = "standard", export_html: bool = True):
        self.api_key = api_key
        self.profile = profile.lower()  # "standard", "banking", "healthcare", "customer_support", "creative"
        self.export_html = export_html
        LiminaMonitor._instance = self

    def set_profile(self, profile_name: str):
        """Changes evaluation strictness profile at runtime."""
        self.profile = profile_name.lower()
        print(f"[limina-sdk]: Active evaluation profile set to: [{self.profile}]")

    @classmethod
    def get_instance(cls):
        if not cls._instance:
            raise RuntimeError("LiminaMonitor is not initialized. Call LiminaMonitor(...) first.")
        return cls._instance

    def _evaluate_locally(self, payload: List[Dict[str, Any]]):
        """Runs evaluation locally on CPU in background thread without blocking host agent."""
        def _worker():
            try:
                from evaluator import evaluate_trajectories_batch, generate_html_report
                from report_generator import generate_ai_report

                report = evaluate_trajectories_batch(payload, run_stress_test=False)
                if report:
                    rating = report.get('executive_summary', {}).get('health_rating', 'F')
                    score = report.get('executive_summary', {}).get('success_rate_percentage', 0.0)
                    
                    if self.export_html:
                        ai_markdown = generate_ai_report(report)
                        report["narrative_report"] = ai_markdown
                        generate_html_report(report, output_path="report.html")

                    print(f"\n[limina-sdk]: Trajectory evaluated locally. Rating: [{rating}] (Score: {score:.1f}%)")
                    if self.export_html:
                        print("[limina-sdk]: Saved interactive report to: report.html")
            except Exception as e:
                pass

        threading.Thread(target=_worker, daemon=True).start()

    def evaluate_logs(self, input_data: Union[str, List[Dict[str, Any]]], source: str = "auto") -> Dict[str, Any]:
        """
        Evaluates historical logs from OpenAI, LangSmith, or standard JSON files.
        Automatically converts them into State-Space DAGs and runs local evaluation.
        """
        from limina.adapters import LogAdapter
        from evaluator import evaluate_trajectories_batch, generate_html_report
        from report_generator import generate_ai_report
        trajectories = LogAdapter.auto_convert(input_data, source=source)
        report = evaluate_trajectories_batch(trajectories, run_stress_test=False)
        ai_markdown = generate_ai_report(report)
        report["narrative_report"] = ai_markdown

        if self.export_html:
            generate_html_report(report, output_path="report.html")
            print("\n[limina-sdk]: Converted and evaluated logs. Saved report.html to disk.")

        return report

    def trace(self, session_id: str = "default_session", description: str = "Monitored Agent Run"):
        def decorator(func: Callable):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                user_text = str(args[0]) if args else str(kwargs)

                _active_session_context.nodes = [
                    {"id": "n1", "type": "user", "text": user_text}
                ]
                _active_session_context.edges = []
                _active_session_context.last_node_id = "n1"
                _active_session_context.node_counter = 2

                output_text = ""
                try:
                    result = func(*args, **kwargs)
                    output_text = str(result)
                    return result
                except Exception as e:
                    output_text = f"EXECUTION_ERROR: {str(e)}"
                    raise e
                finally:
                    duration_ms = (time.time() - start_time) * 1000.0
                    agent_node_id = f"n{_active_session_context.node_counter}"
                    _active_session_context.nodes.append({
                        "id": agent_node_id,
                        "type": "agent",
                        "text": output_text,
                        "execution_time_ms": round(duration_ms, 2)
                    })
                    _active_session_context.edges.append({
                        "from": _active_session_context.last_node_id,
                        "to": agent_node_id
                    })

                    payload = [
                        {
                            "session_id": session_id,
                            "description": description,
                            "nodes": _active_session_context.nodes,
                            "edges": _active_session_context.edges
                        }
                    ]
                    self._evaluate_locally(payload)

            return wrapper
        return decorator

    def trace_tool(self, tool_name: str = "custom_tool"):
        def decorator(func: Callable):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                result = None
                error_msg = None
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    error_msg = str(e)
                    raise e
                finally:
                    duration_ms = (time.time() - start_time) * 1000.0
                    if hasattr(_active_session_context, "nodes"):
                        tool_node_id = f"n{_active_session_context.node_counter}"
                        _active_session_context.node_counter += 1
                        tool_text = json.dumps(result) if isinstance(result, (dict, list)) else str(result or error_msg)

                        _active_session_context.nodes.append({
                            "id": tool_node_id,
                            "type": "tool",
                            "text": tool_text,
                            "execution_time_ms": round(duration_ms, 2)
                        })
                        _active_session_context.edges.append({
                            "from": _active_session_context.last_node_id,
                            "to": tool_node_id
                        })
                        _active_session_context.last_node_id = tool_node_id

            return wrapper
        return decorator