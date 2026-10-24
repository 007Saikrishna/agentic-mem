import os
from dotenv import load_dotenv
load_dotenv()

import requests
import websockets
import asyncio
from .file_manager import append_rule_to_file


SERVER_URL = os.getenv("SERVER_URL")
WS_URL = os.getenv("WS_URL")


def send_memory(text: str):
    print("Sending to shared memory...")
    try:
        response = requests.post(f"{SERVER_URL}/remember", json={"text": text})
        response.raise_for_status()
        print("Success: Rule saved and broadcasted.")
    except Exception as e:
        print(f"Error connecting to server: {e}")

async def listen_for_updates():
    print(f"Connecting to live memory stream at {WS_URL}...")
    try:
        async with websockets.connect(WS_URL) as websocket:
            print("Connected. Listening for peer updates... (Press CTRL+C to quit)")
            while True:
                message = await websocket.recv()
                if message.startswith("NEW_RULE:"):
                    rule = message.split("NEW_RULE:", 1)[1]
                    append_rule_to_file(rule)
    except websockets.exceptions.ConnectionClosed:
        print("Connection to server lost.")
    except Exception as e:
        print(f"WebSocket error: {e}")

def ask_question(question: str) -> str:
    print("Searching project memory...")
    try:
        response = requests.post(f"{SERVER_URL}/ask", json={"question": question})
        response.raise_for_status()
        return response.json()["answer"]
    except Exception as e:
        return f"Error connecting to server: {e}"