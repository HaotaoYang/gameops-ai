
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_status_code():
    response = client.get("/health")

    assert response.status_code == 200


def test_health_json():
    response = client.get("/health")

    assert response.json() == {
        "status": "ok"
    }


def test_health_content_type():
    response = client.get("/health")

    assert (
        response.headers["content-type"]
        == "application/json"
    )


def test_unknown_path():
    response = client.get("/not-found")

    assert response.status_code == 404
