import uuid
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from testcontainers.mongodb import MongoDbContainer  # type: ignore

from archive.shared.data_model import VerificationRun
from biosim_server.dependencies import MONGODB_DATABASE_NAME, MONGODB_VERIFICATION_COLLECTION_NAME

@pytest.fixture(scope="module")
def mongodb_container() -> MongoDbContainer:
    with MongoDbContainer() as container:
        container.start()
        yield container

@pytest_asyncio.fixture(scope="module")
async def mongo_test_client(mongodb_container) -> AsyncIOMotorClient:
    mongo_test_client = AsyncIOMotorClient(mongodb_container.get_connection_url())
    return mongo_test_client

@pytest_asyncio.fixture(scope="module")
async def mongo_test_database(mongo_test_client) -> AsyncIOMotorDatabase:
    test_database: AsyncIOMotorDatabase = mongo_test_client.get_database(name=MONGODB_DATABASE_NAME)
    return test_database

@pytest_asyncio.fixture(scope="module")
async def verification_collection(mongo_test_database) -> AsyncIOMotorCollection:
    test_collection: AsyncIOMotorCollection = mongo_test_database.get_collection(name=MONGODB_VERIFICATION_COLLECTION_NAME)
    return test_collection

@pytest.fixture(scope="module")
def verification_id() -> str:
    return "verification-" + str(uuid.uuid4())

@pytest.fixture(scope="module")
def verification_run_example(verification_id) -> VerificationRun:
    timestamp = str(datetime.now(UTC))
    path = "path/to/omex"
    generated_job_id = verification_id
    simulators = ["copasi", "vcell"]
    include_outputs = True
    rTol = 1e-6
    aTol = 1e-9
    selection_list = ["time", "concentration"]

    return VerificationRun(
        status=JobStatus.PENDING.value,
        job_id=generated_job_id,
        path=path,
        simulators=simulators,
        timestamp=timestamp,
        include_outputs=include_outputs,
        rTol=rTol,
        aTol=aTol,
        selection_list=selection_list,
        # expected_results=report_location,
    )

