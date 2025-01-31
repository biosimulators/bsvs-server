import os
import uuid
from pathlib import Path
from typing import Generator

import pytest
from testcontainers.mongodb import MongoDbContainer  # type: ignore

from biosim_server.common.database.data_models import OmexFile, BiosimulatorVersion
from biosim_server.config import get_local_cache_dir
from biosim_server.workflows.verify import OmexVerifyWorkflowOutput, OmexVerifyWorkflowInput, RunsVerifyWorkflowInput, \
    RunsVerifyWorkflowOutput

temp_data_dir = get_local_cache_dir() / "test_temp_dir"
temp_data_dir.mkdir(exist_ok=True)

@pytest.fixture(scope="session")
def fixture_data_dir() -> Path:
    return Path(os.path.dirname(__file__)) / "local_data"


@pytest.fixture(scope="function")
def omex_verify_workflow_id() -> str:
    return "omex-verification-" + str(uuid.uuid4())


@pytest.fixture(scope="function")
def runs_verify_workflow_id() -> str:
    return "runs-verification-" + str(uuid.uuid4())


@pytest.fixture(scope="function")
def simulator_version_copasi() -> BiosimulatorVersion:
    return BiosimulatorVersion.model_validate_json(
        '{"id":"copasi","name":"COPASI","version":"4.45.296","image":{"url":"ghcr.io/biosimulators/copasi:4.45.296",'
        '"digest":"sha256:7c9cd076eeec494a653353777e42561a2ec9be1bfcc647d0ea84d89fe18999df"}}')


@pytest.fixture(scope="function")
def simulator_version_vcell() -> BiosimulatorVersion:
    return BiosimulatorVersion.model_validate_json(
        '{"id":"vcell","name":"Virtual Cell","version":"7.7.0.13","image":{"url":"ghcr.io/biosimulators/vcell:7.7.0.13",'
        '"digest":"sha256:828b2dc2b983de901c2d68eeb415cb22b46f1db04cdb9e8815d80bf451005216"}}')


@pytest.fixture(scope="function")
def omex_verify_workflow_input(simulator_version_copasi: BiosimulatorVersion,
                               simulator_version_vcell: BiosimulatorVersion) -> OmexVerifyWorkflowInput:
    path = "path/to/omex"
    omex_file = OmexFile(file_hash_md5="hash",
                         uploaded_filename="BIOMD0000000010_tellurium_Negative_feedback_and_ultrasen.omex",
                         file_size=100, omex_gcs_path=path, bucket_name="bucket")
    simulators = [simulator_version_copasi, simulator_version_vcell]
    include_outputs = False
    rel_tol = 1e-4
    abs_tol_min = 1e-3
    abs_tol_scale = 1e-5
    observables = ["time", "concentration"]
    omex_input = OmexVerifyWorkflowInput(omex_file=omex_file, user_description="description",
                                         requested_simulators=simulators, include_outputs=include_outputs,
                                         rel_tol=rel_tol, abs_tol_min=abs_tol_min, abs_tol_scale=abs_tol_scale,
                                         observables=observables)
    return omex_input


@pytest.fixture(scope="function")
def omex_verify_workflow_output_file(fixture_data_dir: Path) -> Path:
    return fixture_data_dir / "OmexVerifyWorkflowOutput_expected.json"


@pytest.fixture(scope="function")
def omex_verify_workflow_output(omex_verify_workflow_input: OmexVerifyWorkflowInput,
                                omex_verify_workflow_output_file: Path,
                                omex_verify_workflow_id: str) -> OmexVerifyWorkflowOutput:
    with open(omex_verify_workflow_output_file) as f:
        workflow_output = OmexVerifyWorkflowOutput.model_validate_json(f.read())
        workflow_output.workflow_id = omex_verify_workflow_id
        return workflow_output


@pytest.fixture(scope="function")
def runs_verify_workflow_input() -> RunsVerifyWorkflowInput:
    include_outputs = False
    rel_tol = 1e-4
    abs_tol_min = 1e-3
    abs_tol_scale = 1e-5
    observables = ["time", "concentration"]
    run_ids = ["67817a2e1f52f47f628af971", "67817a2eba5a3f02b9f2938d"]
    omex_input = RunsVerifyWorkflowInput(user_description="description", biosimulations_run_ids=run_ids,
                                         include_outputs=include_outputs, rel_tol=rel_tol, abs_tol_min=abs_tol_min,
                                         abs_tol_scale=abs_tol_scale, observables=observables)
    return omex_input


@pytest.fixture(scope="function")
def runs_verify_workflow_output_file(fixture_data_dir: Path) -> Path:
    return fixture_data_dir / "RunsVerifyWorkflowOutput_expected.json"


@pytest.fixture(scope="function")
def runs_verify_workflow_output(runs_verify_workflow_input: RunsVerifyWorkflowInput,
                                runs_verify_workflow_output_file: Path,
                                runs_verify_workflow_id: str) -> RunsVerifyWorkflowOutput:
    with open(runs_verify_workflow_output_file) as f:
        workflow_output = RunsVerifyWorkflowOutput.model_validate_json(f.read())
        workflow_output.workflow_id = runs_verify_workflow_id
        return workflow_output


@pytest.fixture(scope="function")
def omex_test_file(fixture_data_dir: Path) -> Path:
    return fixture_data_dir / "BIOMD0000000010_tellurium_Negative_feedback_and_ultrasen.omex"


@pytest.fixture(scope="function")
def hdf5_json_test_file(fixture_data_dir: Path) -> Path:
    return fixture_data_dir / "hdf5_file.json"


@pytest.fixture(scope="function")
def temp_test_data_dir() -> Generator[Path, None, None]:
    temp_data_dir.mkdir(exist_ok=True)

    yield temp_data_dir

    for file in temp_data_dir.iterdir():
        file.unlink()
    temp_data_dir.rmdir()
