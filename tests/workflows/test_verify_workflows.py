import logging
import uuid
from pathlib import Path

import pytest
from temporalio.client import Client, WorkflowHandle
from temporalio.worker import Worker

from biosim_server.io.file_service_local import FileServiceLocal
from biosim_server.omex_sim.biosim1.biosim_service_rest import BiosimServiceRest
from biosim_server.omex_sim.biosim1.models import SourceOmex, BiosimSimulatorSpec, BiosimSimulationRunStatus, \
    BiosimSimulationRun
from biosim_server.omex_sim.workflows.omex_sim_workflow import OmexSimWorkflow, OmexSimWorkflowInput, \
    OmexSimWorkflowOutput, OmexSimWorkflowStatus
from biosim_server.verify.workflows.omex_verify_workflow import OmexVerifyWorkflow, OmexVerifyWorkflowInput, \
    OmexVerifyWorkflowOutput
from tests.fixtures.biosim_service_mock import BiosimServiceMock


@pytest.mark.asyncio
async def test_sim_workflow(temporal_client: Client, temporal_verify_worker: Worker,
                            biosim_service_rest: BiosimServiceMock, file_service_local: FileServiceLocal) -> None:
    assert biosim_service_rest is not None

    # set up the omex file to mock S3
    path_from_root = Path("local_data/BIOMD0000000010_tellurium_Negative_feedback_and_ultrasen.omex")
    test_omex_file = Path(__file__).parent.parent.parent / path_from_root
    s3_path = "path/to/model.omex"
    await file_service_local.upload_file(file_path=test_omex_file, s3_path=s3_path)

    sim_spec = BiosimSimulatorSpec(simulator="vcell", version="latest")
    source_omex = SourceOmex(omex_s3_file=s3_path, name="name")
    sim_workflow_input = OmexSimWorkflowInput(source_omex=source_omex, simulator_spec=sim_spec)
    workflow_handle = await temporal_client.start_workflow(
        OmexSimWorkflow.run,
        args=[sim_workflow_input],
        id=uuid.uuid4().hex,
        task_queue="verification_tasks",
    )
    assert isinstance(workflow_handle, WorkflowHandle)
    workflow_handle_result: OmexSimWorkflowOutput = await workflow_handle.result()
    expected_results = OmexSimWorkflowOutput(
        workflow_id=workflow_handle_result.workflow_id,
        workflow_input=sim_workflow_input,
        workflow_status=OmexSimWorkflowStatus.COMPLETED,
        biosim_run=BiosimSimulationRun(id=uuid.uuid4().hex,
                                       name=source_omex.name,
                                       simulator=sim_spec.simulator,
                                       simulatorVersion=sim_spec.version or "latest",
                                       simulatorDigest=uuid.uuid4().hex,
                                       status=BiosimSimulationRunStatus.SUCCEEDED),
        hdf5_file=None
    )
    if expected_results.biosim_run and workflow_handle_result.biosim_run:
        expected_results.biosim_run.id = workflow_handle_result.biosim_run.id
        expected_results.biosim_run.simulatorVersion = workflow_handle_result.biosim_run.simulatorVersion
        expected_results.biosim_run.simulatorDigest = workflow_handle_result.biosim_run.simulatorDigest
        expected_results.hdf5_file = workflow_handle_result.hdf5_file
    assert workflow_handle_result == expected_results


@pytest.mark.asyncio
async def test_verify_workflow(temporal_client: Client,
                               temporal_verify_worker: Worker,
                               verify_workflow_input: OmexVerifyWorkflowInput,
                               verify_workflow_output: OmexVerifyWorkflowOutput,
                               biosim_service_rest: BiosimServiceRest,
                               file_service_local: FileServiceLocal) -> None:
    assert biosim_service_rest is not None


    # set up the omex file to mock S3
    path_from_root = Path("local_data/BIOMD0000000010_tellurium_Negative_feedback_and_ultrasen.omex")
    test_omex_file = Path(__file__).parent.parent.parent / path_from_root
    s3_path = "path/to/model.omex"
    await file_service_local.upload_file(file_path=test_omex_file, s3_path=s3_path)
    verify_workflow_input.source_omex = SourceOmex(omex_s3_file=s3_path, name="name")

    workflow_id = uuid.uuid4().hex
    workflow_handle = await temporal_client.start_workflow(
        OmexVerifyWorkflow.run,
        args=[verify_workflow_input],
        id=workflow_id,
        task_queue="verification_tasks",
    )
    assert isinstance(workflow_handle, WorkflowHandle)
    workflow_handle_result: OmexVerifyWorkflowOutput = await workflow_handle.result()
    logging.info("workflow_handle_result type is %s", type(workflow_handle_result))
    expected_results = verify_workflow_output
    expected_results.workflow_run_id = workflow_handle_result.workflow_run_id
    expected_results.timestamp = workflow_handle_result.timestamp
    expected_results.workflow_status = workflow_handle_result.workflow_status
    assert workflow_handle_result == expected_results
