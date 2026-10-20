from datetime import date
from typing import Annotated

from fastapi import FastAPI, Path, Query

from app.schemas import PlayerResponse
from services import (
    get_active_players,
    get_high_level_players,
    get_players,
)


app = FastAPI(
    title="GameOps AI",
    description="Game Operations AI Backend",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    """Simple application health check."""
    return {"status": "ok"}


@app.get(
    "/servers/{server_id}/players",
    response_model=list[PlayerResponse],
)
def list_players(
    server_id: Annotated[int, Path(ge=1)],
    min_level: Annotated[
        int | None,
        Query(ge=0, description="Minimum player level"),
    ] = None,
    login_date: Annotated[
        date | None,
        Query(description="Exact last login date"),
    ] = None,
) -> list[PlayerResponse]:
    """Query players by server, minimum level, and last login date."""

    # Case 1: no filters
    if min_level is None and login_date is None:
        raw_players = get_players(server_id)

    # Case 2: minimum level only
    elif login_date is None:
        raw_players = get_high_level_players(
            server_id,
            min_level,
        )

    # Case 3 and 4: login date is provided
    else:
        raw_players = get_active_players(
            server_id,
            login_date.isoformat(),
        )

        # Case 4: both date and level filters
        if min_level is not None:
            raw_players = [
                player
                for player in raw_players
                if player["level"] >= min_level
            ]

    # Keep Day 10's strict Pydantic response validation
    result: list[PlayerResponse] = []

    for player in raw_players:
        player_data = {
            **player,
            "last_login": date.fromisoformat(
                player["last_login"]
            ),
        }

        validated_player = PlayerResponse.model_validate(
            player_data
        )

        result.append(validated_player)

    return result