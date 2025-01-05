import os
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from temporalio.client import Client
from temporalio.worker import Worker
from testcontainers.mongodb import MongoDbContainer  # type: ignore

from biosim_server.api.main import app
from biosim_server.database.database_service import DatabaseService
from biosim_server.database.models import VerificationOutput, VerificationRun
from biosim_server.io.file_service_local import FileServiceLocal
from tests.fixtures.biosim_service_mock import BiosimServiceMock


@pytest.mark.asyncio
async def test_root() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as test_client:
        response = await test_client.get("/")
        assert response.status_code == 200
        assert response.json() == {'docs': 'https://biochecknet.biosimulations.org/docs'}


@pytest.mark.asyncio
async def test_get_output(verification_run_example: VerificationRun, database_service: DatabaseService) -> None:
    await database_service.insert_verification_run(verification_run_example)
    verification_id = verification_run_example.job_id

    expected_verification_output = VerificationOutput(
        job_id=verification_id,
        timestamp=verification_run_example.timestamp,
        status=verification_run_example.status,
        omex_s3_path=verification_run_example.omex_s3_path,
        requested_simulators=verification_run_example.requested_simulators,
        observables=verification_run_example.observables,
        sim_results=None,
        compare_results=None
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as test_client:
        # test with expected response
        response = await test_client.get(f"/get-output/{verification_id}")
        assert response.status_code == 200
        verification_output = VerificationOutput.model_validate(response.json())
        assert verification_output.model_dump_json() == expected_verification_output.model_dump_json()

        # test with non-existent verification_id
        response = await test_client.get(f"/get-output/non-existent-id")
        assert response.status_code == 404

    await database_service.delete_verification_run(verification_id)


@pytest.mark.asyncio
async def test_verify(verification_run_example: VerificationRun, database_service: DatabaseService,
                      file_service_local: FileServiceLocal, temporal_client: Client,
                      temporal_verify_worker: Worker, biosim_service_mock: BiosimServiceMock) -> None:
    root_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    file_path = root_dir / "local_data" / "BIOMD0000000010_tellurium_Negative_feedback_and_ultrasen.omex"
    query_params = {
        "simulators": verification_run_example.requested_simulators,
        "include_outputs": verification_run_example.include_outputs,
        "observables": verification_run_example.observables,
        "comparison_id": verification_run_example.comparison_id,
        "rTol": verification_run_example.rTol,
        "aTol": verification_run_example.aTol
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as test_client:
        with open(file_path, "rb") as file:
            files = {"uploaded_file": (
                "BIOMD0000000010_tellurium_Negative_feedback_and_ultrasen.omex", file, "application/zip")}
            response = await test_client.post("/verify", files=files, params=query_params)
            assert response.status_code == 200
            verification_run = VerificationRun.model_validate(response.json())

            # set timestamp, job_id, and omex_s3_path before comparison (these are set on server)
            expected_verification_run = verification_run_example.model_copy(deep=True)
            expected_verification_run.timestamp = verification_run.timestamp
            expected_verification_run.job_id = verification_run.job_id
            expected_verification_run.omex_s3_path = verification_run.omex_s3_path
            expected_verification_run.workflow_id = verification_run.workflow_id

            assert expected_verification_run.model_dump_json() == verification_run.model_dump_json()

    # verify it is stored in the database
    verification_run_db = await database_service.get_verification_run(verification_run.job_id)
    assert verification_run_db is not None
    assert verification_run_db.model_dump_json() == expected_verification_run.model_dump_json()

    # verify the omex_s3_path file to the original file_path
    # this works because we are using the local file service instead of S3
    omex_s3_path = Path(verification_run.omex_s3_path)
    assert omex_s3_path.exists()
    with open(omex_s3_path, "rb") as f:
        assert f.read() == file_path.read_bytes()

    # verify the workflow is started
    assert verification_run.workflow_id is not None
    workflow_handle = temporal_client.get_workflow_handle(workflow_id=verification_run.workflow_id)
    assert workflow_handle is not None
    workflow_handle_result = await workflow_handle.result()
    assert workflow_handle_result == "s3://bucket-name/reports/final_report.pdf"
