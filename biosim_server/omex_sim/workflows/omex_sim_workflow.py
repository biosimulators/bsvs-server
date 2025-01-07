import logging
from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum

from temporalio import workflow
from temporalio.common import RetryPolicy

from biosim_server.omex_sim.biosim1.models import BiosimSimulationRun, BiosimSimulationRunStatus, HDF5File, \
    Hdf5DataValues, SourceOmex, BiosimSimulatorSpec
from biosim_server.omex_sim.workflows.biosim_activities import get_hdf5_metadata, get_hdf5_data
from biosim_server.omex_sim.workflows.biosim_activities import get_sim_run, submit_biosim_sim, \
    SubmitBiosimSimInput, GetSimRunInput, GetHdf5DataInput, GetHdf5MetadataInput


@dataclass
class OmexSimWorkflowInput:
    source_omex: SourceOmex
    simulator_spec: BiosimSimulatorSpec


class OmexSimWorkflowStatus(StrEnum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class OmexSimWorkflowOutput:
    workflow_id: str
    workflow_input: OmexSimWorkflowInput
    workflow_status: OmexSimWorkflowStatus
    biosim_run: BiosimSimulationRun | None = None
    result_s3_path: str | None = None


@workflow.defn
class OmexSimWorkflow:
    sim_input: OmexSimWorkflowInput
    sim_output: OmexSimWorkflowOutput

    @workflow.init
    def __init__(self, sim_input: OmexSimWorkflowInput) -> None:
        self.sim_input = sim_input
        self.sim_output = OmexSimWorkflowOutput(
            workflow_id=workflow.info().workflow_id,
            workflow_input=self.sim_input,
            workflow_status=OmexSimWorkflowStatus.IN_PROGRESS)

    @workflow.query
    async def get_omex_sim_workflow_run(self) -> OmexSimWorkflowOutput:
        return self.sim_output

    @workflow.run
    async def run(self, sim_input: OmexSimWorkflowInput) -> OmexSimWorkflowOutput:
        self.sim_output.workflow_id = workflow.info().workflow_id
        workflow.logger.setLevel(level=logging.DEBUG)
        workflow.logger.info(f"Child workflow started for {sim_input.simulator_spec.simulator}.")

        workflow.logger.info(f"submitting job for simulator {sim_input.simulator_spec.simulator}.")
        submit_biosim_input = SubmitBiosimSimInput(source_omex=sim_input.source_omex,
                                                   simulator_spec=sim_input.simulator_spec)
        self.sim_output.biosim_run = await workflow.execute_activity(
            submit_biosim_sim,
            args=[submit_biosim_input],
            start_to_close_timeout=timedelta(seconds=60),  # Activity timeout
            retry_policy=RetryPolicy(maximum_attempts=1),
        )

        workflow.logger.info(
            f"Job {self.sim_output.biosim_run.id} for {sim_input.simulator_spec.simulator}, "
            f"status is {self.sim_output.biosim_run.status}.")

        while self.sim_output.biosim_run is not None and self.sim_output.biosim_run.status not in [
            BiosimSimulationRunStatus.SUCCEEDED, BiosimSimulationRunStatus.FAILED]:

            await workflow.sleep(2.0)

            self.sim_output.biosim_run = await workflow.execute_activity(
                get_sim_run, args=[GetSimRunInput(biosim_run_id=self.sim_output.biosim_run.id)],
                start_to_close_timeout=timedelta(seconds=60),
                retry_policy=RetryPolicy(maximum_attempts=3)
            )

            workflow.logger.info(
                f"Job {self.sim_output.biosim_run.id} for {sim_input.simulator_spec.simulator}, "
                f"status is {self.sim_output.biosim_run.status}.")

            if self.sim_output.biosim_run.status == BiosimSimulationRunStatus.FAILED:
                self.sim_output.workflow_status = OmexSimWorkflowStatus.FAILED
                return self.sim_output

        hdf5_metadata_json: str = await workflow.execute_activity(
            get_hdf5_metadata,
            args=[GetHdf5MetadataInput(simulation_run_id=self.sim_output.biosim_run.id)],
            start_to_close_timeout=timedelta(seconds=60),  # Activity timeout
            retry_policy=RetryPolicy(maximum_attempts=100, maximum_interval=timedelta(seconds=5), backoff_coefficient=2.0),
        )

        workflow.logger.info(
            f"Simulation run metadata for simulation_run_id: {self.sim_output.biosim_run.id} is {hdf5_metadata_json}")

        hdf5_file: HDF5File = HDF5File.model_validate_json(hdf5_metadata_json)
        results_dict: dict[str, Hdf5DataValues] = {}
        for group in hdf5_file.groups:
            for dataset in group.datasets:
                workflow.logger.info(f"getting data for dataset: {dataset.name}")
                hdf5_data_values: Hdf5DataValues = await workflow.execute_activity(
                    get_hdf5_data,
                    args=[GetHdf5DataInput(simulation_run_id=self.sim_output.biosim_run.id, dataset_name=dataset.name)],
                    start_to_close_timeout=timedelta(seconds=60),
                    retry_policy=RetryPolicy(maximum_attempts=100, maximum_interval=timedelta(seconds=5), backoff_coefficient=2.0)
                )
                results_dict[dataset.name] = hdf5_data_values

        workflow.logger.info(f"retrieved Simulation run data for simulation_run_id: {self.sim_output.biosim_run.id}")

        # Simulate SLURM job monitoring (replace with actual monitoring activity)
        # await workflow.sleep(1)  # Simulating job run time
        self.sim_output.result_s3_path = f"s3://bucket-name/results/{self.sim_output.workflow_input.simulator_spec.simulator}.output"
        self.sim_output.workflow_status = OmexSimWorkflowStatus.COMPLETED
        return self.sim_output