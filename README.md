# Agentic Shared Memory

A lightweight, collaborative tool that provides a centralized, agentic shared memory system. It allows developers to extract, store, synchronize, and query architectural rules and project constraints in real-time across a local network using MongoDB Atlas, FastAPI, and a Typer CLI.

The system uses Google's `gemini-3.8-flash` to formalize raw developer input into clean constraints, embeds them using `gemini-embedding-2` (768 dimensions), and utilizes MongoDB `$vectorSearch` for Retrieval-Augmented Generation (RAG).

## Features
- **Real-Time Peer Sync:** WebSocket connections instantly broadcast new rules to all connected devices, automatically updating a local `.agent_rules.md` file.
- **Semantic RAG Search:** Ask questions in natural language through the CLI, and the backend will fetch and synthesize mathematically relevant rules from the vector database.
- **Centralized Brain:** MongoDB Atlas Change Streams act as the single source of truth for both human developers and future local AI agents.

---

## Prerequisites
- Python 3.9+
- A MongoDB Atlas Cluster (M0 Free Tier works)
- Google Gemini API Key

## 1. Local Environment Setup
Fork the repo

Clone the repository

Set up a virtual environment using PowerShell:

```powershell
# Create the virtual environment
python -m venv venv

# Activate the virtual environment in PowerShell
.\venv\Scripts\Activate.ps1

# Install required packages
pip install -r requirements.txt
```

## 2. Environment Variables

Create a .env file and add the following variables:

```env
SERVER_URL="http://127.0.0.1:8000"
WS_URL="ws://127.0.0.1:8000/ws"
RULES_FILE=".agent_rules.md"
MONGODB_URI="mongodb+srv://<username>:<password>@<cluster-url>.mongodb.net/"
GEMINI_API_KEY="your_google_api_key_here"
```

## 3. MongoDB Atlas Configuration
Choose language as Python and Driver as pymongo (asynchronous) before obtaining the 
connection string.
You must create a Vector Search index in your Atlas cluster for the RAG `/ask` feature to work.
1. Navigate to **Atlas Search** > **Create Search Index** > **Bring your own embeddings** >> **JSON Editor**.
2. Target the `agent_db.agent_memories` collection.
3. Name the index `vector_index` and apply this schema:

```json
{
  "fields": [
    {
      "numDimensions": 768,
      "path": "embedding",
      "similarity": "cosine",
      "type": "vector"
    }
  ]
}
```

## 4. Testing the Pipeline

To test the system locally, you will need three separate PowerShell windows (ensure your `venv` is activated in all of them).

**Terminal 1: Start the Server (Host Only)**
```powershell
uvicorn server.main:app --reload
```

**Terminal 2: Start the Sync Listener (All Peers)**
```powershell
python -m cli.main sync
```

**Terminal 3: Execute Commands**
First, add a new rule to the database. The AI will extract it, embed it, and broadcast it (watch Terminal 2 for the live update):
```powershell
python -m cli.main remember "All API endpoints must be documented using strict OpenAPI standards."
```

Next, test the semantic RAG search by asking a question related to the rule you just saved:
```powershell
python -m cli.main ask "How should we format our endpoint documentation?"
```

You should see a synthesized conversational answer directly in your terminal, proving the embedding and retrieval pipeline is fully operational!