import os
import json
import httpx
from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel
from google import genai

class BaseAIProvider(ABC):
    @abstractmethod
    async def generate_structured(self, system_prompt: str, user_content: Any, response_model: type[BaseModel], temperature: float = 0.3) -> BaseModel:
        pass

class GeminiProvider(BaseAIProvider):
    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    async def generate_structured(self, system_prompt: str, user_content: Any, response_model: type[BaseModel], temperature: float = 0.3) -> BaseModel:
        config = {
            "system_instruction": system_prompt,
            "temperature": temperature,
            "response_mime_type": "application/json",
            "response_schema": response_model,
        }
        
        # user_content could be a string or a list of dicts (chat history)
        completion = self.client.models.generate_content(
            model=self.model_name,
            contents=user_content,
            config=config
        )
        
        parsed = completion.parsed
        if parsed is None:
            # Fallback string parsing just in case response_schema is dropped
            raw = completion.text or "{}"
            return response_model(**json.loads(raw))
        return parsed

class OllamaProvider(BaseAIProvider):
    def __init__(self):
        self.endpoint = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434/api/generate")
        # default to gemma4:e4b or read from env
        self.model_name = os.getenv("OLLAMA_MODEL", "gemma4:e4b")

    async def generate_structured(self, system_prompt: str, user_content: Any, response_model: type[BaseModel], temperature: float = 0.3) -> BaseModel:
        async with httpx.AsyncClient() as http_client:
            # Flatten chat history if necessary
            if isinstance(user_content, list):
                content_str = "\n".join([f"{msg['role']}: {msg['parts'][0]['text']}" for msg in user_content])
            else:
                content_str = user_content

            fallback_prompt = f"{system_prompt}\n\nCRITICAL: Answer ONLY with valid JSON exactly matching the schema.\n\nInput:\n{content_str}"
            
            res = await http_client.post(
                self.endpoint,
                json={
                    "model": self.model_name,
                    "prompt": fallback_prompt,
                    "format": response_model.model_json_schema(),
                    "stream": False,
                    "options": {
                        "temperature": temperature 
                    }
                },
                timeout=300.0
            )
            res.raise_for_status()
            ollama_data = res.json()
            raw_content = ollama_data.get("response", "{}")
            parsed_json = json.loads(raw_content)
            return response_model(**parsed_json)

def get_ai_provider(provider_name: str = None) -> BaseAIProvider:
    provider_name = provider_name or os.getenv("AI_PROVIDER", "gemini")
    if provider_name.lower() == "ollama":
        return OllamaProvider()
    return GeminiProvider()