import os
import functools
import time
import json
import inspect
import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextvars import ContextVar
from typing import Optional, Callable, Any, Dict, List, Union
from gradio_client import Client

_active_session_ctx: ContextVar[Optional[Dict[str, Any]]] = ContextVar("_active_session_ctx", default=None)
_DEFAULT_ENGINE_URL = "https://api.limina-ai.tech"

def load_local_limina_config() -> dict:
    for filename in ["limina.yaml", "limina.yml"]:
        if os.path.exists(filename):
            try:
                import yaml
                with open(filename, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f)
                    if isinstance(cfg, dict):
                        print(f"[Limina AI]: Loaded declarative policy from [{filename}]")
                        return cfg
            except ImportError:
                pass
            except Exception as e:
                print(f"[Limina AI Warning]: Could not parse {filename}: {e}")
    return {}

class LiminaMonitor:
    """
    Official Python SDK for Limina AI.
    Real-time Trajectory Diagnostics, Regression Testing & Automated Prompt Patching.
    """
    _instance = None

    def __init__(
        self, 
        api_key: Optional[str] = None,
        profile: Optional[str] = None,
        export_html: bool = False,
        host: Optional[str] = None
    ):
        self.api_key = api_key or os.getenv("LIMINA_API_KEY")
        if not self.api_key:
            raise ValueError(
                "[Limina AI]: API Key is missing. Pass it via LiminaMonitor(api_key='...') "
                "or set the LIMINA_API_KEY environment variable."
            )
        self.config = load_local_limina_config()
        active_prof = profile or self.config.get("strictness_profile") or "standard"
        self.profile = str(active_prof).lower()
        self.export_html = export_html
        self.target_url = host or _DEFAULT_ENGINE_URL
        self.client = Client(self.target_url)
        self._executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="limina_trace_uploader")
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

    def evaluate(self, payload: List[Dict[str, Any]], run_stress_test: bool = False) -> Dict[str, Any]:
        """Sends trajectories synchronously to the Limina Engine with declarative config."""
        try:
            for session in payload:
                if "config" not in session:
                    session["config"] = self.config
                if "run_stress_test" not in session:
                    session["run_stress_test"] = run_stress_test

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
                    print("[Limina AI]: Standalone interactive visual report saved to: report.html")
                except Exception as html_err:
                    print(f"[Limina AI Warning]: Could not save report.html locally: {html_err}")

            summary = result.get('executive_summary', {})
            print(f"[Limina AI]: Evaluation complete. Health: [{summary.get('health_rating', 'N/A')}] (Success Rate: {summary.get('success_rate_percentage', 0.0):.1f}%)")
            return result
        except Exception as e:
            print(f"[Limina AI Error]: Evaluation failed: {e}")
            return {"status": "ERROR", "error": str(e)}

    def evaluate_logs(
        self, 
        input_data: Union[str, List[Dict[str, Any]], Dict[str, Any]], 
        source: str = "auto",
        run_stress_test: bool = False
    ) -> Dict[str, Any]:
        """Auto-converts logs and runs batch evaluation."""
        from .adapters import LogAdapter
        trajectories = LogAdapter.auto_convert(input_data, source=source)
        if not trajectories:
            print("[Limina AI Warning]: No valid trajectories extracted from input logs.")
            return {}
        return self.evaluate(trajectories, run_stress_test=run_stress_test)
        
    def compare(
        self, 
        baseline_logs: Union[str, List[Dict[str, Any]], Dict[str, Any]], 
        candidate_logs: Union[str, List[Dict[str, Any]], Dict[str, Any]],
        source: str = "auto",
        fail_on_regression: bool = False
    ) -> Dict[str, Any]:
        """
        Compares Baseline vs. Candidate agent trajectories.
        Returns mathematical delta scores, error resolution matrix and CI/CD gate status.
        If fail_on_regression=True, raises RuntimeError when regressions are detected to block CI/CD.
        """
        from .adapters import LogAdapter
        base_trajectories = LogAdapter.auto_convert(baseline_logs, source=source)
        cand_trajectories = LogAdapter.auto_convert(candidate_logs, source=source)
        
        if not base_trajectories or not cand_trajectories:
            print("[Limina AI Error]: Could not extract valid trajectories for comparison.")
            return {}

        for session in base_trajectories:
            if "config" not in session:
                session["config"] = self.config
        for session in cand_trajectories:
            if "config" not in session:
                session["config"] = self.config

        try:
            raw_result_str = self.client.predict(
                api_key=self.api_key,
                baseline_json=json.dumps(base_trajectories),
                candidate_json=json.dumps(cand_trajectories),
                api_name="/compare"
            )
            result = json.loads(raw_result_str)
            
            diff = result.get("regression_analysis", {})
            metrics = diff.get("metrics", {})
            verdict = diff.get("verdict", "UNKNOWN")
            ci_status = diff.get("ci_gate_status", "UNKNOWN")
            
            print("\n[limina] Regression Verdict: " + verdict + " (Gate: " + ci_status + ")")
            print("-" * 50)
            print(f"  Δ Accuracy   : {metrics.get('delta_accuracy_percentage', 0.0):+0.1f}% ({metrics.get('baseline_accuracy', 0.0)}% -> {metrics.get('candidate_accuracy', 0.0)}%)")
            print(f"  Latency      : {metrics.get('baseline_latency_ms', 0.0)}ms -> {metrics.get('candidate_latency_ms', 0.0)}ms ({metrics.get('delta_latency_ms', 0.0):+0.1f}ms)")
            print(f"  Fixed        : {diff.get('breakdown', {}).get('fixed_count', 0)} resolved")
            print(f"  Regressions  : {diff.get('breakdown', {}).get('new_regressions_count', 0)} broken")
            print(f"  Action       : {diff.get('recommendation')}")
            print("-" * 50 + "\n")

            if fail_on_regression and ci_status == "BLOCKED":
                raise RuntimeError(f"[Limina CI Gate Failed]: Pull Request blocked due to {diff.get('breakdown', {}).get('new_regressions_count', 0)} new regressions detected.")
            
            return result
        except Exception as e:
            if fail_on_regression and "Limina CI Gate Failed" in str(e):
                raise e
            print(f"[Limina Regression Error]: Comparison failed: {e}")
            return {"status": "ERROR", "error": str(e)}

    def _send_to_cloud_async(self, payload: List[Dict[str, Any]]):
        def _worker():
            try:
                self.evaluate(payload)
            except Exception as e:
                print(f"[Limina Background Sync Notice]: {e}")
        self._executor.submit(_worker)

    def flush(self):
        """Waits for any pending background trace uploads to complete."""
        self._executor.shutdown(wait=True)
        self._executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="limina_trace_uploader")

    def trace(self, session_id: str = "default_session", description: str = "Monitored Agent Run", run_stress_test: bool = False):
        def decorator(func: Callable):
            if inspect.iscoroutinefunction(func):
                @functools.wraps(func)
                async def async_wrapper(*args, **kwargs):
                    start_time = time.time()
                    user_text = str(args[0]) if args else str(kwargs)
                    ctx = {
                        "nodes": [{"id": "n1", "type": "user", "text": user_text}],
                        "edges": [],
                        "last_node_id": "n1",
                        "node_counter": 2
                    }
                    token = _active_session_ctx.set(ctx)
                    try:
                        result = await func(*args, **kwargs)
                        output_text = str(result)
                        return result
                    except Exception as e:
                        output_text = f"EXECUTION_ERROR: {str(e)}"
                        raise e
                    finally:
                        duration_ms = (time.time() - start_time) * 1000.0
                        active_ctx = _active_session_ctx.get()
                        if active_ctx:
                            agent_node_id = f"n{active_ctx['node_counter']}"
                            active_ctx["nodes"].append({
                                "id": agent_node_id,
                                "type": "agent",
                                "text": output_text,
                                "execution_time_ms": round(duration_ms, 2)
                            })
                            active_ctx["edges"].append({
                                "from": active_ctx["last_node_id"],
                                "to": agent_node_id
                            })
                            payload = [{
                                "session_id": session_id,
                                "description": description,
                                "nodes": active_ctx["nodes"],
                                "edges": active_ctx["edges"],
                                "run_stress_test": run_stress_test,
                                "config": self.config
                            }]
                            self._send_to_cloud_async(payload)
                        _active_session_ctx.reset(token)

                return async_wrapper

            else:
                @functools.wraps(func)
                def sync_wrapper(*args, **kwargs):
                    start_time = time.time()
                    user_text = str(args[0]) if args else str(kwargs)
                    ctx = {
                        "nodes": [{"id": "n1", "type": "user", "text": user_text}],
                        "edges": [],
                        "last_node_id": "n1",
                        "node_counter": 2
                    }
                    token = _active_session_ctx.set(ctx)
                    try:
                        result = func(*args, **kwargs)
                        output_text = str(result)
                        return result
                    except Exception as e:
                        output_text = f"EXECUTION_ERROR: {str(e)}"
                        raise e
                    finally:
                        duration_ms = (time.time() - start_time) * 1000.0
                        active_ctx = _active_session_ctx.get()
                        if active_ctx:
                            agent_node_id = f"n{active_ctx['node_counter']}"
                            active_ctx["nodes"].append({
                                "id": agent_node_id,
                                "type": "agent",
                                "text": output_text,
                                "execution_time_ms": round(duration_ms, 2)
                            })
                            active_ctx["edges"].append({
                                "from": active_ctx["last_node_id"],
                                "to": agent_node_id
                            })
                            payload = [{
                                "session_id": session_id,
                                "description": description,
                                "nodes": active_ctx["nodes"],
                                "edges": active_ctx["edges"],
                                "run_stress_test": run_stress_test,
                                "config": self.config
                            }]
                            self._send_to_cloud_async(payload)
                        _active_session_ctx.reset(token)

                return sync_wrapper

        return decorator

    def trace_tool(self, tool_name: str = "custom_tool"):
        def decorator(func: Callable):
            if inspect.iscoroutinefunction(func):
                @functools.wraps(func)
                async def async_tool_wrapper(*args, **kwargs):
                    start_time = time.time()
                    result = None
                    error_msg = None
                    try:
                        result = await func(*args, **kwargs)
                        return result
                    except Exception as e:
                        error_msg = str(e)
                        raise e
                    finally:
                        duration_ms = (time.time() - start_time) * 1000.0
                        active_ctx = _active_session_ctx.get()
                        if active_ctx:
                            tool_node_id = f"n{active_ctx['node_counter']}"
                            active_ctx["node_counter"] += 1
                            tool_text = json.dumps(result) if isinstance(result, (dict, list)) else str(result or error_msg)

                            active_ctx["nodes"].append({
                                "id": tool_node_id,
                                "type": "tool",
                                "text": tool_text,
                                "execution_time_ms": round(duration_ms, 2)
                            })
                            active_ctx["edges"].append({
                                "from": active_ctx["last_node_id"],
                                "to": tool_node_id
                            })
                            active_ctx["last_node_id"] = tool_node_id

                return async_tool_wrapper

            else:
                @functools.wraps(func)
                def sync_tool_wrapper(*args, **kwargs):
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
                        active_ctx = _active_session_ctx.get()
                        if active_ctx:
                            tool_node_id = f"n{active_ctx['node_counter']}"
                            active_ctx["node_counter"] += 1
                            tool_text = json.dumps(result) if isinstance(result, (dict, list)) else str(result or error_msg)

                            active_ctx["nodes"].append({
                                "id": tool_node_id,
                                "type": "tool",
                                "text": tool_text,
                                "execution_time_ms": round(duration_ms, 2)
                            })
                            active_ctx["edges"].append({
                                "from": active_ctx["last_node_id"],
                                "to": tool_node_id
                            })
                            active_ctx["last_node_id"] = tool_node_id

                return sync_tool_wrapper

        return decorator