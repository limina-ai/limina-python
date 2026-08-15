# limina/tracer.py
import functools
import time
import requests
import threading
import json
from typing import Optional, Callable, Any, Dict, List

_active_session_context = threading.local()

class LiminaMonitor:
    """
    Client SDK for streaming multi-turn agent execution trajectories to Limina AI.
    """
    _instance = None

    def __init__(self, api_key: str, api_url: str = "http://127.0.0.1:8000/evaluate/trajectory"):
        self.api_key = api_key
        self.api_url = api_url
        LiminaMonitor._instance = self

    @classmethod
    def get_instance(cls):
        if not cls._instance:
            raise RuntimeError("LiminaMonitor is not initialized. Call LiminaMonitor(api_key=...) first.")
        return cls._instance

    def _send_payload_async(self, payload: List[Dict[str, Any]]):
        def _worker():
            try:
                headers = {
                    "X-API-Key": self.api_key,
                    "Content-Type": "application/json"
                }
                requests.post(self.api_url, json=payload, headers=headers, timeout=60)
            except Exception as e:
                pass  # Silent failure in host agent

        threading.Thread(target=_worker, daemon=True).start()

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
                    self._send_payload_async(payload)

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