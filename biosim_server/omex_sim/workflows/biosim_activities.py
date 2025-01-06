import logging
import os
from dataclasses import dataclass

from temporalio import activity

from biosim_server.omex_sim.biosim1.biosim_service import BiosimService
from biosim_server.dependencies import get_file_service, get_biosim_service
from biosim_server.io.file_service import FileService
from biosim_server.omex_sim.biosim1.biosim_service_rest import BiosimServiceRest
from biosim_server.omex_sim.biosim1.models import BiosimSimulationRunStatus, SourceOmex, BiosimSimulatorSpec, BiosimSimulationRun, \
    HDF5File, Hdf5DataValues


@dataclass
class CheckRunStatusInput:
    simulation_run_id: str


@activity.defn
async def check_run_status(input: CheckRunStatusInput) -> BiosimSimulationRunStatus:
    activity.logger.setLevel(logging.INFO)
    biosim_service = BiosimServiceRest()
    status: BiosimSimulationRunStatus = await biosim_service.check_biosim_sim_run_status(input.simulation_run_id)
    return status


@dataclass
class SubmitBiosimSimInput:
    source_omex: SourceOmex
    simulator_spec: BiosimSimulatorSpec


@activity.defn
async def submit_biosim_sim(input: SubmitBiosimSimInput) -> BiosimSimulationRun:
    activity.logger.setLevel(logging.INFO)
    biosim_service: BiosimService | None = get_biosim_service()
    if biosim_service is None:
        raise Exception("Biosim service is not initialized")
    file_service: FileService | None = get_file_service()
    if file_service is None:
        raise Exception("File service is not initialized")
    (_, local_omex_path) = await file_service.download_file(input.source_omex.omex_s3_file)
    simulation_run = await biosim_service.run_biosim_sim(local_omex_path, input.source_omex.name,
                                                         input.simulator_spec)
    os.remove(local_omex_path)
    return simulation_run


@dataclass
class GetHdf5MetadataInput:
    simulation_run_id: str


@activity.defn
async def get_hdf5_metadata(input: GetHdf5MetadataInput) -> str:
    activity.logger.setLevel(logging.INFO)
    biosim_service = BiosimServiceRest()
    hdf5_file: HDF5File = await biosim_service.get_hdf5_metadata(input.simulation_run_id)
    return hdf5_file.model_dump_json()


@dataclass
class GetHdf5DataInput:
    simulation_run_id: str
    dataset_name: str


@activity.defn
async def get_hdf5_data(input: GetHdf5DataInput) -> Hdf5DataValues:
    activity.logger.setLevel(logging.INFO)
    biosim_service = BiosimServiceRest()
    hdf5_data_values: Hdf5DataValues = await biosim_service.get_hdf5_data(simulation_run_id=input.simulation_run_id,
                                                                          dataset_name=input.dataset_name)
    return hdf5_data_values
