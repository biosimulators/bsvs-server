import logging
from datetime import timedelta
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel
from temporalio import workflow
from temporalio.common import RetryPolicy

from biosim_server.common.biosim1_client import HDF5File
from biosim_server.common.database.data_models import BiosimSimulationRun, BiosimulatorVersion, \
    BiosimSimulationRunStatus
from biosim_server.workflows.simulate import GetSimRunInput, get_hdf5_metadata, GetHdf5MetadataInput, get_sim_run
from biosim_server.workflows.verify import generate_statistics, GenerateStatisticsOutput, GenerateStatisticsInput, \
    SimulationRunInfo


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
    user_description: str
    biosimulations_run_ids: list[str]
    include_outputs: bool
    rel_tol: float
    abs_tol_min: float
    abs_tol_scale: float
    observables: Optional[list[str]] = None


class RunsVerifyWorkflowOutput(BaseModel):
    workflow_id: str
    workflow_input: RunsVerifyWorkflowInput
    workflow_status: RunsVerifyWorkflowStatus
    timestamp: str
    workflow_error: Optional[str] = None
    actual_simulators: Optional[list[BiosimulatorVersion]] = None
    workflow_run_id: Optional[str] = None
    workflow_results: Optional[GenerateStatisticsOutput] = None


@workflow.defn
class RunsVerifyWorkflow:
    verify_input: RunsVerifyWorkflowInput
    verify_output: RunsVerifyWorkflowOutput

    @workflow.init
    def __init__(self, verify_input: RunsVerifyWorkflowInput) -> None:
        self.verify_input = verify_input
        # assert verify_input.workflow_id == workflow.info().workflow_id
        self.verify_output = RunsVerifyWorkflowOutput(workflow_id=workflow.info().workflow_id,
            workflow_input=verify_input, workflow_run_id=workflow.info().run_id,
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
            biosimulation_run = await workflow.execute_activity(get_sim_run,
                args=[GetSimRunInput(biosim_run_id=biosimulation_run_id,
                                     abort_on_not_found=True)],
                start_to_close_timeout=timedelta(seconds=60),
                retry_policy=RetryPolicy(maximum_attempts=30))
            biosimulation_runs.append(biosimulation_run)
            if biosimulation_run.status == BiosimSimulationRunStatus.RUN_ID_NOT_FOUND:
                # important to update the state of the workflow before returning, 
                # so that subsequent workflow queries get the correct state
                self.verify_output = RunsVerifyWorkflowOutput(workflow_id=workflow.info().workflow_id,
                    workflow_input=verify_input, workflow_run_id=workflow.info().run_id,
                    workflow_status=RunsVerifyWorkflowStatus.RUN_ID_NOT_FOUND, timestamp=str(workflow.now()),
                    workflow_error=f"Simulation run with id {biosimulation_run_id} not found.")
                return self.verify_output

        workflow.logger.info(f"verified access to completed run ids {verify_input.biosimulations_run_ids}.")

        # Get the HDF5 metadata for each simulation run
        run_data: list[SimulationRunInfo] = []
        for biosimulation_run in biosimulation_runs:
            hdf5_file: HDF5File = await workflow.execute_activity(
                get_hdf5_metadata,
                args=[GetHdf5MetadataInput(simulation_run_id=biosimulation_run.id)],
                start_to_close_timeout=timedelta(seconds=60),
                retry_policy=RetryPolicy(maximum_attempts=100, maximum_interval=timedelta(seconds=5),
                                         backoff_coefficient=2.0))
            run_data.append(SimulationRunInfo(biosim_sim_run=biosimulation_run, hdf5_file=hdf5_file))

        generate_statistics_input = GenerateStatisticsInput(sim_run_info_list=run_data,
                                                            include_outputs=self.verify_input.include_outputs,
                                                            abs_tol_min=self.verify_input.abs_tol_min,
                                                            abs_tol_scale=self.verify_input.abs_tol_scale,
                                                            rel_tol=self.verify_input.rel_tol)
        # Generate comparison report
        generate_statistics_output: GenerateStatisticsOutput = await workflow.execute_activity(
            generate_statistics,
            arg=generate_statistics_input,
            start_to_close_timeout=timedelta(minutes=10),
            retry_policy=RetryPolicy(maximum_attempts=100, backoff_coefficient=2.0,
                                     maximum_interval=timedelta(seconds=10)))
        self.verify_output.workflow_results = generate_statistics_output
        self.verify_output.workflow_status = RunsVerifyWorkflowStatus.COMPLETED
        return self.verify_output
