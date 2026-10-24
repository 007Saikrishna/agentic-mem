from pymongo import AsyncMongoClient
import os

# Connect to the MongoDB cluster
uri = os.getenv("MONGODB_URI")
client = AsyncMongoClient(uri)

# Define the database and collection
db = client.agent_db
collection = db.agent_memories

async def init_db():
    # Create the Time-To-Live index to auto-delete expired rules
    await collection.create_index("expiresAt", expireAfterSeconds=0)

async def insert_memory(memory_doc: dict):
    return await collection.insert_one(memory_doc)

async def search_memories(embedding: list):
    # numCandidates and limit control the speed and accuracy of MongoDB ANN algorithm (Approximate Nearest Neighbour)
    pipeline = [
        {
            "$vectorSearch": {
                "index": "vector_index",
                "path": "embedding",
                "queryVector": embedding,
                # determines potential matches to evaluate and hold in memory while navigating vector space
                # higher number consumes more memory and compute time
                "numCandidates": 50,    
                # final output size
                # sorts and injects exactly 3 rules for gemini to synthesize answer
                "limit": 5
            },
        },
        {
            "$project": {
                "_id": 0,
                "content": 1,
                "score": {"$meta": "vectorSearchScore"}
            }
        }
    ]
    cursor = await collection.aggregate(pipeline)
    return await cursor.to_list(length=5)

async def delete_memory(content: str) -> bool:
    # Deletes the exact rule string returned by the conflict detector
    result = await collection.delete_one({"content": content})
    return result.deleted_count > 0