from typing import AsyncGenerator

import pytest_asyncio
from testcontainers.mongodb import MongoDbContainer  # type: ignore

from biosim_server.dependencies import get_file_service, set_file_service
from biosim_server.io.file_service_S3 import FileServiceS3
from biosim_server.io.file_service_local import FileServiceLocal


@pytest_asyncio.fixture(scope="session")
async def file_service_local() -> AsyncGenerator[FileServiceLocal, None]:
    file_service_local = FileServiceLocal()
    file_service_local.init()
    saved_file_service = get_file_service()
    set_file_service(file_service_local)

    yield file_service_local

    await file_service_local.close()
    set_file_service(saved_file_service)


@pytest_asyncio.fixture(scope="session")
async def file_service_s3() -> AsyncGenerator[FileServiceS3, None]:
    file_service_s3: FileServiceS3 = FileServiceS3()
    saved_file_service = get_file_service()
    set_file_service(file_service_s3)

    yield file_service_s3

    await file_service_s3.close()
    set_file_service(saved_file_service)
