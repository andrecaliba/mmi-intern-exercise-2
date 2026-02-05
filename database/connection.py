import os
from pymongo import AsyncMongoClient

# Connect to MongoDB
mongo_host = os.getenv('MONGO_HOST', 'localhost')
mongo_port = int(os.getenv('MONGO_PORT', 27017))

mongo_uri = f"mongodb://{mongo_host}:{mongo_port}"
client = AsyncMongoClient(mongo_uri)