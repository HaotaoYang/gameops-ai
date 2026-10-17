
from pathlib import Path
from tempfile import TemporaryDirectory

from data import read_players as read_player_models
from models import Player
from players import (
    count_active_players,
    count_players,
    get_active_players,
    get_high_level_players,
    get_players,
    read_players,
)


def run_checks() -> None:
    # 1. Verify the new dataclass-based data layer.
    models = read_player_models()

    assert len(models) == 5
    assert isinstance(models[0], Player)
    assert models[0].name == "Alice"

    # 2. Verify Day 4's read_players() return type.
    old_players = read_players()

    assert len(old_players) == 5
    assert isinstance(old_players[0], dict)

    # 3. Verify server queries.
    assert count_players(3) == 3
    assert count_players(5) == 2
    assert count_players(999) == 0

    assert [
        p["player_id"] for p in get_players(3)
    ] == [1001, 1002, 1004]

    # 4. Verify level-based queries.
    assert [
        p["name"] for p in get_high_level_players(3, 50)
    ] == ["Alice", "David"]

    # 5. Verify date-based queries.
    assert count_active_players(3, "2026-10-14") == 2
    assert count_active_players(5, "2026-10-14") == 0
    assert count_active_players(3, "2026-10-13") == 1

    assert [
        p["name"] for p in get_active_players(
            3, "2026-10-14"
        )
    ] == ["Bob", "David"]

    # 6. Verify returned dictionaries are independent.
    result = get_players(3)
    result[0]["level"] = 999

    assert get_players(3)[0]["level"] == 50

    # 7. Verify invalid dates.
    try:
        get_active_players(3, "2026-13-40")
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid date must fail")

    # 8. Verify missing JSON files.
    with TemporaryDirectory() as tmp_dir:
        missing = Path(tmp_dir) / "missing.json"

        try:
            read_players(missing)
        except ValueError:
            pass
        else:
            raise AssertionError("Missing JSON must fail")

        # 9. Verify invalid JSON syntax.
        invalid = Path(tmp_dir) / "invalid.json"
        invalid.write_text("{broken json", encoding="utf-8")

        try:
            read_players(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid JSON must fail")

    print("Day 5: all checks passed!")


if __name__ == "__main__":
    run_checks()
