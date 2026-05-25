from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import uuid

class SystemState(BaseModel):
    """
    Global execution state passed between all agent nodes.
    Acts as the source of truth for the entire distributed system.
    """
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_prompt: str
    plan: List[str] = Field(default_factory=list)
    current_step_idx: int = 0
    agent_logs: Dict[str, List[str]] = Field(default_factory=dict)
    
    # State Machine control flags
    status: str = "PENDING"  # PENDING, PROCESSING, REVISE, PAUSED, COMPLETED, FAILED
    
    # Human-in-the-loop (HITL) support
    human_feedback: Optional[str] = None
    
    # Anti-Infinite Loop mechanisms
    _last_state_hash: Optional[int] = None
    _unchanged_iterations: int = 0

    def update_hash(self) -> bool:
        """
        Calculates the hash of the current state and returns True if changed.
        Crucial for detecting deadlocks in the state machine graph.
        """
        current_hash = hash(str(self.model_dump()))
        if self._last_state_hash == current_hash:
            self._unchanged_iterations += 1
            return False
        
        self._last_state_hash = current_hash
        self._unchanged_iterations = 0
        return True
