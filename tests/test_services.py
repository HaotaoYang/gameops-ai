
import pytest

from services import (
    count_active_players,
    count_players,
    get_active_players,
    get_high_level_players,
    get_players,
)

from players import (
    get_players as old_get_players,
    read_players as old_read_players,
)


def test_count_players():
    """Count players on existing and missing servers."""
    assert count_players(3) == 3
    assert count_players(5) == 2
    assert count_players(999) == 0


def test_get_players_server_3():
    """Return the correct players for server 3."""
    players = get_players(3)

    assert len(players) == 3

    player_ids = [
        player["player_id"]
        for player in players
    ]

    assert player_ids == [1001, 1002, 1004]


def test_get_players_server_5():
    """Return the correct players for server 5."""
    players = get_players(5)

    assert len(players) == 2
    assert [p["name"] for p in players] == [
        "Charlie",
        "Eva",
    ]


def test_get_players_missing_server():
    """A missing server should return an empty list."""
    assert get_players(999) == []


def test_high_level_players():
    """Filter players by server and minimum level."""
    players = get_high_level_players(3, 50)

    assert [p["name"] for p in players] == [
        "Alice",
        "David",
    ]


def test_high_level_players_boundary():
    """Level 50 itself must be included."""
    players = get_high_level_players(3, 50)

    assert any(
        player["name"] == "Alice"
        and player["level"] == 50
        for player in players
    )


def test_active_players():
    """Filter players by their last login date."""
    players = get_active_players(
        3,
        "2026-10-14"
    )

    assert [p["name"] for p in players] == [
        "Bob",
        "David",
    ]


def test_active_player_counts():
    """Verify all three Day 4 date scenarios."""
    assert count_active_players(3, "2026-10-14") == 2
    assert count_active_players(5, "2026-10-14") == 0
    assert count_active_players(3, "2026-10-13") == 1


def test_invalid_query_date():
    """Invalid date input must produce ValueError."""
    with pytest.raises(
        ValueError,
        match="查询日期格式无效"
    ):
        get_active_players(3, "2026-13-40")


def test_returned_player_is_independent():
    """Changing a returned dict must not change data."""
    players = get_players(3)

    players[0]["level"] = 999

    fresh_players = get_players(3)

    assert fresh_players[0]["level"] == 50


def test_old_players_api():
    """Day 3 and Day 4 compatibility must be preserved."""
    players = old_get_players(3)

    assert len(players) == 3
    assert isinstance(players[0], dict)

    old_data = old_read_players()

    assert len(old_data) == 5
    assert isinstance(old_data[0], dict)
