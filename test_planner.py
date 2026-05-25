import asyncio
from core.schema import SystemState
from nodes.agents import planner_agent

async def test():
    state = SystemState(user_prompt="test")
    state = await planner_agent(state)
    print("STATUS:", state.status)
    print("LOGS:", state.agent_logs)

if __name__ == "__main__":
    asyncio.run(test())
