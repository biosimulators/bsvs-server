import logging
import uuid
from pathlib import Path

import pytest
from temporalio.client import Client, WorkflowHandle
from temporalio.worker import Worker

from biosim_server.config import get_settings
from biosim_server.io.file_service_S3 import FileServiceS3
from biosim_server.io.file_service_local import FileServiceLocal
from biosim_server.omex_sim.biosim1.biosim_service_rest import BiosimServiceRest
from biosim_server.omex_sim.biosim1.models import SourceOmex, BiosimSimulatorSpec, BiosimSimulationRunStatus, \
    BiosimSimulationRun
from biosim_server.omex_sim.workflows.omex_sim_workflow import OmexSimWorkflow, OmexSimWorkflowInput, \
    OmexSimWorkflowOutput, OmexSimWorkflowStatus
from biosim_server.verify.workflows.activities import ComparisonStatistics
from biosim_server.verify.workflows.omex_verify_workflow import OmexVerifyWorkflow, OmexVerifyWorkflowInput, \
    OmexVerifyWorkflowOutput
from biosim_server.verify.workflows.runs_verify_workflow import RunsVerifyWorkflow, RunsVerifyWorkflowInput, \
    RunsVerifyWorkflowOutput
from tests.fixtures.biosim_service_mock import BiosimServiceMock
from tests.fixtures.s3_fixtures import file_service_s3_test_base_path


@pytest.mark.asyncio
async def test_sim_workflow(temporal_client: Client, temporal_verify_worker: Worker,
                            biosim_service_rest: BiosimServiceMock, file_service_local: FileServiceLocal) -> None:
    assert biosim_service_rest is not None

    # set up the omex file to mock S3
    path_from_root = Path("local_data/BIOMD0000000010_tellurium_Negative_feedback_and_ultrasen.omex")
    test_omex_file = Path(__file__).parent.parent.parent / path_from_root
    s3_path = "path/to/model.omex"
    await file_service_local.upload_file(file_path=test_omex_file, s3_path=s3_path)

    sim_spec = BiosimSimulatorSpec(simulator="vcell", version="latest")
    source_omex = SourceOmex(omex_s3_file=s3_path, name="name")
    sim_workflow_input = OmexSimWorkflowInput(source_omex=source_omex, simulator_spec=sim_spec)
    workflow_handle = await temporal_client.start_workflow(OmexSimWorkflow.run, args=[sim_workflow_input],
        id=uuid.uuid4().hex, task_queue="verification_tasks", )
    assert isinstance(workflow_handle, WorkflowHandle)
    workflow_handle_result: OmexSimWorkflowOutput = await workflow_handle.result()
    expected_results = OmexSimWorkflowOutput(workflow_id=workflow_handle_result.workflow_id,
        workflow_input=sim_workflow_input, workflow_status=OmexSimWorkflowStatus.COMPLETED,
        biosim_run=BiosimSimulationRun(id=uuid.uuid4().hex, name=source_omex.name, simulator=sim_spec.simulator,
                                       simulatorVersion=sim_spec.version or "latest", simulatorDigest=uuid.uuid4().hex,
                                       status=BiosimSimulationRunStatus.SUCCEEDED),
        hdf5_file=workflow_handle_result.hdf5_file, )
    if expected_results.biosim_run and workflow_handle_result.biosim_run:
        expected_results.biosim_run.id = workflow_handle_result.biosim_run.id
        expected_results.biosim_run.simulatorVersion = workflow_handle_result.biosim_run.simulatorVersion
        expected_results.biosim_run.simulatorDigest = workflow_handle_result.biosim_run.simulatorDigest
    assert workflow_handle_result == expected_results


@pytest.mark.skipif(len(get_settings().storage_secret) == 0,
                    reason="S3 config STORAGE_SECRET not supplied")
@pytest.mark.asyncio
async def test_omex_verify_workflow_S3(temporal_client: Client, temporal_verify_worker: Worker,
                               omex_verify_workflow_input: OmexVerifyWorkflowInput,
                               omex_verify_workflow_output: OmexVerifyWorkflowOutput,
                               biosim_service_rest: BiosimServiceRest, file_service_s3: FileServiceS3,
                               file_service_s3_test_base_path: Path) -> None:
    assert biosim_service_rest is not None

    # set up the omex file to mock S3 (uploads on the fly)
    path_from_root = Path("local_data/BIOMD0000000010_tellurium_Negative_feedback_and_ultrasen.omex")
    test_omex_file = Path(__file__).parent.parent.parent / path_from_root
    s3_path = str(file_service_s3_test_base_path / "test_verify_workflow" / f"omex {uuid.uuid4().hex}" / test_omex_file.name)

    await file_service_s3.upload_file(file_path=test_omex_file, s3_path=s3_path)
    workflow_id = uuid.uuid4().hex
    logging.info(f"Stored test omex file at {s3_path}")
    omex_verify_workflow_input.source_omex = SourceOmex(omex_s3_file=s3_path, name="name")

    observed_results: OmexVerifyWorkflowOutput = await temporal_client.execute_workflow(
        OmexVerifyWorkflow.run, args=[omex_verify_workflow_input],
        # result_type=OmexVerifyWorkflowOutput,
        id=workflow_id, task_queue="verification_tasks")

    # with open(Path(__file__).parent.parent.parent / "local_data" / "OmexVerifyWorkflowOutput_expected.json", "w") as f:
    #     f.write(observed_results.model_dump_json())

    assert_omex_verify_results(observed_results=observed_results, expected_results_template=omex_verify_workflow_output)


@pytest.mark.asyncio
async def test_omex_verify_workflow_mockS3(temporal_client: Client, temporal_verify_worker: Worker,
                               omex_verify_workflow_input: OmexVerifyWorkflowInput,
                               omex_verify_workflow_output: OmexVerifyWorkflowOutput,
                               biosim_service_rest: BiosimServiceRest, file_service_local: FileServiceLocal) -> None:
    assert biosim_service_rest is not None

    # set up the omex file to mock S3 (uploads on the fly)
    path_from_root = Path("local_data/BIOMD0000000010_tellurium_Negative_feedback_and_ultrasen.omex")
    test_omex_file = Path(__file__).parent.parent.parent / path_from_root
    s3_path = "path/to/model.omex"
    await file_service_local.upload_file(file_path=test_omex_file, s3_path=s3_path)
    workflow_id = uuid.uuid4().hex
    omex_verify_workflow_input.source_omex = SourceOmex(omex_s3_file=s3_path, name="name")

    observed_results: OmexVerifyWorkflowOutput = await temporal_client.execute_workflow(
        OmexVerifyWorkflow.run, args=[omex_verify_workflow_input],
        # result_type=OmexVerifyWorkflowOutput,
        id=workflow_id, task_queue="verification_tasks")

    # with open(Path(__file__).parent.parent.parent / "local_data" / "OmexVerifyWorkflowOutput_expected.json", "w") as f:
    #     f.write(observed_results.model_dump_json())

    assert_omex_verify_results(observed_results=observed_results, expected_results_template=omex_verify_workflow_output)


@pytest.mark.asyncio
async def test_run_verify_workflow(temporal_client: Client, temporal_verify_worker: Worker,
                               runs_verify_workflow_input: RunsVerifyWorkflowInput,
                               runs_verify_workflow_output: RunsVerifyWorkflowOutput,
                               biosim_service_rest: BiosimServiceRest, file_service_s3: FileServiceS3) -> None:
    assert biosim_service_rest is not None

    workflow_id = uuid.uuid4().hex

    observed_results: RunsVerifyWorkflowOutput = await temporal_client.execute_workflow(
        RunsVerifyWorkflow.run, args=[runs_verify_workflow_input],
        # result_type=RunsVerifyWorkflowOutput,
        id=workflow_id, task_queue="verification_tasks")

    # with open(Path(__file__).parent.parent.parent / "local_data" / "RunsVerifyWorkflowOutput_expected.json", "w") as f:
    #     f.write(observed_results.model_dump_json())

    assert_runs_verify_results(observed_results=observed_results, expected_results_template=runs_verify_workflow_output)


def assert_omex_verify_results(observed_results: OmexVerifyWorkflowOutput,
                               expected_results_template: OmexVerifyWorkflowOutput) -> None:

    # customize expected results to match those things which vary between runs
    expected_results = expected_results_template.model_copy(deep=True)
    expected_results.workflow_id = observed_results.workflow_id
    expected_results.workflow_input.source_omex.omex_s3_file = observed_results.workflow_input.source_omex.omex_s3_file
    expected_results.workflow_run_id = observed_results.workflow_run_id
    expected_results.timestamp = observed_results.timestamp
    if expected_results.workflow_results and observed_results.workflow_results:
        for i in range(len(expected_results.workflow_results.sims_run_info)):
            expected_biosim_sim_run = expected_results.workflow_results.sims_run_info[i].biosim_sim_run
            expected_hdf5_file = expected_results.workflow_results.sims_run_info[i].hdf5_file
            result_biosim_sim_run = observed_results.workflow_results.sims_run_info[i].biosim_sim_run
            result_hdf5_file = observed_results.workflow_results.sims_run_info[i].hdf5_file

            expected_hdf5_file.uri = result_hdf5_file.uri
            expected_hdf5_file.id = result_hdf5_file.id
            expected_biosim_sim_run.id = result_biosim_sim_run.id
            expected_biosim_sim_run.simulatorVersion = result_biosim_sim_run.simulatorVersion
            expected_biosim_sim_run.simulatorDigest = result_biosim_sim_run.simulatorDigest

    # compare the comparison statistics separately, seems not to be 100% deterministic
    assert expected_results.workflow_results is not None
    assert observed_results.workflow_results is not None
    ds_names = list(expected_results.workflow_results.comparison_statistics.keys())
    num_simulators = len(expected_results_template.workflow_input.requested_simulators)
    for ds_name in ds_names:
        for i in range(num_simulators):
            for j in range(num_simulators):
                assert observed_results.workflow_results is not None
                observed_compare_i_j: ComparisonStatistics = \
                observed_results.workflow_results.comparison_statistics[ds_name][i][j]
                expected_compare_i_j: ComparisonStatistics = \
                expected_results.workflow_results.comparison_statistics[ds_name][i][j]
                # assert observed_compare_i_j.mse == expected_compare_i_j.mse
                assert observed_compare_i_j.is_close == expected_compare_i_j.is_close
                assert observed_compare_i_j.error_message == expected_compare_i_j.error_message
                assert observed_compare_i_j.simulator_version_i == expected_compare_i_j.simulator_version_i
                assert observed_compare_i_j.simulator_version_j == expected_compare_i_j.simulator_version_j
    expected_results.workflow_results.comparison_statistics = observed_results.workflow_results.comparison_statistics

    # compare everything else which has not been hardwired to match
    assert observed_results == expected_results


def assert_runs_verify_results(observed_results: RunsVerifyWorkflowOutput,
                               expected_results_template: RunsVerifyWorkflowOutput) -> None:

    # customize expected results to match those things which vary between runs
    expected_results = expected_results_template.model_copy(deep=True)
    expected_results.workflow_id = observed_results.workflow_id
    expected_results.workflow_run_id = observed_results.workflow_run_id
    expected_results.timestamp = observed_results.timestamp
    if expected_results.workflow_results and observed_results.workflow_results:
        for i in range(len(expected_results.workflow_results.sims_run_info)):
            expected_biosim_sim_run = expected_results.workflow_results.sims_run_info[i].biosim_sim_run
            expected_hdf5_file = expected_results.workflow_results.sims_run_info[i].hdf5_file
            result_biosim_sim_run = observed_results.workflow_results.sims_run_info[i].biosim_sim_run
            result_hdf5_file = observed_results.workflow_results.sims_run_info[i].hdf5_file

            expected_hdf5_file.uri = result_hdf5_file.uri
            expected_hdf5_file.id = result_hdf5_file.id
            expected_biosim_sim_run.id = result_biosim_sim_run.id
            expected_biosim_sim_run.simulatorVersion = result_biosim_sim_run.simulatorVersion
            expected_biosim_sim_run.simulatorDigest = result_biosim_sim_run.simulatorDigest

    # compare the comparison statistics separately, seems not to be 100% deterministic
    assert expected_results.workflow_results is not None
    assert observed_results.workflow_results is not None
    ds_names = list(expected_results.workflow_results.comparison_statistics.keys())
    num_simulators = len(expected_results_template.workflow_input.biosimulations_run_ids)
    for ds_name in ds_names:
        for i in range(num_simulators):
            for j in range(num_simulators):
                assert observed_results.workflow_results is not None
                observed_compare_i_j: ComparisonStatistics = \
                observed_results.workflow_results.comparison_statistics[ds_name][i][j]
                expected_compare_i_j: ComparisonStatistics = \
                expected_results.workflow_results.comparison_statistics[ds_name][i][j]
                # assert observed_compare_i_j.mse == expected_compare_i_j.mse
                assert observed_compare_i_j.is_close == expected_compare_i_j.is_close
                assert observed_compare_i_j.error_message == expected_compare_i_j.error_message
                assert observed_compare_i_j.simulator_version_i == expected_compare_i_j.simulator_version_i
                assert observed_compare_i_j.simulator_version_j == expected_compare_i_j.simulator_version_j
    expected_results.workflow_results.comparison_statistics = observed_results.workflow_results.comparison_statistics

    # compare everything else which has not been hardwired to match
    assert observed_results == expected_results
