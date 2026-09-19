"""Application-level errors safe to expose through the API."""


class ApplicationError(Exception):
    """Expected application failure with a stable public code."""

    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class TenantIsolationError(ApplicationError):
    """Raised when code attempts to cross the active organization boundary."""

    def __init__(self) -> None:
        super().__init__(
            code="tenant_isolation_violation",
            message="The requested resource is not available in this organization.",
            status_code=403,
        )
