from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class State(BaseModel):
    """
    Global state object passed between agent nodes.
    """
    messages: List[Dict[str, str]] = Field(
        default_factory=list, 
        description="Global conversation memory"
    )
    execution_log: List[str] = Field(
        default_factory=list, 
        description="Execution log of events"
    )
    current_task: Optional[str] = Field(
        default=None, 
        description="Current active task"
    )
    loop_counter: int = Field(
        default=0, 
        description="Loop counter to track total transitions"
    )
    
    # Internal attribute to track unchanged iterations
    _unchanged_iterations: int = 0
    _last_state_hash: Optional[int] = None

    def update_hash(self) -> bool:
        """
        Calculates the hash of the current state and returns True if changed.
        """
        current_hash = hash(str(self.model_dump()))
        if self._last_state_hash == current_hash:
            self._unchanged_iterations += 1
            return False
        
        self._last_state_hash = current_hash
        self._unchanged_iterations = 0
        return True
