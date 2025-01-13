import asyncio
import logging
from datetime import timedelta
from enum import StrEnum
from typing import Any, Optional

from pydantic import BaseModel
from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.workflow import ChildWorkflowHandle

from biosim_server.omex_sim.biosim1.models import BiosimSimulatorSpec, SourceOmex, Hdf5DataValues
from biosim_server.omex_sim.workflows.omex_sim_workflow import OmexSimWorkflow, OmexSimWorkflowInput
from biosim_server.verify.workflows.activities import generate_statistics


class OmexVerifyWorkflowStatus(StrEnum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class OmexVerifyWorkflowInput(BaseModel):
    workflow_id: str
    source_omex: SourceOmex
    user_description: str
    requested_simulators: list[BiosimSimulatorSpec]
    include_outputs: bool
    rTol: float
    aTol: float
    observables: Optional[list[str]] = None


class SimulatorRMSE(BaseModel):
    simulator1: str
    simulator2: str
    rmse_scores: dict[str, float]


class OmexVerifyWorkflowResults(BaseModel):
    sim_results: Optional[list[dict[str, Hdf5DataValues]]] = None
    compare_results: Optional[list[SimulatorRMSE]] = None


class OmexVerifyWorkflowOutput(BaseModel):
    workflow_input: OmexVerifyWorkflowInput
    workflow_status: OmexVerifyWorkflowStatus
    timestamp: str
    actual_simulators: Optional[list[BiosimSimulatorSpec]] = None
    workflow_run_id: Optional[str] = None
    workflow_results: Optional[OmexVerifyWorkflowResults] = None


@workflow.defn
class OmexVerifyWorkflow:
    verify_input: OmexVerifyWorkflowInput
    verify_output: OmexVerifyWorkflowOutput

    @workflow.init
    def __init__(self, verify_input: OmexVerifyWorkflowInput) -> None:
        self.verify_input = verify_input
        # assert verify_input.workflow_id == workflow.info().workflow_id
        self.verify_output = OmexVerifyWorkflowOutput(
            workflow_input=verify_input,
            workflow_run_id=workflow.info().run_id,
            workflow_status=OmexVerifyWorkflowStatus.IN_PROGRESS,
            timestamp=str(workflow.now()))

    @workflow.query(name="get_output")
    async def get_omex_sim_workflow_output(self) -> OmexVerifyWorkflowOutput:
        return self.verify_output

    @workflow.run
    async def run(self, verify_input: OmexVerifyWorkflowInput) -> OmexVerifyWorkflowOutput:
        workflow.logger.setLevel(level=logging.INFO)
        workflow.logger.info("Main workflow started.")

        # Launch child workflows for each simulator
        child_workflows: list[Any] = []
        for simulator_spec in verify_input.requested_simulators:
            child_workflows.append(
                workflow.start_child_workflow(
                    OmexSimWorkflow.run,
                    args=[OmexSimWorkflowInput(
                        source_omex=verify_input.source_omex,
                        simulator_spec=simulator_spec)],
                    task_queue="verification_tasks",
                    execution_timeout=timedelta(minutes=10),
                )
            )

        workflow.logger.info(f"Launched {len(child_workflows)} child workflows.")

        # # print types of all members of child_workflows
        # for i in child_workflows:
        #     workflow.logger.info(f"waiting for child workflow type is {type(i)}")
        #     await i
        #

        # Wait for all child workflows to complete
        child_results: list[ChildWorkflowHandle[dict[str, str], Any]] = await asyncio.gather(*child_workflows)
        # print types of all members of child_results
        for i in child_results:
            workflow.logger.info(f"child_results member type is {type(i)}")

        workflow.logger.info(f"All child workflows completed: {child_results}")
        workflow.logger.info(f"child_results type is {type(child_results)}")

        real_results: list[str] = []
        for i in child_results:
            workflow.logger.info(f"child_results member type is {type(i)}")
            a: ChildWorkflowHandle[dict[str,str], Any] = i
            real_results.append(str(await a))
            workflow.logger.info(f"real_results member type is {type(a.result())}")

        # Generate comparison report
        report_location = await workflow.execute_activity(
            generate_statistics,
            arg=real_results,
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(maximum_attempts=100, backoff_coefficient=2.0, maximum_interval=timedelta(seconds=10)),
        )
        workflow.logger.info(f"Report generated at: {report_location}")

        self.verify_output.workflow_status = OmexVerifyWorkflowStatus.COMPLETED
        return self.verify_output
