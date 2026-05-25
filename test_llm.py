import asyncio
from core.llm import llm

async def run():
    print("Testing Hugging Face LLM Endpoint...")
    try:
        response = await llm.generate("Hello, are you online?")
        print("Success:")
        print(response)
    except Exception as e:
        print("Failed:")
        print(e)

if __name__ == "__main__":
    asyncio.run(run())
