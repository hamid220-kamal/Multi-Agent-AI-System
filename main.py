from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import json

from core.schema import SystemState
from core.engine import AsyncGraphOrchestrator
from nodes.agents import (
    planner_agent, planner_router,
    researcher_agent, researcher_router,
    supervisor_agent, supervisor_router,
    critic_agent, critic_router
)

app = FastAPI(title="Advanced Agent Orchestrator", version="1.0.0")

# Instantiate and configure the Engine
engine = AsyncGraphOrchestrator(max_iterations=10)
engine.add_node("planner", planner_agent, planner_router)
engine.add_node("researcher", researcher_agent, researcher_router)
engine.add_node("supervisor", supervisor_agent, supervisor_router)
engine.add_node("critic", critic_agent, critic_router)

class OrchestrationRequest(BaseModel):
    user_prompt: str

class ResumeRequest(BaseModel):
    state_snapshot: dict
    human_feedback: str

@app.post("/api/v1/agent/orchestrate")
async def orchestrate_agents(request: OrchestrationRequest):
    """Starts a new asynchronous agent pipeline."""
    state = SystemState(user_prompt=request.user_prompt)
    
    # Return Server-Sent Events (SSE) stream for real-time telemetry
    return StreamingResponse(
        engine.stream_execution(state, entrypoint="planner"),
        media_type="text/event-stream"
    )

@app.post("/api/v1/agent/resume")
async def resume_agents(request: ResumeRequest):
    """Resumes a paused pipeline using injected human feedback."""
    # Re-hydrate state from snapshot
    state = SystemState(**request.state_snapshot)
    
    # Inject human feedback and flip status to allow routing to continue
    state.human_feedback = request.human_feedback
    state.status = "PROCESSING"
    
    # Resume the stream starting from the supervisor node
    return StreamingResponse(
        engine.stream_execution(state, entrypoint="supervisor"),
        media_type="text/event-stream"
    )
