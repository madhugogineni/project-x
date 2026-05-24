from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/api/v1/system/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_profile_types_catalog() -> None:
    response = client.get("/api/v1/profiles/types")

    assert response.status_code == 200
    assert response.json()["supported_types"] == ["PRIMARY", "ADVISOR", "NOMINEE"]
