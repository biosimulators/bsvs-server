import uuid

import pytest
from temporalio.client import WorkflowHandle

from biosim_server.workflows.omex_sim_workflow import OmexSimWorkflow, SimulatorWorkflowInput
from biosim_server.workflows.omex_verify_workflow import OmexVerifyWorkflow


@pytest.mark.asyncio
async def test_sim_workflow(temporal_client, temporal_verify_worker):
    sim_workflow_input = SimulatorWorkflowInput(model_path="path/to/model.obj", simulator_name="simulatorC")

    workflow_handle = await temporal_client.start_workflow(
        OmexSimWorkflow.run,
        args=[sim_workflow_input],
        id=uuid.uuid4().hex,
        task_queue="verification_tasks",
    )
    assert isinstance(workflow_handle, WorkflowHandle)
    workflow_handle_result = await workflow_handle.result()
    expected_results = {'result_path': 's3://bucket-name/results/simulatorC.output',
                        'simulator': 'simulatorC',
                        'status': 'completed'}
    assert workflow_handle_result == expected_results


@pytest.mark.asyncio
async def test_verify_workflow(temporal_client, temporal_verify_worker):
    model_file_path = "path/to/model.obj"
    simulator_names = ["simulatorC", "simulatorD"]

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
