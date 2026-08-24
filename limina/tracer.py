import os
import functools
import time
import json
import threading
from typing import Optional, Callable, Any, Dict, List, Union
from gradio_client import Client

_active_session_context = threading.local()

_DEFAULT_ENGINE_URL = "https://api.limina-ai.tech"

class LiminaMonitor:
    """
    Official Python SDK for Limina AI.
    Real-time Trajectory Diagnostics & Automated Prompt Patching.
    """
    _instance = None

    def __init__(
        self, 
        api_key: Optional[str] = None,
        profile: str = "standard",
        export_html: bool = False,
        host: Optional[str] = None
    ):
        self.api_key = api_key or os.getenv("LIMINA_API_KEY")
        if not self.api_key:
            raise ValueError(
                "[Limina AI]: API Key is missing. Pass it via LiminaMonitor(api_key='...') "
                "or set the LIMINA_API_KEY environment variable."
            )

        self.profile = profile.lower()
        self.export_html = export_html
        self.target_url = host or _DEFAULT_ENGINE_URL
        self.client = Client(self.target_url)
        self._threads = []
        LiminaMonitor._instance = self

    def set_profile(self, profile_name: str):
        """Sets the active strictness profile ('standard', 'banking', 'healthcare', 'customer_support', 'creative')."""
        self.profile = profile_name.lower()
        print(f"[Limina AI]: Active evaluation profile set to: [{self.profile}]")

    @classmethod
    def get_instance(cls):
        if not cls._instance:
            raise RuntimeError("LiminaMonitor is not initialized. Call LiminaMonitor(api_key=...) first.")
        return cls._instance

    def evaluate(self, payload: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Sends trajectories synchronously to the Limina Engine."""
        try:
            raw_result_str = self.client.predict(
                api_key=self.api_key,
                payload_json=json.dumps(payload),
                api_name="/evaluate"
            )
            result = json.loads(raw_result_str)

            if "error" in result:
                print(f"[Limina AI Error]: {result['error']}")
                return result
            if self.export_html and result.get("rendered_html"):
                try:
                    with open("report.html", "w", encoding="utf-8") as f:
                        f.write(result["rendered_html"])
                    print("[Limina AI]: Interactive visual report successfully generated at: report.html")
                except Exception as html_err:
                    print(f"[Limina AI Warning]: Could not save report.html locally: {html_err}")

            summary = result.get('executive_summary', {})
            print(f"[Limina AI]: Evaluation complete. Health: [{summary.get('health_rating', 'N/A')}] (Success Rate: {summary.get('success_rate_percentage', 0.0):.1f}%)")
            return result
        except Exception as e:
            print(f"[Limina AI Error]: Evaluation failed: {e}")
            return {"status": "ERROR", "error": str(e)}

    def evaluate_logs(self, input_data: Union[str, List[Dict[str, Any]], Dict[str, Any]], source: str = "auto") -> Dict[str, Any]:
        from .adapters import LogAdapter
        trajectories = LogAdapter.auto_convert(input_data, source=source)
        if not trajectories:
            print("[Limina AI Warning]: No valid trajectories extracted from input logs.")
            return {}
        return self.evaluate(trajectories)

    def _send_to_cloud(self, payload: List[Dict[str, Any]]):
        def _worker():
            try:
                self.evaluate(payload)
            except Exception:
                pass
        t = threading.Thread(target=_worker, daemon=False)
        self._threads.append(t)
        t.start()

    def flush(self):
        """Waits for any pending background trace uploads to complete."""
        for t in self._threads:
            if t.is_alive():
                t.join(timeout=10)
        self._threads.clear()

    def trace(self, session_id: str = "default_session", description: str = "Monitored Agent Run"):
        def decorator(func: Callable):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                user_text = str(args[0]) if args else str(kwargs)

                _active_session_context.nodes = [{"id": "n1", "type": "user", "text": user_text}]
                _active_session_context.edges = []
                _active_session_context.last_node_id = "n1"
                _active_session_context.node_counter = 2

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

                    payload = [{
                        "session_id": session_id,
                        "description": description,
                        "nodes": _active_session_context.nodes,
                        "edges": _active_session_context.edges
                    }]
                    self._send_to_cloud(payload)

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