from fastapi import FastAPI
from pydantic import BaseModel
from core.state import State
from core.orchestrator import AgentOrchestrator
from nodes.planner import planner_node
from nodes.researcher import researcher_node
from nodes.critic import critic_node

app = FastAPI(title="Multi-Agent AI System")

# Initialize orchestrator
orchestrator = AgentOrchestrator()

# Register nodes
orchestrator.add_node("planner", planner_node)
orchestrator.add_node("researcher", researcher_node)
orchestrator.add_node("critic", critic_node)

# Define transitions (Linear flow as example)
orchestrator.add_edge("planner", "researcher")
orchestrator.add_edge("researcher", "critic")

# Set entry point
orchestrator.set_entry_point("planner")

class AgentRunRequest(BaseModel):
    user_intent: str

@app.post("/api/v1/agent/run", response_model=State)
async def run_agent_workflow(request: AgentRunRequest):
    """
    Endpoint to trigger the asynchronous multi-agent orchestration loop.
    """
    initial_state = State(
        current_task="Process intent: " + request.user_intent
    )
    initial_state.messages.append({"role": "user", "content": request.user_intent})
    
    final_state = await orchestrator.run(initial_state)
    return final_state

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
