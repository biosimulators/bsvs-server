import logging
import os
from typing import Optional

from aiohttp import ClientResponseError
from pydantic import BaseModel
from temporalio import activity

from biosim_server.common.biosim1_client import BiosimService, BiosimServiceRest
from biosim_server.common.database.data_models import BiosimSimulationRun, BiosimulatorVersion, \
    BiosimSimulationRunStatus, BiosimulatorWorkflowRun, HDF5File, Hdf5DataValues
from biosim_server.common.storage import FileService
from biosim_server.dependencies import get_file_service, get_biosim_service, get_database_service
from biosim_server.omex_archives import OmexFile


class GetBiosimSimulationRunActivityInput(BaseModel):
    biosim_run_id: str
    abort_on_not_found: Optional[bool] = False


@activity.defn
async def get_biosim_simulation_run_activity(get_sim_run_input: GetBiosimSimulationRunActivityInput) -> BiosimSimulationRun:
    activity.logger.setLevel(logging.INFO)
    biosim_service = BiosimServiceRest()
    try:
        biosim_sim_run: BiosimSimulationRun = await biosim_service.get_sim_run(get_sim_run_input.biosim_run_id)
        return biosim_sim_run
    except ClientResponseError as e:
        if e.status == 404:
            activity.logger.warn(f"Simulation run with id {get_sim_run_input.biosim_run_id} not found.", exc_info=e)
            if get_sim_run_input.abort_on_not_found:
                # return a failed simulation run rather than raising an exception to avoid retrying the activity
                return BiosimSimulationRun(
                    id=get_sim_run_input.biosim_run_id,
                    name="",
                    simulator_version=BiosimulatorVersion(id="", name="", version="", image_url="", image_digest="", created="", updated=""),
                    status=BiosimSimulationRunStatus.RUN_ID_NOT_FOUND,
                    error_message=f"Simulation run {get_sim_run_input.biosim_run_id} not found",
                )
        raise e


class SubmitBiosimSimulationRunActivityInput(BaseModel):
    omex_file: OmexFile
    simulator_version: BiosimulatorVersion


@activity.defn
async def submit_biosim_simulation_run_activity(input: SubmitBiosimSimulationRunActivityInput) -> BiosimSimulationRun:
    activity.logger.setLevel(logging.INFO)
    biosim_service: BiosimService | None = get_biosim_service()
    if biosim_service is None:
        raise Exception("Biosim service is not initialized")
    file_service: FileService | None = get_file_service()
    if file_service is None:
        raise Exception("File service is not initialized")
    (_, local_omex_path) = await file_service.download_file(gcs_path=input.omex_file.omex_gcs_path)
    activity.logger.info(f"Downloaded OMEX file from gcs_path {input.omex_file.omex_gcs_path} to local path {local_omex_path}")
    simulation_run = await biosim_service.run_biosim_sim(local_omex_path=local_omex_path, omex_name=input.omex_file.uploaded_filename,
                                                         simulator_version=input.simulator_version)
    os.remove(local_omex_path)
    activity.logger.info(f"Deleted local OMEX file at {local_omex_path}")
    return simulation_run


class GetHdf5FileActivityInput(BaseModel):
    simulation_run_id: str


@activity.defn
async def get_hdf5_file_activity(input: GetHdf5FileActivityInput) -> HDF5File:
    activity.logger.setLevel(logging.INFO)
    biosim_service = BiosimServiceRest()
    hdf5_file: HDF5File = await biosim_service.get_hdf5_metadata(input.simulation_run_id)
    return hdf5_file


class GetBiosimulatorWorkflowRunsActivityInput(BaseModel):
    file_hash_md5: str
    sim_digest: str
    cache_buster: str


@activity.defn
async def get_biosimulator_workflow_runs_activity(input: GetBiosimulatorWorkflowRunsActivityInput) -> list[BiosimulatorWorkflowRun]:
    activity.logger.setLevel(logging.INFO)
    activity.logger.info(f"Getting biosimulator workflow runs with file hash {input.file_hash_md5} and sim digest {input.sim_digest}")
    database_service = get_database_service()
    assert database_service is not None
    return await database_service.get_biosimulator_workflow_runs(file_hash_md5=input.file_hash_md5, image_digest=input.sim_digest,
                                                                 cache_buster=input.cache_buster)


class SaveBiosimulatorWorkflowRunActivityInput(BaseModel):
    biosim_workflow_run: BiosimulatorWorkflowRun


@activity.defn
async def save_biosimulator_workflow_run_activity(input: SaveBiosimulatorWorkflowRunActivityInput) -> BiosimulatorWorkflowRun:
    activity.logger.setLevel(logging.INFO)
    activity.logger.info(f"Saving biosimulator workflow run with id {input.biosim_workflow_run.database_id}")
    database_service = get_database_service()
    assert database_service is not None
    return await database_service.insert_biosimulator_workflow_run(sim_workflow_run=input.biosim_workflow_run)


class GetHdf5DataValuesActivityInput(BaseModel):
    simulation_run_id: str
    dataset_name: str


@activity.defn
async def get_hdf5_data_values_activity(get_input: GetHdf5DataValuesActivityInput) -> Hdf5DataValues:
    activity.logger.setLevel(logging.INFO)
    biosim_service = BiosimServiceRest()
    hdf5_data_values: Hdf5DataValues = await biosim_service.get_hdf5_data(simulation_run_id=get_input.simulation_run_id,
                                                                          dataset_name=get_input.dataset_name)
    return hdf5_data_values
