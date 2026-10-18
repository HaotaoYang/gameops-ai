
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


def test_server_3_players():
    """Server 3 should have exactly three players."""
    response = client.get("/servers/3/players")

    assert response.status_code == 200

    players = response.json()

    assert isinstance(players, list)
    assert len(players) == 3

    assert [
        player["player_id"]
        for player in players
    ] == [1001, 1002, 1004]


def test_server_5_players():
    """Server 5 should have exactly two players."""
    response = client.get("/servers/5/players")

    assert response.status_code == 200

    players = response.json()

    assert len(players) == 2

    assert [
        player["name"]
        for player in players
    ] == ["Charlie", "Eva"]


def test_missing_server_players():
    """A missing server returns an empty player list."""
    response = client.get("/servers/999/players")

    assert response.status_code == 200
    assert response.json() == []


def test_invalid_server_id():
    """Non-integer server IDs should be rejected."""
    response = client.get("/servers/abc/players")

    assert response.status_code == 422

    body = response.json()
    assert "detail" in body


def test_zero_server_id():
    """Server IDs must be >= 1."""
    response = client.get("/servers/0/players")

    assert response.status_code == 422


def test_player_response_fields():
    """Player records contain expected fields and types."""
    response = client.get("/servers/3/players")

    assert response.status_code == 200

    players = response.json()
    first = players[0]

    assert first["player_id"] == 1001
    assert first["name"] == "Alice"
    assert first["server_id"] == 3
    assert first["level"] == 50
    assert first["last_login"] == "2026-10-13"

    assert isinstance(first["player_id"], int)
    assert isinstance(first["name"], str)


def test_player_response_model_structure():
    response = client.get("/servers/3/players")

    assert response.status_code == 200

    first = response.json()[0]

    assert set(first.keys()) == {
        "player_id",
        "name",
        "server_id",
        "level",
        "last_login",
    }

    assert first["last_login"] == "2026-10-13"


def test_openapi_player_schema():
    response = client.get("/openapi.json")

    assert response.status_code == 200

    document = response.json()

    schemas = document["components"]["schemas"]

    assert "PlayerResponse" in schemas

    player_schema = schemas["PlayerResponse"]

    properties = player_schema["properties"]

    assert properties["player_id"]["type"] == "integer"
    assert properties["name"]["type"] == "string"
    assert properties["last_login"]["format"] == "date"
