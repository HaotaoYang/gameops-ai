
import json

import pytest

from data import read_players
from models import Player


def make_player(
    player_id: int = 1001
) -> dict:
    """Create a valid player record for tests."""
    return {
        "player_id": player_id,
        "name": "Alice",
        "server_id": 3,
        "level": 50,
        "last_login": "2026-10-13",
    }


def write_json(tmp_path, data):
    """Write test data and return its temporary path."""
    file_path = tmp_path / "players.json"

    file_path.write_text(
        json.dumps(data, ensure_ascii=False),
        encoding="utf-8",
    )

    return file_path


def test_read_players():
    """Read existing player data into dataclass objects."""
    players = read_players()

    assert len(players) == 5
    assert isinstance(players[0], Player)
    assert players[0].name == "Alice"


def test_read_valid_temp_file(tmp_path):
    """Read a valid independent JSON file."""
    file_path = write_json(
        tmp_path,
        [make_player()]
    )

    players = read_players(file_path)

    assert len(players) == 1
    assert players[0].player_id == 1001


def test_missing_file(tmp_path):
    """A missing file must produce a clear error."""
    file_path = tmp_path / "missing.json"

    with pytest.raises(
        ValueError,
        match="玩家数据文件不存在"
    ):
        read_players(file_path)


def test_invalid_json(tmp_path):
    """Malformed JSON must be rejected."""
    file_path = tmp_path / "invalid.json"

    file_path.write_text(
        "{broken json",
        encoding="utf-8"
    )

    with pytest.raises(
        ValueError,
        match="玩家数据 JSON 格式错误"
    ):
        read_players(file_path)


def test_root_must_be_array(tmp_path):
    """The JSON root must be a list."""
    file_path = write_json(
        tmp_path,
        make_player()
    )

    with pytest.raises(
        ValueError,
        match="玩家数据必须是 JSON 数组"
    ):
        read_players(file_path)


def test_player_must_be_object(tmp_path):
    """Every player record must be a JSON object."""
    file_path = write_json(
        tmp_path,
        ["not a player"]
    )

    with pytest.raises(
        ValueError,
        match="玩家数据不是对象"
    ):
        read_players(file_path)


def test_missing_required_field(tmp_path):
    """Required fields cannot be omitted."""
    player = make_player()
    del player["server_id"]

    file_path = write_json(
        tmp_path,
        [player]
    )

    with pytest.raises(
        ValueError,
        match="玩家缺少字段: server_id"
    ):
        read_players(file_path)


def test_invalid_field_type(tmp_path):
    """A server ID must be an integer."""
    player = make_player()
    player["server_id"] = "three"

    file_path = write_json(
        tmp_path,
        [player]
    )

    with pytest.raises(
        ValueError,
        match="玩家字段类型错误: server_id"
    ):
        read_players(file_path)


def test_invalid_login_date(tmp_path):
    """Invalid login dates must be rejected."""
    player = make_player()
    player["last_login"] = "2026-13-40"

    file_path = write_json(
        tmp_path,
        [player]
    )

    with pytest.raises(
        ValueError,
        match="玩家登录日期无效"
    ):
        read_players(file_path)


def test_empty_player_list(tmp_path):
    """An empty list is a valid JSON dataset."""
    file_path = write_json(
        tmp_path,
        []
    )

    assert read_players(file_path) == []
