import asyncio
import logging
import random

from temporalio.client import Client
from temporalio.worker import Worker

from biosim_server.biosim1.api_client import check_run_status, run_project
from biosim_server.biosim1.simdata_api_client import get_hdf5_metadata, get_hdf5_data
from biosim_server.workflows.activities import upload_model_to_s3, generate_statistics
from biosim_server.workflows.omex_sim_workflow import OmexSimWorkflow
from biosim_server.workflows.omex_verify_workflow import OmexVerifyWorkflow

interrupt_event = asyncio.Event()


async def main():
    logging.basicConfig(level=logging.INFO)

    random.seed(667)

    client = await Client.connect("localhost:7233")

    run_futures = []
    handle = Worker(
        client,
        task_queue="verification_tasks",
        # workflows=[main_workflow.MainWorkflow, simulator_run_workflow.SimulatorWorkflow],
        workflows=[OmexVerifyWorkflow],
        activities=[upload_model_to_s3, generate_statistics],
    )
    run_futures.append(handle.run())
    handle = Worker(
        client,
        task_queue="simulation_runs",
        workflows=[OmexSimWorkflow],
        activities=[check_run_status, run_project, get_hdf5_metadata, get_hdf5_data],
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
