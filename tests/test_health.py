from fastapi.testclient import TestClient


def test_healthcheck_returns_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_returns_service_status(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["service"] == "FacNor API"


def test_cors_allows_vite_frontend_origin(client: TestClient) -> None:
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
