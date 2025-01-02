from typing import AsyncGenerator

import pytest_asyncio
from testcontainers.mongodb import MongoDbContainer  # type: ignore

from biosim_server.dependencies import get_file_service, set_file_service
from biosim_server.io.file_service_S3 import FileServiceS3
from biosim_server.io.local_file_service import LocalFileService


@pytest_asyncio.fixture(scope="session")
async def file_service_local() -> AsyncGenerator[LocalFileService, None]:
    file_service_local: LocalFileService = LocalFileService()
    saved_file_service = get_file_service()

    yield file_service_local

    file_service_local.cleanup()
    set_file_service(saved_file_service)


@pytest_asyncio.fixture(scope="session")
async def file_service_s3() -> AsyncGenerator[FileServiceS3, None]:
    file_service_s3: FileServiceS3 = FileServiceS3()
    saved_file_service = get_file_service()

    yield file_service_s3

    set_file_service(saved_file_service)
