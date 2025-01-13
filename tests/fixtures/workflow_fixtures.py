import uuid
from datetime import UTC, datetime

import pytest
from testcontainers.mongodb import MongoDbContainer  # type: ignore

from biosim_server.omex_sim.biosim1.models import SourceOmex, BiosimSimulatorSpec
from biosim_server.verify.workflows.omex_verify_workflow import OmexVerifyWorkflowOutput, OmexVerifyWorkflowInput, \
    OmexVerifyWorkflowStatus


@pytest.fixture(scope="function")
def verify_workflow_id() -> str:
    return "verification-" + str(uuid.uuid4())

@pytest.fixture(scope="function")
def verify_workflow_input(verify_workflow_id: str) -> OmexVerifyWorkflowInput:
    path = "path/to/omex"
    simulators = [BiosimSimulatorSpec(simulator="copasi"), BiosimSimulatorSpec(simulator="vcell")]
    include_outputs = True
    rTol = 1e-6
    aTol = 1e-9
    observables = ["time", "concentration"]
    omex_input = OmexVerifyWorkflowInput(
        workflow_id=verify_workflow_id,
        source_omex=SourceOmex(omex_s3_file=path, name="name"),
        user_description="description",
        requested_simulators=simulators,
        include_outputs=include_outputs,
        rTol=rTol,
        aTol=aTol,
        observables=observables
    )
    return omex_input


@pytest.fixture(scope="function")
def verify_workflow_output(verify_workflow_input: OmexVerifyWorkflowInput) -> OmexVerifyWorkflowOutput:
    timestamp = str(datetime.now(UTC))
    run_id = "run_id-" + str(uuid.uuid4())
    return OmexVerifyWorkflowOutput(
        workflow_input=verify_workflow_input,
        workflow_status=OmexVerifyWorkflowStatus.PENDING,
        timestamp=timestamp,
        workflow_run_id=run_id
    )


