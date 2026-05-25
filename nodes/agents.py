import asyncio
from typing import List
from pydantic import BaseModel, Field
from core.schema import SystemState
from core.llm import llm
from tools.search import search_web

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
    
    system_prompt = "You are an expert Researcher Agent. Formulate the best DuckDuckGo web search query to gather data for the current step."
    user_msg = f"Overall Objective: {state.user_prompt}\nCurrent Step to Execute: {current_step}"
    
    try:
        # Ask LLM to determine the search query
        query_output = await llm.generate_structured(
            prompt=user_msg,
            schema=SearchQuerySchema,
            system=system_prompt
        )
        search_query = query_output.query
        state.agent_logs["researcher"].append(f"Executing search: '{search_query}'")
        
        # Execute the search tool autonomously
        results = await search_web(search_query)
        
        # Append to shared memory
        if "research_data" not in state.shared_memory:
            state.shared_memory["research_data"] = []
            
        state.shared_memory["research_data"].append({
            "step": current_step,
            "query": search_query,
            "results": results
        })
        
        state.current_step_idx += 1
        state.status = "PROCESSING"
        
    except Exception as e:
        state.agent_logs["researcher"].append(f"Error: {str(e)}")
        state.status = "FAILED"
        
    return state

async def critic_agent(state: SystemState) -> SystemState:
    if "critic" not in state.agent_logs:
        state.agent_logs["critic"] = []
        
    data = state.shared_memory.get("research_data", [])
    
    # Simple truncate to avoid massive context window overload for the free cloud model
    str_data = str(data)[:2500] 
    
    system_prompt = "You are a stringent Critic Agent. Evaluate the provided search results to determine if they satisfy the user's original objective."
    user_msg = f"Objective: {state.user_prompt}\nData Gathered So Far:\n{str_data}"
    
    try:
        eval_output = await llm.generate_structured(
            prompt=user_msg,
            schema=EvaluationSchema,
            system=system_prompt
        )
        
        state.agent_logs["critic"].append(f"Evaluation: {eval_output.reason} (Passed: {eval_output.passed})")
        
        if eval_output.passed or state.current_step_idx >= len(state.plan):
            # If the LLM says it passed, or we exhausted all steps, we complete.
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
        return "critic"
    return "END"

def critic_router(state: SystemState) -> str:
    if state.status == "REVISE":
        return "researcher"
    return "END"
