import asyncio
import logging
from datetime import timedelta
from typing import List, Coroutine, Any

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.workflow import ChildWorkflowHandle

# Import activity functions and child workflows
from biosim_server.workflows.activities import upload_model_to_s3, generate_statistics
from biosim_server.workflows.omex_sim_workflow import OmexSimWorkflow, SimulatorWorkflowInput


# Define the Main Workflow
@workflow.defn
class OmexVerifyWorkflow:
    @workflow.run
    async def run(self, model_file_path: str, simulator_names: List[str]) -> str:
        """
        Main workflow to orchestrate SLURM jobs and generate a report.

        Args:
            model_file_path (str): Local path to the model file.
            simulator_names (List[str]): List of simulator names.

        Returns:
            str: Report location or status identifier.
        """
        workflow.logger.setLevel(level=logging.INFO)
        workflow.logger.info("Main workflow started.")

        # Upload model to S3
        s3_model_path: str = await workflow.execute_activity(
            upload_model_to_s3,
            model_file_path,
            start_to_close_timeout=timedelta(seconds=10),  # Activity timeout
            retry_policy=RetryPolicy(maximum_attempts=3),
        )
        workflow.logger.info(f"Model uploaded to S3: {s3_model_path}")

        # Launch child workflows for each simulator
        child_workflows: List[Coroutine[Any, Any, ChildWorkflowHandle]] = []
        for simulator_name in simulator_names:
            child_workflows.append(
                workflow.start_child_workflow(
                    OmexSimWorkflow.run,
                    args=[SimulatorWorkflowInput(model_path=s3_model_path, simulator_name=simulator_name)],
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
        child_results: tuple[Any] = await asyncio.gather(*child_workflows)
        # print types of all members of child_results
        for i in child_results:
            workflow.logger.info(f"child_results member type is {type(i)}")

        workflow.logger.info(f"All child workflows completed: {child_results}")
        workflow.logger.info(f"child_results type is {type(child_results)}")

        real_results: list[str] = []
        for i in child_results:
            workflow.logger.info(f"child_results member type is {type(i)}")
            a: ChildWorkflowHandle = i
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
