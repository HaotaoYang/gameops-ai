from datetime import date

from fastapi.testclient import TestClient

from app.main import app
from app.schemas import PlayerResponse
from services import get_players


client = TestClient(app)


def test_week2_health_contract():
    """Health endpoint must keep its original response."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["content-type"] == "application/json"


def test_week2_unfiltered_player_contract():
    """The original player query must remain compatible."""
    response = client.get("/servers/3/players")

    assert response.status_code == 200

    players = response.json()

    assert [p["player_id"] for p in players] == [
        1001, 1002, 1004
    ]

    assert set(players[0]) == {
        "player_id",
        "name",
        "server_id",
        "level",
        "last_login",
    }


def test_week2_all_filters_and_pagination():
    """Filter first, then apply pagination."""
    response = client.get(
        "/servers/3/players",
        params={
            "min_level": 40,
            "login_date": "2026-10-14",
            "limit": 1,
            "offset": 1,
        },
    )

    assert response.status_code == 200

    players = response.json()

    assert len(players) == 1
    assert players[0]["name"] == "David"


def test_week2_empty_result_contract():
    """A valid query with no matches returns 200 and []."""
    response = client.get(
        "/servers/3/players",
        params={
            "min_level": 99,
            "login_date": "2026-10-14",
            "limit": 10,
        },
    )

    assert response.status_code == 200
    assert response.json() == []


def test_week2_query_validation_contract():
    """Invalid inputs must be rejected before business processing."""
    invalid_queries = [
        "/servers/0/players",
        "/servers/abc/players",
        "/servers/3/players?min_level=-1",
        "/servers/3/players?login_date=invalid",
        "/servers/3/players?limit=0",
        "/servers/3/players?limit=101",
        "/servers/3/players?offset=-1",
    ]

    for url in invalid_queries:
        response = client.get(url)

        assert response.status_code == 422, url
        assert "detail" in response.json(), url


def test_week2_pydantic_schema_contract():
    """The Pydantic model must validate strict field types."""
    valid_player = {
        "player_id": 1001,
        "name": "Alice",
        "server_id": 3,
        "level": 50,
        "last_login": date(2026, 10, 13),
    }

    player = PlayerResponse.model_validate(
        valid_player
    )

    assert player.level == 50
    assert player.last_login == date(2026, 10, 13)

    serialized = player.model_dump(
        mode="json"
    )

    assert serialized["last_login"] == "2026-10-13"


def test_week2_response_does_not_mutate_business_data():
    """Making an API request must not mutate source player data."""
    before = get_players(3)

    response = client.get(
        "/servers/3/players",
        params={
            "min_level": 50,
            "login_date": "2026-10-14",
        },
    )

    assert response.status_code == 200

    after = get_players(3)

    assert after == before
    assert isinstance(after[0]["last_login"], str)


def test_week2_openapi_contract():
    """OpenAPI must describe both routes and their parameters."""
    response = client.get("/openapi.json")

    assert response.status_code == 200

    document = response.json()

    assert "/health" in document["paths"]

    player_route = document["paths"][
        "/servers/{server_id}/players"
    ]["get"]

    parameter_names = {
        item["name"]
        for item in player_route["parameters"]
    }

    assert parameter_names == {
        "server_id",
        "min_level",
        "login_date",
        "limit",
        "offset",
    }

    assert "PlayerResponse" in document[
        "components"
    ]["schemas"]