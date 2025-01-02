import uuid

import pytest
from temporalio.client import WorkflowHandle
from temporalio.worker import Worker

from biosim_server.workflows.activities import generate_statistics, upload_model_to_s3
from biosim_server.workflows.biosim_activities import get_hdf5_data, get_hdf5_metadata, run_project, check_run_status
from biosim_server.workflows.omex_sim_workflow import OmexSimWorkflow
from biosim_server.workflows.omex_verify_workflow import OmexVerifyWorkflow


@pytest.mark.asyncio
async def test_verify_workflow(temporal_client):
    # Run a worker for the workflow
    model_file_path = "path/to/model.obj"
    simulator_names = ["simulatorC", "simulatorD"]
    async with Worker(
            temporal_client,
            task_queue="verification_tasks",
            workflows=[OmexVerifyWorkflow],
            activities=[upload_model_to_s3, generate_statistics],
            debug_mode=True,
    ) as worker_1:
        async with Worker(
                temporal_client,
                task_queue="simulation_runs",
                workflows=[OmexSimWorkflow],
                activities=[check_run_status, run_project, get_hdf5_metadata, get_hdf5_data],
                debug_mode=True,
        ) as worker_2:

            workflow_handle = await temporal_client.start_workflow(
                OmexVerifyWorkflow.run,
                args=[model_file_path, simulator_names],
                id=uuid.uuid4().hex,
                task_queue="verification_tasks",
            )
            assert isinstance(workflow_handle, WorkflowHandle)
            workflow_handle_result = await workflow_handle.result()
            expected_results = 's3://bucket-name/reports/final_report.pdf'
            assert workflow_handle_result == expected_results
