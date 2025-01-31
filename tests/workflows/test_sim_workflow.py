import uuid
from pathlib import Path

import pytest
from temporalio.client import Client, WorkflowHandle
from temporalio.worker import Worker

from biosim_server.common.biosim1_client import BiosimServiceRest
from biosim_server.common.database.data_models import BiosimSimulationRun, BiosimSimulationRunStatus, \
    BiosimulatorVersion
from biosim_server.common.database.database_service import DatabaseService
from biosim_server.common.storage import FileServiceLocal
from biosim_server.common.storage.data_cache import get_cached_omex_file_from_local
from biosim_server.workflows.simulate import OmexSimWorkflow, OmexSimWorkflowInput, OmexSimWorkflowOutput, \
    OmexSimWorkflowStatus


@pytest.mark.asyncio
async def test_sim_workflow(temporal_client: Client, temporal_verify_worker: Worker, omex_test_file: Path,
                            biosim_service_rest: BiosimServiceMock, file_service_local: FileServiceLocal) -> None:
    assert biosim_service_rest is not None

    # set up the omex file to mock GCS
    omex_file = OmexFile(file_hash_md5="hash", file_size=1000, uploaded_filename="BIOMD0000000010_tellurium_Negative_feedback_and_ultrasen.omex", bucket_name=get_settings().storage_bucket, omex_gcs_path="path/to/hash.omex")
    await file_service_local.upload_file(file_path=omex_test_file, gcs_path=omex_file.omex_gcs_path)

    sim_spec = BiosimSimulatorSpec(simulator="vcell", version="latest")
    sim_workflow_input = OmexSimWorkflowInput(omex_file=omex_file, simulator_spec=sim_spec)
    workflow_handle = await temporal_client.start_workflow(OmexSimWorkflow.run, args=[sim_workflow_input],
        id=uuid.uuid4().hex, task_queue="verification_tasks", )
    assert isinstance(workflow_handle, WorkflowHandle)
    workflow_handle_result: OmexSimWorkflowOutput = await workflow_handle.result()
    expected_results = OmexSimWorkflowOutput(workflow_id=workflow_handle_result.workflow_id,
        workflow_input=sim_workflow_input, workflow_status=OmexSimWorkflowStatus.COMPLETED,
        biosim_run=BiosimSimulationRun(id=uuid.uuid4().hex, name=omex_file.uploaded_filename, simulator=sim_spec.simulator,
                                       simulatorVersion=sim_spec.version or "latest", simulatorDigest=uuid.uuid4().hex,
                                       status=BiosimSimulationRunStatus.SUCCEEDED),
        hdf5_file=workflow_handle_result.hdf5_file, )
    if expected_results.biosim_run and workflow_handle_result.biosim_run:
        expected_results.biosim_run.id = workflow_handle_result.biosim_run.id
        expected_results.biosim_run.simulatorVersion = workflow_handle_result.biosim_run.simulatorVersion
        expected_results.biosim_run.simulatorDigest = workflow_handle_result.biosim_run.simulatorDigest
    assert workflow_handle_result == expected_results
