import asyncio
import uuid

from temporalio.client import Client

from biosim_server.common.biosim1_client import BiosimService
from biosim_server.common.database.data_models import OmexFile
from biosim_server.common.temporal import pydantic_data_converter
from biosim_server.workflows.simulate import OmexSimWorkflow, OmexSimWorkflowInput, OmexSimWorkflowOutput


async def start_workflow() -> None:
    client = await Client.connect("localhost:7233", data_converter=pydantic_data_converter)
    omex_file = OmexFile(file_hash_md5="hash", uploaded_filename="BIOMD0000000010_tellurium_Negative_feedback_and_ultrasen.omex", file_size=100, omex_gcs_path="path/to/hash.omex", bucket_name="bucket")
    omex_sim_workflow_input = OmexSimWorkflowInput(omex_file=omex_file, simulator_spec=BiosimSimulatorSpec(simulator="vcell"))
    handle = await client.start_workflow(
        OmexSimWorkflow.run,
        args=[OmexSimWorkflowInput(omex_file=omex_sim_workflow_input.omex_file,
                                   simulator_spec=omex_sim_workflow_input.simulator_spec)],
        task_queue="verification_tasks",
        id=uuid.uuid4().hex,
    )
    print(f"Started workflow with ID: {handle.id}")

    query_result: OmexSimWorkflowOutput = await handle.query(OmexSimWorkflow.get_omex_sim_workflow_run, args=[])
    print(f"Workflow status: {query_result.workflow_status}")



if __name__ == "__main__":
    asyncio.run(start_workflow())
