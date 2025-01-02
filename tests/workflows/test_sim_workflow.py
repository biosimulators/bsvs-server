import uuid

import pytest
from temporalio.client import WorkflowHandle
from temporalio.worker import Worker

from biosim_server.workflows.biosim_activities import get_hdf5_data, get_hdf5_metadata, run_project, check_run_status
from biosim_server.workflows.omex_sim_workflow import OmexSimWorkflow, SimulatorWorkflowInput


@pytest.mark.asyncio
async def test_sim_workflow(temporal_client):
    # Run a worker for the workflow
    sim_workflow_input = SimulatorWorkflowInput(model_path="path/to/model.obj", simulator_name="simulatorC")
    async with Worker(
            temporal_client,
            task_queue="simulation_runs",
            workflows=[OmexSimWorkflow],
            activities=[check_run_status, run_project, get_hdf5_metadata, get_hdf5_data],
    ):
        workflow_handle = await temporal_client.start_workflow(
            OmexSimWorkflow.run,
            args=[sim_workflow_input],
            id=uuid.uuid4().hex,
            task_queue="simulation_runs",
        )
        assert isinstance(workflow_handle, WorkflowHandle)
        workflow_handle_result = await workflow_handle.result()
        expected_results = {'result_path': 's3://bucket-name/results/simulatorC.output',
                            'simulator': 'simulatorC',
                            'status': 'completed'}
        assert workflow_handle_result == expected_results
