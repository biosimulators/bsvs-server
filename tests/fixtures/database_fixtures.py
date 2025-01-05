import uuid
from datetime import UTC, datetime
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from testcontainers.mongodb import MongoDbContainer  # type: ignore

from biosim_server.database.database_service import DatabaseService
from biosim_server.database.database_service_mongo import DatabaseServiceMongo
from biosim_server.database.models import JobStatus, VerificationRun
from biosim_server.dependencies import MONGODB_DATABASE_NAME, MONGODB_VERIFICATION_COLLECTION_NAME, \
    get_database_service, set_database_service


@pytest.fixture(scope="session")
def mongodb_container() -> MongoDbContainer:
    with MongoDbContainer() as container:
        container.start()
        yield container

@pytest_asyncio.fixture(scope="function")
async def mongo_test_client(mongodb_container: MongoDbContainer) -> AsyncGenerator[AsyncIOMotorClient,None]:
    mongo_test_client = AsyncIOMotorClient(mongodb_container.get_connection_url())
    yield mongo_test_client
    mongo_test_client.close()

@pytest_asyncio.fixture(scope="function")
async def database_service(mongo_test_client: AsyncIOMotorClient) -> AsyncGenerator[DatabaseService,None]:
    db_service = DatabaseServiceMongo(
        db_client=mongo_test_client,
        db_name=MONGODB_DATABASE_NAME,
        verification_col_name=MONGODB_VERIFICATION_COLLECTION_NAME)
    saved_db_service = get_database_service()
    set_database_service(db_service)

    yield db_service

    await db_service.close()
    set_database_service(saved_db_service)


@pytest_asyncio.fixture(scope="function")
async def mongo_test_database(mongo_test_client: AsyncIOMotorClient) -> AsyncIOMotorDatabase:
    test_database: AsyncIOMotorDatabase = mongo_test_client.get_database(name=MONGODB_DATABASE_NAME)
    return test_database

@pytest_asyncio.fixture(scope="function")
async def verification_collection(mongo_test_database: AsyncIOMotorDatabase) -> AsyncIOMotorCollection:
    test_collection: AsyncIOMotorCollection = mongo_test_database.get_collection(name=MONGODB_VERIFICATION_COLLECTION_NAME)
    return test_collection

@pytest.fixture(scope="module")
def verification_id() -> str:
    return "verification-" + str(uuid.uuid4())

@pytest.fixture(scope="module")
def verification_run_example(verification_id: str) -> VerificationRun:
    timestamp = str(datetime.now(UTC))
    path = "path/to/omex"
    generated_job_id = verification_id
    simulators = ["copasi", "vcell"]
    include_outputs = True
    rTol = 1e-6
    aTol = 1e-9
    observables = ["time", "concentration"]

    return VerificationRun(
        status=str(JobStatus.PENDING.value),
        job_id=generated_job_id,
        omex_s3_path=path,
        requested_simulators=simulators,
        comparison_id="compare_id",
        timestamp=timestamp,
        include_outputs=include_outputs,
        rTol=rTol,
        aTol=aTol,
        observables=observables,
    )

