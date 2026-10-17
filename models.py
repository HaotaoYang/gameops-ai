from dataclasses import dataclass, asdict

@dataclass
class Player:
    player_id: int
    name: str
    server_id: int
    level: int
    last_login: str

    def to_dict(self) -> dict[str, int | str]:
        """Return a dictionary representation of the player."""
        return asdict(self)