
"""Compatibility layer for Day 3 and Day 4 code."""

from data import read_players as read_player_models
from main import main
from services import (
    count_active_players,
    count_players,
    get_active_players,
    get_high_level_players,
    get_players,
)


def read_players(file_path=None):
    """Return player dictionaries, preserving the Day 4 API."""
    if file_path is None:
        models = read_player_models()
    else:
        models = read_player_models(file_path)

    return [player.to_dict() for player in models]


if __name__ == "__main__":
    main()
