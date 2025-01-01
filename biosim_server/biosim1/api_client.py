import json
import logging
import os
from dataclasses import asdict
from typing import BinaryIO, Union

import aiofiles
import aiohttp
from temporalio import activity

from biosim_server.biosim1.models import SimulationRun, SourceOmex, Simulator, SimulationRunApiRequest


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
