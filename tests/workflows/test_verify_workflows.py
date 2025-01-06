import uuid
from pathlib import Path

import pytest
from temporalio.client import Client, WorkflowHandle
from temporalio.worker import Worker

from biosim_server.io.file_service_local import FileServiceLocal
from biosim_server.omex_sim.biosim1.models import SourceOmex, BiosimSimulatorSpec, BiosimSimulationRunStatus
from biosim_server.omex_sim.workflows.omex_sim_workflow import OmexSimWorkflow, OmexSimWorkflowInput, \
    OmexSimWorkflowRun, OmexSimWorkflowStatus
from biosim_server.omex_verify.workflows.omex_verify_workflow import OmexVerifyWorkflow, OmexVerifyWorkflowInput
from tests.fixtures.biosim_service_mock import BiosimServiceMock


@pytest.mark.asyncio
async def test_sim_workflow(temporal_client: Client, temporal_verify_worker: Worker,
                            biosim_service_mock: BiosimServiceMock, file_service_local: FileServiceLocal) -> None:
    assert biosim_service_mock is not None

    # set up the omex file to mock S3
    path_from_root = Path("local_data/BIOMD0000000010_tellurium_Negative_feedback_and_ultrasen.omex")
    test_omex_file = Path(__file__).parent.parent.parent / path_from_root
    s3_path = "path/to/model.omex"
    await file_service_local.upload_file(file_path=test_omex_file, s3_path=s3_path)

    sim_spec = BiosimSimulatorSpec(simulator="vcell", version="1.0")
    source_omex = SourceOmex(omex_s3_file=s3_path, name="name")
    sim_workflow_input = OmexSimWorkflowInput(source_omex=source_omex, simulator_spec=sim_spec)
    workflow_handle = await temporal_client.start_workflow(
        OmexSimWorkflow.run,
        args=[sim_workflow_input],
        id=uuid.uuid4().hex,
        task_queue="verification_tasks",
    )
    assert isinstance(workflow_handle, WorkflowHandle)
    workflow_handle_result: OmexSimWorkflowRun = await workflow_handle.result()
    expected_results = OmexSimWorkflowRun(source_omex=source_omex, workflow_status=OmexSimWorkflowStatus.COMPLETED,
                                          sim_job_status=BiosimSimulationRunStatus.SUCCEEDED,
                                          sim_spec=sim_spec, result_s3_path='s3://bucket-name/results/vcell.output')
    expected_results.sim_job_id = workflow_handle_result.sim_job_id
    assert workflow_handle_result == expected_results


@pytest.mark.asyncio
async def test_verify_workflow(temporal_client: Client, temporal_verify_worker: Worker,
                               biosim_service_mock: BiosimServiceMock, file_service_local: FileServiceLocal) -> None:
    assert biosim_service_mock is not None

    # set up the omex file to mock S3
    path_from_root = Path("local_data/BIOMD0000000010_tellurium_Negative_feedback_and_ultrasen.omex")
    test_omex_file = Path(__file__).parent.parent.parent / path_from_root
    s3_path = "path/to/model.omex"
    await file_service_local.upload_file(file_path=test_omex_file, s3_path=s3_path)

    workflow_handle = await temporal_client.start_workflow(
        OmexVerifyWorkflow.run,
        args=[OmexVerifyWorkflowInput(source_omex=SourceOmex(omex_s3_file=s3_path, name="model_name"),
                                      simulator_specs=[BiosimSimulatorSpec(simulator="vcell", version="1.0"),
                                                       BiosimSimulatorSpec(simulator="copasi", version="1.0")])],
        id=uuid.uuid4().hex,
        task_queue="verification_tasks",
    )
    assert isinstance(workflow_handle, WorkflowHandle)
    workflow_handle_result = await workflow_handle.result()
    expected_results = 's3://bucket-name/reports/final_report.pdf'
    assert workflow_handle_result == expected_results
