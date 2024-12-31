from typing import List, Dict

from temporalio import activity


@activity.defn
async def upload_model_to_s3(model_file_path: str) -> str:
    """
    Uploads the model file to S3.

    Args:
        model_file_path (str): Local path to the model file.

    Returns:
        str: S3 path of the uploaded model.
    """
    # Simulate upload logic
    s3_path = f"s3://bucket-name/models/{model_file_path.split('/')[-1]}"
    return s3_path


@activity.defn
async def generate_statistics(run_ids: list[str]) -> str:
    """
    Generates a comparison report from the results.

    Args:
        results (List[Dict]): List of results from simulators.

    Returns:
        str: S3 path or location of the report.
    """
    # Simulate report generation logic
    report_path = "s3://bucket-name/reports/final_report.pdf"
    return report_path
