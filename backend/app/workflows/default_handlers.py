"""Built-in deterministic handlers used by the configurable response workflow."""

from collections.abc import Mapping

from app.domain.enums import RunStatus
from app.workflows.contracts import StageExecutionContext, StageResult
from app.workflows.registry import StageRegistry


class ConfiguredStageHandler:
    """A safe generic stage that records its configured outcome in workflow context."""

    version = "1.0"

    def __init__(self, key: str) -> None:
        self.key = key

    async def execute(
        self,
        context: StageExecutionContext,
        config: Mapping[str, object],
    ) -> StageResult:
        wait_for_approval = bool(config.get("wait_for_approval", False))
        status = RunStatus.WAITING_FOR_APPROVAL if wait_for_approval else RunStatus.SUCCEEDED
        output = {
            "stage": self.key,
            "summary": str(config.get("summary", f"{self.key} completed")),
            "simulation": bool(context.values.get("simulation", False)),
        }
        return StageResult(
            output=output,
            context_updates={self.key: output},
            status=status,
        )


BUILT_IN_STAGE_HANDLERS = (
    "detect-disruption",
    "assess-impact",
    "score-risk",
    "generate-scenarios",
    "recommend-action",
    "route-approval",
    "execute-mitigation",
    "verify-outcome",
)


def create_stage_registry() -> StageRegistry:
    """Return the application registry shared by authoring and execution APIs."""

    registry = StageRegistry()
    for key in BUILT_IN_STAGE_HANDLERS:
        registry.register(ConfiguredStageHandler(key))
    return registry
