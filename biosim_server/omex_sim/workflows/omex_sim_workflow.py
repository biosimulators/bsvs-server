import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Dict

from temporalio import workflow
from temporalio.common import RetryPolicy

from biosim_server.omex_sim.biosim1.models import SimulationRun, SimulationRunStatus, HDF5File, Hdf5DataValues, \
    SourceOmex, SimulatorSpec
from biosim_server.omex_sim.workflows.biosim_activities import check_run_status, run_project, RunProjectInput, \
    CheckRunStatusInput, GetHdf5DataInput, GetHdf5MetadataInput
from biosim_server.omex_sim.workflows.biosim_activities import get_hdf5_metadata, get_hdf5_data


@dataclass
class OmexSimWorkflowInput:
    source_omex: SourceOmex
    simulator_spec: SimulatorSpec


@workflow.defn
class OmexSimWorkflow:
    @workflow.run
    async def run(self, sim_input: OmexSimWorkflowInput) -> Dict[str, str]:
        """
        Child workflow to handle SLURM job submission and monitoring.

        Args:
            sim_input (OmexSimWorkflowInput): Input data for the child workflow.
                Contains the model path and simulator name.

        Returns:
            Dict: Result metadata (e.g., output file location, status).
        """
        workflow.logger.setLevel(level=logging.DEBUG)
        workflow.logger.info(f"Child workflow started for {sim_input.simulator_spec.simulator}.")

        workflow.logger.info(f"submitting job for simulator {sim_input.simulator_spec.simulator}.")
        sim_run: SimulationRun = await workflow.execute_activity(
            run_project,
            args=[RunProjectInput(source_omex=sim_input.source_omex, simulator_spec=sim_input.simulator_spec)],
            start_to_close_timeout=timedelta(seconds=10),  # Activity timeout
            retry_policy=RetryPolicy(maximum_attempts=3),
        )

        
        
        # Simulate SLURM job submission (activity can replace this)
        # job_id = f"job-{sim_input.simulator_name}"
        job_id = "61fea4968edd56f301e6a803"
        workflow.logger.info(f"Job {job_id} submitted for {sim_input.simulator_spec.simulator}.")

        workflow.logger.info(f"getting simulation run status for simulation_run_id: {job_id}")
        status_str: str = await workflow.execute_activity(
            check_run_status,
            args=[CheckRunStatusInput(simulation_run_id=job_id)],
            start_to_close_timeout=timedelta(seconds=10),  # Activity timeout
            retry_policy=RetryPolicy(maximum_attempts=3),
        )
        status = SimulationRunStatus.from_str(status_str)
        workflow.logger.info(f"Simulation run status for simulation_run_id: {job_id} is {status.value}")

        hdf5_metadata_json: str = await workflow.execute_activity(
            get_hdf5_metadata,
            args=[GetHdf5MetadataInput(simulation_run_id=job_id)],
            start_to_close_timeout=timedelta(seconds=10),  # Activity timeout
            retry_policy=RetryPolicy(maximum_attempts=3),
        )

        workflow.logger.info(f"Simulation run metadata for simulation_run_id: {job_id} is {hdf5_metadata_json}")

        hdf5_file: HDF5File = HDF5File.model_validate_json(hdf5_metadata_json)
        results_dict: dict[str, Hdf5DataValues] = {}
        for group in hdf5_file.groups:
            for dataset in group.datasets:
                workflow.logger.info(f"getting data for dataset: {dataset.name}")
                hdf5_data_values: Hdf5DataValues = await workflow.execute_activity(
                    get_hdf5_data,
                    args=[GetHdf5DataInput(simulation_run_id=job_id, dataset_name=dataset.name)],
                    start_to_close_timeout=timedelta(seconds=10),  # Activity timeout
                    retry_policy=RetryPolicy(maximum_attempts=3),
                )
                results_dict[dataset.name] = hdf5_data_values

        workflow.logger.info(f"retrieved Simulation run data for simulation_run_id: {job_id}")

        # Simulate SLURM job monitoring (replace with actual monitoring activity)
        # await workflow.sleep(1)  # Simulating job run time
        result_path = f"s3://bucket-name/results/{sim_input.simulator_spec.simulator}.output"

        return {"simulator": sim_input.simulator_spec.simulator, "result_path": result_path, "status": "completed"}
