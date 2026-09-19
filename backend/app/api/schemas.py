"""Shared API response contracts."""

from typing import TypeVar

from pydantic import BaseModel, Field

DataT = TypeVar("DataT")


class ResponseMeta(BaseModel):
    """Metadata common to successful responses."""

    request_id: str


class ResponseEnvelope[DataT](BaseModel):
    """Stable envelope for successful API responses."""

    data: DataT
    meta: ResponseMeta


class ErrorItem(BaseModel):
    """Machine-readable error item."""

    code: str
    message: str
    details: list[dict[str, object]] = Field(default_factory=list)


class ErrorEnvelope(BaseModel):
    """Stable envelope for failed API responses."""

    error: ErrorItem
    meta: ResponseMeta
