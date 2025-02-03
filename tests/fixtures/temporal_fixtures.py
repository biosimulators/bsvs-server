from typing import AsyncGenerator

import pytest
import pytest_asyncio
from temporalio.client import Client
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker, UnsandboxedWorkflowRunner

from biosim_server.common.temporal import pydantic_data_converter
from biosim_server.dependencies import get_temporal_client, set_temporal_client
from biosim_server.workflows.simulate import get_biosim_simulation_run_activity, submit_biosim_simulation_run_activity, get_hdf5_file_activity, get_hdf5_data_values_activity, \
    OmexSimWorkflow, save_biosimulator_workflow_run_activity, get_biosimulator_workflow_runs_activity
from biosim_server.workflows.verify import OmexVerifyWorkflow, RunsVerifyWorkflow, generate_statistics_activity
from biosim_server.workflows.verify.activities import create_biosimulator_workflow_runs_activity


@pytest_asyncio.fixture(scope="session")
async def temporal_env(request: pytest.FixtureRequest) -> AsyncGenerator[WorkflowEnvironment, None]:
    env_type = request.config.getoption("--workflow-environment")
    if env_type == "local":
        env = await WorkflowEnvironment.start_local(data_converter=pydantic_data_converter)
    elif env_type == "time-skipping":
        env = await WorkflowEnvironment.start_time_skipping(data_converter=pydantic_data_converter)
    else:
        env = WorkflowEnvironment.from_client(await Client.connect(env_type, data_converter=pydantic_data_converter))

    yield env

    await env.shutdown()


@pytest_asyncio.fixture(scope="function")
async def temporal_client(temporal_env: WorkflowEnvironment) -> AsyncGenerator[Client, None]:
    saved_client = get_temporal_client()
    set_temporal_client(temporal_env.client)

    yield temporal_env.client

    set_temporal_client(saved_client)


@pytest_asyncio.fixture(scope="function")
async def temporal_verify_worker(temporal_client: Client) -> AsyncGenerator[Worker, None]:
    async with Worker(
            temporal_client,
            task_queue="verification_tasks",
            workflows=[OmexVerifyWorkflow, OmexSimWorkflow, RunsVerifyWorkflow],
            activities=[generate_statistics_activity, get_biosim_simulation_run_activity, submit_biosim_simulation_run_activity, get_hdf5_file_activity, get_hdf5_data_values_activity,
                        save_biosimulator_workflow_run_activity, get_biosimulator_workflow_runs_activity,
                        create_biosimulator_workflow_runs_activity],
            debug_mode=True,
            workflow_runner=UnsandboxedWorkflowRunner()
    ) as worker:
        yield worker
