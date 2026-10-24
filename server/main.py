from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, WebSocket
from pydantic import BaseModel
from contextlib import asynccontextmanager
from . import database, llm
import asyncio

connected_clients = set()

async def watch_changes():
    # Listen to the MongoDB Change Stream and broadcast new rules to local IDE files
    # Note the added 'await' below:
    async with await database.collection.watch() as stream:
        async for change in stream:
            if change["operationType"] == "insert":
                rule_text = change["fullDocument"]["content"]
                for client in connected_clients:
                    await client.send_text(f"NEW_RULE:{rule_text}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.init_db()
    asyncio.create_task(watch_changes())
    yield

app = FastAPI(lifespan=lifespan)

class PromptRequest(BaseModel):
    text: str

@app.post("/remember")
async def remember_rule(request: PromptRequest):
    rule_data = await llm.extract_rule(request.text)
    if rule_data:
        rule_data["embedding"] = await llm.generate_embedding(rule_data["content"])
        await database.insert_memory(rule_data)
        return {"status": "Rule saved to shared memory"}
    return {"status": "No rule detected"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except:
        connected_clients.remove(websocket)
        

class AskRequest(BaseModel):
    question: str

@app.post("/ask")
async def ask_memory(request: AskRequest):
    query_vector = await llm.generate_embedding(request.question)
    results = await database.search_memories(query_vector)
    
    if not results:
        return {"answer": "No relevant project rules found in memory."}
        
    context_rules = [doc["content"] for doc in results]
    
    final_answer = await llm.synthesize_answer(request.question, context_rules)
    return {"answer": final_answer}