import uuid
from pathlib import Path

import pytest
from temporalio.client import Client, WorkflowHandle
from temporalio.worker import Worker

from biosim_server.common.biosim1_client import BiosimServiceRest
from biosim_server.common.database.data_models import BiosimulatorVersion
from biosim_server.common.database.database_service import DatabaseService
from biosim_server.omex_archives import get_cached_omex_file_from_local
from biosim_server.workflows.simulate import OmexSimWorkflow, OmexSimWorkflowInput, OmexSimWorkflowOutput, \
    OmexSimWorkflowStatus
from tests.fixtures.file_service_local import FileServiceLocal


@pytest.mark.asyncio
async def test_sim_workflow(temporal_client: Client, temporal_verify_worker: Worker, omex_test_file: Path,
                            biosim_service_rest: BiosimServiceRest, file_service_local: FileServiceLocal,
                            database_service_mongo: DatabaseService) -> None:
    assert biosim_service_rest is not None

    omex_file = await get_cached_omex_file_from_local(omex_file=omex_test_file, filename=omex_test_file.name)

    simulator_versions = await biosim_service_rest.get_simulator_versions()
    simulator_version: BiosimulatorVersion | None = None
    for sim in simulator_versions:
        if sim.id == 'copasi':
            simulator_version = sim
    assert simulator_version is not None

    sim_workflow_input = OmexSimWorkflowInput(omex_file=omex_file, simulator_version=simulator_version, cache_buster="0")
    workflow_handle = await temporal_client.start_workflow(OmexSimWorkflow.run, args=[sim_workflow_input],
        id=uuid.uuid4().hex, task_queue="verification_tasks", )
    assert isinstance(workflow_handle, WorkflowHandle)
    workflow_handle_result: OmexSimWorkflowOutput = await workflow_handle.result()
    workflow_run = workflow_handle_result.biosimulator_workflow_run
    expected_results = OmexSimWorkflowOutput(workflow_id=workflow_handle_result.workflow_id,
                                             workflow_status=OmexSimWorkflowStatus.COMPLETED,
                                             biosimulator_workflow_run=workflow_run)
    assert expected_results.biosimulator_workflow_run is not None
    expected_biosim_run = expected_results.biosimulator_workflow_run.biosim_run
    assert expected_biosim_run is not None
    assert workflow_handle_result is not None
    assert workflow_run is not None
    if expected_biosim_run and workflow_run.biosim_run:
        expected_biosim_run.id = workflow_run.biosim_run.id
        expected_biosim_run.simulator_version = workflow_run.biosim_run.simulator_version
    assert workflow_handle_result == expected_results
