import asyncio
import logging
import os
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from temporalio.client import Client
from temporalio.worker import Worker

from biosim_server.api.main import app
from biosim_server.config import get_settings
from biosim_server.io.file_service_S3 import FileServiceS3
from biosim_server.io.file_service_local import FileServiceLocal
from biosim_server.omex_sim.biosim1.biosim_service_rest import BiosimServiceRest
from biosim_server.verify.workflows.omex_verify_workflow import OmexVerifyWorkflowInput, OmexVerifyWorkflowOutput, \
    OmexVerifyWorkflowStatus
from biosim_server.verify.workflows.runs_verify_workflow import RunsVerifyWorkflowInput, RunsVerifyWorkflowOutput, \
    RunsVerifyWorkflowStatus
from tests.workflows.test_verify_workflows import assert_omex_verify_results, assert_runs_verify_results


@pytest.mark.asyncio
async def test_root() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as test_client:
        response = await test_client.get("/")
        assert response.status_code == 200
        assert response.json() == {'docs': 'https://biochecknet.biosimulations.org/docs'}


@pytest.mark.asyncio
async def test_get_output_not_found(omex_verify_workflow_input: OmexVerifyWorkflowInput,
                                    omex_verify_workflow_output: OmexVerifyWorkflowOutput) -> None:

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as test_client:
        # test with non-existent verification_id
        response = await test_client.get(f"/verify_omex/non-existent-id")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_omex_verify_and_get_output_mockS3(omex_verify_workflow_input: OmexVerifyWorkflowInput,
                                         omex_verify_workflow_output: OmexVerifyWorkflowOutput,
                                         file_service_local: FileServiceLocal,
                                         temporal_client: Client,
                                         temporal_verify_worker: Worker,
                                         biosim_service_rest: BiosimServiceRest) -> None:
    root_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    file_path = root_dir / "local_data" / "BIOMD0000000010_tellurium_Negative_feedback_and_ultrasen.omex"
    assert omex_verify_workflow_input.observables is not None
    query_params: dict[str, float | str | list[str]] = {
        "workflow_id_prefix": "verification-",
        "simulators": [sim.simulator for sim in omex_verify_workflow_input.requested_simulators],
        "include_outputs": omex_verify_workflow_input.include_outputs,
        "user_description": omex_verify_workflow_input.user_description,
        "observables": omex_verify_workflow_input.observables,
        "rel_tol": omex_verify_workflow_input.rel_tol,
        "abs_tol": omex_verify_workflow_input.abs_tol
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as test_client:
        with open(file_path, "rb") as file:
            upload_filename = "BIOMD0000000010_tellurium_Negative_feedback_and_ultrasen.omex"
            files = {"uploaded_file": (upload_filename, file, "application/zip")}
            response = await test_client.post("/verify_omex", files=files, params=query_params)
            assert response.status_code == 200

        output = OmexVerifyWorkflowOutput.model_validate(response.json())

        # poll api until job is completed
        while output.workflow_status != OmexVerifyWorkflowStatus.COMPLETED:
            await asyncio.sleep(5)
            response = await test_client.get(f"/verify_omex/{output.workflow_id}")
            if response.status_code == 200:
                output = OmexVerifyWorkflowOutput.model_validate(response.json())
                logging.info(f"polling, job status is: {output.workflow_status}")

        assert_omex_verify_results(observed_results=output, expected_results_template=omex_verify_workflow_output)


@pytest.mark.skipif(len(get_settings().storage_secret) == 0,
                    reason="S3 config STORAGE_SECRET not supplied")
@pytest.mark.asyncio
async def test_omex_verify_and_get_output_S3(omex_verify_workflow_input: OmexVerifyWorkflowInput,
                                         omex_verify_workflow_output: OmexVerifyWorkflowOutput,
                                         file_service_s3: FileServiceS3,
                                         temporal_client: Client,
                                         temporal_verify_worker: Worker,
                                         biosim_service_rest: BiosimServiceRest) -> None:
    root_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    file_path = root_dir / "local_data" / "BIOMD0000000010_tellurium_Negative_feedback_and_ultrasen.omex"
    assert omex_verify_workflow_input.observables is not None
    query_params: dict[str, float | str | list[str]] = {
        "workflow_id_prefix": "verification-",
        "simulators": [sim.simulator for sim in omex_verify_workflow_input.requested_simulators],
        "include_outputs": omex_verify_workflow_input.include_outputs,
        "user_description": omex_verify_workflow_input.user_description,
        "observables": omex_verify_workflow_input.observables,
        "rel_tol": omex_verify_workflow_input.rel_tol,
        "abs_tol": omex_verify_workflow_input.abs_tol
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as test_client:
        with open(file_path, "rb") as file:
            upload_filename = "BIOMD0000000010_tellurium_Negative_feedback_and_ultrasen.omex"
            files = {"uploaded_file": (upload_filename, file, "application/zip")}
            response = await test_client.post("/verify_omex", files=files, params=query_params)
            assert response.status_code == 200

        output = OmexVerifyWorkflowOutput.model_validate(response.json())

        # poll api until job is completed
        while output.workflow_status != OmexVerifyWorkflowStatus.COMPLETED:
            await asyncio.sleep(5)
            response = await test_client.get(f"/verify_omex/{output.workflow_id}")
            if response.status_code == 200:
                output = OmexVerifyWorkflowOutput.model_validate(response.json())
                logging.info(f"polling, job status is: {output.workflow_status}")

        assert_omex_verify_results(observed_results=output, expected_results_template=omex_verify_workflow_output)


@pytest.mark.asyncio
async def test_runs_verify_and_get_output(runs_verify_workflow_input: RunsVerifyWorkflowInput,
                                         runs_verify_workflow_output: RunsVerifyWorkflowOutput,
                                         file_service_local: FileServiceLocal,
                                         temporal_client: Client,
                                         temporal_verify_worker: Worker,
                                         biosim_service_rest: BiosimServiceRest) -> None:
    root_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    file_path = root_dir / "local_data" / "BIOMD0000000010_tellurium_Negative_feedback_and_ultrasen.omex"
    assert runs_verify_workflow_input.observables is not None
    query_params: dict[str, float | str | list[str]] = {
        "workflow_id_prefix": "verification-",
        "biosimulations_run_ids": runs_verify_workflow_input.biosimulations_run_ids,
        "include_outputs": runs_verify_workflow_input.include_outputs,
        "user_description": runs_verify_workflow_input.user_description,
        "observables": runs_verify_workflow_input.observables,
        "rel_tol": runs_verify_workflow_input.rel_tol,
        "abs_tol": runs_verify_workflow_input.abs_tol
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as test_client:
        with open(file_path, "rb") as file:
            response = await test_client.post("/verify_runs", params=query_params)
            assert response.status_code == 200

        output = RunsVerifyWorkflowOutput.model_validate(response.json())

        # poll api until job is completed
        while output.workflow_status != RunsVerifyWorkflowStatus.COMPLETED:
            await asyncio.sleep(5)
            response = await test_client.get(f"/verify_runs/{output.workflow_id}")
            if response.status_code == 200:
                output = RunsVerifyWorkflowOutput.model_validate(response.json())
                logging.info(f"polling, job status is: {output.workflow_status}")

        assert_runs_verify_results(observed_results=output, expected_results_template=runs_verify_workflow_output)
