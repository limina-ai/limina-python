import json
import os
import uuid
from typing import List, Dict, Any, Union

class LogAdapter:
    """
    Universal adapter to convert raw logs from OpenAI, LangSmith, LangChain, 
    and generic chat transcripts into Limina DAG trajectories.
    """
    @staticmethod
    def _extract_text_content(content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            texts = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    texts.append(str(part.get("text", "")))
                else:
                    texts.append(str(part))
            return " ".join(texts)
        return str(content or "")

    @classmethod
    def from_openai(cls, messages: List[Dict[str, Any]], session_id: str = None, description: str = "OpenAI Converted Session") -> Dict[str, Any]:
        session_id = session_id or f"openai_session_{uuid.uuid4().hex[:8]}"
        nodes = []
        edges = []
        node_idx = 1

        for msg in messages:
            role = msg.get("role", "user")
            content = cls._extract_text_content(msg.get("content"))
            tool_calls = msg.get("tool_calls", [])

            if role == "user":
                node_id = f"n{node_idx}"
                nodes.append({"id": node_id, "type": "user", "label": "USER", "text": content})
                if node_idx > 1:
                    edges.append({"from": f"n{node_idx-1}", "to": node_id})
                node_idx += 1

            elif role == "assistant" and tool_calls:
                for tc in tool_calls:
                    node_id = f"n{node_idx}"
                    func_name = tc.get("function", {}).get("name", "tool_call")
                    func_args = tc.get("function", {}).get("arguments", "")
                    
                    text_repr = json.dumps({"tool": func_name, "args": func_args}) if isinstance(func_args, dict) else str(func_args)
                    nodes.append({
                        "id": node_id,
                        "type": "tool",
                        "label": func_name.upper(),
                        "text": text_repr,
                        "execution_time_ms": 150.0
                    })
                    if node_idx > 1:
                        edges.append({"from": f"n{node_idx-1}", "to": node_id})
                    node_idx += 1

            elif role == "tool":
                node_id = f"n{node_idx}"
                nodes.append({"id": node_id, "type": "tool", "label": "TOOL_OUTPUT", "text": content, "execution_time_ms": 120.0})
                if node_idx > 1:
                    edges.append({"from": f"n{node_idx-1}", "to": node_id})
                node_idx += 1

            elif role == "assistant":
                node_id = f"n{node_idx}"
                nodes.append({"id": node_id, "type": "agent", "label": "AGENT", "text": content})
                if node_idx > 1:
                    edges.append({"from": f"n{node_idx-1}", "to": node_id})
                node_idx += 1

        return {"session_id": session_id, "description": description, "nodes": nodes, "edges": edges}

    @classmethod
    def from_langsmith(cls, run_data: Dict[str, Any], session_id: str = None) -> Dict[str, Any]:
        session_id = session_id or run_data.get("id") or f"langchain_session_{uuid.uuid4().hex[:8]}"
        nodes = []
        edges = []
        node_idx = 1

        inputs = run_data.get("inputs", {})
        input_text = str(inputs.get("input") or inputs.get("query") or inputs)
        
        user_node_id = f"n{node_idx}"
        nodes.append({"id": user_node_id, "type": "user", "label": "USER", "text": input_text})
        node_idx += 1

        for child in run_data.get("child_runs", []):
            c_type = "tool" if child.get("run_type") == "tool" else "thought"
            c_name = child.get("name", "Tool")
            c_outputs = str(child.get("outputs", {}))
            c_latency = child.get("latency_ms") or 140.0

            node_id = f"n{node_idx}"
            nodes.append({"id": node_id, "type": c_type, "label": c_name.upper(), "text": c_outputs, "execution_time_ms": float(c_latency)})
            edges.append({"from": f"n{node_idx-1}", "to": node_id})
            node_idx += 1

        outputs = run_data.get("outputs", {})
        output_text = str(outputs.get("output") or outputs.get("result") or outputs)
        
        agent_node_id = f"n{node_idx}"
        nodes.append({"id": agent_node_id, "type": "agent", "label": "AGENT", "text": output_text})
        edges.append({"from": f"n{node_idx-1}", "to": agent_node_id})

        return {"session_id": session_id, "description": run_data.get("name", "LangChain Execution Trace"), "nodes": nodes, "edges": edges}

    @classmethod
    def auto_convert(cls, raw_logs: Union[str, List, Dict], source: str = "auto") -> List[Dict[str, Any]]:
        if isinstance(raw_logs, str):
            trimmed = raw_logs.strip()
            if (trimmed.startswith("{") or trimmed.startswith("[")) and not os.path.isfile(raw_logs):
                try:
                    data = json.loads(trimmed)
                except Exception:
                    data = raw_logs
            elif os.path.isfile(raw_logs):
                with open(raw_logs, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                try:
                    data = json.loads(raw_logs)
                except Exception:
                    return []
        else:
            data = raw_logs

        if not data:
            return []

        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict) and "nodes" in data[0] and "edges" in data[0]:
            return data

        if isinstance(data, dict) and "nodes" in data and "edges" in data:
            return [data]

        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict) and "role" in data[0]:
            return [cls.from_openai(data, session_id="openai_single_session")]

        trajectories = []

        if isinstance(data, list):
            for idx, item in enumerate(data):
                if isinstance(item, list):
                    trajectories.append(cls.from_openai(item, session_id=f"openai_session_{idx+1}"))
                elif isinstance(item, dict):
                    if "nodes" in item and "edges" in item:
                        trajectories.append(item)
                    elif "messages" in item:
                        trajectories.append(cls.from_openai(item["messages"], session_id=item.get("session_id", f"session_{idx+1}")))
                    elif "run_type" in item or "child_runs" in item:
                        trajectories.append(cls.from_langsmith(item, session_id=item.get("id", f"langsmith_session_{idx+1}")))
                    elif "input" in item and "output" in item:
                        trajectories.append({
                            "session_id": item.get("session_id", f"session_{idx+1}"),
                            "description": item.get("description", "Converted Generic Trace"),
                            "nodes": [
                                {"id": "n1", "type": "user", "label": "USER", "text": str(item["input"])},
                                {"id": "n2", "type": "agent", "label": "AGENT", "text": str(item["output"])}
                            ],
                            "edges": [{"from": "n1", "to": "n2"}]
                        })

        elif isinstance(data, dict):
            if "child_runs" in data or "run_type" in data:
                trajectories.append(cls.from_langsmith(data))
            elif "messages" in data:
                trajectories.append(cls.from_openai(data["messages"]))

        return trajectories