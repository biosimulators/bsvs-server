from typing import Annotated

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from pymongo.results import InsertOneResult
from typing_extensions import override

from archive.shared.data_model import VerificationRun
from biosim_server.database.database_service import DatabaseService
from biosim_server.dependencies import get_database, MONGODB_DATABASE_NAME, MONGODB_VERIFICATION_COLLECTION_NAME


class DatabaseServiceMongo(DatabaseService):
    db_client: AsyncIOMotorClient
    verification_run_col: AsyncIOMotorCollection

    def __init__(self, db: Annotated[AsyncIOMotorClient, get_database()]) -> None:
        self.db = db
        self.verification_run_col = self.db.get_database(MONGODB_DATABASE_NAME).get_collection(MONGODB_VERIFICATION_COLLECTION_NAME)

    @override
    async def insert_verification_run(self, verification_run: VerificationRun) -> None:
        result: InsertOneResult = await self.verification_run_col.insert_one(verification_run.model_dump())
        if result.acknowledged:
            return
        else:
            raise Exception("Insert failed")

    @override
    async def get_verification_run(self, job_id: str) -> VerificationRun:
        document = await self.verification_run_col.find_one({"job_id": job_id})
        if document is not None:
            return VerificationRun.model_validate(document)
        else:
            raise Exception("Document not found")

    @override
    async def delete_verification_run(self, job_id: str) -> None:
        result = await self.verification_run_col.delete_one({"job_id": job_id})
        if result.deleted_count == 1:
            return
        else:
            raise Exception("Delete failed")
