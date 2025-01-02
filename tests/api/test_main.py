import pytest
from fastapi.testclient import TestClient
from testcontainers.mongodb import MongoDbContainer  # type: ignore

from biosim_server.api.main import app
from biosim_server.database.models import VerificationOutput


@pytest.mark.asyncio
async def test_root():
    with TestClient(app) as test_client:
        response = test_client.get("/")
        assert response.status_code == 200
        assert response.json() == {'docs': 'https://biochecknet.biosimulations.org/docs'}


# @pytest.mark.asyncio
# async def test_get_output(verification_collection, verification_run_example, database_service):
#     await database_service.insert_verification_run(verification_run_example)
#     verification_id = verification_run_example.job_id
#
#     expected_verification_output = VerificationOutput(
#         job_id=verification_id,
#         timestamp=verification_run_example.timestamp,
#         status=verification_run_example.status,
#         omex_path=verification_run_example.omex_path,
#         requested_simulators=verification_run_example.requested_simulators,
#         observables=verification_run_example.observables,
#         sim_results=None,
#         compare_results=None
#     )
#
#     with TestClient(app) as test_client:
#         response = test_client.get(f"/get-output/{verification_id}")
#         assert response.status_code == 200
#         verification_output = VerificationOutput.model_validate(response.json())
#         assert verification_output.model_dump_json() == expected_verification_output.model_dump_json()
#
#     await database_service.delete_verification_run(verification_id)