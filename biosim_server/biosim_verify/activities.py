import logging
from typing import TypeAlias

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel
from temporalio import activity

from biosim_server.biosim_omex import get_cached_omex_file_from_raw
from biosim_server.biosim_runs import BiosimulatorWorkflowRun, Hdf5DataValues, get_hdf5_data_values_activity, \
    GetHdf5DataValuesActivityInput
from biosim_server.biosim_verify import CompareSettings, ComparisonStatistics
from biosim_server.biosim_verify.models import SimulationRunInfo, GenerateStatisticsActivityOutput, RunData
from biosim_server.dependencies import get_file_service, get_database_service, get_omex_database_service

NDArray1b: TypeAlias = np.ndarray[tuple[int], np.dtype[np.bool]]
NDArray1f: TypeAlias = np.ndarray[tuple[int], np.dtype[np.float64]]
NDArray2f: TypeAlias = np.ndarray[tuple[int, int], np.dtype[np.float64]]
NDArray3f: TypeAlias = np.ndarray[tuple[int, int, int], np.dtype[np.float64]]


class GenerateStatisticsActivityInput(BaseModel):
    sim_run_info_list: list[SimulationRunInfo]
    compare_settings: CompareSettings


@activity.defn
async def generate_statistics_activity(gen_stats_input: GenerateStatisticsActivityInput) -> GenerateStatisticsActivityOutput:
    # Gather the data from each run for each dataset
    num_runs = len(gen_stats_input.sim_run_info_list)
    datasets: dict[str, dict[str, Hdf5DataValues]] = {}
    sims_run_data: list[RunData] = []

    for run_index_i in range(num_runs):
        sim_run_info_i = gen_stats_input.sim_run_info_list[run_index_i]
        run_id_i = sim_run_info_i.biosim_sim_run.id
        datasets[run_id_i] = {}
        dataset_names_i = [dataset.name for group in sim_run_info_i.hdf5_file.groups for dataset in group.datasets]
        for dataset_name in dataset_names_i:
            data: Hdf5DataValues = await get_hdf5_data_values_activity(
                GetHdf5DataValuesActivityInput(simulation_run_id=run_id_i, dataset_name=dataset_name))
            datasets[run_id_i][dataset_name] = data
            var_names = sim_run_info_i.hdf5_file.datasets[dataset_name].sedml_labels
            run_data: RunData = RunData(run_id=run_id_i, dataset_name=dataset_name, var_names=var_names, data=data)
            sims_run_data.append(run_data)

    # collect the list of unique dataset names
    dataset_names: set[str] = set()
    for run_index_i in range(num_runs):
        sim_run_info_j = gen_stats_input.sim_run_info_list[run_index_i]
        for group in sim_run_info_j.hdf5_file.groups:
            for dataset in group.datasets:
                 dataset_names.add(dataset.name)
    # get list of unique dataset_vars by reading the metadata within each dataset

    activity.logger.info(f"Found {len(dataset_names)} unique datasets")

    # for each unique dataset name, compare the results from run_i with run_j (where i < j)
    comparison_statistics: dict[
        str, list[list[ComparisonStatistics]]] = {}  # matrix of comparison statistics per dataset
    for dataset_name in dataset_names:
        ds_comparison: list[list[ComparisonStatistics]] = []  # holds comparisons for this dataset
        for run_index_i in range(num_runs):
            sim_run_info_i = gen_stats_input.sim_run_info_list[run_index_i]
            run_id_i = sim_run_info_i.biosim_sim_run.id
            results_i: dict[str, Hdf5DataValues] = datasets[run_id_i]
            labels_i = sim_run_info_i.hdf5_file.datasets[dataset_name].sedml_labels
            data_i: Hdf5DataValues = results_i[dataset_name]
            array_i: NDArray[np.float64] = np.array(data_i.values, dtype=np.float64).reshape(data_i.shape)
            simulation_version_i = f"{sim_run_info_i.biosim_sim_run.simulator_version.id}:{sim_run_info_i.biosim_sim_run.simulator_version.version}"

            ds_comparison_i: list[ComparisonStatistics] = []  # holds comparisons [i,:] for this dataset

            for run_index_j in range(num_runs):
                sim_run_info_j = gen_stats_input.sim_run_info_list[run_index_j]
                run_id_j = sim_run_info_j.biosim_sim_run.id
                results_j: dict[str, Hdf5DataValues] = datasets[run_id_j]
                labels_j = sim_run_info_j.hdf5_file.datasets[dataset_name].sedml_labels
                simulation_version_j = f"{sim_run_info_j.biosim_sim_run.simulator_version.id}:{sim_run_info_j.biosim_sim_run.simulator_version.version}"

                # create a comparison statistics object with default values, add data or error message if needed
                stats_i_j = ComparisonStatistics(simulator_version_i=simulation_version_i,
                                                 simulator_version_j=simulation_version_j, dataset_name=dataset_name,
                                                 var_names=labels_i)  # for runs i,j

                if labels_i != labels_j:
                    stats_i_j.error_message = f"Variables of {simulation_version_i} and {simulation_version_j} do not match, {labels_i} != {labels_j}"
                    activity.logger.error(stats_i_j.error_message)
                    ds_comparison_i.append(stats_i_j)
                    continue

                if dataset_name not in results_i or dataset_name not in results_j:
                    stats_i_j.error_message = f"Dataset {dataset_name} not found in results for {simulation_version_i} or {simulation_version_j}"
                    activity.logger.error(stats_i_j.error_message)
                    ds_comparison_i.append(stats_i_j)
                    continue

                data_j: Hdf5DataValues = results_j[dataset_name]
                array_j: NDArray[np.float64] = np.array(data_j.values, dtype=np.float64).reshape(data_j.shape)  # convert to numpy array

                if array_i.shape != array_j.shape:
                    stats_i_j.error_message = f"Shapes of {simulation_version_i} and {simulation_version_j} do not match, {array_i.shape} != {array_j.shape}"
                    activity.logger.error(stats_i_j.error_message)
                    ds_comparison_i.append(stats_i_j)
                    continue

                # compute statistics
                is_close, score = calc_stats(arr1=array_i, arr2=array_j,
                                             rel_tol=gen_stats_input.compare_settings.rel_tol,
                                             abs_tol_min=gen_stats_input.compare_settings.abs_tol_min,
                                             atol_scale=gen_stats_input.compare_settings.abs_tol_scale)
                is_close_list: list[bool] = is_close.tolist()
                score_list: list[float] = score.tolist()

                activity.logger.info(
                    f"Comparing {simulation_version_j}:run={run_id_i} and {simulation_version_j}:run={run_id_j} for dataset {dataset_name} score: {score} is_close: {is_close}")

                stats_i_j.score = score_list
                stats_i_j.is_close = is_close_list
                stats_i_j.error_message = None
                ds_comparison_i.append(stats_i_j)
            ds_comparison.append(ds_comparison_i)
        comparison_statistics[dataset_name] = ds_comparison

    gen_stats_output = GenerateStatisticsActivityOutput(sims_run_info=gen_stats_input.sim_run_info_list,
                                                        comparison_statistics=comparison_statistics)
    if gen_stats_input.compare_settings.include_outputs:
        gen_stats_output.sim_run_data = sims_run_data

    return gen_stats_output


def calc_stats(arr1: NDArray[np.float64], arr2: NDArray[np.float64],
                     rel_tol: float, abs_tol_min: float, atol_scale: float) -> tuple[NDArray1b, NDArray1f]:
    """
    Calculate the statistics for comparing two arrays.

    computes the same function as hdf5_compare.compare_arrays:

       atol = np.nanmax([atol_min, max1*atol_scale, max2*atol_scale])
       score = np.nanmax(abs(arr1 - arr2) / (atol + rtol * abs(arr2)))
       close = np.allclose(arr1, arr2, rtol=rtol, atol=atol, equal_nan=False)

    but as vectors to retain the score and is_close for each variable
    """
    assert arr1.shape == arr2.shape
    assert len(arr1.shape) == 2

    # atol = np.nanmax([atol_min, max1*atol_scale, max2*atol_scale])
    #
    #   using temporary 3D array to hold the absolute tolerance arrays to get an element-wise max)
    # ... there is probably a simpler way to do this with numpy while still avoiding loops
    max1 = np.nanmax(a=arr1, axis=1)  # shape=(arr1.shape[0],) - max value for each variable in arr1
    max2 = np.nanmax(a=arr2, axis=1)  # shape=(arr2.shape[0],) - max value for each variable in arr2
    abs_tol_arrays = np.zeros((3, arr1.shape[0]))
    abs_tol_arrays[0, :] = np.multiply(np.ones(shape=arr1.shape[0]), abs_tol_min)
    abs_tol_arrays[1, :] = np.multiply(max1, atol_scale)
    abs_tol_arrays[2, :] = np.multiply(max2, atol_scale)
    atol_array = np.max(abs_tol_arrays, axis=0)

    # score = np.nanmax(abs(arr1 - arr2) / (atol + rtol * abs(arr2)))
    rel_tol_array = np.multiply(np.ones(shape=arr1.shape[0]), rel_tol)  # shape=(arr1.shape[0],)
    numerator = np.abs(arr1 - arr2)
    scaled_arr2 = np.multiply(rel_tol_array[:, np.newaxis], np.abs(arr2))
    denominator = np.add(atol_array[:,np.newaxis], scaled_arr2)
    score: NDArray1f = np.nanmax(a=np.divide(numerator, denominator), axis=1)

    # close = np.allclose(arr1, arr2, rtol=rel_tol, atol=atol, equal_nan=False)
    is_close: NDArray1b = np.less(score, 1.0)  # type: ignore
    assert len(is_close.shape) == 1 and len(score.shape) == 1 and is_close.shape == score.shape
    return is_close, score


class CreateBiosimulatorWorkflowRunsActivityInput(BaseModel):
    sim_run_infos: list[SimulationRunInfo]


@activity.defn
async def create_biosimulator_workflow_runs_activity(input: CreateBiosimulatorWorkflowRunsActivityInput) -> list[
    BiosimulatorWorkflowRun]:
    activity.logger.setLevel(level=logging.INFO)
    # invoke action to query or create/save-to-database the list of corresponding BiosimulatorWorkflowRuns
    # 1) see if BiosimulatorWorkflowRuns are already present in our database with same run_ids
    # 2) see if the omex file(s) are already present in database, if not save them
    # 3) create BiosimulatorWorkflowRun and save to database for each run_id
    omex_database_service = get_omex_database_service()
    assert omex_database_service is not None
    database_service = get_database_service()
    assert database_service is not None
    file_service = get_file_service()
    assert file_service is not None

    saved_biosimulator_workflow_runs: list[BiosimulatorWorkflowRun] = []
    for sim_run_info in input.sim_run_infos:
        activity.logger.info(f"Processing run_id {sim_run_info.biosim_sim_run.id}")
        #
        # check if a BiosimulatorWorkflowRun already exists for this run_id
        #
        biosimulator_workflow_runs = await database_service.get_biosimulator_workflow_runs_by_biosim_runid(
            biosim_run_id=sim_run_info.biosim_sim_run.id)
        if len(biosimulator_workflow_runs) > 0:
            if len(biosimulator_workflow_runs) > 1:
                raise Exception( f"Found multiple BiosimulatorWorkflowRuns for biosim_run_id "
                                 f"{sim_run_info.biosim_sim_run.id}")
            saved_biosimulator_workflow_runs.append(biosimulator_workflow_runs[0])
            continue

        #
        # BiosimulatorWorkflowRuns not found - create the OmexFile locally (with hash) and save it to the database
        #
        biosimulations_omex_path = f"simulations/{sim_run_info.biosim_sim_run.id}/archive.omex"
        content: bytes | None = await file_service.get_file_contents(biosimulations_omex_path)
        if content is None:
            raise FileNotFoundError(f"Could not find file for run_id {sim_run_info.biosim_sim_run.id}")
        omex_file = await get_cached_omex_file_from_raw(file_service=file_service, omex_database=omex_database_service,
                                                        omex_file_contents=content,
                                                        filename=biosimulations_omex_path.replace("/", "_"))

        #
        # save the BiosimulatorWorkflowRun to the database
        #
        cache_buster = f"imported biosimulations run_id {sim_run_info.biosim_sim_run.id}"
        biosimulator_workflow_run = BiosimulatorWorkflowRun(
            workflow_id="",
            file_hash_md5=omex_file.file_hash_md5,
            image_digest=sim_run_info.biosim_sim_run.simulator_version.image_digest,
            cache_buster=cache_buster,
            omex_file=omex_file,
            simulator_version=sim_run_info.biosim_sim_run.simulator_version,
            biosim_run=sim_run_info.biosim_sim_run,
            hdf5_file=sim_run_info.hdf5_file
        )
        saved_biosimulator_workflow_run = await database_service.insert_biosimulator_workflow_run(
            sim_workflow_run=biosimulator_workflow_run)
        saved_biosimulator_workflow_runs.append(saved_biosimulator_workflow_run)

    return saved_biosimulator_workflow_runs