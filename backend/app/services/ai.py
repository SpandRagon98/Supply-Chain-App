"""Versioned prompt execution and LLM-run telemetry; optional downstream assistance only."""

import hashlib
import json
from time import perf_counter

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import LLMProvider
from app.domain.enums import LLMRunStatus
from app.domain.models import LLMModelConfiguration, LLMRun, PromptTemplate
from app.domain.tenant import TenantContext


class AIService:
    def __init__(self, session: AsyncSession, tenant: TenantContext, provider: LLMProvider) -> None:
        self.session, self.tenant, self.provider = session, tenant, provider

    async def run(
        self,
        configuration: LLMModelConfiguration,
        prompt: PromptTemplate,
        inputs: dict[str, object],
        task: str,
    ) -> tuple[dict[str, object], LLMRun]:
        if (
            configuration.organization_id != self.tenant.organization_id
            or prompt.organization_id != self.tenant.organization_id
        ):
            raise ValueError("AI configuration and prompt must belong to the active tenant")
        rendered_system, rendered_user = (
            self._render(prompt.system_template, inputs),
            self._render(prompt.user_template, inputs),
        )
        digest = hashlib.sha256(
            json.dumps(inputs, sort_keys=True, default=str).encode()
        ).hexdigest()
        started = perf_counter()
        run = LLMRun(
            organization_id=self.tenant.organization_id,
            model_configuration_id=configuration.id,
            prompt_template_id=prompt.id,
            provider=configuration.provider,
            model=configuration.model,
            prompt_version=prompt.version,
            status=LLMRunStatus.PENDING,
            input_hash=digest,
        )
        self.session.add(run)
        await self.session.flush()
        try:
            output, usage = await self.provider.generate_structured(
                task=task,
                system_prompt=rendered_system,
                user_prompt=rendered_user,
                output_schema=prompt.output_schema,
            )
            run.status, run.output_payload = LLMRunStatus.SUCCEEDED, output
            run.input_tokens, run.output_tokens = (
                usage.get("input_tokens"),
                usage.get("output_tokens"),
            )
        except Exception as error:
            run.status, run.error_code = LLMRunStatus.FAILED, type(error).__name__
            run.output_payload = {"error": "Provider execution failed; inspect telemetry."}
            await self.session.flush()
            raise
        finally:
            run.latency_ms = int((perf_counter() - started) * 1000)
            await self.session.flush()
        return output, run

    @staticmethod
    def _render(template: str, inputs: dict[str, object]) -> str:
        try:
            return template.format_map(inputs)
        except KeyError as error:
            raise ValueError(f"Prompt requires missing input: {error.args[0]}") from error
