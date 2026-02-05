from database.connection import client

db = client["exercise-2"]
collection = db["article"]

async def has_duplicate(url: str) -> bool:
    return await collection.find_one({"url": url}) is not None