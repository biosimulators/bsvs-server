import json
import logging
import os
from dataclasses import dataclass, asdict
from typing import BinaryIO, Union

import aiofiles
import aiohttp
from pydantic import BaseModel
from temporalio import activity

from temporal.biosim_models import SimulationRun, SourceOmex, Simulator

ATTRIBUTE_VALUE_TYPE = int | float | str | bool | list[str] | list[int] | list[float] | list[bool]


class HDF5Attribute(BaseModel):
    key: str
    value: ATTRIBUTE_VALUE_TYPE


class HDF5Dataset(BaseModel):
    name: str
    shape: list[int]
    attributes: list[HDF5Attribute]


class HDF5Group(BaseModel):
    name: str
    attributes: list[HDF5Attribute]
    datasets: list[HDF5Dataset]


class HDF5File(BaseModel):
    filename: str
    id: str
    uri: str
    groups: list[HDF5Group]


@dataclass
class Hdf5DataValues:
    # simulation_run_id: str
    # dataset_name: str
    shape: list[int]
    values: list[float]

@dataclass
class SimulationRunApiRequest:
    name: str  # what does this correspond to?
    simulator: str
    simulatorVersion: str
    maxTime: int  # in minutes
    # email: Optional[str] = None
    # cpus: Optional[int] = None
    # memory: Optional[int] = None (in GB)


@activity.defn
async def check_run_status(simulation_run_id: str) -> str:
    api_base_url = os.environ.get('API_BASE_URL') or "https://api.biosimulations.org"
    assert (api_base_url is not None)

    async with aiohttp.ClientSession() as session:
        async with session.get(api_base_url + "/runs/" + simulation_run_id) as resp:
            resp.raise_for_status()
            getrun_dict = await resp.json()

    result = str(getrun_dict['status'])
    return result


@activity.defn
async def get_hdf5_metadata(simulation_run_id: str) -> str:
    api_base_url = os.environ.get('SIMDATA_API_BASE_URL') or "https://simdata.api.biosimulations.org"
    assert (api_base_url is not None)

    async with aiohttp.ClientSession() as session:
        url = f"{api_base_url}/datasets/{simulation_run_id}/metadata"
        async with session.get(url) as resp:
            resp.raise_for_status()
            hdf5_metadata_json = await resp.text()
            return hdf5_metadata_json
            # hdf5_file: HDF5File = HDF5File.model_validate_json(hdf5_metadata_json)
            # for group in hdf5_file.groups:
            #     for dataset in group.datasets:
            #         for attribute in dataset.attributes:
            #             if attribute.key == "value":
            #                 if isinstance(attribute.value, list):
            #                     attribute.value = attribute.value[:10]
            # return hdf5_file.model_dump_json()


@activity.defn
async def get_hdf5_data(simulation_run_id: str, dataset_name: str) -> Hdf5DataValues:
    api_base_url = os.environ.get('SIMDATA_API_BASE_URL') or "https://simdata.api.biosimulations.org"
    assert (api_base_url is not None)

    async with aiohttp.ClientSession() as session:
        url = f"{api_base_url}/datasets/{simulation_run_id}/data"
        async with session.get(url, params={"dataset_name": dataset_name}) as resp:
            resp.raise_for_status()
            hdf5_data_dict = await resp.json()
            activity.logger.info(f"Got data for dataset: {dataset_name}")
            hdf5_data_values = Hdf5DataValues(shape=hdf5_data_dict['shape'], values=hdf5_data_dict['values'])
            return hdf5_data_values


@activity.defn
async def run_project(
        source_omex: SourceOmex,
        simulator: Simulator,
        simulator_version: str) -> SimulationRun:
    """
    This function runs the project on biosimulations.
    """
    activity.logger.setLevel(logging.INFO)
    api_base_url = str(os.environ.get('API_BASE_URL')) or "https://api.biosimulations.org"

    simulation_run_request = SimulationRunApiRequest(
        name=source_omex.name,
        simulator=simulator,
        simulatorVersion=simulator_version,
        maxTime=600,
    )

    print(source_omex.omex_file)
    async with aiohttp.ClientSession() as session:
        multipart_form_data: dict[str, Union[tuple[str, BinaryIO], tuple[None, str]]] = {
            'file': (source_omex.name + '.omex', file_sender(file_name=source_omex.omex_file)),
            'simulationRun': (None, json.dumps(asdict(simulation_run_request))),
        }
        async with session.post(api_base_url + '/runs', data=multipart_form_data) as resp:
            resp.raise_for_status()
            res = await resp.json()

    activity.logger.info(f"Ran {source_omex.name} on biosimulations with simulation id: {res['id']}")
    activity.logger.info(f"results: {res}")
    simulation_id = res["id"]

    sim_run = SimulationRun(
        simulator=simulator,
        simulator_version=res['simulatorVersion'],
        simulation_id=simulation_id,
        project_id=source_omex.name,
        status=res['status']
    )

    activity.logger.info("Ran " + source_omex.name + " on biosimulations with simulation id: " + simulation_id)
    activity.logger.info("View:", api_base_url + "/runs/" + simulation_id)
    return sim_run


async def file_sender(file_name=None):
    async with aiofiles.open(file_name, 'rb') as f:
        chunk = await f.read(64 * 1024)
        while chunk:
            yield chunk
            chunk = await f.read(64 * 1024)
