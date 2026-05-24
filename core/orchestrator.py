from typing import Callable, Dict, Awaitable, Optional
from core.state import State

NodeFunction = Callable[[State], Awaitable[State]]

class AgentOrchestrator:
    """
    State Machine orchestrator that manages nodes and deterministic transitions.
    """
    def __init__(self):
        self.nodes: Dict[str, NodeFunction] = {}
        self.edges: Dict[str, str] = {}
        self.entry_point: Optional[str] = None

    def add_node(self, name: str, func: NodeFunction) -> None:
        """Register an agent node."""
        self.nodes[name] = func

    def add_edge(self, from_node: str, to_node: str) -> None:
        """Define a deterministic transition between nodes."""
        self.edges[from_node] = to_node

    def set_entry_point(self, node_name: str) -> None:
        """Set the starting node for the orchestration graph."""
        self.entry_point = node_name

    async def fallback_exit(self, state: State) -> State:
        """Graceful fallback triggered upon infinite loop detection."""
        state.execution_log.append("Fallback exit triggered due to infinite loop protection.")
        state.current_task = "ABORTED"
        return state

    async def run(self, initial_state: State) -> State:
        """
        Execute the orchestration loop starting from the entry point.
        """
        if not self.entry_point:
            raise ValueError("Entry point must be set before running the orchestrator.")

        current_node_name = self.entry_point
        state = initial_state
        state.update_hash() # Initialize hash
        
        while current_node_name and current_node_name in self.nodes:
            state.loop_counter += 1
            node_func = self.nodes[current_node_name]
            
            # Execute current node
            state = await node_func(state)
            
            # Infinite loop protection
            changed = state.update_hash()
            if not changed and state._unchanged_iterations >= 5:
                return await self.fallback_exit(state)
            
            # Route to next node
            current_node_name = self.edges.get(current_node_name)
            
        return state
