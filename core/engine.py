import asyncio
import json
from typing import Callable, Dict, Awaitable, AsyncGenerator
from core.schema import SystemState

NodeFunction = Callable[[SystemState], Awaitable[SystemState]]
RouterFunction = Callable[[SystemState], str]

class AsyncGraphOrchestrator:
    def __init__(self):
        self.nodes: Dict[str, NodeFunction] = {}
        self.routers: Dict[str, RouterFunction] = {}
        self.entry_point: str | None = None

    def add_node(self, name: str, func: NodeFunction) -> None:
        self.nodes[name] = func

    def add_conditional_edges(self, from_node: str, router: RouterFunction) -> None:
        self.routers[from_node] = router

    def set_entry_point(self, name: str) -> None:
        self.entry_point = name

    async def emergency_fallback_node(self, state: SystemState) -> SystemState:
        if "emergency_fallback" not in state.agent_logs:
            state.agent_logs["emergency_fallback"] = []
        state.agent_logs["emergency_fallback"].append("Infinite loop detected. Forcing completion.")
        state.status = "COMPLETED"
        state.shared_memory["emergency_override"] = True
        state.plan = ["ABORTED DUE TO LOOP"]
        return state

    async def stream_orchestrate(self, state: SystemState) -> AsyncGenerator[str, None]:
        if not self.entry_point:
            yield f"data: {json.dumps({'error': 'Entry point not set'})}\n\n"
            return

        current_node = self.entry_point
        state.status = "PROCESSING"
        
        while current_node and current_node in self.nodes:
            # Pre-execution event
            yield f"data: {json.dumps({'event': 'node_start', 'node': current_node, 'state_summary': state.model_dump(exclude={'shared_memory'})})}\n\n"
            
            # Continuous telemetry and loop breakers
            state.loop_telemetry[current_node] = state.loop_telemetry.get(current_node, 0) + 1
            
            if state.loop_telemetry[current_node] > 3:
                yield f"data: {json.dumps({'event': 'loop_detected', 'node': current_node})}\n\n"
                try:
                    state = await self.emergency_fallback_node(state)
                except Exception as e:
                    yield f"data: {json.dumps({'event': 'error', 'node': 'emergency_fallback', 'error': str(e)})}\n\n"
                
                yield f"data: {json.dumps({'event': 'node_complete', 'node': 'emergency_fallback', 'status': state.status})}\n\n"
                break

            # Execute the node function
            node_func = self.nodes[current_node]
            try:
                state = await node_func(state)
            except Exception as e:
                state.status = "FAILED"
                if current_node not in state.agent_logs:
                    state.agent_logs[current_node] = []
                state.agent_logs[current_node].append(f"Execution failed: {str(e)}")
                yield f"data: {json.dumps({'event': 'error', 'node': current_node, 'error': str(e)})}\n\n"
                break
                
            yield f"data: {json.dumps({'event': 'node_complete', 'node': current_node, 'status': state.status})}\n\n"

            # Check if execution finished
            if state.status in ["COMPLETED", "FAILED"]:
                break

            # Conditional Routing
            if current_node in self.routers:
                try:
                    current_node = self.routers[current_node](state)
                except Exception as e:
                    state.status = "FAILED"
                    yield f"data: {json.dumps({'event': 'routing_error', 'node': current_node, 'error': str(e)})}\n\n"
                    break
            else:
                # No router means execution ends
                break
                
        yield f"data: {json.dumps({'event': 'workflow_end', 'final_status': state.status})}\n\n"
