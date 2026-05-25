import asyncio
import json
from typing import Callable, Dict, Awaitable, AsyncGenerator
from core.schema import SystemState

NodeFunction = Callable[[SystemState], Awaitable[SystemState]]
RouterFunction = Callable[[SystemState], str]

class AsyncGraphOrchestrator:
    """
    A zero-dependency, high-performance State Machine Orchestrator.
    Executes native Python asyncio nodes strictly mapped to deterministic routing edges.
    """
    def __init__(self, max_iterations: int = 15):
        self.nodes: Dict[str, NodeFunction] = {}
        self.routers: Dict[str, RouterFunction] = {}
        self.max_iterations = max_iterations

    def add_node(self, name: str, func: NodeFunction, router: RouterFunction):
        """Registers a compute node and its outbound routing logic."""
        self.nodes[name] = func
        self.routers[name] = router

    async def stream_execution(self, state: SystemState, entrypoint: str) -> AsyncGenerator[str, None]:
        """
        Executes the graph while yielding real-time JSON telemetry chunks for HTTP streaming.
        Stops on COMPLETED, FAILED, or PAUSED (Human-in-the-loop).
        """
        current_node_name = entrypoint
        iteration_count = 0

        while iteration_count < self.max_iterations:
            iteration_count += 1
            
            if current_node_name not in self.nodes:
                state.status = "FAILED"
                yield json.dumps({"event": "error", "error": f"Node {current_node_name} not found"}) + "\n"
                break

            # 1. Yield Start Event
            yield json.dumps({
                "event": "node_start",
                "node": current_node_name,
                "task_id": state.task_id
            }) + "\n"

            # 2. Execute Async Compute Node
            node_func = self.nodes[current_node_name]
            try:
                state = await node_func(state)
            except Exception as e:
                state.status = "FAILED"
                yield json.dumps({"event": "error", "node": current_node_name, "error": str(e)}) + "\n"
                break

            # 3. Detect State Mutations / Infinite Loops
            if not state.update_hash() and state._unchanged_iterations > 2:
                state.status = "FAILED"
                yield json.dumps({"event": "error", "error": "Infinite loop detected. State failed to mutate."}) + "\n"
                break

            # 4. Yield Completion Event
            yield json.dumps({
                "event": "node_complete",
                "node": current_node_name,
                "status": state.status,
                "logs": state.agent_logs.get(current_node_name, [])
            }) + "\n"

            # 5. Check Terminal States (including PAUSED for Human-in-the-loop)
            if state.status in ["COMPLETED", "FAILED", "PAUSED"]:
                break

            # 6. Route to Next Node
            router_func = self.routers[current_node_name]
            next_node = router_func(state)
            
            if next_node == "END":
                break
                
            current_node_name = next_node

        # Safety catch for max iterations
        if iteration_count >= self.max_iterations and state.status not in ["COMPLETED", "FAILED", "PAUSED"]:
            state.status = "FAILED"
            yield json.dumps({"event": "error", "error": "Max iterations reached without resolution."}) + "\n"
