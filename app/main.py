
from datetime import date
from typing import Annotated

from fastapi import FastAPI, Path

from app.schemas import PlayerResponse
from services import get_players


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
    server_id: Annotated[int, Path(ge=1)]
) -> list[PlayerResponse]:
    """Return validated player response models."""

    raw_players = get_players(server_id)

    result = []

    for player in raw_players:
        player_data = {
            **player,
            "last_login": date.fromisoformat(
                player["last_login"]
            )
        }

        validated_player = PlayerResponse.model_validate(
            player_data
        )

        result.append(validated_player)

    return result
