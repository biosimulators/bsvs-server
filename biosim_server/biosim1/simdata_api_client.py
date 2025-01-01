import os

import aiohttp
from temporalio import activity

from biosim_server.biosim1.models import Hdf5DataValues


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
