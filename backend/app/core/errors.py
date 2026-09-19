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


class WorkflowNotFoundError(ApplicationError):
    """Raised when a tenant cannot access the requested workflow resource."""

    def __init__(self, resource: str) -> None:
        super().__init__(
            code="workflow_resource_not_found",
            message=f"The requested {resource} was not found.",
            status_code=404,
        )


class PublishedWorkflowImmutableError(ApplicationError):
    """Raised when published workflow content is edited in place."""

    def __init__(self) -> None:
        super().__init__(
            code="published_workflow_immutable",
            message=(
                "Published workflow versions are immutable; clone the version to create a draft."
            ),
            status_code=409,
        )


class WorkflowValidationError(ApplicationError):
    """Raised when a workflow graph cannot be safely published or executed."""

    def __init__(self, issues: tuple[str, ...]) -> None:
        self.issues = issues
        super().__init__(
            code="workflow_validation_failed",
            message="Workflow validation failed: " + "; ".join(issues),
            status_code=422,
        )


class StageHandlerNotFoundError(ApplicationError):
    """Raised when a workflow references an unavailable stage implementation."""

    def __init__(self, key: str, version: str) -> None:
        super().__init__(
            code="stage_handler_not_found",
            message=f"Stage handler '{key}' version '{version}' is not registered.",
            status_code=422,
        )


class ConnectorNotFoundError(ApplicationError):
    """Raised when a connector or adapter is unavailable in the active tenant."""

    def __init__(self, resource: str) -> None:
        super().__init__(
            code="connector_not_found",
            message=f"The requested {resource} was not found.",
            status_code=404,
        )


class ConnectorUnavailableError(ApplicationError):
    """Raised when a configured connector cannot currently execute."""

    def __init__(self, message: str) -> None:
        super().__init__(
            code="connector_unavailable",
            message=message,
            status_code=409,
        )
