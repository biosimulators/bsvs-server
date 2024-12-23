import os
import re
import unicodedata
import urllib
import zipfile
from pathlib import Path
from tempfile import mkdtemp
from typing import *

import h5py
import libsbml
import chardet
from fastapi import UploadFile
from google.cloud import storage

from shared.biosimulations_runutils.biosim_pipeline.biosim_api import check_run_status, run_project
from shared.biosimulations_runutils.biosim_pipeline.data_manager import DataManager
from shared.biosimulations_runutils.biosim_pipeline.datamodels import Simulator, SimulationRun
from shared.data_model import BiosimulationsRunOutputData, BiosimulationsReportOutput
from worker.data_model import SBMLSpeciesMapping, ReportDataSetPath, SimulatorReportData
from shared.utils import printc, visit_datasets


def check_upload_file_extension(file: UploadFile, purpose: str, ext: str, message: str = None) -> bool:
    if not file.filename.endswith(ext):
        msg = message or f"Files for {purpose} must be passed in {ext} format."
        raise ValueError(msg)
    else:
        return True


async def save_uploaded_file(uploaded_file: UploadFile, save_dest: str) -> str:
    """Write `fastapi.UploadFile` instance passed by api gateway user to `save_dest`."""
    file_path = os.path.join(save_dest, uploaded_file.filename)
    with open(file_path, 'wb') as file:
        contents = await uploaded_file.read()
        file.write(contents)
    return file_path


def upload_blob(bucket_name, source_file_name, destination_blob_name):
    """Uploads a file to the bucket."""
    # The ID of your GCS bucket
    # bucket_name = "your-bucket-name"
    # The path to your file to upload
    # source_file_name = "local/path/to/file"
    # The ID of your GCS object
    # destination_blob_name = "storage-object-name"

    storage_client = storage.Client('bio-check-428516')
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    # Optional: set a generation-match precondition to avoid potential race conditions
    # and data corruptions. The request to upload is aborted if the object's
    # generation number does not match your precondition. For a destination
    # object that does not yet exist, set the if_generation_match precondition to 0.
    # If the destination object already exists in your bucket, set instead a
    # generation-match precondition using its generation number.
    generation_match_precondition = 0

    blob.upload_from_filename(source_file_name, if_generation_match=generation_match_precondition)

    return {
        'message': f"File {source_file_name} uploaded to {destination_blob_name}."
    }


async def write_uploaded_file(job_id: str, bucket_name: str, uploaded_file: UploadFile, extension: str) -> str:
    # bucket params
    upload_prefix = f"file_uploads/{job_id}/"
    bucket_prefix = f"gs://{bucket_name}/" + upload_prefix

    save_dest = mkdtemp()
    fp = await save_uploaded_file(uploaded_file, save_dest)  # save uploaded file to ephemeral store

    # Save uploaded omex file to Google Cloud Storage
    uploaded_file_location = None
    properly_formatted_omex = check_upload_file_extension(uploaded_file, 'uploaded_file', extension)
    if properly_formatted_omex:
        blob_dest = upload_prefix + fp.split("/")[-1]
        upload_blob(bucket_name=bucket_name, source_file_name=fp, destination_blob_name=blob_dest)
        uploaded_file_location = blob_dest

    return uploaded_file_location


def download_blob(bucket_name, source_blob_name, destination_file_name):
    """Downloads a blob from the bucket."""
    # bucket_name = "your-bucket-name"
    # source_blob_name = "storage-object-name"
    # destination_file_name = "local/path/to/file"

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(source_blob_name)

    # Download the file to a destination
    blob.download_to_filename(destination_file_name)


def download_file_from_bucket(source_blob_path: str, out_dir: str, bucket_name: str) -> str:
    """Download any file specified in a given job_params (mongo db collection document) which is saved in the bucket to out_dir. The file is assumed to originate from bucket_name.

        Returns:
            filepath (`str`) of the downloaded file.
    """
    source_blob_name = source_blob_path
    local_fp = os.path.join(out_dir, source_blob_name.split('/')[-1])
    download_blob(bucket_name=bucket_name, source_blob_name=source_blob_name, destination_file_name=local_fp)
    return local_fp


def get_sbml_species_mapping(sbml_fp: str) -> dict:
    """

    Args:
        - sbml_fp: `str`: path to the SBML model file.

    Returns:
        Dictionary mapping of {sbml_species_names(usually the actual observable name): sbml_species_ids(ids used in the solver)}
    """
    # read file
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

    return dict(zip(names, species_ids))


def download_file(source_blob_path: str, out_dir: str, bucket_name: str) -> str:
    """Download any file specified in a given job_params (mongo db collection document) to out_dir. The file is assumed to originate from bucket_name.

        Returns:
            filepath (`str`) of the downloaded file.
    """
    source_blob_name = source_blob_path
    local_fp = os.path.join(out_dir, source_blob_name.split('/')[-1])
    download_blob(bucket_name=bucket_name, source_blob_name=source_blob_name, destination_file_name=local_fp)
    return local_fp


def read_uploaded_file(bucket_name, source_blob_name, destination_file_name):
    download_blob(bucket_name, source_blob_name, destination_file_name)

    with open(destination_file_name, 'r') as f:
        return f.read()


async def _save_uploaded_file(uploaded_file: UploadFile | str, save_dest: str) -> str:
    """Write `fastapi.UploadFile` instance passed by api gateway user to `save_dest`."""
    if isinstance(uploaded_file, UploadFile):
        filename = uploaded_file.filename
    else:
        filename = uploaded_file

    file_path = os.path.join(save_dest, filename)
    # case: is a fastapi upload
    if isinstance(uploaded_file, UploadFile):
        with open(file_path, 'wb') as file:
            contents = await uploaded_file.read()
            file.write(contents)
    # case: is a string
    else:
        with open(filename, 'r') as fp:
            contents = fp.read()
        with open(file_path, 'w') as f:
            f.write(contents)

    return file_path


class IOBase(object):
    @classmethod
    def make_dir(cls, fp: str, mk_temp: bool = False) -> str | None:
        if mk_temp:
            return mkdtemp()
        else:
            if not os.path.exists(fp):
                os.mkdir(fp)

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
            omex_src_dir=None,
            out_dir=None,
            project_id=None,
            simulator=None,
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
            simulator,
            simulator_version="latest",
            project_id=None,
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


