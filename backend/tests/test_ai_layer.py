"""Phase 10 provider boundary and structured mock-output tests."""

import pytest

from app.ai import MockLLMProvider
from app.services.ai import AIService


async def test_mock_provider_returns_output_matching_requested_shape() -> None:
    output, usage = await MockLLMProvider().generate_structured(
        task="incident_summary",
        system_prompt="Be concise",
        user_prompt="CPU-X9 affected",
        output_schema={
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "confidence": {"type": "number"},
                "risks": {"type": "array"},
            },
        },
    )
    assert output["summary"].startswith("Mock incident_summary")
    assert output["confidence"] == 0
    assert output["risks"] == []
    assert usage["input_tokens"] > 0


def test_prompt_rendering_rejects_missing_versioned_input() -> None:
    with pytest.raises(ValueError, match="incident"):
        AIService._render("Explain {incident}", {})
