import asyncio
import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.workflow import ChildWorkflowHandle

from biosim_server.omex_sim.biosim1.models import SimulatorSpec, SourceOmex
from biosim_server.omex_sim.workflows.omex_sim_workflow import OmexSimWorkflow, OmexSimWorkflowInput
from biosim_server.omex_verify.workflows.activities import generate_statistics


@dataclass
class OmexVerifyWorkflowInput:
    source_omex: SourceOmex
    simulator_specs: list[SimulatorSpec]


# Define the Main Workflow
@workflow.defn
class OmexVerifyWorkflow:
    @workflow.run
    async def run(self, omex_verify_workflow_input: OmexVerifyWorkflowInput) -> str:
        """
        Main workflow to orchestrate SLURM jobs and generate a report.

        Args:
            model_file_path (str): Local path to the model file.
            simulator_names (list[str]): list of simulator names.

        Returns:
            str: Report location or status identifier.
        """
        workflow.logger.setLevel(level=logging.INFO)
        workflow.logger.info("Main workflow started.")

        # Launch child workflows for each simulator
        child_workflows: list[Any] = []
        for simulator_spec in omex_verify_workflow_input.simulator_specs:
            child_workflows.append(
                workflow.start_child_workflow(
                    OmexSimWorkflow.run,
                    args=[OmexSimWorkflowInput(
                        source_omex=omex_verify_workflow_input.source_omex,
                        simulator_spec=simulator_spec)],
                    task_queue="verification_tasks",
                    execution_timeout=timedelta(seconds=10),
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
            retry_policy=RetryPolicy(maximum_attempts=3),
        )
        workflow.logger.info(f"Report generated at: {report_location}")

        # Return the report location
        return report_location
