import json

player = {
    "player_id": 1001,
    "name": "Alice",
    "level": 50
}

print(player)

json_text = json.dumps(
    player,
    ensure_ascii = False,
    indent = 4
)

print(json_text)

restored_player = json.loads(json_text)

print(restored_player["name"])