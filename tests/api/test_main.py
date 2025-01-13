import os
from copy import copy
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from temporalio.client import Client
from temporalio.worker import Worker
from testcontainers.mongodb import MongoDbContainer  # type: ignore

from biosim_server.api.main import app
from biosim_server.io.file_service_local import FileServiceLocal
from biosim_server.omex_sim.biosim1.biosim_service_rest import BiosimServiceRest
from biosim_server.omex_sim.biosim1.models import SourceOmex
from biosim_server.verify.workflows.omex_verify_workflow import OmexVerifyWorkflowInput, OmexVerifyWorkflowOutput, \
    OmexVerifyWorkflowStatus


@pytest.mark.asyncio
async def test_root() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as test_client:
        response = await test_client.get("/")
        assert response.status_code == 200
        assert response.json() == {'docs': 'https://biochecknet.biosimulations.org/docs'}


@pytest.mark.asyncio
async def test_get_output_not_found(verify_workflow_input: OmexVerifyWorkflowInput,
                          verify_workflow_output: OmexVerifyWorkflowOutput) -> None:

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as test_client:
        # test with non-existent verification_id
        response = await test_client.get(f"/get-output/non-existent-id")
        assert response.status_code == 404



@pytest.mark.asyncio
async def test_verify_and_get_output(verify_workflow_input: OmexVerifyWorkflowInput,
                                     verify_workflow_output: OmexVerifyWorkflowOutput,
                                     file_service_local: FileServiceLocal,
                                     temporal_client: Client,
                                     temporal_verify_worker: Worker,
                                     biosim_service_rest: BiosimServiceRest) -> None:
    root_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    file_path = root_dir / "local_data" / "BIOMD0000000010_tellurium_Negative_feedback_and_ultrasen.omex"
    assert verify_workflow_input.observables is not None
    query_params: dict[str, float | str | list[str]] = {
        "workflow_id_prefix": "verification-",
        "simulators": [sim.simulator for sim in verify_workflow_input.requested_simulators],
        "include_outputs": verify_workflow_input.include_outputs,
        "user_description": verify_workflow_input.user_description,
        "observables": verify_workflow_input.observables,
        "rTol": verify_workflow_input.rTol,
        "aTol": verify_workflow_input.aTol
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as test_client:
        with open(file_path, "rb") as file:
            files = {"uploaded_file": (
                "BIOMD0000000010_tellurium_Negative_feedback_and_ultrasen.omex", file, "application/zip")}
            response = await test_client.post("/verify", files=files, params=query_params)
            assert response.status_code == 200

            workflow_output = OmexVerifyWorkflowOutput.model_validate(response.json())
            output = OmexVerifyWorkflowOutput(
                workflow_input=OmexVerifyWorkflowInput(
                    workflow_id=workflow_output.workflow_input.workflow_id,
                    source_omex=SourceOmex(omex_s3_file=workflow_output.workflow_input.source_omex.omex_s3_file,
                                           name=workflow_output.workflow_input.source_omex.name),
                    user_description=workflow_output.workflow_input.user_description,
                    requested_simulators=workflow_output.workflow_input.requested_simulators,
                    include_outputs=workflow_output.workflow_input.include_outputs,
                    rTol=workflow_output.workflow_input.rTol,
                    aTol=workflow_output.workflow_input.aTol,
                    observables=workflow_output.workflow_input.observables
                ),
                workflow_status=workflow_output.workflow_status,
                timestamp=workflow_output.timestamp,
                workflow_run_id=workflow_output.workflow_run_id
            )

            # set timestamp, job_id, and omex_s3_path before comparison (these are set on server)
            expected_verify_workflow_output = OmexVerifyWorkflowOutput(
                workflow_input=copy(verify_workflow_input),
                workflow_status=OmexVerifyWorkflowStatus.PENDING,
                timestamp=output.timestamp,
                workflow_run_id=output.workflow_run_id
            )
            expected_verify_workflow_output.workflow_input.source_omex.omex_s3_file = output.workflow_input.source_omex.omex_s3_file
            expected_verify_workflow_output.workflow_input.workflow_id = output.workflow_input.workflow_id
            expected_verify_workflow_output.timestamp = output.timestamp
            expected_verify_workflow_output.workflow_run_id = output.workflow_run_id
            assert expected_verify_workflow_output == output

    # verify the omex_s3_path file to the original file_path
    # this works because we are using the local file service instead of S3
    omex_s3_path = Path(output.workflow_input.source_omex.omex_s3_file)
    assert omex_s3_path.exists()
    with open(omex_s3_path, "rb") as f:
        assert f.read() == file_path.read_bytes()

    # verify the workflow is started
    # assert output.workflow_run_id is not None
    workflow_handle = temporal_client.get_workflow_handle(workflow_id=output.workflow_input.workflow_id, result_type=OmexVerifyWorkflowOutput)
    assert workflow_handle is not None
    workflow_handle_result: OmexVerifyWorkflowOutput = await workflow_handle.result()
    expected_verify_workflow_output.timestamp = workflow_handle_result.timestamp
    expected_verify_workflow_output.workflow_run_id = workflow_handle_result.workflow_run_id
    expected_verify_workflow_output.workflow_status = workflow_handle_result.workflow_status

    assert workflow_handle_result == expected_verify_workflow_output
