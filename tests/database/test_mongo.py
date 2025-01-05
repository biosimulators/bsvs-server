import pytest
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo.results import InsertOneResult
from testcontainers.mongodb import MongoDbContainer  # type: ignore

from biosim_server.database.database_service import DatabaseService
from biosim_server.database.models import VerificationRun
from tests.fixtures.database_fixtures import verification_collection


@pytest.mark.asyncio
async def test_mongo(verification_collection: AsyncIOMotorCollection,
                     verification_run_example: VerificationRun) -> None:
    expected_verification_run = VerificationRun.model_validate(verification_run_example.model_dump())

    # insert a document into the database
    result: InsertOneResult = await verification_collection.insert_one(expected_verification_run.model_dump())
    assert result.acknowledged

    # reread the document from the database
    document = await verification_collection.find_one({"job_id": verification_run_example.job_id})
    assert document is not None

    # check that the document in the database is the same as the original document
    actual_verification_run = VerificationRun.model_validate(document)
    assert actual_verification_run == expected_verification_run

    # delete the document from the database
    del_result = await verification_collection.delete_one({"job_id": verification_run_example.job_id})
    assert del_result.deleted_count == 1


@pytest.mark.asyncio
async def test_database_service(database_service: DatabaseService, verification_run_example: VerificationRun) -> None:
    expected_verification_run = VerificationRun.model_validate(verification_run_example.model_dump())

    # insert a document into the database, read it back, make sure it matches
    await database_service.insert_verification_run(expected_verification_run)
    document: VerificationRun = await database_service.get_verification_run(verification_run_example.job_id)

    # check that the document in the database is the same as the original document
    assert document == expected_verification_run

    # delete the document from the database
    await database_service.delete_verification_run(verification_run_example.job_id)
