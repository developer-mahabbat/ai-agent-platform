import asyncio
import json
import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator, Callable, Optional

from ..base import SDKModule, SDKResult

logger = logging.getLogger(__name__)


class NodeType(str, Enum):
    SUPERVISOR = "supervisor"
    AGENT = "agent"
    TOOL = "tool"
    CONDITIONAL = "conditional"
    PARALLEL = "parallel"
    MEMORY = "memory"
    RETRY = "retry"
    REFLECTION = "reflection"
    EVALUATION = "evaluation"
    HUMAN_APPROVAL = "human_approval"
    ERROR_RECOVERY = "error_recovery"
    ROUTER = "router"


class NodeStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING = "waiting"


@dataclass
class GraphNode:
    id: str
    name: str
    node_type: NodeType = NodeType.AGENT
    agent_role: str = ""
    tool_name: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    condition: Optional[Callable[[dict], str]] = None
    next_nodes: dict[str, str] = field(default_factory=dict)
    retry_count: int = 3
    timeout: int = 60
    parallel_nodes: list["GraphNode"] = field(default_factory=list)
    status: NodeStatus = NodeStatus.PENDING
    output: str = ""
    error: str = ""


@dataclass
class StateGraph:
    id: str
    nodes: dict[str, GraphNode] = field(default_factory=dict)
    edges: list[tuple[str, str, Optional[str]]] = field(default_factory=list)
    entry_point: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    checkpoint: Optional[str] = None


class OrchestratorEvent:
    def __init__(self, event_type: str, node_id: str = "", content: str = "",
                 status: str = "", data: dict | None = None):
        self.type = event_type
        self.node_id = node_id
        self.content = content
        self.status = status
        self.data = data or {}
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> dict:
        return {
            "event": self.type,
            "node_id": self.node_id,
            "content": self.content,
            "status": self.status,
            "data": self.data,
            "timestamp": self.timestamp,
        }


AGENT_PROMPTS = {
    "planner": {
        "role": "Planner Agent",
        "description": "Breaks down complex tasks into clear, actionable steps",
        "instructions": """You are a Planner Agent. Your job is to:
1. Analyze the user's goal thoroughly
2. Break it down into 3-7 clear, sequential steps
3. For each step, specify what needs to be done and what tools to use
4. Consider dependencies between steps

Output your plan as a numbered list. Be specific and actionable.""",
    },
    "coder": {
        "role": "Coder Agent",
        "description": "Writes, reads, and modifies code and files",
        "instructions": """You are a Coder Agent. You can create, read, and modify files.
When asked to create files or write code, use the write_file tool.
When exploring existing code, use read_file and list_dir.
Run code with run_python to verify it works.

Always:
- Write complete, working code
- Use write_file to create files
- Verify with run_python when possible
- Explain what you're building""",
    },
    "researcher": {
        "role": "Researcher Agent",
        "description": "Searches for and synthesizes information",
        "instructions": """You are a Researcher Agent. You search the web and synthesize findings.
Use search_web to find information.
Use read_url to fetch full pages.
Cite your sources.

Always provide:
- Key findings organized by topic
- Source URLs for each claim
- A brief summary at the end""",
    },
    "reasoner": {
        "role": "Reasoner Agent",
        "description": "Thinks through problems step by step",
        "instructions": """You are a Reasoner Agent. You think through problems carefully.
- Break down complex reasoning into clear steps
- Consider multiple perspectives
- Validate assumptions
- Provide well-reasoned conclusions""",
    },
    "reviewer": {
        "role": "Reviewer Agent",
        "description": "Reviews work and provides improvement feedback",
        "instructions": """You are a Reviewer Agent. Review the previous work and provide feedback.
Check for:
- Correctness and completeness
- Code quality and best practices
- Missing edge cases
- Potential improvements

If the work is good, say "APPROVED" at the end.
If changes are needed, say "NEEDS_IMPROVEMENT" and list specific changes.""",
    },
}


class OrchestratorSDK(SDKModule):
    name = "orchestrator"
    version = "2.0.0"

    def __init__(self, context=None):
        super().__init__(context)
        self._graphs: dict[str, StateGraph] = {}

    async def initialize(self) -> None:
        logger.info("OrchestratorSDK initialized")

    async def shutdown(self) -> None:
        self._graphs.clear()
        logger.info("OrchestratorSDK shut down")

    def create_graph(self, name: str = "default") -> str:
        gid = f"graph_{uuid.uuid4().hex[:12]}"
        graph = StateGraph(id=gid)
        graph.context["name"] = name
        self._graphs[gid] = graph
        logger.info(f"StateGraph created: {gid}")
        return gid

    def add_node(self, graph_id: str, node: GraphNode) -> None:
        graph = self._graphs.get(graph_id)
        if not graph:
            raise ValueError(f"Graph {graph_id} not found")
        graph.nodes[node.id] = node
        if not graph.entry_point:
            graph.entry_point = node.id

    def add_edge(self, graph_id: str, from_id: str, to_id: str, condition: Optional[str] = None) -> None:
        graph = self._graphs.get(graph_id)
        if not graph:
            raise ValueError(f"Graph {graph_id} not found")
        graph.edges.append((from_id, to_id, condition))
        node = graph.nodes.get(from_id)
        if node:
            if condition:
                node.next_nodes[condition] = to_id
            else:
                node.next_nodes["__default__"] = to_id

    def set_entry_point(self, graph_id: str, node_id: str) -> None:
        graph = self._graphs.get(graph_id)
        if not graph:
            raise ValueError(f"Graph {graph_id} not found")
        graph.entry_point = node_id

    async def run(
        self, graph_id: str, initial_input: dict[str, Any] | None = None
    ) -> AsyncIterator[OrchestratorEvent]:
        graph = self._graphs.get(graph_id)
        if not graph:
            yield OrchestratorEvent("error", content=f"Graph {graph_id} not found")
            return

        if initial_input:
            graph.context.update(initial_input)

        current_id = graph.entry_point
        visited = set()
        max_steps = 50

        while current_id and len(visited) < max_steps:
            if current_id in visited:
                yield OrchestratorEvent("error", node_id=current_id,
                    content="Cycle detected, stopping")
                break
            visited.add(current_id)

            node = graph.nodes.get(current_id)
            if not node:
                yield OrchestratorEvent("error", node_id=current_id,
                    content=f"Node {current_id} not found")
                break

            node.status = NodeStatus.RUNNING
            yield OrchestratorEvent("node_start", node_id=node.id,
                content=f"Starting {node.name} ({node.node_type.value})")

            result = None
            if node.node_type == NodeType.SUPERVISOR:
                result = await self._run_supervisor(node, graph)
            elif node.node_type == NodeType.AGENT:
                result = await self._run_agent_with_tools(node, graph)
            elif node.node_type == NodeType.TOOL:
                result = await self._run_tool(node, graph)
            elif node.node_type == NodeType.CONDITIONAL:
                result = await self._run_conditional(node, graph)
            elif node.node_type == NodeType.PARALLEL:
                result = await self._run_parallel(node, graph)
            elif node.node_type == NodeType.REFLECTION:
                result = await self._run_reflection(node, graph)
            elif node.node_type == NodeType.ROUTER:
                result = await self._run_router(node, graph)
            else:
                result = {"output": f"Executed {node.name}", "next": None}

            if result:
                node.output = result.get("output", "")
                next_id = result.get("next")
                graph.context[node.id] = node.output

                if next_id:
                    current_id = next_id
                else:
                    current_id = self._get_next_node(graph, node)

                if result.get("status") == "failed":
                    node.status = NodeStatus.FAILED
                    node.error = result.get("error", "")
                    yield OrchestratorEvent("node_fail", node_id=node.id,
                        content=node.error, status="failed")
                    if result.get("recover"):
                        yield OrchestratorEvent("recovery", node_id=node.id,
                            content="Attempting recovery")
                        current_id = result["recover"]
                    else:
                        break
                else:
                    node.status = NodeStatus.COMPLETED
                    yield OrchestratorEvent("node_complete", node_id=node.id,
                        content=node.output[:200], status="completed")
            else:
                node.status = NodeStatus.FAILED
                yield OrchestratorEvent("node_fail", node_id=node.id,
                    content="No result returned", status="failed")
                break

        graph.checkpoint = datetime.utcnow().isoformat()
        yield OrchestratorEvent("graph_complete", content="Graph execution finished",
            data={"steps": len(visited), "graph_id": graph_id})

    def _get_next_node(self, graph: StateGraph, node: GraphNode) -> Optional[str]:
        for from_id, to_id, condition in graph.edges:
            if from_id == node.id and condition == "__default__":
                return to_id
        for from_id, to_id, condition in graph.edges:
            if from_id == node.id and condition is None:
                return to_id
        return None

    async def _run_supervisor(self, node: GraphNode, graph: StateGraph) -> dict:
        goal = graph.context.get("goal", "")
        history = graph.context.get("history", [])
        prev_work = self._get_context_summary(graph)

        container = self._get_container()
        provider = container.provider_sdk
        cfg = container.config

        prompt = f"""You are a Supervisor Agent. Analyze the user's request and delegate to the right agent.

Goal: {goal}

Previous context (if any): {prev_work}

Available agents:
- planner: Breaks down complex tasks into steps — use for multi-step tasks
- coder: Writes and modifies code and files — use for programming tasks
- researcher: Searches for information — use for research questions
- reasoner: Thinks through problems — use for analysis/reasoning

Respond with EXACTLY one of: planner, coder, researcher, reasoner
No other text."""

        messages = [{"role": "system", "content": prompt}]
        for h in history[-5:]:
            messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
        if not history:
            messages.append({"role": "user", "content": goal})

        try:
            result = await provider.chat_completion(cfg.default_provider, cfg.default_model, messages)
            if result.success and result.data:
                text = (result.data.get("choices", [{}])[0]
                        .get("message", {}).get("content", "")).strip().lower()
                for agent in ["planner", "coder", "researcher", "reasoner"]:
                    if agent in text:
                        logger.info(f"Supervisor delegated to: {agent}")
                        return {"output": f"Delegating to {agent}", "next": node.next_nodes.get(agent)}
        except Exception as e:
            logger.warning(f"Supervisor error: {e}")

        return {"output": "Delegating to default", "next": node.next_nodes.get("__default__")}

    async def _run_agent_with_tools(self, node: GraphNode, graph: StateGraph) -> dict:
        container = self._get_container()
        provider = container.provider_sdk
        tool_sdk = container.tool_sdk
        cfg = container.config

        goal = graph.context.get("goal", "")
        role = node.agent_role
        agent_info = AGENT_PROMPTS.get(role, AGENT_PROMPTS["reasoner"])
        prev_context = self._get_context_summary(graph)

        tool_docs = self._get_tool_docs(tool_sdk, role)

        system_prompt = f"""You are a {agent_info['role']}. {agent_info['description']}.

{agent_info['instructions']}

Available tools:
{tool_docs}

TOOL USAGE:
When you need to use a tool, output:
[TOOL]
{{"name": "tool_name", "params": {{"key": "value"}}}}
[/TOOL]

The tool will execute and the result will be given to you.
You can use multiple tools sequentially.
When you are done, respond with your final answer (no [TOOL] tags).
Do NOT wrap your final answer in [TOOL] tags."""

        messages = [{"role": "system", "content": system_prompt}]

        if prev_context:
            messages.append({"role": "assistant", "content": f"Previous work done:\n{prev_context}"})

        messages.append({"role": "user", "content": f"Goal: {goal}\n\nPlease start working on this task. Use tools as needed."})

        full_output = ""
        max_loops = 15
        tool_used = False

        for loop in range(max_loops):
            response = ""
            try:
                async for chunk in provider.stream_chat(cfg.default_provider, cfg.default_model, messages):
                    if chunk.startswith("data: "):
                        data_str = chunk[6:].strip()
                        if data_str and data_str not in ("[DONE]", ""):
                            try:
                                d = json.loads(data_str)
                                for c in d.get("choices", []):
                                    token = c.get("delta", {}).get("content", "") or c.get("text", "")
                                    if token:
                                        response += token
                            except json.JSONDecodeError:
                                pass
            except Exception as e:
                logger.warning(f"Agent stream error: {e}")
                if full_output:
                    break
                return {"output": f"({role} offline: {e})"}

            if not response:
                break

            tool_match = re.search(r'\[TOOL\](.*?)\[/TOOL\]', response, re.DOTALL)
            if tool_match:
                tool_used = True
                try:
                    raw = tool_match.group(1).strip()
                    tool_data = json.loads(raw)
                    tool_name = tool_data.get("name", "")
                    tool_params = tool_data.get("params", {})

                    logger.info(f"Agent {role} calling tool: {tool_name}")
                    tool_result = await tool_sdk.execute(tool_name, tool_params)
                    result_str = tool_result.output if tool_result.success else f"ERROR: {tool_result.error}"

                    messages.append({"role": "assistant", "content": response})
                    messages.append({"role": "user", "content": f"Tool '{tool_name}' result:\n{result_str}\n\nContinue with your work or provide the final answer."})

                    non_tool = re.sub(r'\[TOOL\].*?\[/TOOL\]', '', response, flags=re.DOTALL).strip()
                    full_output += non_tool + f"\n[Used tool: {tool_name}]\n"
                except Exception as e:
                    logger.warning(f"Tool execution error: {e}")
                    messages.append({"role": "assistant", "content": response})
                    messages.append({"role": "user", "content": f"Tool error: {e}\n\nPlease continue without this tool."})
                    full_output += response + "\n"
            else:
                full_output += response
                break

        if tool_used:
            graph.context["tools_used"] = graph.context.get("tools_used", [])
            graph.context["tools_used"].append(role)

        graph.context[f"{role}_response"] = full_output
        return {"output": full_output}

    def _get_tool_docs(self, tool_sdk, role: str) -> str:
        all_tools = [
            ("write_file", "Create or overwrite a file", '{"path": "file_path", "content": "file_content"}'),
            ("read_file", "Read a file", '{"path": "file_path"}'),
            ("list_dir", "List directory contents", '{"path": "dir_path"}'),
            ("run_python", "Execute Python code", '{"code": "python_code", "timeout": 30}'),
            ("run_command", "Run a shell command", '{"command": "shell_command", "timeout": 30}'),
            ("search_web", "Search the web", '{"query": "search_query", "max_results": 10}'),
            ("read_url", "Fetch and extract text from a URL", '{"url": "page_url"}'),
            ("calculate", "Evaluate a math expression", '{"expression": "2 + 2"}'),
            ("now", "Get current date and time", "{}"),
        ]

        docs = []
        for name, desc, example in all_tools:
            docs.append(f"  - {name}: {desc}")
            docs.append(f"    Params: {example}")

        return "\n".join(docs)

    def _get_context_summary(self, graph: StateGraph) -> str:
        parts = []
        for role in ["planner", "researcher", "coder", "reasoner", "reviewer"]:
            key = f"{role}_response"
            if key in graph.context and graph.context[key]:
                val = graph.context[key]
                parts.append(f"=== {role.upper()} OUTPUT ===\n{val[:500]}")
        return "\n\n".join(parts)

    async def _run_tool(self, node: GraphNode, graph: StateGraph) -> dict:
        container = self._get_container()
        tool_sdk = container.tool_sdk
        result = await tool_sdk.execute(node.tool_name, node.params)
        return {"output": result.output if result.success else result.error,
                "status": "success" if result.success else "failed",
                "error": result.error if not result.success else ""}

    async def _run_conditional(self, node: GraphNode, graph: StateGraph) -> dict:
        if node.condition:
            next_id = node.condition(graph.context)
            return {"output": f"Conditional routing to {next_id}", "next": next_id}
        return {"output": "No condition", "next": node.next_nodes.get("__default__")}

    async def _run_parallel(self, node: GraphNode, graph: StateGraph) -> dict:
        tasks = [self._run_agent_with_tools(n, graph) for n in node.parallel_nodes]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        outputs = []
        for r in results:
            if isinstance(r, dict):
                outputs.append(r.get("output", ""))
        return {"output": "\n---\n".join(outputs)}

    async def _run_reflection(self, node: GraphNode, graph: StateGraph) -> dict:
        container = self._get_container()
        provider = container.provider_sdk
        cfg = container.config

        prev_output = graph.context.get(node.params.get("reflect_on", ""), "")
        if not prev_output:
            prev_output = self._get_context_summary(graph)

        prompt = f"""Review this work and provide constructive feedback.
Check for correctness, completeness, and quality.

Work to review:
{prev_output[:2000]}

If the work is good and complete, respond with "APPROVED" and a brief summary.
If improvements are needed, respond with "NEEDS_IMPROVEMENT" and list specific changes needed."""

        messages = [
            {"role": "system", "content": "You are a Review Agent. Critique work and suggest improvements."},
            {"role": "user", "content": prompt},
        ]
        try:
            result = await provider.chat_completion(cfg.default_provider, cfg.default_model, messages)
            if result.success and result.data:
                text = (result.data.get("choices", [{}])[0]
                        .get("message", {}).get("content", ""))
                graph.context["review_result"] = text
                return {"output": text}
        except Exception as e:
            logger.warning(f"Reflection error: {e}")

        return {"output": "(review unavailable)"}

    async def _run_router(self, node: GraphNode, graph: StateGraph) -> dict:
        intent = node.params.get("intent", "")
        route_to = node.next_nodes.get(intent) or node.next_nodes.get("__default__", "")
        return {"output": f"Routing to {route_to}", "next": route_to}

    def _get_container(self):
        from app.core.container import Container
        return Container()

    async def build_default_agent_graph(self, goal: str) -> str:
        gid = self.create_graph(f"agent_graph_{uuid.uuid4().hex[:8]}")
        graph = self._graphs[gid]
        graph.context["goal"] = goal

        supervisor = GraphNode(id="supervisor", name="Supervisor", node_type=NodeType.SUPERVISOR)
        self.add_node(gid, supervisor)

        planner = GraphNode(id="planner", name="Planner", node_type=NodeType.AGENT, agent_role="planner")
        self.add_node(gid, planner)

        researcher = GraphNode(id="researcher", name="Researcher", node_type=NodeType.AGENT, agent_role="researcher")
        self.add_node(gid, researcher)

        coder = GraphNode(id="coder", name="Coder", node_type=NodeType.AGENT, agent_role="coder")
        self.add_node(gid, coder)

        reasoner = GraphNode(id="reasoner", name="Reasoner", node_type=NodeType.AGENT, agent_role="reasoner")
        self.add_node(gid, reasoner)

        reviewer = GraphNode(id="reviewer", name="Reviewer", node_type=NodeType.REFLECTION,
                             params={"reflect_on": "__last__"})
        self.add_node(gid, reviewer)

        self.add_edge(gid, "supervisor", "planner", "planner")
        self.add_edge(gid, "supervisor", "researcher", "researcher")
        self.add_edge(gid, "supervisor", "coder", "coder")
        self.add_edge(gid, "supervisor", "reasoner", "reasoner")
        self.add_edge(gid, "supervisor", "planner", "__default__")

        self.add_edge(gid, "planner", "researcher", "__default__")
        self.add_edge(gid, "researcher", "coder", "__default__")
        self.add_edge(gid, "coder", "reasoner", "__default__")
        self.add_edge(gid, "reasoner", "reviewer", "__default__")

        return gid
