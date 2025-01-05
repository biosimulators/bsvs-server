import asyncio
import logging
import random

from temporalio.client import Client
from temporalio.worker import Worker, UnsandboxedWorkflowRunner

from biosim_server.omex_verify.workflows.activities import generate_statistics
from biosim_server.omex_sim.workflows.biosim_activities import check_run_status, run_project
from biosim_server.omex_sim.workflows.biosim_activities import get_hdf5_metadata, get_hdf5_data
from biosim_server.omex_sim.workflows.omex_sim_workflow import OmexSimWorkflow
from biosim_server.omex_verify.workflows.omex_verify_workflow import OmexVerifyWorkflow

interrupt_event = asyncio.Event()


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    random.seed(667)

    client = await Client.connect("localhost:7233")

    run_futures = []
    handle = Worker(
        client,
        task_queue="verification_tasks",
        workflows=[OmexVerifyWorkflow, OmexSimWorkflow],
        activities=[generate_statistics, check_run_status, run_project, get_hdf5_metadata, get_hdf5_data],
        workflow_runner=UnsandboxedWorkflowRunner()
    )
    run_futures.append(handle.run())
    print("Started worker for verification_tasks, ctrl+c to exit")

    await asyncio.gather(*run_futures)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        interrupt_event.set()
        loop.run_until_complete(loop.shutdown_asyncgens())
        print("\nShutting down workers")
