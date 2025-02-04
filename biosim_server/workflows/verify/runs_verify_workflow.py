import logging
from datetime import timedelta
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel
from temporalio import workflow
from temporalio.common import RetryPolicy

from biosim_server.biosim_runs import BiosimSimulationRun, BiosimSimulationRunStatus, BiosimulatorWorkflowRun, HDF5File, \
    GetBiosimSimulationRunActivityInput, get_hdf5_file_activity, GetHdf5FileActivityInput, get_biosim_simulation_run_activity
from biosim_server.biosim_verify import CompareSettings
from biosim_server.workflows.verify import generate_statistics_activity, GenerateStatisticsActivityOutput, \
    GenerateStatisticsActivityInput, SimulationRunInfo
from biosim_server.workflows.verify.activities import create_biosimulator_workflow_runs_activity, \
    CreateBiosimulatorWorkflowRunsActivityInput


class RunsVerifyWorkflowStatus(StrEnum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RUN_ID_NOT_FOUND = "RUN_ID_NOT_FOUND"

    @property
    def is_done(self) -> bool:
        return self in [RunsVerifyWorkflowStatus.COMPLETED, RunsVerifyWorkflowStatus.FAILED,
                        RunsVerifyWorkflowStatus.RUN_ID_NOT_FOUND]


class RunsVerifyWorkflowInput(BaseModel):
    biosimulations_run_ids: list[str]
    compare_settings: CompareSettings


class RunsVerifyWorkflowOutput(BaseModel):
    workflow_id: str
    compare_settings: CompareSettings
    workflow_status: RunsVerifyWorkflowStatus
    timestamp: str
    workflow_run_id: Optional[str] = None
    workflow_error: Optional[str] = None
    workflow_results: Optional[GenerateStatisticsActivityOutput] = None


@workflow.defn
class RunsVerifyWorkflow:
    verify_input: RunsVerifyWorkflowInput
    verify_output: RunsVerifyWorkflowOutput

    @workflow.init
    def __init__(self, verify_input: RunsVerifyWorkflowInput) -> None:
        self.verify_input = verify_input
        # assert verify_input.workflow_id == workflow.info().workflow_id
        self.verify_output = RunsVerifyWorkflowOutput(workflow_id=workflow.info().workflow_id,
            compare_settings=verify_input.compare_settings, workflow_run_id=workflow.info().run_id,
            workflow_status=RunsVerifyWorkflowStatus.IN_PROGRESS, timestamp=str(workflow.now()))

    @workflow.query(name="get_output")
    def get_runs_sim_workflow_output(self) -> RunsVerifyWorkflowOutput:
        return self.verify_output

    @workflow.run
    async def run(self, verify_input: RunsVerifyWorkflowInput) -> RunsVerifyWorkflowOutput:
        workflow.logger.setLevel(level=logging.INFO)
        workflow.logger.info("Main workflow started.")

        # verify biosimulation runs are valid and complete and retrieve Simulation results metadata
        biosimulation_runs: list[BiosimSimulationRun] = []
        for biosimulation_run_id in verify_input.biosimulations_run_ids:
            biosimulation_run = await workflow.execute_activity(get_biosim_simulation_run_activity,
                                                                args=[GetBiosimSimulationRunActivityInput(biosim_run_id=biosimulation_run_id,
                                                                                                          abort_on_not_found=True)],
                                                                start_to_close_timeout=timedelta(seconds=60),
                                                                retry_policy=RetryPolicy(maximum_attempts=30))
            biosimulation_runs.append(biosimulation_run)
            if biosimulation_run.status == BiosimSimulationRunStatus.RUN_ID_NOT_FOUND:
                # important to update the state of the workflow before returning, 
                # so that subsequent workflow queries get the correct state
                self.verify_output = RunsVerifyWorkflowOutput(workflow_id=workflow.info().workflow_id,
                    compare_settings=verify_input.compare_settings, workflow_run_id=workflow.info().run_id,
                    workflow_status=RunsVerifyWorkflowStatus.RUN_ID_NOT_FOUND, timestamp=str(workflow.now()),
                    workflow_error=f"Simulation run with id {biosimulation_run_id} not found.")
                return self.verify_output

        workflow.logger.info(f"verified access to completed run ids {verify_input.biosimulations_run_ids}.")

        # Get the HDF5 metadata for each simulation run
        run_data: list[SimulationRunInfo] = []

        for biosimulation_run in biosimulation_runs:
            hdf5_file: HDF5File = await workflow.execute_activity(
                get_hdf5_file_activity,
                args=[GetHdf5FileActivityInput(simulation_run_id=biosimulation_run.id)],
                start_to_close_timeout=timedelta(seconds=60),
                retry_policy=RetryPolicy(maximum_attempts=100, maximum_interval=timedelta(seconds=5),
                                         backoff_coefficient=2.0))
            run_data.append(SimulationRunInfo(biosim_sim_run=biosimulation_run, hdf5_file=hdf5_file))

        simulator_workflow_runs: list[BiosimulatorWorkflowRun] = await workflow.execute_activity(
            create_biosimulator_workflow_runs_activity,
            args=[CreateBiosimulatorWorkflowRunsActivityInput(sim_run_infos=run_data)],
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=RetryPolicy(maximum_attempts=100, maximum_interval=timedelta(seconds=5),
                                     backoff_coefficient=2.0))

        generate_statistics_input = GenerateStatisticsActivityInput(sim_run_info_list=run_data,
                                                                    compare_settings=self.verify_input.compare_settings)
        # Generate comparison report
        generate_statistics_output: GenerateStatisticsActivityOutput = await workflow.execute_activity(
            generate_statistics_activity,
            arg=generate_statistics_input,
            start_to_close_timeout=timedelta(minutes=10),
            retry_policy=RetryPolicy(maximum_attempts=100, backoff_coefficient=2.0,
                                     maximum_interval=timedelta(seconds=10)))
        self.verify_output.workflow_results = generate_statistics_output
        self.verify_output.workflow_status = RunsVerifyWorkflowStatus.COMPLETED
        return self.verify_output


