from fastapi import FastAPI

app = FastAPI(
    title="GameOps AI",
    description="Game Operations AI Backend",
    version="0.1.0",
)

@app.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}