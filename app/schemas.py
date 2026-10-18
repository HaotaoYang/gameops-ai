
from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class PlayerResponse(BaseModel):
    """Public HTTP response model for a game player."""

    model_config = ConfigDict(strict=True)

    player_id: int = Field(
        gt=0,
        description="Unique player ID",
    )

    name: str = Field(
        min_length=1,
        description="Player name",
    )

    server_id: int = Field(
        ge=1,
        description="Game server ID",
    )

    level: int = Field(
        ge=0,
        description="Player level",
    )

    last_login: date = Field(
        description="Player's last login date",
    )
