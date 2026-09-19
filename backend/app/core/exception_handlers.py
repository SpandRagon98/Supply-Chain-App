"""Safe, consistent HTTP exception translation."""

from typing import Any

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.schemas import ErrorEnvelope, ErrorItem, ResponseMeta
from app.core.errors import ApplicationError

logger = structlog.get_logger(__name__)


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


def _error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    details: list[dict[str, object]] | None = None,
) -> JSONResponse:
    payload = ErrorEnvelope(
        error=ErrorItem(code=code, message=message, details=details or []),
        meta=ResponseMeta(request_id=_request_id(request)),
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump(mode="json"))


async def application_error_handler(request: Request, exc: Exception) -> JSONResponse:
    error = exc
    if not isinstance(error, ApplicationError):  # pragma: no cover - framework contract
        raise error
    return _error_response(
        request,
        status_code=error.status_code,
        code=error.code,
        message=error.message,
    )


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    error = exc
    if not isinstance(error, RequestValidationError):  # pragma: no cover - framework contract
        raise error
    details: list[dict[str, Any]] = []
    for item in error.errors():
        details.append(
            {
                "location": [str(part) for part in item["loc"]],
                "message": item["msg"],
                "type": item["type"],
            }
        )
    return _error_response(
        request,
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        code="validation_error",
        message="The request could not be validated.",
        details=details,
    )


async def http_error_handler(request: Request, exc: Exception) -> JSONResponse:
    error = exc
    if not isinstance(error, StarletteHTTPException):  # pragma: no cover - framework contract
        raise error
    message = error.detail if isinstance(error.detail, str) else "The request failed."
    return _error_response(
        request,
        status_code=error.status_code,
        code="http_error",
        message=message,
    )


async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_exception", error_type=type(exc).__name__)
    return _error_response(
        request,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="internal_error",
        message="An unexpected error occurred.",
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Install error handlers in most-specific-first order."""

    app.add_exception_handler(ApplicationError, application_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_error_handler)
    app.add_exception_handler(Exception, unexpected_error_handler)
