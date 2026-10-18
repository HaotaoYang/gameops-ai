from typing import Annotated
from fastapi import FastAPI, Path
from services import get_players

app = FastAPI(
    title="GameOps AI",
    description="Game Operations AI Backend",
    version="0.1.0",
)

@app.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}

@app.get("/servers/{server_id}/players")
def list_players(
    server_id: Annotated[int, Path(ge=1)]
) -> list[dict[str, int | str]]:
    """List players for a given server."""
    return get_players(server_id)