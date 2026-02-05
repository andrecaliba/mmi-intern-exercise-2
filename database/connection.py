import os
from pymongo import AsyncMongoClient
from pymongo.database import Database
from typing import Optional

class DatabaseManager:
    client: Optional[AsyncMongoClient] = None
    db: Optional[Database] = None

    @classmethod
    async def connect(cls):
        mongo_uri = os.getenv('MONGO_URL', 'mongodb://mongodb:27017')
        cls.client = AsyncMongoClient(mongo_uri)
        cls.db = cls.client['exercise-2']
        print(f"uri: {mongo_uri}")
        await cls.create_indexes()

    @classmethod
    async def disconnect(cls):
        if cls.client:
            await cls.client.close()

    @classmethod
    async def create_indexes(cls):
        await cls.db['articles'].create_index("url", unique=True)
    
    @classmethod
    def get_database(cls) -> Database:
        if cls.db is None:
            raise Exception("Database not connected")
        return cls.db
    
async def get_db() -> Database:
    return DatabaseManager.get_database()
    
