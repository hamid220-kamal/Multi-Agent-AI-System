import asyncio
from typing import List
from pydantic import BaseModel, Field
from core.schema import SystemState
from core.llm import llm
from tools.search import search_web
from core.memory import vector_memory

# ---------------------------------------------------------
# Pydantic Schemas for Structured LLM Outputs
# ---------------------------------------------------------
class PlanSchema(BaseModel):
    steps: List[str] = Field(description="A sequential list of distinct steps to fulfill the user request.")

class SearchQuerySchema(BaseModel):
    query: str = Field(description="The precise web search query to fetch needed information for the current step.")

class EvaluationSchema(BaseModel):
    passed: bool = Field(description="True if the data fully satisfies the user prompt, False otherwise.")
    reason: str = Field(description="Detailed explanation of why it passed or failed.")

# ---------------------------------------------------------
# Agent Nodes
# ---------------------------------------------------------
async def planner_agent(state: SystemState) -> SystemState:
    if "planner" not in state.agent_logs:
        state.agent_logs["planner"] = []
        
    state.agent_logs["planner"].append("Invoking LLM to generate plan.")
    
    system_prompt = "You are an expert Planner Agent. Break down the user's objective into a short, logical 2-3 step execution plan."
    try:
        plan_output = await llm.generate_structured(
            prompt=state.user_prompt,
            schema=PlanSchema,
            system=system_prompt
        )
        state.plan = plan_output.steps
        state.agent_logs["planner"].append(f"Plan generated: {state.plan}")
        state.current_step_idx = 0
        state.status = "PROCESSING"
    except Exception as e:
        state.agent_logs["planner"].append(f"LLM Error: {str(e)}")
        state.status = "FAILED"
        
    return state

async def researcher_agent(state: SystemState) -> SystemState:
    if "researcher" not in state.agent_logs:
        state.agent_logs["researcher"] = []
        
    current_step = state.plan[state.current_step_idx] if state.current_step_idx < len(state.plan) else "Finalizing research"
    state.agent_logs["researcher"].append(f"Formulating query for step: {current_step}")
    
    system_prompt = "You are an expert Researcher Agent. Formulate the best web search query."
    user_msg = f"Overall Objective: {state.user_prompt}\nCurrent Step to Execute: {current_step}"
    
    try:
        query_output = await llm.generate_structured(
            prompt=user_msg,
            schema=SearchQuerySchema,
            system=system_prompt
        )
        search_query = query_output.query
        state.agent_logs["researcher"].append(f"Executing search: '{search_query}'")
        
        # Execute the search tool
        results = await search_web(search_query)
        
        # Store into Vector DB
        for res in results:
            if isinstance(res, dict) and "body" in res:
                vector_memory.add_memory(
                    text=res["body"],
                    metadata={"query": search_query, "step": current_step}
                )
        
        state.agent_logs["researcher"].append("Saved findings into Vector DB.")
        
        state.current_step_idx += 1
        state.status = "PROCESSING"
        
    except Exception as e:
        state.agent_logs["researcher"].append(f"Error: {str(e)}")
        state.status = "FAILED"
        
    return state

async def supervisor_agent(state: SystemState) -> SystemState:
    """
    Human-in-the-Loop Node.
    Pauses orchestration to wait for human approval before sending findings to the critic.
    """
    if "supervisor" not in state.agent_logs:
        state.agent_logs["supervisor"] = []

    if state.human_feedback is None:
        state.agent_logs["supervisor"].append("Pausing execution. Awaiting human validation...")
        state.status = "PAUSED"
    else:
        state.agent_logs["supervisor"].append(f"Received human feedback: '{state.human_feedback}'")
        state.status = "PROCESSING"
        
    return state

async def critic_agent(state: SystemState) -> SystemState:
    if "critic" not in state.agent_logs:
        state.agent_logs["critic"] = []
        
    state.agent_logs["critic"].append("Querying Vector DB for context...")
    rag_context = vector_memory.query_memory(state.user_prompt, n_results=5)
    
    str_data = "\n---\n".join(rag_context) if rag_context else "No relevant data found."
    
    # Inject human feedback into the evaluation prompt if present
    feedback_injection = f"\nHuman Supervisor Feedback: {state.human_feedback}" if state.human_feedback else ""
    
    system_prompt = "You are a stringent Critic Agent. Evaluate the retrieved semantic memory context to determine if it satisfies the user's original objective."
    user_msg = f"Objective: {state.user_prompt}{feedback_injection}\nSemantic Memory Gathered:\n{str_data}"
    
    try:
        eval_output = await llm.generate_structured(
            prompt=user_msg,
            schema=EvaluationSchema,
            system=system_prompt
        )
        
        state.agent_logs["critic"].append(f"Evaluation: {eval_output.reason} (Passed: {eval_output.passed})")
        
        if eval_output.passed or state.current_step_idx >= len(state.plan):
            state.status = "COMPLETED"
        else:
            state.status = "REVISE"
            
    except Exception as e:
        state.agent_logs["critic"].append(f"Error: {str(e)}")
        state.status = "FAILED"
        
    return state

# ---------------------------------------------------------
# Routers
# ---------------------------------------------------------
def planner_router(state: SystemState) -> str:
    if state.status == "PROCESSING":
        return "researcher"
    return "END"

def researcher_router(state: SystemState) -> str:
    if state.status == "PROCESSING":
        # Route to Supervisor for Human Approval instead of straight to Critic
        return "supervisor"
    return "END"

def supervisor_router(state: SystemState) -> str:
    if state.status == "PROCESSING":
        return "critic"
    return "END" # Will end up here if status is PAUSED

def critic_router(state: SystemState) -> str:
    if state.status == "REVISE":
        # Clear feedback so the supervisor triggers a pause again next cycle
        state.human_feedback = None 
        return "researcher"
    return "END"
