import logging
from functools import lru_cache

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from pymongo.results import InsertOneResult
from typing_extensions import override

from biosim_server.common.database.data_models import OmexFile
from biosim_server.common.database.database_service import DatabaseService
from biosim_server.config import get_settings

logger = logging.getLogger(__name__)

class DatabaseServiceMongo(DatabaseService):
    _db_client: AsyncIOMotorClient
    _omex_file_col: AsyncIOMotorCollection

    def __init__(self, db_client: AsyncIOMotorClient) -> None:
        self._db_client = db_client
        self._omex_file_col = self._db_client.get_database(get_settings().mongo_db_name).get_collection(
            get_settings().mongo_collection_omex_files)

    @override
    async def insert_omex_file(self, omex_file: OmexFile) -> None:
        logger.info(f"Inserting OMEX file with hash {omex_file.file_hash_md5}")
        result: InsertOneResult = await self._omex_file_col.insert_one(omex_file.model_dump())
        if result.acknowledged:
            return
        else:
            raise Exception("Insert failed")

    # @lru_cache
    @override
    async def get_omex_file(self, file_hash_md5: str) -> OmexFile | None:
        logger.info(f"Getting OMEX file with hash {file_hash_md5}")
        document = await self._omex_file_col.find_one({"file_hash_md5": file_hash_md5})
        if document is not None:
            return OmexFile.model_validate(document)
        else:
            return None

    @override
    async def delete_omex_file(self, file_hash_md5: str) -> None:
        logger.info(f"Deleting OMEX file with hash {file_hash_md5}")
        result = await self._omex_file_col.delete_one({"file_hash_md5": file_hash_md5})
        if result.deleted_count == 1:
            return
        else:
            raise Exception("Delete failed")

    @override
    async def list_omex_files(self) -> list[OmexFile]:
        logger.info(f"listing OMEX files")
        return [OmexFile.model_validate(document) async for document in self._omex_file_col.find()]

    @override
    async def close(self) -> None:
        self._db_client.close()
