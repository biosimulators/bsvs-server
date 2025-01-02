import logging

from temporalio import activity

from biosim_server.biosim1.biosim_service_rest import BiosimServiceRest
from biosim_server.biosim1.models import Hdf5DataValues, HDF5File
from biosim_server.biosim1.models import SimulationRun, SourceOmex, Simulator, SimulationRunStatus


@activity.defn
async def check_run_status(simulation_run_id: str) -> str:
    activity.logger.setLevel(logging.INFO)
    biosim_service = BiosimServiceRest()
    status: SimulationRunStatus = await biosim_service.check_run_status(simulation_run_id)
    return str(status.value)


@activity.defn
async def run_project(source_omex: SourceOmex, simulator: Simulator, simulator_version: str) -> SimulationRun:
    activity.logger.setLevel(logging.INFO)
    biosim_service = BiosimServiceRest()
    simulation_run = await biosim_service.run_project(source_omex, simulator, simulator_version)
    return simulation_run


@activity.defn
async def get_hdf5_metadata(simulation_run_id: str) -> str:
    activity.logger.setLevel(logging.INFO)
    biosim_service = BiosimServiceRest()
    hdf5_file: HDF5File = await biosim_service.get_hdf5_metadata(simulation_run_id)
    return hdf5_file.model_dump_json()


@activity.defn
async def get_hdf5_data(simulation_run_id: str, dataset_name: str) -> Hdf5DataValues:
    activity.logger.setLevel(logging.INFO)
    biosim_service = BiosimServiceRest()
    hdf5_data_values: Hdf5DataValues = await biosim_service.get_hdf5_data(simulation_run_id, dataset_name)
    return hdf5_data_values
