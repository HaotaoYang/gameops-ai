
from datetime import date

from data import read_players
from models import Player


def get_player_models(server_id: int) -> list[Player]:
    """Return Player objects belonging to a server."""
    result: list[Player] = []

    for player in read_players():
        if player.server_id == server_id:
            result.append(player)

    return result


def get_players(
    server_id: int
) -> list[dict[str, int | str]]:
    """Return player dictionaries for a server."""
    result: list[dict[str, int | str]] = []

    for player in get_player_models(server_id):
        result.append(player.to_dict())

    return result


def count_players(server_id: int) -> int:
    """Count players belonging to a server."""
    return len(get_player_models(server_id))


def get_high_level_players(
    server_id: int,
    min_level: int
) -> list[dict[str, int | str]]:
    """Return players at or above the specified level."""
    result: list[dict[str, int | str]] = []

    for player in get_player_models(server_id):
        if player.level >= min_level:
            result.append(player.to_dict())

    return result


def get_active_players(
    server_id: int,
    target_date: str
) -> list[dict[str, int | str]]:
    """Return players whose last login is the target date."""

    try:
        query_date = date.fromisoformat(target_date)
    except ValueError as exc:
        raise ValueError(
            f"查询日期格式无效: {target_date}"
        ) from exc

    result: list[dict[str, int | str]] = []

    for player in get_player_models(server_id):
        login_date = date.fromisoformat(
            player.last_login
        )

        if login_date == query_date:
            result.append(player.to_dict())

    return result


def count_active_players(
    server_id: int,
    target_date: str
) -> int:
    """Count players whose last login is the target date."""
    return len(get_active_players(server_id, target_date))
