import asyncio
import uuid

from temporalio.client import Client

from biosim_server.omex_sim.biosim1.models import SourceOmex, BiosimSimulatorSpec
from biosim_server.omex_sim.workflows.omex_sim_workflow import OmexSimWorkflow, OmexSimWorkflowInput, \
    OmexSimWorkflowRun


async def start_workflow() -> None:
    client = await Client.connect("localhost:7233")
    omex_sim_workflow_input = OmexSimWorkflowInput(
        source_omex=SourceOmex(omex_s3_file="path/to/model.obj", name="name"),
        simulator_spec=BiosimSimulatorSpec(simulator="vcell"))
    handle = await client.start_workflow(
        OmexSimWorkflow.run,
        args=[OmexSimWorkflowInput(source_omex=omex_sim_workflow_input.source_omex,
                                   simulator_spec=omex_sim_workflow_input.simulator_spec)],
        task_queue="verification_tasks",
        id=uuid.uuid4().hex,
    )
    print(f"Started workflow with ID: {handle.id}")

    query_result: OmexSimWorkflowRun = await handle.query(OmexSimWorkflow.get_omex_sim_workflow_run, args=[])
    print(f"Workflow status: {query_result.workflow_status}")



if __name__ == "__main__":
    asyncio.run(start_workflow())
