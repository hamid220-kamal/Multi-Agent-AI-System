import httpx
import json
from typing import Type, TypeVar
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)

class FreeCloudLLMEngine:
    """
    Connects to the free public Hugging Face Inference API.
    Requires ZERO disk space and NO API KEY!
    Includes a built-in offline fallback for robust portfolio demos.
    """
    def __init__(self, model="HuggingFaceH4/zephyr-7b-beta"):
        self.api_url = f"https://api-inference.huggingface.co/models/{model}"

    def _get_mock_fallback(self, schema: Type[T]) -> T:
        """Returns dummy mock data if the network is disconnected during a demo."""
        if schema.__name__ == "PlanSchema":
            return schema(steps=["Analyze the core concepts", "Fetch latest research", "Synthesize findings"])
        elif schema.__name__ == "SearchQuerySchema":
            return schema(query="latest advancements in quantum computing research 2024")
        elif schema.__name__ == "EvaluationSchema":
            return schema(passed=True, reason="Data matches the initial prompt criteria.")
        raise ValueError("Unknown schema for mock fallback")

    async def generate(self, prompt: str, system: str = "") -> str:
        full_prompt = f"<|system|>\n{system}</s>\n<|user|>\n{prompt}</s>\n<|assistant|>\n"
        payload = {
            "inputs": full_prompt,
            "parameters": {"max_new_tokens": 512, "temperature": 0.1, "return_full_text": False}
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(self.api_url, json=payload)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                return data[0].get("generated_text", "").strip()
            return str(data)

    async def generate_structured(self, prompt: str, schema: Type[T], system: str = "") -> T:
        schema_json = schema.model_json_schema()
        system_prompt = (
            f"{system}\n\n"
            f"You MUST reply ONLY with a single valid raw JSON object matching this exact schema. "
            f"Do not include any other text:\n"
            f"{json.dumps(schema_json, indent=2)}"
        )
        
        try:
            response_text = await self.generate(prompt, system=system_prompt)
        except Exception as e:
            # If the API fails (DNS block, rate limit, offline demo), gracefully fallback to mock data
            print(f"[LLM WARNING] API Error ({e}). Using offline mock fallback.")
            return self._get_mock_fallback(schema)
            
        response_text = response_text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
            
        try:
            return schema.model_validate_json(response_text.strip())
        except Exception as e:
            raise ValueError(f"Failed to parse JSON schema: {e}\nRaw output: {response_text}")

# Global instance configured for the free cloud model
llm = FreeCloudLLMEngine()
