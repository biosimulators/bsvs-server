import uuid
from datetime import datetime, UTC

import pytest
from pymongo.results import InsertOneResult
from testcontainers.mongodb import MongoDbContainer  # type: ignore

from archive.shared.data_model import VerificationRun, JobStatus
from tests.fixtures.database_fixtures import verification_collection


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

@pytest.mark.asyncio
async def test_database_write(verification_collection, verification_run_example):
    expected_verification_run = verification_run_example

    # insert a document into the database
    result: InsertOneResult = await verification_collection.insert_one(expected_verification_run.model_dump()) # type: ignore
    assert result.acknowledged

    # reread the document from the database
    document = await verification_collection.find_one({"job_id": verification_run_example.job_id})
    assert document is not None

    # check that the document in the database is the same as the original document
    actual_verification_run = VerificationRun.model_validate(document)
    assert actual_verification_run == expected_verification_run

