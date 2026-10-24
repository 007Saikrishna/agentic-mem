import os
import json
import requests
import typer
import asyncio
import websockets
from dotenv import load_dotenv

load_dotenv()

app = typer.Typer()
CONFIG_PATH = os.path.expanduser("~/.agentic-mem/config.json")

# Pull URLs dynamically from .env, falling back to localhost if missing
SERVER_URL = os.getenv("SERVER_URL", "http://127.0.0.1:8000")
WS_URL = os.getenv("WS_URL", "ws://127.0.0.1:8000/ws")

def save_token(token: str):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump({"access_token": token}, f)

def get_token():
    if not os.path.exists(CONFIG_PATH):
        return None
    with open(CONFIG_PATH, "r") as f:
        return json.load(f).get("access_token")

@app.command()
def signup(email: str, password: str, project_id: str = "default-project"):
    response = requests.post(f"{SERVER_URL}/signup", json={"email": email, "password": password, "project_id": project_id})
    if response.status_code == 200:
        token = response.json()["access_token"]
        save_token(token)
        typer.echo("[+] Account created successfully and logged in!")
    else:
        typer.echo(f"[-] Signup failed: {response.text}")

@app.command()
def login(email: str, password: str):
    response = requests.post(f"{SERVER_URL}/login", json={"email": email, "password": password})
    if response.status_code == 200:
        token = response.json()["access_token"]
        save_token(token)
        typer.echo("[+] Logged in successfully! Token saved locally.")
    else:
        typer.echo(f"[-] Login failed: {response.text}")

@app.command()
def logout():
    if os.path.exists(CONFIG_PATH):
        os.remove(CONFIG_PATH)
        typer.echo("[+] Logged out successfully! Local token cleared.")
    else:
        typer.echo("[-] You are not currently logged in.")

@app.command()
def remember(text: str):
    token = get_token()
    if not token:
        typer.echo("[-] Unauthorized. Please log in first: python -m cli.main login <email> <password>")
        return
        
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(f"{SERVER_URL}/remember", json={"text": text}, headers=headers)
    
    if response.status_code == 200:
        typer.echo(response.json().get("status"))
    else:
        typer.echo(f"[-] Failed to save rule: {response.text}")

@app.command()
def ask(question: str):
    token = get_token()
    if not token:
        typer.echo("[-] Unauthorized. Please log in first.")
        return
        
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(f"{SERVER_URL}/ask", json={"question": question}, headers=headers)
    
    if response.status_code == 200:
        typer.echo(f"\nAI Answer:\n{response.json().get('answer')}")
    else:
        typer.echo(f"[-] Request failed: {response.text}")

async def run_sync():
    typer.echo(f"Connecting to live memory stream at {WS_URL}...")
    try:
        async with websockets.connect(WS_URL) as websocket:
            typer.echo("Connected. Listening for peer updates... (Press CTRL+C to quit)")
            while True:
                message = await websocket.recv()
                if message.startswith("NEW_RULE:"):
                    rule_text = message.split("NEW_RULE:")[1]
                    with open(".agent_rules.md", "a") as f:
                        f.write(f"\n- {rule_text}")
                    typer.echo(f"[+] Rule synced to .agent_rules.md: {rule_text}")
    except Exception as e:
        typer.echo(f"Sync disconnected: {e}")

@app.command()
def sync():
    asyncio.run(run_sync())

if __name__ == "__main__":
    app()