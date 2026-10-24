import typer
import asyncio
from . import connection

app = typer.Typer(help="Agentic Shared Memory CLI")

@app.command()
def remember(text: str):
    """Extract and save a rule to the remote agentic memory."""
    connection.send_memory(text)

@app.command()
def sync():
    """Listen for live updates from peers and sync to local files."""
    try:
        asyncio.run(connection.listen_for_updates())
    except KeyboardInterrupt:
        print("\nSync stopped by user.")

@app.command()
def ask(question: str):
    """Query the agentic memory for project rules."""
    answer = connection.ask_question(question)
    print(f"\n{answer}\n")

if __name__ == "__main__":
    app()