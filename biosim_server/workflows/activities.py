from typing import List, Dict

from temporalio import activity

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
