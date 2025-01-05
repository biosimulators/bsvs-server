import asyncio
import uuid

from temporalio.client import Client

from biosim_server.biosim1.models import SourceOmex, SimulatorSpec
from biosim_server.workflows.omex_verify_workflow import OmexVerifyWorkflow, OmexVerifyWorkflowInput


async def start_workflow() -> None:
    client = await Client.connect("localhost:7233")
    source_omex = SourceOmex(omex_s3_file="path/to/model.omex", name="model_name")
    handle = await client.start_workflow(
        OmexVerifyWorkflow.run,
        args=[OmexVerifyWorkflowInput(source_omex=source_omex,
                                      simulator_specs=[SimulatorSpec(simulator="vcell", version="1.0"),
                                                       SimulatorSpec(simulator="copasi", version="1.0")])],
        task_queue="verification_tasks",
        id=uuid.uuid4().hex,
    )
    print(f"Started workflow with ID: {handle.id}")


if __name__ == "__main__":
    asyncio.run(start_workflow())
