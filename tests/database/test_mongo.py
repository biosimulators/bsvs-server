import pytest
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo.results import InsertOneResult
from testcontainers.mongodb import MongoDbContainer  # type: ignore

from biosim_server.verify.workflows.omex_verify_workflow import OmexVerifyWorkflowOutput
from tests.fixtures.database_fixtures import mongo_test_collection


@pytest.mark.asyncio
async def test_mongo(mongo_test_collection: AsyncIOMotorCollection,
                     omex_verify_workflow_output: OmexVerifyWorkflowOutput) -> None:

     # insert a document into the database
    result: InsertOneResult = await mongo_test_collection.insert_one(omex_verify_workflow_output.model_dump())
    assert result.acknowledged

    # reread the document from the database
    document = await mongo_test_collection.find_one({"workflow_run_id": omex_verify_workflow_output.workflow_run_id})
    assert document is not None

    # check that the document in the database is the same as the original document
    expected_verify_workflow_output = OmexVerifyWorkflowOutput(workflow_id=omex_verify_workflow_output.workflow_id,
                                                               workflow_input=omex_verify_workflow_output.workflow_input,
                                                               workflow_status=omex_verify_workflow_output.workflow_status,
                                                               timestamp=omex_verify_workflow_output.timestamp,
                                                               workflow_run_id=omex_verify_workflow_output.workflow_run_id,
                                                               workflow_results=omex_verify_workflow_output.workflow_results)
    assert expected_verify_workflow_output == omex_verify_workflow_output

    # delete the document from the database
    del_result = await mongo_test_collection.delete_one({"workflow_run_id": omex_verify_workflow_output.workflow_run_id})
    assert del_result.deleted_count == 1
