from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, WebSocket, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from contextlib import asynccontextmanager
from . import database, llm, auth
import asyncio

connected_clients = set()
security = HTTPBearer()

async def watch_changes():
    # Listen to the MongoDB Change Stream and broadcast new rules to local IDE files
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

# --- AUTHENTICATION MODELS ---
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    project_id: str = "default-project"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

# --- AUTHENTICATION DEPENDENCY ---
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = auth.verify_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload  # Contains {"sub": email, "project_id": ...}


# --- AUTH ENDPOINTS ---
@app.post("/signup", response_model=Token)
async def signup(user: UserCreate):
    # Check if user already exists in MongoDB 'users' collection
    existing_user = await database.db.users.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_pw = auth.hash_password(user.password)
    user_doc = {
        "email": user.email,
        "hashed_password": hashed_pw,
        "project_id": user.project_id
    }
    await database.db.users.insert_one(user_doc)
    
    token = auth.create_access_token({"sub": user.email, "project_id": user.project_id})
    return {"access_token": token, "token_type": "bearer"}

@app.post("/login", response_model=Token)
async def login(user: UserLogin):
    db_user = await database.db.users.find_one({"email": user.email})
    if not db_user or not auth.verify_password(user.password, db_user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    token = auth.create_access_token({"sub": db_user["email"], "project_id": db_user["project_id"]})
    return {"access_token": token, "token_type": "bearer"}


# --- CORE MEMORY ENDPOINTS ---
class PromptRequest(BaseModel):
    text: str

@app.post("/remember")
async def remember_rule(request: PromptRequest, current_user: dict = Depends(get_current_user)):
    # You can now use current_user["project_id"] to isolate memories per team/project!
    rule_data = await llm.extract_rule(request.text)
    if rule_data:
        rule_data["embedding"] = await llm.generate_embedding(rule_data["content"])
        rule_data["project_id"] = current_user.get("project_id", "default-project")
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
async def ask_memory(request: AskRequest, current_user: dict = Depends(get_current_user)):
    query_vector = await llm.generate_embedding(request.question)
    results = await database.search_memories(query_vector)
    
    if not results:
        return {"answer": "No relevant project rules found in memory."}
        
    context_rules = [doc["content"] for doc in results]
    
    final_answer = await llm.synthesize_answer(request.question, context_rules)
    return {"answer": final_answer}