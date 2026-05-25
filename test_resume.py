import asyncio
import httpx
import json

async def test_human_in_the_loop():
    url_start = "http://127.0.0.1:8000/api/v1/agent/orchestrate"
    url_resume = "http://127.0.0.1:8000/api/v1/agent/resume"
    
    print("--- Phase 1: Initiating Pipeline ---")
    state_snapshot = {}
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream("POST", url_start, json={"user_prompt": "Research the latest advancements in quantum computing."}) as response:
            async for chunk in response.aiter_lines():
                if chunk:
                    data = json.loads(chunk)
                    print(f"[{data.get('event').upper()}] {data.get('node', 'unknown')} -> status: {data.get('status', 'RUNNING')}")
                    
                    # Capture the latest state snapshot right when the system pauses
                    if data.get('status') == "PAUSED":
                        print("\n[SYSTEM PAUSED] Awaiting Human Validation...")
                        # In a real app, this snapshot would be fetched from a database or Redis via task_id.
                        # For our demo, we just recreate the basic state that led to the pause.
                        state_snapshot = {
                            "task_id": data.get("task_id", "demo-id"),
                            "user_prompt": "Research the latest advancements in quantum computing.",
                            "plan": ["Analyze the core concepts", "Fetch latest research", "Synthesize findings"],
                            "current_step_idx": 1,
                            "agent_logs": {},
                            "status": "PAUSED"
                        }
                        break
                        
    # Simulate a human taking 2 seconds to read the research and provide feedback
    print("\n--- Phase 2: Human Reviewing ---")
    await asyncio.sleep(2)
    feedback = "Looks great! Make sure the critic focuses heavily on error correction techniques in quantum computing."
    print(f"Human input provided: '{feedback}'\n")

    print("--- Phase 3: Resuming Pipeline ---")
    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream("POST", url_resume, json={"state_snapshot": state_snapshot, "human_feedback": feedback}) as response:
            async for chunk in response.aiter_lines():
                if chunk:
                    data = json.loads(chunk)
                    print(f"[{data.get('event').upper()}] {data.get('node', 'unknown')} -> status: {data.get('status', 'RUNNING')}")
                    
    print("\n[DONE] HITL Workflow Completed!")

if __name__ == "__main__":
    asyncio.run(test_human_in_the_loop())
