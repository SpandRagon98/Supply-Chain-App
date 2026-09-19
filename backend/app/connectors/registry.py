"""Versioned connector-adapter registry."""

from app.connectors.contracts import ConnectorAdapter
from app.core.errors import ConnectorNotFoundError


class ConnectorRegistry:
    def __init__(self) -> None:
        self._adapters: dict[tuple[str, str], ConnectorAdapter] = {}

    def register(self, adapter: ConnectorAdapter) -> None:
        reference = (adapter.key, adapter.version)
        if reference in self._adapters:
            raise ValueError(
                f"Connector adapter '{adapter.key}' version "
                f"'{adapter.version}' is already registered."
            )
        self._adapters[reference] = adapter

    def get(self, key: str, version: str) -> ConnectorAdapter:
        try:
            return self._adapters[(key, version)]
        except KeyError as error:
            raise ConnectorNotFoundError("connector adapter") from error

    @property
    def references(self) -> tuple[tuple[str, str], ...]:
        return tuple(sorted(self._adapters))
