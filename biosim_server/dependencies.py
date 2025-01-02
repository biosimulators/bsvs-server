from motor.motor_asyncio import AsyncIOMotorClient

from biosim_server.biosim1.biosim_service import BiosimService
from biosim_server.biosim1.biosim_service_rest import BiosimServiceRest
from biosim_server.io.file_service import FileService
from biosim_server.io.file_service_S3 import FileServiceS3

MONGODB_URL = "mongodb://localhost:27017"
MONGODB_DATABASE_NAME = "mydatabase"
MONGODB_VERIFICATION_COLLECTION_NAME = "verification"
mongodb_client: AsyncIOMotorClient = AsyncIOMotorClient(MONGODB_URL)

file_service: FileService = FileServiceS3()

biosim_service: BiosimService = BiosimServiceRest()


def get_database() -> AsyncIOMotorClient:
    return mongodb_client


def get_file_service() -> FileService:
    return file_service


def get_biosim_service() -> BiosimService:
    return biosim_service
