from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from core.schema import SystemState
from core.engine import AsyncGraphOrchestrator
from nodes.agents import (
    planner_agent, researcher_agent, critic_agent,
    planner_router, researcher_router, critic_router
)

app = FastAPI(title="Advanced Multi-Agent Autonomous Pipeline")

# Initialize and map the graph engine
orchestrator = AsyncGraphOrchestrator()

orchestrator.add_node("planner", planner_agent)
orchestrator.add_node("researcher", researcher_agent)
orchestrator.add_node("critic", critic_agent)

orchestrator.add_conditional_edges("planner", planner_router)
orchestrator.add_conditional_edges("researcher", researcher_router)
orchestrator.add_conditional_edges("critic", critic_router)

orchestrator.set_entry_point("planner")

class OrchestrateRequest(BaseModel):
    user_prompt: str

@app.post("/api/v1/agent/orchestrate")
async def orchestrate_agent(request: OrchestrateRequest):
    """
    Asynchronous Server-Sent Events (SSE) streaming endpoint.
    Yields live JSON chunks showing agent-by-agent system status.
    """
    initial_state = SystemState(user_prompt=request.user_prompt)
    
    return StreamingResponse(
        orchestrator.stream_orchestrate(initial_state),
        media_type="text/event-stream"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
