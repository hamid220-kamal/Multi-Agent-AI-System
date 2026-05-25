import httpx
import asyncio
import json

async def test_pipeline():
    url = "http://127.0.0.1:8000/api/v1/agent/orchestrate"
    payload = {"user_prompt": "Research the latest advancements in quantum computing."}
    
    print("Starting pipeline stream...\n")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        # Parse the JSON string yielded by our SSE stream
                        data_chunk = json.loads(line[6:])
                        
                        event = data_chunk.get("event")
                        node = data_chunk.get("node", "N/A")
                        
                        if event == "node_start":
                            print(f"[START] {node}")
                        elif event == "node_complete":
                            print(f"[COMPLETED] {node} -> status: {data_chunk.get('status')}")
                        elif event == "loop_detected":
                            print(f"[\u26a0\ufe0f LOOP WARNING] Node '{node}' visited too many times!")
                        elif event == "error":
                            print(f"[\u274c ERROR] {node}: {data_chunk.get('error')}")
                        elif event == "workflow_end":
                            print(f"\n[DONE] Workflow finished with final status: {data_chunk.get('final_status')}")
                            
    except Exception as e:
        print(f"Error connecting to server: {e}")

if __name__ == "__main__":
    asyncio.run(test_pipeline())
