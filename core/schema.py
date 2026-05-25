from pydantic import BaseModel, Field
from typing import List, Dict, Any
import uuid

class SystemState(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_prompt: str
    plan: List[str] = Field(default_factory=list)
    current_step_idx: int = Field(default=0)
    agent_logs: Dict[str, List[str]] = Field(default_factory=dict)
    shared_memory: Dict[str, Any] = Field(default_factory=dict)
    loop_telemetry: Dict[str, int] = Field(default_factory=dict)
    status: str = Field(default="PENDING")
