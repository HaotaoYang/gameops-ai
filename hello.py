def greet(name: str) -> str:
    """Return a welcome message."""
    return f"Hello, {name}! Welcome to AI Development."

def main() -> None:
    name = "Erlang Developer"
    message = greet(name)
    print(message)

if __name__ == "__main__":
    main()