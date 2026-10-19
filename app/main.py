
from datetime import date
from typing import Annotated

from fastapi import FastAPI, Path, Query

from app.schemas import PlayerResponse
from services import get_high_level_players, get_players


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
) -> list[PlayerResponse]:
    """Return players with an optional minimum level."""

    if min_level is None:
        raw_players = get_players(server_id)
    else:
        raw_players = get_high_level_players(
            server_id,
            min_level,
        )

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
