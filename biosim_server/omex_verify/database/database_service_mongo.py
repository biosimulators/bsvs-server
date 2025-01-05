from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from pymongo.results import InsertOneResult
from typing_extensions import override

from biosim_server.omex_verify.database.database_service import DatabaseService, DocumentNotFoundError
from biosim_server.omex_verify.database.models import VerificationRun


class DatabaseServiceMongo(DatabaseService):
    db_client: AsyncIOMotorClient
    verification_run_col: AsyncIOMotorCollection

    def __init__(self, db_client: AsyncIOMotorClient, db_name: str, verification_col_name: str) -> None:
        self.db_client = db_client
        self.verification_run_col = self.db_client.get_database(db_name).get_collection(verification_col_name)

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
            raise DocumentNotFoundError("Document not found")

    @override
    async def delete_verification_run(self, job_id: str) -> None:
        result = await self.verification_run_col.delete_one({"job_id": job_id})
        if result.deleted_count == 1:
            return
        else:
            raise Exception("Delete failed")

    @override
    async def close(self) -> None:
        self.db_client.close()
