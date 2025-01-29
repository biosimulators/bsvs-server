import uuid
from pathlib import Path

import pytest
from temporalio.client import Client, WorkflowHandle
from temporalio.worker import Worker

from biosim_server.common.biosim1_client import SourceOmex, BiosimSimulatorSpec, BiosimSimulationRunStatus, \
    BiosimSimulationRun
from biosim_server.common.storage import FileServiceLocal
from biosim_server.workflows.simulate import OmexSimWorkflow, OmexSimWorkflowInput, OmexSimWorkflowOutput, \
    OmexSimWorkflowStatus
from tests.fixtures.biosim_service_mock import BiosimServiceMock


@pytest.mark.asyncio
async def test_sim_workflow(temporal_client: Client, temporal_verify_worker: Worker, omex_test_file: Path,
                            biosim_service_rest: BiosimServiceMock, file_service_local: FileServiceLocal) -> None:
    assert biosim_service_rest is not None

    # set up the omex file to mock GCS
    gcs_path = "path/to/model.omex"
    await file_service_local.upload_file(file_path=omex_test_file, gcs_path=gcs_path)

    sim_spec = BiosimSimulatorSpec(simulator="vcell", version="latest")
    source_omex = SourceOmex(omex_s3_file=gcs_path, name="name")
    sim_workflow_input = OmexSimWorkflowInput(source_omex=source_omex, simulator_spec=sim_spec)
    workflow_handle = await temporal_client.start_workflow(OmexSimWorkflow.run, args=[sim_workflow_input],
        id=uuid.uuid4().hex, task_queue="verification_tasks", )
    assert isinstance(workflow_handle, WorkflowHandle)
    workflow_handle_result: OmexSimWorkflowOutput = await workflow_handle.result()
    expected_results = OmexSimWorkflowOutput(workflow_id=workflow_handle_result.workflow_id,
        workflow_input=sim_workflow_input, workflow_status=OmexSimWorkflowStatus.COMPLETED,
        biosim_run=BiosimSimulationRun(id=uuid.uuid4().hex, name=source_omex.name, simulator=sim_spec.simulator,
                                       simulatorVersion=sim_spec.version or "latest", simulatorDigest=uuid.uuid4().hex,
                                       status=BiosimSimulationRunStatus.SUCCEEDED),
        hdf5_file=workflow_handle_result.hdf5_file, )
    if expected_results.biosim_run and workflow_handle_result.biosim_run:
        expected_results.biosim_run.id = workflow_handle_result.biosim_run.id
        expected_results.biosim_run.simulatorVersion = workflow_handle_result.biosim_run.simulatorVersion
        expected_results.biosim_run.simulatorDigest = workflow_handle_result.biosim_run.simulatorDigest
    assert workflow_handle_result == expected_results
