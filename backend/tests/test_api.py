from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


def test_api_validates_questions_and_body_size(monkeypatch):
    monkeypatch.setattr(settings, "scheduler_enabled", False)
    with TestClient(app) as client:
        response = client.post("/api/analyses", json={"question": " "})
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "invalid_request"
        assert client.post("/api/analyses", content="x" * 17000).status_code == 413


def test_openapi_contains_typed_routes():
    schema = app.openapi()
    assert "Snapshot" in schema["components"]["schemas"]
    assert "/api/reports/{report_id}/refresh" in schema["paths"]
