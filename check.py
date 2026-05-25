import httpx
import asyncio

async def run():
    async with httpx.AsyncClient() as c:
        r = await c.post('http://127.0.0.1:8000/api/v1/agent/orchestrate', json={'user_prompt':'Research quantum computing.'})
        print(r.text)

asyncio.run(run())
