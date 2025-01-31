import asyncio
import uuid

from temporalio.client import Client

from biosim_server.common.biosim1_client import BiosimService
from biosim_server.common.database.data_models import OmexFile
from biosim_server.common.temporal import pydantic_data_converter
from biosim_server.dependencies import get_biosim_service, init_standalone, shutdown_standalone
from biosim_server.workflows.simulate import OmexSimWorkflow, OmexSimWorkflowInput, OmexSimWorkflowOutput


async def start_workflow() -> None:
    await init_standalone()

    client = await Client.connect("localhost:7233", data_converter=pydantic_data_converter)
    omex_file = OmexFile(file_hash_md5="hash", uploaded_filename="BIOMD0000000010_tellurium_Negative_feedback_and_ultrasen.omex", file_size=100, omex_gcs_path="path/to/hash.omex", bucket_name="bucket")
    biosim_service: BiosimService | None = get_biosim_service()
    assert biosim_service is not None
    simulator_version = (await biosim_service.get_simulator_versions())[0]
    omex_sim_workflow_input = OmexSimWorkflowInput(omex_file=omex_file, simulator_version=simulator_version,
                                                   cache_buster="0")
    handle = await client.start_workflow(
        OmexSimWorkflow.run, args=[omex_sim_workflow_input],
        task_queue="verification_tasks",
        id=uuid.uuid4().hex,
    )
    print(f"Started workflow with ID: {handle.id}")

    query_result: OmexSimWorkflowOutput = await handle.query(OmexSimWorkflow.get_omex_sim_workflow_run, args=[])
    print(f"Workflow status: {query_result.workflow_status}")

    await shutdown_standalone()



if __name__ == "__main__":
    asyncio.run(start_workflow())
