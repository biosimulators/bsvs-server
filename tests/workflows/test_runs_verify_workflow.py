import asyncio
import logging
import uuid
from pathlib import Path

import pytest
from temporalio.client import Client
from temporalio.worker import Worker

from biosim_server.common.biosim1_client import BiosimServiceRest
from biosim_server.common.storage import FileServiceGCS
from biosim_server.workflows.verify import RunsVerifyWorkflow, RunsVerifyWorkflowInput, \
    RunsVerifyWorkflowOutput, RunsVerifyWorkflowStatus
from biosim_server.common.database.data_models import ComparisonStatistics


@pytest.mark.asyncio
async def test_run_verify_workflow(temporal_client: Client, temporal_verify_worker: Worker,
                               runs_verify_workflow_input: RunsVerifyWorkflowInput,
                               runs_verify_workflow_output: RunsVerifyWorkflowOutput,
                               runs_verify_workflow_output_file: Path,
                               biosim_service_rest: BiosimServiceRest, file_service_gcs: FileServiceGCS) -> None:
    assert biosim_service_rest is not None

    workflow_id = uuid.uuid4().hex

    observed_results: RunsVerifyWorkflowOutput = await temporal_client.execute_workflow(
        RunsVerifyWorkflow.run, args=[runs_verify_workflow_input],
        # result_type=RunsVerifyWorkflowOutput,
        id=workflow_id, task_queue="verification_tasks")

    # uncomment to update fixture for future tests
    # with open(runs_verify_workflow_output_file, "w") as f:
    #     f.write(observed_results.model_dump_json(indent=2))

    assert_runs_verify_results(observed_results=observed_results, expected_results_template=runs_verify_workflow_output)


@pytest.mark.asyncio
async def test_run_verify_workflow_not_found_execute(temporal_client: Client, temporal_verify_worker: Worker,
                               runs_verify_workflow_input: RunsVerifyWorkflowInput,
                               runs_verify_workflow_output: RunsVerifyWorkflowOutput,
                               biosim_service_rest: BiosimServiceRest, file_service_gcs: FileServiceGCS) -> None:
    assert biosim_service_rest is not None

    workflow_id = uuid.uuid4().hex

    runs_verify_workflow_input = runs_verify_workflow_input.model_copy(deep=True)
    runs_verify_workflow_input.biosimulations_run_ids[0] = "bad_id"

    observed_results: RunsVerifyWorkflowOutput = await temporal_client.execute_workflow(
        RunsVerifyWorkflow.run, args=[runs_verify_workflow_input], id=workflow_id, task_queue="verification_tasks")
    assert observed_results.workflow_status == RunsVerifyWorkflowStatus.RUN_ID_NOT_FOUND
    assert observed_results.workflow_error == "Simulation run with id bad_id not found."


@pytest.mark.asyncio
async def test_run_verify_workflow_not_found_poll(temporal_client: Client, temporal_verify_worker: Worker,
                               runs_verify_workflow_input: RunsVerifyWorkflowInput,
                               runs_verify_workflow_output: RunsVerifyWorkflowOutput,
                               biosim_service_rest: BiosimServiceRest, file_service_gcs: FileServiceGCS) -> None:
    assert biosim_service_rest is not None

    workflow_id = uuid.uuid4().hex

    runs_verify_workflow_input = runs_verify_workflow_input.model_copy(deep=True)
    runs_verify_workflow_input.biosimulations_run_ids[0] = "bad_id"

    handle = await temporal_client.start_workflow(
        RunsVerifyWorkflow.run,
        args=[runs_verify_workflow_input],
        id=workflow_id, task_queue="verification_tasks")

    # poll until the workflow completes using workflow query mechanism
    observed_results: RunsVerifyWorkflowOutput = await handle.query("get_output", result_type=RunsVerifyWorkflowOutput)
    while not observed_results.workflow_status.is_done:
        await asyncio.sleep(1)
        observed_results = await handle.query("get_output", result_type=RunsVerifyWorkflowOutput)
        logging.log(logging.INFO, f"Workflow status: {observed_results.workflow_status}")

    assert observed_results.workflow_status == RunsVerifyWorkflowStatus.RUN_ID_NOT_FOUND
    assert observed_results.workflow_error == "Simulation run with id bad_id not found."


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
            expected_biosim_sim_run.simulator_version = result_biosim_sim_run.simulator_version

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
