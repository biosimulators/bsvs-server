import pytest

from biosim_server.common.database.data_models import OmexFile, BiosimulatorVersion, BiosimulatorWorkflowRun
from biosim_server.common.database.database_service_mongo import DatabaseServiceMongo
from biosim_server.workflows.verify import OmexVerifyWorkflowOutput


@pytest.mark.asyncio
async def test_omex_file(database_service_mongo: DatabaseServiceMongo) -> None:
    omex_file = OmexFile(file_hash_md5="1234", bucket_name="test_bucket",
                         uploaded_filename="BIOMD0000000010_tellurium_Negative_feedback_and_ultrasen.omex",
                         omex_gcs_path="path/to/omex", file_size=100000)
    inserted_omex_file = await database_service_mongo.insert_omex_file(omex_file=omex_file)
    database_omex_file = await database_service_mongo.get_omex_file(file_hash_md5=omex_file.file_hash_md5)
    assert database_omex_file == inserted_omex_file

    assert database_omex_file.database_id is not None
    database_id = database_omex_file.database_id
    database_omex_file.database_id = None
    assert database_omex_file == omex_file

    await database_service_mongo.delete_omex_file(database_id=database_id)

    assert await database_service_mongo.get_omex_file(file_hash_md5=omex_file.file_hash_md5) is None

    with pytest.raises(Exception):
        await database_service_mongo.delete_omex_file(database_id=database_id)


@pytest.mark.asyncio
async def test_biosimulator_workflow_run(database_service_mongo: DatabaseServiceMongo,
                                        omex_verify_workflow_output: OmexVerifyWorkflowOutput) -> None:
    workflow_id = "workflow_id"
    omex_file = OmexFile(file_hash_md5="1234", bucket_name="test_bucket",
                         uploaded_filename="BIOMD0000000010_tellurium_Negative_feedback_and_ultrasen.omex",
                         omex_gcs_path="path/to/omex", file_size=100000)
    simulator_version = BiosimulatorVersion(id="tellurium", name="tellurium", version="2.0.0",
                                            image_url="url", image_digest="digest")
    assert omex_verify_workflow_output.workflow_results is not None
    biosim_run = omex_verify_workflow_output.workflow_results.sims_run_info[0].biosim_sim_run
    hdf5_file = omex_verify_workflow_output.workflow_results.sims_run_info[0].hdf5_file
    sim_output = BiosimulatorWorkflowRun(workflow_id=workflow_id, file_hash_md5=omex_file.file_hash_md5,
                                         sim_digest=simulator_version.image_digest, omex_file=omex_file,
                                         simulator_version=simulator_version, biosim_run=biosim_run, hdf5_file=hdf5_file)

    inserted_sim_output1 = await database_service_mongo.insert_biosimulator_workflow_run(sim_output=sim_output)
    assert inserted_sim_output1.database_id is not None
    sim_outputs: list[BiosimulatorWorkflowRun] = await database_service_mongo.get_biosimulator_workflow_runs(
                                                             file_hash_md5=omex_file.file_hash_md5,
                                                             sim_digest=simulator_version.image_digest)
    assert sim_outputs == [inserted_sim_output1]

    inserted_sim_output2 = await database_service_mongo.insert_biosimulator_workflow_run(sim_output=sim_output)
    assert inserted_sim_output2.database_id is not None
    sim_outputs = await database_service_mongo.get_biosimulator_workflow_runs(file_hash_md5=omex_file.file_hash_md5,
                                                                              sim_digest=simulator_version.image_digest)
    assert sim_outputs == [inserted_sim_output1, inserted_sim_output2]

    await database_service_mongo.delete_biosimulator_workflow_run(database_id=inserted_sim_output1.database_id)
    await database_service_mongo.delete_biosimulator_workflow_run(database_id=inserted_sim_output2.database_id)

    with pytest.raises(Exception):
        await database_service_mongo.delete_biosimulator_workflow_run(database_id=inserted_sim_output1.database_id)


