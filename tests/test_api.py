
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

def test_players_without_min_level():
    """Existing API behavior must stay unchanged."""
    response = client.get("/servers/3/players")

    assert response.status_code == 200

    players = response.json()

    assert [p["player_id"] for p in players] == [
        1001, 1002, 1004
    ]


def test_players_min_level_50():
    """The boundary level 50 must be included."""
    response = client.get(
        "/servers/3/players",
        params={"min_level": 50},
    )

    assert response.status_code == 200

    players = response.json()

    assert [p["name"] for p in players] == [
        "Alice", "David"
    ]


def test_players_min_level_60():
    """Only David meets the minimum level 60."""
    response = client.get(
        "/servers/3/players",
        params={"min_level": 60},
    )

    assert response.status_code == 200

    players = response.json()

    assert [p["name"] for p in players] == ["David"]


def test_players_min_level_61():
    """A valid filter with no matches returns an empty list."""
    response = client.get(
        "/servers/3/players",
        params={"min_level": 61},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_players_min_level_zero():
    """Zero is a valid explicit minimum level."""
    response = client.get(
        "/servers/3/players",
        params={"min_level": 0},
    )

    assert response.status_code == 200
    assert len(response.json()) == 3


def test_players_negative_min_level():
    """Negative minimum levels must be rejected."""
    response = client.get(
        "/servers/3/players",
        params={"min_level": -1},
    )

    assert response.status_code == 422


def test_players_invalid_min_level():
    """A non-integer minimum level must be rejected."""
    response = client.get(
        "/servers/3/players",
        params={"min_level": "abc"},
    )

    assert response.status_code == 422


def test_openapi_min_level_query_parameter():
    """OpenAPI must document min_level as a query parameter."""
    response = client.get("/openapi.json")

    assert response.status_code == 200

    document = response.json()

    operation = document["paths"][
        "/servers/{server_id}/players"
    ]["get"]

    parameters = operation["parameters"]

    min_level_params = [
        param
        for param in parameters
        if param["name"] == "min_level"
    ]

    assert len(min_level_params) == 1

    param = min_level_params[0]

    assert param["in"] == "query"
    assert param["required"] is False

def test_players_login_date_only():
    """Exact last login date should return Bob and David."""
    response = client.get(
        "/servers/3/players",
        params={"login_date": "2026-10-14"},
    )

    assert response.status_code == 200

    players = response.json()

    assert [p["name"] for p in players] == [
        "Bob", "David"
    ]


def test_players_login_date_other_day():
    """October 13 should return Alice."""
    response = client.get(
        "/servers/3/players",
        params={"login_date": "2026-10-13"},
    )

    assert response.status_code == 200

    assert [
        p["name"] for p in response.json()
    ] == ["Alice"]


def test_players_combined_filters():
    """Date and minimum level must both match."""
    response = client.get(
        "/servers/3/players",
        params={
            "min_level": 50,
            "login_date": "2026-10-14",
        },
    )

    assert response.status_code == 200

    assert [
        p["name"] for p in response.json()
    ] == ["David"]


def test_players_combined_filters_no_match():
    """Valid combined filters can return an empty list."""
    response = client.get(
        "/servers/3/players",
        params={
            "min_level": 61,
            "login_date": "2026-10-14",
        },
    )

    assert response.status_code == 200
    assert response.json() == []


def test_players_invalid_login_date():
    """Invalid date text must return 422."""
    response = client.get(
        "/servers/3/players",
        params={"login_date": "abc"},
    )

    assert response.status_code == 422


def test_players_nonexistent_calendar_date():
    """An impossible calendar date must be rejected."""
    response = client.get(
        "/servers/3/players",
        params={"login_date": "2026-02-30"},
    )

    assert response.status_code == 422


def test_players_date_filter_server_isolation():
    """Date filtering must not include other servers."""
    response = client.get(
        "/servers/5/players",
        params={"login_date": "2026-10-14"},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_players_combined_filter_with_zero_level():
    """Zero remains a valid explicitly provided level."""
    response = client.get(
        "/servers/3/players",
        params={
            "min_level": 0,
            "login_date": "2026-10-14",
        },
    )

    assert response.status_code == 200

    assert [
        p["name"] for p in response.json()
    ] == ["Bob", "David"]


def test_players_combined_invalid_level():
    """An invalid level must still be rejected with a date."""
    response = client.get(
        "/servers/3/players",
        params={
            "min_level": -1,
            "login_date": "2026-10-14",
        },
    )

    assert response.status_code == 422


def test_openapi_login_date_query_parameter():
    """OpenAPI must document login_date as optional query."""
    response = client.get("/openapi.json")

    assert response.status_code == 200

    document = response.json()

    operation = document["paths"][
        "/servers/{server_id}/players"
    ]["get"]

    parameters = operation["parameters"]

    matches = [
        param
        for param in parameters
        if param["name"] == "login_date"
    ]

    assert len(matches) == 1

    param = matches[0]

    assert param["in"] == "query"
    assert param["required"] is False