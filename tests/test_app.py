from fastapi.testclient import TestClient

from main import app


def test_application_starts_and_exposes_health(database_path):
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_application_uses_same_schema_initialization(database_path):
    with TestClient(app) as client:
        response = client.get("/schema/tables")
    assert response.status_code == 200
    assert {"users", "clients", "invoices", "invoice_lines"}.issubset(set(response.json()["tables"]))


def test_database_health_reports_initialized_schema(database_path):
    with TestClient(app) as client:
        response = client.get("/health/db")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] is True
    assert {"users", "clients", "invoices", "invoice_lines"}.issubset(set(payload["tables"]))
