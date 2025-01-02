from motor.motor_asyncio import AsyncIOMotorClient

MONGODB_URL = "mongodb://localhost:27017"
MONGODB_DATABASE_NAME = "mydatabase"
MONGODB_VERIFICATION_COLLECTION_NAME = "verification"
mongodb_client: AsyncIOMotorClient = AsyncIOMotorClient(MONGODB_URL)

def get_database() -> AsyncIOMotorClient:
    return mongodb_client
