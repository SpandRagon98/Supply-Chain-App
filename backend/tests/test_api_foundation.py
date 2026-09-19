"""API middleware and error contract tests."""

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.core.errors import ApplicationError


def test_liveness_uses_response_envelope_and_request_id(client: TestClient) -> None:
    response = client.get("/api/v1/health/live", headers={"X-Request-ID": "test-request"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "test-request"
    assert response.json() == {
        "data": {"status": "healthy", "checks": {}},
        "meta": {"request_id": "test-request"},
    }


def test_request_id_is_generated(client: TestClient) -> None:
    response = client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.headers["X-Request-ID"]
    assert response.json()["meta"]["request_id"] == response.headers["X-Request-ID"]


def test_not_found_uses_safe_error_envelope(client: TestClient) -> None:
    response = client.get("/does-not-exist")

    assert response.status_code == 404
    assert response.json()["error"] == {
        "code": "http_error",
        "message": "Not Found",
        "details": [],
    }


def test_application_error_is_translated(app: FastAPI) -> None:
    @app.get("/expected-error")
    async def expected_error() -> None:
        raise ApplicationError("conflict", "The resource conflicts.", 409)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/expected-error")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


def test_validation_error_omits_input_values(app: FastAPI) -> None:
    @app.get("/validated")
    async def validated(limit: int) -> dict[str, int]:
        return {"limit": limit}

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/validated", params={"limit": "secret-not-a-number"})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert "secret-not-a-number" not in response.text


def test_non_string_http_error_is_safely_translated(app: FastAPI) -> None:
    @app.get("/structured-error")
    async def structured_error() -> None:
        raise HTTPException(status_code=400, detail={"private": "value"})

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/structured-error")

    assert response.status_code == 400
    assert response.json()["error"]["message"] == "The request failed."
    assert "private" not in response.text


def test_unexpected_error_hides_exception_details(app: FastAPI) -> None:
    @app.get("/unexpected-error")
    async def unexpected_error() -> None:
        raise RuntimeError("database password must not leak")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/unexpected-error")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "database password" not in response.text


def test_cors_allows_configured_origin(client: TestClient) -> None:
    response = client.options(
        "/api/v1/health/live",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
