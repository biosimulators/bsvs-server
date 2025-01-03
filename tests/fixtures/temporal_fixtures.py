from typing import AsyncGenerator

import pytest_asyncio
from temporalio.client import Client
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from biosim_server.dependencies import get_temporal_client, set_temporal_client
from biosim_server.workflows.activities import upload_model_to_s3, generate_statistics
from biosim_server.workflows.biosim_activities import check_run_status, run_project, get_hdf5_metadata, get_hdf5_data
from biosim_server.workflows.omex_sim_workflow import OmexSimWorkflow
from biosim_server.workflows.omex_verify_workflow import OmexVerifyWorkflow


@pytest_asyncio.fixture(scope="session")
async def temporal_env(request) -> AsyncGenerator[WorkflowEnvironment, None]:
    env_type = request.config.getoption("--workflow-environment")
    if env_type == "local":
        env = await WorkflowEnvironment.start_local()
    elif env_type == "time-skipping":
        env = await WorkflowEnvironment.start_time_skipping()
    else:
        env = WorkflowEnvironment.from_client(await Client.connect(env_type))

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
            workflows=[OmexVerifyWorkflow, OmexSimWorkflow],
            activities=[upload_model_to_s3, generate_statistics, check_run_status, run_project, get_hdf5_metadata,
                        get_hdf5_data],
            debug_mode=True,
    ) as worker:
        yield worker
