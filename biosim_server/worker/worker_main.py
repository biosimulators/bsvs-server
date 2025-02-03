import asyncio
import logging
import random

from temporalio.worker import Worker, UnsandboxedWorkflowRunner

from biosim_server.dependencies import get_temporal_client, init_standalone
from biosim_server.workflows.simulate.biosim_activities import get_hdf5_file_activity, get_hdf5_data_values_activity, \
    save_biosimulator_workflow_run_activity, get_biosimulator_workflow_runs_activity
from biosim_server.workflows.simulate.biosim_activities import get_biosim_simulation_run_activity, submit_biosim_simulation_run_activity
from biosim_server.workflows.simulate.omex_sim_workflow import OmexSimWorkflow
from biosim_server.workflows.verify.activities import generate_statistics_activity, create_biosimulator_workflow_runs_activity
from biosim_server.workflows.verify.omex_verify_workflow import OmexVerifyWorkflow
from biosim_server.workflows.verify.runs_verify_workflow import RunsVerifyWorkflow

interrupt_event = asyncio.Event()


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    random.seed(667)

    await init_standalone()

    client = get_temporal_client()
    if client is None:
        raise Exception("Could not connect to Temporal service")

    run_futures = []
    handle = Worker(
        client,
        task_queue="verification_tasks",
        workflows=[OmexVerifyWorkflow, OmexSimWorkflow, RunsVerifyWorkflow],
        activities=[generate_statistics_activity, get_biosim_simulation_run_activity, submit_biosim_simulation_run_activity, get_hdf5_file_activity, get_hdf5_data_values_activity,
                    save_biosimulator_workflow_run_activity, get_biosimulator_workflow_runs_activity,
                    create_biosimulator_workflow_runs_activity],
        workflow_runner=UnsandboxedWorkflowRunner(),
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
