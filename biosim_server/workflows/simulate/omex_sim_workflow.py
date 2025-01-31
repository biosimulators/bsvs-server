import logging
from datetime import timedelta
from enum import StrEnum

from pydantic import BaseModel
from temporalio import workflow
from temporalio.common import RetryPolicy

from biosim_server.common.biosim1_client import HDF5File
from biosim_server.common.database.data_models import OmexFile, BiosimSimulationRun, BiosimulatorVersion, \
    BiosimSimulationRunStatus, BiosimulatorWorkflowRun
from biosim_server.workflows.simulate import get_hdf5_metadata, get_sim_run, submit_biosim_sim, SubmitBiosimSimInput, \
    GetSimRunInput, GetHdf5MetadataInput
from biosim_server.workflows.simulate.biosim_activities import save_biosimulator_workflow_run_activity


class OmexSimWorkflowInput(BaseModel):
    omex_file: OmexFile
    simulator_version: BiosimulatorVersion
    cache_buster: str


class OmexSimWorkflowStatus(StrEnum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class OmexSimWorkflowOutput(BaseModel):
    workflow_id: str
    workflow_status: OmexSimWorkflowStatus
    biosimulator_workflow_run: BiosimulatorWorkflowRun | None = None


@workflow.defn
class OmexSimWorkflow:
    sim_input: OmexSimWorkflowInput
    sim_output: OmexSimWorkflowOutput

    @workflow.init
    def __init__(self, sim_input: OmexSimWorkflowInput) -> None:
        self.sim_input = sim_input
        self.sim_output = OmexSimWorkflowOutput(workflow_id=workflow.info().workflow_id,
                                                workflow_status=OmexSimWorkflowStatus.IN_PROGRESS)

    @workflow.query
    def get_omex_sim_workflow_run(self) -> OmexSimWorkflowOutput:
        return self.sim_output

    @workflow.run
    async def run(self, sim_input: OmexSimWorkflowInput) -> OmexSimWorkflowOutput:
        self.sim_output.workflow_id = workflow.info().workflow_id
        workflow.logger.setLevel(level=logging.DEBUG)
        workflow.logger.info(f"Child workflow started for {sim_input.simulator_version.id}.")

        workflow.logger.info(f"submitting job for simulator {sim_input.simulator_version.id}.")
        submit_biosim_input = SubmitBiosimSimInput(omex_file=sim_input.omex_file,
                                                   simulator_version=sim_input.simulator_version)
        biosim_simulation_run: BiosimSimulationRun = await workflow.execute_activity(
            submit_biosim_sim,
            args=[submit_biosim_input],
            start_to_close_timeout=timedelta(seconds=60),  # Activity timeout
            retry_policy=RetryPolicy(maximum_attempts=1),
        )

        workflow.logger.info(
            f"Job {biosim_simulation_run.id} for {sim_input.simulator_version.id}, "
            f"status is {biosim_simulation_run.status}.")

        while biosim_simulation_run is not None and biosim_simulation_run.status not in [
            BiosimSimulationRunStatus.SUCCEEDED, BiosimSimulationRunStatus.FAILED]:

            await workflow.sleep(2.0)

            biosim_simulation_run = await workflow.execute_activity(
                get_sim_run, args=[GetSimRunInput(biosim_run_id=biosim_simulation_run.id)],
                start_to_close_timeout=timedelta(seconds=60),
                retry_policy=RetryPolicy(maximum_attempts=3)
            )

            workflow.logger.info(
                f"Job {biosim_simulation_run.id} for {sim_input.simulator_version.id}, "
                f"status is {biosim_simulation_run.status}.")

            if biosim_simulation_run.status == BiosimSimulationRunStatus.FAILED:
                self.sim_output.workflow_status = OmexSimWorkflowStatus.FAILED
                return self.sim_output

        hdf5_file: HDF5File = await workflow.execute_activity(
            get_hdf5_metadata,
            args=[GetHdf5MetadataInput(simulation_run_id=biosim_simulation_run.id)],
            start_to_close_timeout=timedelta(seconds=60),  # Activity timeout
            retry_policy=RetryPolicy(maximum_attempts=100, maximum_interval=timedelta(seconds=5), backoff_coefficient=2.0),
        )

        workflow.logger.info(
            f"Simulation run metadata for simulation_run_id: {biosim_simulation_run.id} is {hdf5_file.model_dump_json()}")

        self.sim_output.workflow_status = OmexSimWorkflowStatus.COMPLETED

        biosimulator_workflow_run = BiosimulatorWorkflowRun(workflow_id=self.sim_output.workflow_id,
                                                            file_hash_md5=self.sim_input.omex_file.file_hash_md5,
                                                            image_digest=self.sim_input.simulator_version.image_digest,
                                                            cache_buster=self.sim_input.cache_buster,
                                                            omex_file=self.sim_input.omex_file,
                                                            simulator_version=self.sim_input.simulator_version,
                                                            biosim_run=biosim_simulation_run,
                                                            hdf5_file=hdf5_file)
        saved_biosimulator_workflow_run = await workflow.execute_activity(
            save_biosimulator_workflow_run_activity,
            args=[biosimulator_workflow_run],
            start_to_close_timeout=timedelta(seconds=60),  # Activity timeout
            retry_policy=RetryPolicy(maximum_attempts=100, maximum_interval=timedelta(seconds=5),
                                     backoff_coefficient=2.0),
        )
        self.sim_output.biosimulator_workflow_run = saved_biosimulator_workflow_run
        return self.sim_output
