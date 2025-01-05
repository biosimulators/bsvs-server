import json
import logging
import os
from dataclasses import asdict
from typing import BinaryIO, Union, AsyncGenerator

import aiofiles
import aiohttp
from typing_extensions import override

from biosim_server.omex_sim.biosim1.biosim_service import BiosimService
from biosim_server.omex_sim.biosim1.models import SimulationRun, SimulationRunApiRequest, HDF5File, \
    Hdf5DataValues, SimulationRunStatus, SimulatorSpec

logger = logging.getLogger(__name__)


class BiosimServiceRest(BiosimService):
    @override
    async def check_run_status(self, simulation_run_id: str) -> SimulationRunStatus:
        api_base_url = os.environ.get('API_BASE_URL') or "https://api.biosimulations.org"
        assert (api_base_url is not None)

        async with aiohttp.ClientSession() as session:
            async with session.get(api_base_url + "/runs/" + simulation_run_id) as resp:
                resp.raise_for_status()
                getrun_dict = await resp.json()

        result = str(getrun_dict['status'])
        return SimulationRunStatus(result)

    @override
    async def run_project(self, local_omex_path: str, omex_name: str, simulator_spec: SimulatorSpec) -> SimulationRun:
        """
        This function runs the project on biosimulations.
        """
        api_base_url = str(os.environ.get('API_BASE_URL')) or "https://api.biosimulations.org"

        simulation_run_request = SimulationRunApiRequest(
            name=omex_name,
            simulator_spec=simulator_spec,
            maxTime=600,
        )

        print(local_omex_path)
        async with (aiohttp.ClientSession() as session):
            with open(local_omex_path, 'rb') as f:
                multipart_form_data: dict[str, Union[tuple[str, BinaryIO, str], tuple[None, str]]] = {
                    'file': (omex_name + '.omex', f, "application/zip"),
                    'simulationRun': (None, json.dumps(asdict(simulation_run_request))),
                }
                async with session.post(api_base_url + '/runs', data=multipart_form_data) as resp:
                    resp.raise_for_status()
                    res = await resp.json()

        logger.info(f"Ran {omex_name} on biosimulations with simulation id: {res['id']}")
        logger.info(f"results: {res}")
        simulation_id = res["id"]

        if simulator_spec.version is None:
            simulator_spec.version = res['simulatorVersion']

        sim_run = SimulationRun(
            simulator_spec=simulator_spec,
            simulation_id=simulation_id,
            project_id=omex_name,
            status=res['status']
        )

        logger.info("Ran " + omex_name + " on biosimulations with simulation id: " + simulation_id)
        logger.info("View:", api_base_url + "/runs/" + simulation_id)
        return sim_run

    @override
    async def get_hdf5_metadata(self, simulation_run_id: str) -> HDF5File:
        api_base_url = os.environ.get('SIMDATA_API_BASE_URL') or "https://simdata.api.biosimulations.org"
        assert (api_base_url is not None)

        async with aiohttp.ClientSession() as session:
            url = f"{api_base_url}/datasets/{simulation_run_id}/metadata"
            async with session.get(url) as resp:
                resp.raise_for_status()
                hdf5_metadata_json = await resp.text()
                hdf5_file: HDF5File = HDF5File.model_validate_json(hdf5_metadata_json)
                return hdf5_file

    @override
    async def get_hdf5_data(self, simulation_run_id: str, dataset_name: str) -> Hdf5DataValues:
        api_base_url = os.environ.get('SIMDATA_API_BASE_URL') or "https://simdata.api.biosimulations.org"
        assert (api_base_url is not None)

        async with aiohttp.ClientSession() as session:
            url = f"{api_base_url}/datasets/{simulation_run_id}/data"
            async with session.get(url, params={"dataset_name": dataset_name}) as resp:
                resp.raise_for_status()
                hdf5_data_dict = await resp.json()
                logger.info(f"Got data for dataset: {dataset_name}")
                hdf5_data_values = Hdf5DataValues(shape=hdf5_data_dict['shape'], values=hdf5_data_dict['values'])
                return hdf5_data_values

    @override
    async def close(self) -> None:
        pass


async def file_sender(file_name: str) -> AsyncGenerator[bytes, None]:
    async with aiofiles.open(file_name, 'rb') as f:
        chunk = await f.read(64 * 1024)
        while chunk:
            yield chunk
            chunk = await f.read(64 * 1024)
