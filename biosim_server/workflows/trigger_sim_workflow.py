import asyncio
import uuid

from temporalio.client import Client

from biosim_server.biosim1.models import SourceOmex, SimulatorSpec
from biosim_server.workflows.omex_sim_workflow import OmexSimWorkflow, OmexSimWorkflowInput


async def start_workflow() -> None:
    client = await Client.connect("localhost:7233")
    omex_sim_workflow_input = OmexSimWorkflowInput(
        source_omex=SourceOmex(omex_s3_file="path/to/model.obj", name="name"),
        simulator_spec=SimulatorSpec(simulator="vcell"))
    handle = await client.start_workflow(
        OmexSimWorkflow.run,
        args=[OmexSimWorkflowInput(source_omex=omex_sim_workflow_input.source_omex,
                                   simulator_spec=omex_sim_workflow_input.simulator_spec)],
        task_queue="verification_tasks",
        id=uuid.uuid4().hex,
    )
    print(f"Started workflow with ID: {handle.id}")


if __name__ == "__main__":
    asyncio.run(start_workflow())
