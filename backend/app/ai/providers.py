"""Provider boundary; domain workflows never import or depend on these implementations."""
# mypy: ignore-errors

import json
from collections.abc import Mapping
from typing import Protocol

import httpx


class LLMProvider(Protocol):
    async def generate_structured(
        self,
        *,
        task: str,
        system_prompt: str,
        user_prompt: str,
        output_schema: Mapping[str, object],
    ) -> tuple[dict[str, object], dict[str, int]]: ...


class MockLLMProvider:
    """Deterministic provider for tests, demos, and keyless local development."""

    async def generate_structured(
        self,
        *,
        task: str,
        system_prompt: str,
        user_prompt: str,
        output_schema: Mapping[str, object],
    ) -> tuple[dict[str, object], dict[str, int]]:
        properties = dict(output_schema.get("properties", {}))
        result: dict[str, object] = {}
        for key, schema in properties.items():
            kind = dict(schema).get("type") if isinstance(schema, Mapping) else None
            result[key] = (
                []
                if kind == "array"
                else {}
                if kind == "object"
                else False
                if kind == "boolean"
                else 0
                if kind in {"number", "integer"}
                else f"Mock {task}: {user_prompt[:120]}"
            )
        return result, {
            "input_tokens": len(system_prompt.split()) + len(user_prompt.split()),
            "output_tokens": len(json.dumps(result).split()),
        }


class OpenAIProvider:
    """Small Responses API client with JSON-schema output enforcement."""

    def __init__(
        self, api_key: str, model: str, base_url: str = "https://api.openai.com/v1"
    ) -> None:
        self.api_key, self.model, self.base_url = api_key, model, base_url.rstrip("/")

    async def generate_structured(
        self,
        *,
        task: str,
        system_prompt: str,
        user_prompt: str,
        output_schema: Mapping[str, object],
    ) -> tuple[dict[str, object], dict[str, int]]:
        payload = {
            "model": self.model,
            "instructions": system_prompt,
            "input": user_prompt,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": task.replace("-", "_"),
                    "schema": dict(output_schema),
                    "strict": True,
                }
            },
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/responses",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
            )
            response.raise_for_status()
            body = response.json()
        text = body.get("output_text")
        if not isinstance(text, str):
            raise ValueError("OpenAI response did not contain structured output text")
        output = json.loads(text)
        if not isinstance(output, dict):
            raise ValueError("OpenAI structured output must be a JSON object")
        usage = body.get("usage", {})
        return output, {
            "input_tokens": int(usage.get("input_tokens", 0)),
            "output_tokens": int(usage.get("output_tokens", 0)),
        }
