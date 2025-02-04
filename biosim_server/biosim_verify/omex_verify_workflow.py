import asyncio
import logging
from datetime import timedelta
from enum import StrEnum
from typing import Any, Optional, Coroutine

from pydantic import BaseModel
from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.workflow import ChildWorkflowHandle

from biosim_server.biosim_runs import BiosimulatorVersion, OmexSimWorkflow, OmexSimWorkflowInput, OmexSimWorkflowOutput
from biosim_server.biosim_verify import CompareSettings
from biosim_server.biosim_omex import OmexFile
from biosim_server.biosim_verify.activities import generate_statistics_activity, GenerateStatisticsActivityInput, \
    GenerateStatisticsActivityOutput, SimulationRunInfo


class OmexVerifyWorkflowStatus(StrEnum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

    def __str__(self) -> str:
        return str(self.value)


class OmexVerifyWorkflowInput(BaseModel):
    omex_file: OmexFile
    requested_simulators: list[BiosimulatorVersion]
    cache_buster: str
    compare_settings: CompareSettings


class OmexVerifyWorkflowOutput(BaseModel):
    workflow_id: str
    compare_settings: CompareSettings
    workflow_status: OmexVerifyWorkflowStatus
    timestamp: str
    workflow_run_id: Optional[str] = None
    workflow_error: Optional[str] = None
    workflow_results: Optional[GenerateStatisticsActivityOutput] = None


@workflow.defn
class OmexVerifyWorkflow:
    verify_input: OmexVerifyWorkflowInput
    verify_output: OmexVerifyWorkflowOutput

    @workflow.init
    def __init__(self, verify_input: OmexVerifyWorkflowInput) -> None:
        self.verify_input = verify_input
        # assert verify_input.workflow_id == workflow.info().workflow_id
        self.verify_output = OmexVerifyWorkflowOutput(
            workflow_id=workflow.info().workflow_id,
            compare_settings=verify_input.compare_settings,
            workflow_run_id=workflow.info().run_id,
            workflow_status=OmexVerifyWorkflowStatus.IN_PROGRESS,
            timestamp=str(workflow.now()))

    @workflow.query(name="get_output")
    def get_omex_sim_workflow_output(self) -> OmexVerifyWorkflowOutput:
        return self.verify_output

    @workflow.run
    async def run(self, verify_input: OmexVerifyWorkflowInput) -> OmexVerifyWorkflowOutput:
        workflow.logger.setLevel(level=logging.INFO)
        workflow.logger.info("Main workflow started.")

        # Launch child workflows for each simulator
        child_workflows: list[
            Coroutine[Any, Any, ChildWorkflowHandle[OmexSimWorkflowInput, OmexSimWorkflowOutput]]] = []
        for simulator_spec in verify_input.requested_simulators:
            child_workflows.append(
                workflow.start_child_workflow(OmexSimWorkflow.run,  # type: ignore
                                              args=[OmexSimWorkflowInput(omex_file=verify_input.omex_file,
                                                                         simulator_version=simulator_spec,
                                                                         cache_buster=verify_input.cache_buster)],
                                              result_type=OmexSimWorkflowOutput,
                                              task_queue="verification_tasks", execution_timeout=timedelta(minutes=10), ))

        workflow.logger.info(f"waiting for {len(child_workflows)} child simulation workflows.")
        # Wait for all child workflows to complete
        child_results: list[ChildWorkflowHandle[OmexSimWorkflowInput, OmexSimWorkflowOutput]] = await asyncio.gather(
            *child_workflows)

        run_data: list[SimulationRunInfo] = []
        for child_result in child_results:
            omex_sim_workflow_output = await child_result
            if not child_result.done():
                raise Exception(
                    "Child workflow did not complete successfully, even after asyncio.gather on all workflows")

            if omex_sim_workflow_output.biosimulator_workflow_run is None:
                continue
            assert omex_sim_workflow_output.biosimulator_workflow_run is not None
            assert omex_sim_workflow_output.biosimulator_workflow_run.biosim_run is not None
            assert omex_sim_workflow_output.biosimulator_workflow_run.hdf5_file is not None
            run_data.append(SimulationRunInfo(biosim_sim_run=omex_sim_workflow_output.biosimulator_workflow_run.biosim_run,
                                              hdf5_file=omex_sim_workflow_output.biosimulator_workflow_run.hdf5_file))

        # Generate comparison report
        generate_statistics_output: GenerateStatisticsActivityOutput = await workflow.execute_activity(
            generate_statistics_activity,
            arg=GenerateStatisticsActivityInput(sim_run_info_list=run_data, compare_settings=verify_input.compare_settings),
            start_to_close_timeout=timedelta(minutes=10),
            retry_policy=RetryPolicy(maximum_attempts=100, backoff_coefficient=2.0,
                                     maximum_interval=timedelta(seconds=10)), )
        self.verify_output.workflow_results = generate_statistics_output

        self.verify_output.workflow_status = OmexVerifyWorkflowStatus.COMPLETED
        return self.verify_output
