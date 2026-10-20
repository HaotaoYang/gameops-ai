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
        Query(
            ge=0,
            description="Minimum player level",
        ),
    ] = None,
    login_date: Annotated[
        date | None,
        Query(
            description="Exact last login date",
        ),
    ] = None,
    limit: Annotated[
        int | None,
        Query(
            ge=1,
            le=100,
            description="Maximum number of players",
        ),
    ] = None,
    offset: Annotated[
        int,
        Query(
            ge=0,
            description="Number of players to skip",
        ),
    ] = 0,
) -> list[PlayerResponse]:
    """Filter players and apply optional pagination."""

    # Step 1: apply existing filters
    if min_level is None and login_date is None:
        raw_players = get_players(server_id)

    elif login_date is None:
        raw_players = get_high_level_players(
            server_id,
            min_level,
        )

    else:
        raw_players = get_active_players(
            server_id,
            login_date.isoformat(),
        )

        if min_level is not None:
            raw_players = [
                player
                for player in raw_players
                if player["level"] >= min_level
            ]

    # Step 2: paginate AFTER filtering
    if limit is None:
        paged_players = raw_players[offset:]
    else:
        paged_players = raw_players[
            offset:offset + limit
        ]

    # Step 3: keep strict Pydantic validation
    result: list[PlayerResponse] = []

    for player in paged_players:
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