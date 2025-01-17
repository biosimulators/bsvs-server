import os
import uuid
from pathlib import Path

import pytest
from testcontainers.mongodb import MongoDbContainer  # type: ignore

from biosim_server.common.biosim1_client import SourceOmex, BiosimSimulatorSpec
from biosim_server.workflows.verify import OmexVerifyWorkflowOutput, OmexVerifyWorkflowInput, RunsVerifyWorkflowInput, \
    RunsVerifyWorkflowOutput


@pytest.fixture(scope="function")
def omex_verify_workflow_id() -> str:
    return "omex-verification-" + str(uuid.uuid4())


@pytest.fixture(scope="function")
def runs_verify_workflow_id() -> str:
    return "runs-verification-" + str(uuid.uuid4())


@pytest.fixture(scope="function")
def omex_verify_workflow_input() -> OmexVerifyWorkflowInput:
    path = "path/to/omex"
    simulators = [BiosimSimulatorSpec(simulator="copasi"), BiosimSimulatorSpec(simulator="vcell")]
    include_outputs = False
    rel_tol = 1e-6
    abs_tol = 1e-9
    observables = ["time", "concentration"]
    omex_input = OmexVerifyWorkflowInput(source_omex=SourceOmex(omex_s3_file=path, name="name"),
                                         user_description="description", requested_simulators=simulators, include_outputs=include_outputs, rel_tol=rel_tol,
                                         abs_tol=abs_tol, observables=observables)
    return omex_input


@pytest.fixture(scope="function")
def omex_verify_workflow_output(omex_verify_workflow_input: OmexVerifyWorkflowInput,
                                omex_verify_workflow_id: str) -> OmexVerifyWorkflowOutput:
    root_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    with open(root_dir / "local_data" / "OmexVerifyWorkflowOutput_expected.json") as f:
        workflow_output = OmexVerifyWorkflowOutput.model_validate_json(f.read())
        workflow_output.workflow_id = omex_verify_workflow_id
        return workflow_output


@pytest.fixture(scope="function")
def runs_verify_workflow_input() -> RunsVerifyWorkflowInput:
    include_outputs = False
    rel_tol = 1e-6
    abs_tol = 1e-9
    observables = ["time", "concentration"]
    run_ids = ["67817a2e1f52f47f628af971", "67817a2eba5a3f02b9f2938d"]
    omex_input = RunsVerifyWorkflowInput(user_description="description", biosimulations_run_ids=run_ids,
                                         include_outputs=include_outputs, rel_tol=rel_tol, abs_tol=abs_tol, observables=observables)
    return omex_input


@pytest.fixture(scope="function")
def runs_verify_workflow_output(runs_verify_workflow_input: RunsVerifyWorkflowInput,
                                runs_verify_workflow_id: str) -> RunsVerifyWorkflowOutput:
    root_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    with open(root_dir / "local_data" / "RunsVerifyWorkflowOutput_expected.json") as f:
        workflow_output = RunsVerifyWorkflowOutput.model_validate_json(f.read())
        workflow_output.workflow_id = runs_verify_workflow_id
        return workflow_output
