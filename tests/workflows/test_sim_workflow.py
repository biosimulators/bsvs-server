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
                            biosim_service_rest: BiosimServiceRest, file_service_local: FileServiceLocal,
                            database_service_mongo: DatabaseService) -> None:
    assert biosim_service_rest is not None

    omex_file = await get_cached_omex_file_from_local(omex_file=omex_test_file, filename=omex_test_file.name)

    await file_service_local.upload_file(file_path=omex_test_file, gcs_path=omex_file.omex_gcs_path)
    simulator_versions = await biosim_service_rest.get_simulator_versions()
    simulator_version: BiosimulatorVersion | None = None
    for sim in simulator_versions:
        if sim.id == 'copasi':
            simulator_version = sim
    assert simulator_version is not None

    sim_workflow_input = OmexSimWorkflowInput(omex_file=omex_file, simulator_version=simulator_version)
    workflow_handle = await temporal_client.start_workflow(OmexSimWorkflow.run, args=[sim_workflow_input],
        id=uuid.uuid4().hex, task_queue="verification_tasks", )
    assert isinstance(workflow_handle, WorkflowHandle)
    workflow_handle_result: OmexSimWorkflowOutput = await workflow_handle.result()
    expected_results = OmexSimWorkflowOutput(workflow_id=workflow_handle_result.workflow_id,
        workflow_input=sim_workflow_input, workflow_status=OmexSimWorkflowStatus.COMPLETED,
        biosim_run=BiosimSimulationRun(id=uuid.uuid4().hex, name=omex_file.uploaded_filename, simulator_version=simulator_version,
                                       status=BiosimSimulationRunStatus.SUCCEEDED),
        hdf5_file=workflow_handle_result.hdf5_file, )
    if expected_results.biosim_run and workflow_handle_result.biosim_run:
        expected_results.biosim_run.id = workflow_handle_result.biosim_run.id
        expected_results.biosim_run.simulator_version = workflow_handle_result.biosim_run.simulator_version
    assert workflow_handle_result == expected_results
