
from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas import PlayerResponse


def valid_player_data() -> dict:
    return {
        "player_id": 1001,
        "name": "Alice",
        "server_id": 3,
        "level": 50,
        "last_login": date(2026, 10, 13),
    }


def test_valid_player_model():
    player = PlayerResponse.model_validate(
        valid_player_data()
    )

    assert player.player_id == 1001
    assert player.name == "Alice"
    assert player.last_login == date(2026, 10, 13)


def test_reject_string_player_id():
    data = valid_player_data()
    data["player_id"] = "1001"

    with pytest.raises(ValidationError):
        PlayerResponse.model_validate(data)


def test_reject_negative_level():
    data = valid_player_data()
    data["level"] = -1

    with pytest.raises(ValidationError):
        PlayerResponse.model_validate(data)


def test_reject_empty_name():
    data = valid_player_data()
    data["name"] = ""

    with pytest.raises(ValidationError):
        PlayerResponse.model_validate(data)


def test_reject_invalid_date():
    data = valid_player_data()
    data["last_login"] = "not-a-date"

    with pytest.raises(ValidationError):
        PlayerResponse.model_validate(data)


def test_model_json_serialization():
    player = PlayerResponse.model_validate(
        valid_player_data()
    )

    json_text = player.model_dump_json()

    assert '"player_id":1001' in json_text
    assert '"last_login":"2026-10-13"' in json_text
