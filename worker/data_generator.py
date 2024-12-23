import asyncio
import time
import os
import uuid
import warnings

import requests
from tempfile import mkdtemp
from shutil import rmtree
from typing import *
from pathlib import Path

import numpy as np
from dotenv import load_dotenv

from shared.biosimulations_runutils.biosim_pipeline.datamodels import Simulator
from shared.data_model import BiosimulationsRunOutputData
from shared.io import RunUtilsIO

from shared.utils import *


__all__ = [
    "DataGenerator",
    "batch_generate_omex_outputs",
    "get_biomodel_archive"
]


load_dotenv('../tests/.env')


def get_biomodel_archive(model_id: str, dest_dir: Optional[str] = None) -> str:
    """
    Download all files for a given Biomodel as an OMEX archive from the Biomodels REST API, optionally specifying a download destination. *NOTE*: This file may be opened as a typical zip file.

    :param model_id: (`Union[str, List[str]]`) A single biomodel id as a string or a list of biomodel ids as strings.
    :param dest_dir: (`str`) destination directory at which to save downloaded file. If `None` is passed, downloads to cwd. Defaults to `None`.

    :return: Filepath of the downloaded biomodel OMEX(zip) archive
    :rtype: `str`
    """
    base_url = "https://www.ebi.ac.uk/biomodels/model/download"
    url = f"{base_url}/{model_id}"
    params = {}

    try:
        resp = requests.get(url, params=params, stream=True)

        if resp.status_code == 200:
            dest = dest_dir or os.getcwd()
            fp = os.path.join(dest, f"{model_id}.omex")
            with open(fp, "wb") as file:
                for chunk in resp.iter_content(chunk_size=8192):
                    file.write(chunk)
            print(f"File downloaded successfully and saved as {fp}")

            return fp
        elif resp.status_code == 400:
            warnings.warn("Error 400: File Not Found")
        elif resp.status_code == 404:
            warnings.warn("Error 404: Invalid Model ID Supplied")
        else:
            warnings.warn(f"Unexpected error: {resp.status_code} - {resp.text}")
    except requests.RequestException as e:
        warnings.warn(f"An error occurred: {e}")


def batch_generate_omex_outputs(biomodel_ids: list[str], output_dir: str | Path, json_fp: str, simulators, buffer):
    data_generator = DataGenerator()
    for biomodel_id in biomodel_ids:
        omex_outputs = data_generator.generate_omex_output_data(biomodel_id, output_dir, simulators, buffer, use_instance_dir=True)

        printc(omex_outputs.keys(), f"{biomodel_id} --> the final output keys for {biomodel_id}")

        outputfile_id = min(str(uuid.uuid4()).split('-'))
        # json_fp = f'./verification_request/output_data/{test_biomodel_id}-outputs-{outputfile_id}.json'
        data_generator.export_data(omex_outputs, json_fp, verbose=True)


class DataGenerator:
    def __init__(self,
                 out_dir: Optional[str | Path | os.PathLike[str]] = None):
        self.out_dir = out_dir or mkdtemp(self.__repr__())

    def __repr__(self):
        return f"{self.__class__.__name__}"

    def __del__(self):
        if self.__repr__() in self.out_dir:
            rmtree(self.out_dir)

    def export_data(self, omex_outputs: dict[str, dict[str, np.ndarray | list[float]]], fp: os.PathLike[str] | str, verbose: bool = False):
        import json
        with open(fp, 'w') as json_file:
            json.dump(omex_outputs, json_file, indent=4)
            if verbose:
                printc(fp, "Wrote data to JSON @")
                print(f'EXISTS({fp}): {os.path.exists(fp)}')

    def generate_omex_output_data(
            self,
            biomodel_entrypoint: str | os.PathLike[str],
            out_dir: str | Path,
            simulators: list[str | tuple[str, str]],
            fetch_buffer: int = 2,
            use_instance_dir: bool = True,
    ) -> BiosimulationsRunOutputData | dict[str, dict[str, np.ndarray | list[float]]]:
        dest = self.out_dir if use_instance_dir else out_dir
        output_data = asyncio.run(
            self._generate(biomodel_entrypoint, dest, simulators, fetch_buffer, mode="omex")
        )
        return output_data

    def generate_sbml_output_data(
            self,
            sbml_entrypoint: str | os.PathLike[str],
            start: int,
            stop: int,
            num_steps: int,
            simulators: list[str | tuple[str, str]],
    ):
        pass

    async def _generate(
            self,
            biomodel_entrypoint: str | os.PathLike[str],
            out_dir: str | Path,
            simulators: list[str | tuple[str, str]],
            fetch_buffer: int = 2,
            mode: str = "omex"
    ) -> BiosimulationsRunOutputData | dict[str, dict[str, np.ndarray | list[float]]]:
        os.makedirs(out_dir) if not os.path.exists(out_dir) else None

        # submit run
        output_dirpaths, omex_src_dirpath = await self.submit_omex_simulations(
            entrypoint=biomodel_entrypoint,
            dest_dir=out_dir,
            simulators=simulators,
            buffer=fetch_buffer,
        )

        # refresh status for each output
        printc(f"> Waiting {fetch_buffer} seconds before refreshing status...\n")
        time.sleep(fetch_buffer)

        # async fetch outputs
        output_data = await self.fetch_simulator_report_outputs(output_dirpaths, omex_src_dirpath, fetch_buffer)

        return output_data

    async def submit_omex_simulations(
            self,
            entrypoint: str | os.PathLike[str],
            dest_dir: str | Path,
            simulators: List[Union[Tuple[str, str], str]],
            buffer: int = 2
    ) -> tuple[list[Path], Path]:
        fp = get_biomodel_archive(entrypoint, dest_dir)  # if not entrypoint.endswith('.omex') else entrypoint
        omex_src_dir = Path(os.path.dirname(fp))

        # submit a simulation for each simulator specified
        output_filepaths = []
        for simulator in simulators:
            # parse simulator version
            version = "latest"
            if isinstance(simulator, tuple):
                if len(simulator) == 2:
                    version = simulator[1]

            # create dedicated output dir for each simulator
            output_dest = os.path.join(dest_dir, simulator)
            if not os.path.exists(output_dest):
                os.makedirs(output_dest)
            sim_output_dest_path = Path(output_dest)

            # run the simulation
            printc(f"> Submitting simulation of {entrypoint} with {simulator}...\n")
            RunUtilsIO.upload_omex(
                simulator=Simulator[f'{simulator}'],
                simulator_version=version,
                omex_src_dir=omex_src_dir,
                out_dir=sim_output_dest_path,
            )
            printc(f"Simulation submitted. Waiting for {buffer} seconds...", simulator)

            # wait and then refresh status
            time.sleep(buffer)
            printc("> Refreshing status...\n")
            RunUtilsIO.refresh_status(omex_src_dir=omex_src_dir, out_dir=sim_output_dest_path)

            # record output filepath
            output_filepaths.append(sim_output_dest_path)
            printc(f'> Simulation submission completed for {simulator}.\n')

        return output_filepaths, omex_src_dir

    async def fetch_simulator_report_outputs(
            self,
            output_dirpaths: list[Path],
            omex_src_dirpath: Path,
            buffer: int = 2,
            verbose: bool = False
    ) -> dict[str, BiosimulationsRunOutputData | dict[str, str] | dict]:
        output_data = {}
        for output_dirpath in output_dirpaths:
            printc(output_dirpath, "Fetching data for output dirpath: ")
            status_updates = RunUtilsIO.refresh_status(omex_src_dir=omex_src_dirpath, out_dir=output_dirpath, return_status=True)

            # iterate over each simulation in the status updates
            for sim_id in status_updates:
                status_data = status_updates[sim_id]
                terminal_statuses = ['succeeded', 'failed']
                simulator = status_data['simulator']
                printc(sim_id, f"{simulator}-->Fetching status updates")

                while status_data['status'].lower() not in terminal_statuses:
                    # status not ready, wait and re-fetch status
                    if verbose:
                        printc(f"\033[5m{status_data.get('status')} Attempting another refresh...\n", f'\033[5m{simulator}')
                    el = f'{sim_id} not yet ready '
                    for _ in range(buffer):
                        el += '.'
                        printc(el, simulator)
                        time.sleep(1)
                    # time.sleep(buffer)

                    status_updates = RunUtilsIO.refresh_status(omex_src_dir=omex_src_dirpath, out_dir=output_dirpath, return_status=True)
                    status_data = status_updates.get(sim_id, status_data)

                # status check is complete
                final_simulation_status = status_data['status'].lower()
                printc(alert=f"> Status check complete for {simulator}:", msg=final_simulation_status)

                # download files and get data
                sim_data = {}
                # run is successful
                if 'failed' not in final_simulation_status:
                    printc("Run was successful! Now downloading simulation files...", simulator)
                    simulator_output_zippath = RunUtilsIO.download_runs(omex_src_dir=omex_src_dirpath, out_dir=output_dirpath)
                    if simulator_output_zippath is not None:
                        printc(f"Downloaded files to {simulator_output_zippath}", simulator)

                        # get the simulators output data from zip file
                        if os.path.exists(simulator_output_zippath):
                            sim_data = RunUtilsIO.extract_simulator_report_outputs(simulator_output_zippath, output_dirpath)
                        else:
                            # somehow path is misconfigured
                            printc(f"{simulator_output_zippath} does not exist.", simulator, error=True)
                # run failed
                else:
                    printc(final_simulation_status, "WARNING: ")
                    sim_data = {"ERROR": "Simulation failed."}

                # assign simulator data
                output_data[str(simulator).split('.')[-1]] = sim_data

        return output_data


