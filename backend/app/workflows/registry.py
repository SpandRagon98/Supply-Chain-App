"""In-process registry mapping persisted stage references to implementations."""

from app.core.errors import StageHandlerNotFoundError
from app.workflows.contracts import StageHandler


class StageRegistry:
    """Register versioned handlers without hard-coding orchestration branches."""

    def __init__(self) -> None:
        self._handlers: dict[tuple[str, str], StageHandler] = {}

    def register(self, handler: StageHandler) -> None:
        reference = (handler.key, handler.version)
        if reference in self._handlers:
            raise ValueError(
                f"Stage handler '{handler.key}' version '{handler.version}' is already registered."
            )
        self._handlers[reference] = handler

    def get(self, key: str, version: str) -> StageHandler:
        try:
            return self._handlers[(key, version)]
        except KeyError as error:
            raise StageHandlerNotFoundError(key, version) from error

    def contains(self, key: str, version: str) -> bool:
        return (key, version) in self._handlers

    @property
    def references(self) -> tuple[tuple[str, str], ...]:
        return tuple(sorted(self._handlers))
