import asyncio
import uuid

from temporalio.client import Client

from biosim_server.workflows.omex_sim_workflow import OmexSimWorkflow, SimulatorWorkflowInput


async def start_workflow():
    client = await Client.connect("localhost:7233")
    sim_workflow_input = SimulatorWorkflowInput(model_path="path/to/model.obj", simulator_name="simulatorC")
    handle = await client.start_workflow(
        OmexSimWorkflow.run,
        args=[sim_workflow_input],
        task_queue="simulation_runs",
        id=uuid.uuid4().hex,
    )
    print(f"Started workflow with ID: {handle.id}")


if __name__ == "__main__":
    asyncio.run(start_workflow())
