import os
import unicodedata
import re
import urllib
import zipfile
import chardet
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import *

import numpy as np
import h5py
import libsbml
import typer

from datagen.biosimulations_runutils.biosim_pipeline import run_project, check_run_status
from datagen.biosimulations_runutils.biosim_pipeline.data_manager import DataManager
from datagen.biosimulations_runutils.biosim_pipeline import Simulator, SimulationRun
from datagen.biosimulations_runutils.common.api_utils import download_file

from datagen.utils import visit_datasets, printc


__all__ = [
    'BaseClass',
    'BiosimulationsRunOutputData',
    'SEDMLReportDataSet',
    'SimulatorReportData',
    'ReportDataSetPath',
    'SBMLSpeciesMapping',
    'IOBase',
    'RunUtilsIO'
]


@dataclass
class BaseClass:
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BiosimulationsReportOutput(BaseClass):
    dataset_label: str
    data: np.ndarray


@dataclass
class BiosimulationsRunOutputData(BaseClass):
    report_path: str
    data: List[BiosimulationsReportOutput]


class SEDMLReportDataSet(dict):
    pass


class SimulatorReportData(dict):
    pass


class ReportDataSetPath(str):
    pass


class SBMLSpeciesMapping(dict):
    pass


class IOBase(object):
    @classmethod
    def detect_encoding(cls, file_path: os.PathLike[str]) -> dict:
        with open(file_path, 'rb') as f:
            raw_data = f.read()
            result = chardet.detect(raw_data)
            return result

    @classmethod
    # find report and get data
    def get_report_filepath(cls, output_dirpath: os.PathLike[str]) -> str | None:
        # find report and get data
        report_fp = None
        for filepath in os.listdir(output_dirpath):
            if "output" in filepath:
                output_dir = os.path.join(output_dirpath, filepath)
                for outfile in os.listdir(output_dir):
                    out_path = os.path.join(output_dir, outfile)
                    if out_path.endswith(".h5"):
                        report_fp = out_path

        return report_fp

    @classmethod
    def extract_simulator_report_outputs(
            cls,
            simulator_output_zippath: os.PathLike[str],
            output_dirpath: os.PathLike[str]
    ) -> Union[BiosimulationsRunOutputData, dict[str, str]]:
        """
        Extract simulator output data from
        """
        # unzip and extract output files
        with zipfile.ZipFile(simulator_output_zippath, 'r') as zip_ref:
            zip_ref.extractall(output_dirpath)

        report_fp = cls.get_report_filepath(output_dirpath)

        return cls.get_formatted_simulator_report_outputs(report_file_path=report_fp)

    @classmethod
    def get_formatted_simulator_report_outputs(
            cls,
            report_file_path: os.PathLike[str] | str,
            return_as_dict: bool = True,
            dataset_label_id: str = 'sedmlDataSetLabels',
    ) -> Union[SimulatorReportData, BiosimulationsRunOutputData]:
        """
        Get the output/observables data for the specified report, derived from a simulator run submission.

        :param report_file_path: Path to the report file.
        :param return_as_dict: If True, return a dictionary containing the simulator report data, otherwise return a BiosimulationsRunOutputData object (See documentation for more details).
        :param dataset_label_id: Dataset label ID. Defaults to 'sedmlDataSetLabels'.

        :return: Report data for the specified simulator output report indexed by observable/species name.
        :rtype: Union[SimulatorReportData, BiosimulationsRunOutputData]
        """
        with h5py.File(report_file_path, 'r') as sedml_group:
            # get the dataset path for reports within sedml group
            dataset_path = cls.get_report_dataset_path(report_file_path)
            dataset = sedml_group[dataset_path]

            if return_as_dict:
                # check if dataset has attributes for labels
                if dataset_label_id in dataset.attrs:
                    labels = [label.decode('utf-8') for label in dataset.attrs[dataset_label_id]]
                    if "Time" in labels:
                        labels.remove("Time")
                else:
                    raise ValueError(f"No dataset labels found in the attributes with the name '{dataset_label_id}'.")

                # get labeled data from report
                data = dataset[()]
                return SimulatorReportData({label: data[idx].tolist() for idx, label in enumerate(labels)})
            else:
                # return as datamodel
                outputs = []
                ds_labels = [label.decode('utf-8') for label in dataset.attrs[dataset_label_id]]
                for label in ds_labels:
                    dataset_index = list(ds_labels).index(label)
                    data = dataset[()]
                    specific_data = data[dataset_index]
                    output = BiosimulationsReportOutput(dataset_label=label, data=specific_data)
                    outputs.append(output)

                return BiosimulationsRunOutputData(report_path=report_file_path, data=outputs)

    @classmethod
    def get_report_dataset_path(
            cls,
            report_file_path: str,
            keyword: str = "report"
    ) -> ReportDataSetPath:
        with h5py.File(report_file_path, 'r') as f:
            report_ds = visit_datasets(f)
            ds_paths = list(report_ds.keys())
            report_ds_path = ds_paths.pop() if len(ds_paths) < 2 else list(sorted(ds_paths))[0]   # TODO: make this better
            return ReportDataSetPath(report_ds_path)

    @classmethod
    def get_sbml_species_mapping(cls, sbml_fp: str) -> SBMLSpeciesMapping:
        sbml_reader = libsbml.SBMLReader()
        sbml_doc = sbml_reader.readSBML(sbml_fp)
        sbml_model_object = sbml_doc.getModel()

        # parse and handle names/ids
        sbml_species_ids = []
        for spec in sbml_model_object.getListOfSpecies():
            spec_name = spec.name
            if not spec_name:
                spec.name = spec.getId()
            if not spec.name == "":
                sbml_species_ids.append(spec)
        names = list(map(lambda s: s.name, sbml_species_ids))
        species_ids = [spec.getId() for spec in sbml_species_ids]

        return SBMLSpeciesMapping(zip(names, species_ids))

    @classmethod
    def fix_non_ascii_characters(cls, file_path: os.PathLike[str], output_file: os.PathLike[str]) -> None:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        non_ascii_chars = set(re.findall(r'[^\x00-\x7F]', content))
        replacements = {}
        for char in non_ascii_chars:
            ascii_name = unicodedata.name(char, None)
            if ascii_name:
                ascii_equivalent = ascii_name.lower().replace(" ", "_")
                replacements[char] = ascii_equivalent
            else:
                replacements[char] = ""

        for original, replacement in replacements.items():
            content = content.replace(original, replacement)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"Fixed file saved to {output_file}")


class RunUtilsIO(IOBase):
    """Biosimulations runutils-specific super-set of `IOBase` using `biosimulations_runutils` logic."""
    def __new__(cls, *args, **kwargs):
        return super().__new__(cls)

    @classmethod
    def download_runs(
            cls,
            omex_src_dir: Annotated[Union[Path, None], typer.Option(help="defaults env.OMEX_SOURCE_DIR")] = None,
            out_dir: Annotated[Union[Path, None], typer.Option(help="defaults to env.OMEX_OUTPUT_DIR")] = None,
            project_id: Annotated[Union[str, None], typer.Option(help="filter by project_id")] = None,
            simulator: Annotated[Union[Simulator, None], typer.Option(help="filter by simulator")] = None,
    ) -> Path:
        data_manager = DataManager(omex_src_dir=omex_src_dir, out_dir=out_dir)
        api_base_url = os.environ.get('API_BASE_URL')
        runs: list[SimulationRun] = data_manager.read_run_requests()

        for run in runs:
            # refresh status
            cls.refresh_status(omex_src_dir=omex_src_dir, out_dir=out_dir)

            if project_id and project_id != run.project_id:
                continue
            if simulator and simulator != run.simulator:
                continue
            if run.status is not None and run.status.lower() != "succeeded":
                continue

            printc(alert="> Retrieving simulation run: ", msg=run.model_dump_json())

            simdir = data_manager.get_run_output_dir(run)
            if os.path.exists(simdir / "results.zip"):
                continue

            try:
                out_filepath = Path(simdir / "results.zip")
                download_file(url=f"{api_base_url}/results/" + run.simulation_id + "/download",
                              out_file=out_filepath)

                return out_filepath
            except urllib.error.HTTPError as e:
                printc(alert="Failure:", msg=e, error=True)

    @classmethod
    def refresh_status(
            cls,
            omex_src_dir: Path,
            out_dir: Path,
            return_status: bool = False,
    ) -> dict[str, dict[str, Path | str | None | Simulator]]:
        statuses = {}
        data_manager = DataManager(omex_src_dir=omex_src_dir, out_dir=out_dir)
        runs: list[SimulationRun] = data_manager.read_run_requests()
        for run in runs:
            if run.status is not None and (run.status.lower() == "succeeded" or run.status.lower() == "failed"):
                continue
            run.status = check_run_status(run)
            statuses[run.simulation_id] = {'status': run.status, 'out_dir': out_dir, 'simulator': run.simulator}
        data_manager.write_runs(runs)

        if return_status:
            return statuses

    @classmethod
    def upload_omex(
            cls,
            simulator: Annotated[Simulator, typer.Option(help="simulator to run")] = Simulator.vcell,
            simulator_version: Annotated[str, typer.Option(help="simulator version to run - defaults to 'latest'")] = "latest",
            project_id: Annotated[Union[str, None], typer.Option(help="filter by project_id")] = None,
            omex_src_dir: Path = None,
            out_dir: Path = None
    ) -> None:
        data_manager = DataManager(omex_src_dir=omex_src_dir, out_dir=out_dir)
        projects = data_manager.read_projects()

        for source_omex in data_manager.get_source_omex_archives():
            if source_omex.project_id in projects:
                printc(f"> project {source_omex.project_id} is already validated and published")
                continue
            if project_id is not None and source_omex.project_id != project_id:
                continue
            printc(source_omex.project_id, "Project ID: ")
            run_project(source_omex=source_omex, simulator=simulator, simulator_version=simulator_version, data_manager=data_manager)
    # simulator_outputs = read_report_outputs(report_file_path=report_path)
    # data = explore_hdf5_data(report_path)
    # dataset_keys = data.keys()
    # dataset_path = list(data.keys()).pop() if len(dataset_keys) == 1 else list(data.keys())[0]
    # labeled_data = read_report_outputs_with_labels(report_file_path=report_path, dataset_path=dataset_path)
    # return labeled_data


STATUS_SCHEMA = {
    "$run_id(str)": {
        "status": "str",
        "out_dir": "PathLike[str]",
        "simulator": "Simulator"
    }
}

