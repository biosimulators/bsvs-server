import asyncio
import uuid

from temporalio.client import Client

from temporal.main_workflow import MainWorkflow


async def start_workflow():
    client = await Client.connect("localhost:7233")
    handle = await client.start_workflow(
        MainWorkflow.run,
        args=["path/to/model.obj", ["simulatorC", "simulatorD"]],
        task_queue="verification_tasks",
        id=uuid.uuid4().hex,
    )
    print(f"Started workflow with ID: {handle.id}")


if __name__ == "__main__":
    asyncio.run(start_workflow())
