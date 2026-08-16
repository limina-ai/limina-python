# limina/adapters.py
import json
import uuid
from typing import List, Dict, Any, Union

class LogAdapter:
    """
    Universal adapter to convert raw logs from OpenAI, LangSmith, LangChain, 
    and generic chat transcripts into Limina State-Space DAG trajectories.
    """

    @staticmethod
    def from_openai(messages: List[Dict[str, Any]], session_id: str = None, description: str = "OpenAI Converted Session") -> Dict[str, Any]:
        """
        Converts OpenAI ChatCompletion message history (including tool_calls) into a Limina DAG trajectory.
        """
        session_id = session_id or f"openai_session_{uuid.uuid4().hex[:8]}"
        nodes = []
        edges = []
        node_idx = 1

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content") or ""
            tool_calls = msg.get("tool_calls", [])

            # 1. User Input Node
            if role == "user":
                node_id = f"n{node_idx}"
                nodes.append({
                    "id": node_id,
                    "type": "user",
                    "label": "USER",
                    "text": str(content)
                })
                if node_idx > 1:
                    edges.append({"from": f"n{node_idx-1}", "to": node_id})
                node_idx += 1

            # 2. Assistant with Tool Calls (Thought / Action)
            elif role == "assistant" and tool_calls:
                for tc in tool_calls:
                    node_id = f"n{node_idx}"
                    func_name = tc.get("function", {}).get("name", "tool_call")
                    func_args = tc.get("function", {}).get("arguments", "")
                    nodes.append({
                        "id": node_id,
                        "type": "tool",
                        "label": func_name.upper(),
                        "text": json.dumps({"tool": func_name, "args": func_args}) if isinstance(func_args, dict) else str(func_args),
                        "execution_time_ms": 150.0
                    })
                    if node_idx > 1:
                        edges.append({"from": f"n{node_idx-1}", "to": node_id})
                    node_idx += 1

            # 3. Tool Return Node (Database / Vector context)
            elif role == "tool":
                node_id = f"n{node_idx}"
                nodes.append({
                    "id": node_id,
                    "type": "tool",
                    "label": "TOOL_OUTPUT",
                    "text": str(content),
                    "execution_time_ms": 120.0
                })
                if node_idx > 1:
                    edges.append({"from": f"n{node_idx-1}", "to": node_id})
                node_idx += 1

            # 4. Final Assistant Response
            elif role == "assistant":
                node_id = f"n{node_idx}"
                nodes.append({
                    "id": node_id,
                    "type": "agent",
                    "label": "AGENT",
                    "text": str(content)
                })
                if node_idx > 1:
                    edges.append({"from": f"n{node_idx-1}", "to": node_id})
                node_idx += 1

        return {
            "session_id": session_id,
            "description": description,
            "nodes": nodes,
            "edges": edges
        }

    @staticmethod
    def from_langsmith(run_data: Dict[str, Any], session_id: str = None) -> Dict[str, Any]:
        """
        Converts LangChain / LangSmith run trees into a Limina DAG trajectory.
        """
        session_id = session_id or run_data.get("id") or f"langchain_session_{uuid.uuid4().hex[:8]}"
        nodes = []
        edges = []
        node_idx = 1

        # Extract Inputs
        inputs = run_data.get("inputs", {})
        input_text = str(inputs.get("input") or inputs.get("query") or inputs)
        
        user_node_id = f"n{node_idx}"
        nodes.append({
            "id": user_node_id,
            "type": "user",
            "label": "USER",
            "text": input_text
        })
        node_idx += 1

        # Extract Child Runs (Tools / Chains)
        child_runs = run_data.get("child_runs", [])
        for child in child_runs:
            c_type = "tool" if child.get("run_type") == "tool" else "thought"
            c_name = child.get("name", "Tool")
            c_outputs = str(child.get("outputs", {}))
            c_latency = child.get("latency_ms") or 140.0

            node_id = f"n{node_idx}"
            nodes.append({
                "id": node_id,
                "type": c_type,
                "label": c_name.upper(),
                "text": c_outputs,
                "execution_time_ms": float(c_latency)
            })
            edges.append({"from": f"n{node_idx-1}", "to": node_id})
            node_idx += 1

        # Extract Final Output
        outputs = run_data.get("outputs", {})
        output_text = str(outputs.get("output") or outputs.get("result") or outputs)
        
        agent_node_id = f"n{node_idx}"
        nodes.append({
            "id": agent_node_id,
            "type": "agent",
            "label": "AGENT",
            "text": output_text
        })
        edges.append({"from": f"n{node_idx-1}", "to": agent_node_id})

        return {
            "session_id": session_id,
            "description": run_data.get("name", "LangChain Execution Trace"),
            "nodes": nodes,
            "edges": edges
        }

    @classmethod
    def auto_convert(cls, raw_logs: Union[str, List, Dict], source: str = "auto") -> List[Dict[str, Any]]:
        """
        Auto-detects format and converts raw logs into standard Limina DAG trajectories.
        """
        # Load from file if string path provided
        if isinstance(raw_logs, str):
            with open(raw_logs, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = raw_logs

        # If already in Limina DAG format (contains nodes and edges)
        if isinstance(data, list) and len(data) > 0 and "nodes" in data[0] and "edges" in data[0]:
            return data

        trajectories = []

        # Case 1: List of OpenAI conversation histories
        if isinstance(data, list):
            for idx, item in enumerate(data):
                if isinstance(item, list):  # list of message dicts
                    trajectories.append(cls.from_openai(item, session_id=f"openai_session_{idx+1}"))
                elif isinstance(item, dict) and "messages" in item:
                    trajectories.append(cls.from_openai(item["messages"], session_id=item.get("session_id", f"session_{idx+1}")))
                elif isinstance(item, dict) and ("run_type" in item or "child_runs" in item):
                    trajectories.append(cls.from_langsmith(item))
                elif isinstance(item, dict) and ("input" in item and "output" in item):
                    # Generic input/output log
                    trajectories.append({
                        "session_id": item.get("session_id", f"session_{idx+1}"),
                        "description": item.get("description", "Converted Generic Trace"),
                        "nodes": [
                            {"id": "n1", "type": "user", "label": "USER", "text": str(item["input"])},
                            {"id": "n2", "type": "agent", "label": "AGENT", "text": str(item["output"])}
                        ],
                        "edges": [{"from": "n1", "to": "n2"}]
                    })

        # Case 2: Single LangSmith / LangChain run dump
        elif isinstance(data, dict):
            if "child_runs" in data or "run_type" in data:
                trajectories.append(cls.from_langsmith(data))
            elif "messages" in data:
                trajectories.append(cls.from_openai(data["messages"]))

        return trajectories