import logging
from dataclasses import dataclass
from typing import Dict

from temporalio import workflow


@dataclass
class SimulatorWorkflowInput:
    model_path: str
    simulator_name: str


@workflow.defn
class SimulatorWorkflow:
    @workflow.run
    async def run(self, sim_input: SimulatorWorkflowInput) -> Dict[str, str]:
        """
        Child workflow to handle SLURM job submission and monitoring.

        Args:
            sim_input (SimulatorWorkflowInput): Input data for the child workflow.
                Contains the model path and simulator name.

        Returns:
            Dict: Result metadata (e.g., output file location, status).
        """
        workflow.logger.setLevel(level=logging.DEBUG)
        workflow.logger.info(f"Child workflow started for {sim_input.simulator_name}.")

        # Simulate SLURM job submission (activity can replace this)
        job_id = f"job-{sim_input.simulator_name}"
        workflow.logger.info(f"Job {job_id} submitted for {sim_input.simulator_name}.")

        # Simulate SLURM job monitoring (replace with actual monitoring activity)
        await workflow.sleep(1)  # Simulating job run time
        result_path = f"s3://bucket-name/results/{sim_input.simulator_name}.output"

        return {"simulator": sim_input.simulator_name, "result_path": result_path, "status": "completed"}
