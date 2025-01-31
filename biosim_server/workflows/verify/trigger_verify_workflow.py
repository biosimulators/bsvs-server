import asyncio
import uuid

from biosim_server.common.database.data_models import OmexFile, BiosimulatorVersion
from biosim_server.dependencies import init_standalone, shutdown_standalone, get_temporal_client, get_biosim_service
from biosim_server.workflows.verify import OmexVerifyWorkflow, OmexVerifyWorkflowInput


async def start_workflow() -> None:
    await init_standalone()

    client = get_temporal_client()
    assert client is not None
    omex_file = OmexFile(omex_gcs_path="path/to/model.omex", uploaded_filename="BIOMD0000000010_tellurium_Negative_feedback_and_ultrasen.omex", file_hash_md5="hash", file_size=100, bucket_name="bucket")

    biosim_service = get_biosim_service()
    assert biosim_service is not None
    simulator_versions: list[BiosimulatorVersion] = await biosim_service.get_simulator_versions()
    workflow_id = uuid.uuid4().hex
    handle = await client.start_workflow(
        OmexVerifyWorkflow.run,
        args=[OmexVerifyWorkflowInput(
            omex_file=omex_file,
            user_description="description",
            requested_simulators=[simulator_versions[0], simulator_versions[1]],
            include_outputs=True,
            rel_tol=1e-4,
            abs_tol_min=1e-3,
            abs_tol_scale=1e-5,
            observables=["time", "concentration"]
        )],
        task_queue="verification_tasks",
        id=workflow_id,
    )
    print(f"Started workflow with ID: {handle.id}")

    await shutdown_standalone()


if __name__ == "__main__":
    asyncio.run(start_workflow())
