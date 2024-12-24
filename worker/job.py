import logging
import math
import tempfile
from asyncio import sleep
from typing import *

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from pymongo.collection import Collection as MongoCollection

from shared.data_model import JobStatus, DatabaseCollections, BUCKET_NAME, DEV_ENV_PATH, DEFAULT_SIMULATORS
from shared.database import MongoDbConnector
from shared.io import download_file
from shared.log_config import setup_logging
from shared.utils import unique_id, handle_sbml_exception, get_output_stack


# for dev only
load_dotenv(DEV_ENV_PATH)


class Supervisor:
    def __init__(self, db_connector: MongoDbConnector, queue_timer: int = 10, preferred_queue_index: int = 0):
        self.db_connector = db_connector
        self.queue_timer = queue_timer
        self.preferred_queue_index = preferred_queue_index
        self.job_queue = self.db_connector.pending_jobs()
        self._supervisor_id: Optional[str] = "supervisor_" + unique_id()
        self.logger = logging.getLogger("biochecknet.job.supervisor.log")
        setup_logging(self.logger)

    async def check_jobs(self) -> int:
        """Returns non-zero if max retries reached, zero otherwise."""
        for _ in range(self.queue_timer):
            # perform check
            await self.run_job_check()
            await sleep(2)

            # refresh jobs
            self.job_queue = self.db_connector.pending_jobs()

        return 0

    async def run_job_check(self):
        worker = None
        for i, pending_job in enumerate(self.job_queue):
            # get job params
            job_id = pending_job.get('job_id')
            source = pending_job.get('path')
            source_name = source.split('/')[-1] if source is not None else "No-Source-File"

            # check terminal collections for job
            job_completed = self.job_exists(job_id=job_id, collection_name="completed_jobs")
            job_failed = self.job_exists(job_id=job_id, collection_name="failed_jobs")

            # case: job is not complete, otherwise do nothing
            if not job_completed and not job_failed:
                # change job status for client by inserting a new in progress job
                job_in_progress = self.job_exists(job_id=job_id, collection_name="in_progress_jobs")
                if not job_in_progress:
                    in_progress_entry = {
                        'job_id': job_id,
                        'timestamp': self.db_connector.timestamp(),
                        'status': JobStatus.IN_PROGRESS.value,
                        'requested_simulators': pending_job.get('simulators'),
                        'source': source
                    }

                    # special handling of composition jobs TODO: move this to the supervisor below
                    if job_id.startswith('composition-run'):
                        in_progress_entry['composite_spec'] = pending_job.get('composite_spec')
                        in_progress_entry['simulator'] = pending_job.get('simulators')
                        in_progress_entry['duration'] = pending_job.get('duration')

                    # insert new inprogress job with the same job_id
                    in_progress_job = await self.db_connector.insert_job_async(
                        collection_name="in_progress_jobs",
                        **in_progress_entry
                    )

                    # remove job from pending
                    self.db_connector.db.pending_jobs.delete_one({'job_id': job_id})

                # run job again
                try:
                    worker = Worker(job=pending_job)

                    # when worker completes, dismiss worker (if in parallel)
                    await worker.run()

                    # create new completed job using the worker's job_result
                    result_data = worker.job_result
                    await self.db_connector.write(
                        collection_name=DatabaseCollections.COMPLETED_JOBS.value,
                        job_id=job_id,
                        timestamp=self.db_connector.timestamp(),
                        status=JobStatus.COMPLETED.value,
                        results=result_data,
                        source=source_name,
                        requested_simulators=pending_job.get('simulators')
                    )

                    # remove in progress job
                    self.db_connector.db.in_progress_jobs.delete_one({'job_id': job_id})
                except:
                    # save new execution error to db
                    error = handle_sbml_exception()
                    self.logger.error(error)
                    await self.db_connector.write(
                        collection_name="failed_jobs",
                        job_id=job_id,
                        timestamp=self.db_connector.timestamp(),
                        status=JobStatus.FAILED.value,
                        results=error,
                        source=source_name
                    )
                    # remove in progress job TODO: refactor this
                    self.db_connector.db.in_progress_jobs.delete_one({'job_id': job_id})

    def job_exists(self, job_id: str, collection_name: str) -> bool:
        """Returns True if job with the given job_id exists, False otherwise."""
        unique_id_query = {'job_id': job_id}
        coll: MongoCollection = self.db_connector.db[collection_name]
        job = coll.find_one(unique_id_query) or None

        return job is not None


# run singularity in docker 1 batch mode 1 web version
class Worker:
    job_params: Dict
    job_id: str
    job_result: Dict | None
    job_failed: bool
    supervisor: Supervisor
    logger: logging.Logger

    def __init__(self, job: Dict, supervisor: Supervisor = None):
        """
        :param job: job parameters received from the supervisor (who gets it from the db) which is a document from the pending_jobs collection within mongo.
        """
        self.logger = logging.getLogger(f"worker.Worker.log")
        setup_logging(self.logger)
        self.job_params = job
        self.job_id = self.job_params['job_id']
        self.supervisor = supervisor
        self.job_result = {}
        self.job_failed = False
        self.verifier = Verifier()

        # for parallel processing in a pool of workers. TODO: eventually implement this.
        self.worker_id = unique_id()

    async def run(self, selection_list: List[str] = None) -> Dict:
        # process simulation
        input_fp = self.job_params['path']
        selection_list = self.job_params.get('selection_list')
        if input_fp.endswith('.omex'):
            self.execute_omex_job()
        else:
            raise IOError('Input file must be a valid OMEX archive.')

        # select data if applicable
        selections = self.job_params.get("selection_list", selection_list)
        if selections is not None:
            self.job_result = self.verifier.select_observables(job_result=self.job_result, observables=selections)

        # calculate rmse
        try:
            rmse_matrix = self.verifier.calculate_pairwise_rmse()
            self.job_result['rmse'] = self.verifier.format_rmse_matrix(rmse_matrix)
            # self.job_result['rmse'] = self._calculate_pairwise_rmse()
        except:
            e = handle_sbml_exception()
            self.logger.error(e)
            self.job_result['rmse'] = {'error': e}

        return self.job_result

    def execute_omex_job(self):
        params = None
        out_dir = tempfile.mkdtemp()
        source_fp = self.job_params['path']
        source_report_fp = self.job_params.get('expected_results')

        # download sbml file
        local_fp = download_file(source_blob_path=source_fp, out_dir=out_dir, bucket_name=BUCKET_NAME)

        # get ground truth from bucket if applicable
        truth_vals = None
        local_report_fp = None
        # if source_report_fp is not None:
        #     local_report_fp = download_file(source_blob_path=source_report_fp, out_dir=out_dir, bucket_name=BUCKET_NAME)
        #     truth_vals = read_h5_reports(local_report_fp)

        simulators = self.job_params.get('simulators', DEFAULT_SIMULATORS)
        include_outs = self.job_params.get('include_outputs', False)
        tol = self.job_params.get('rTol')
        atol = self.job_params.get('aTol')
        comparison_id = self.job_params.get('job_id')

        result = self.verifier.run_comparison(
            path=local_fp,
            simulators=simulators,
            out_dir=out_dir,
            include_outputs=include_outs,
            truth_vals=truth_vals
        )

        self.job_result = result
        # except:
        # error = handle_sbml_exception()
        # logger.error(error)
        # self.job_result = {"error": error}

    def get_result(self) -> tuple[dict, bool]:
        return (self.job_result, self.job_failed)


class Verifier:
    """Class which handles all non-network-based verification and data formatting logic."""
    def calculate_inter_simulator_rmse(self, target_simulator: str, job_result: Dict):
        # extract data fields
        spec_data = job_result

        # iterate through observables
        mse_values = []
        for observable, sim_details in spec_data.items():
            mse_data = sim_details['mse'][target_simulator]

            # exclude self-comparison and collect MSE values with other simulators
            for sim, mse in mse_data.items():
                if sim != target_simulator:
                    mse_values.append(mse)

        return math.sqrt(sum(mse_values) / len(mse_values)) if mse_values else 0.0

    def format_rmse_matrix(self, matrix) -> dict[str, dict[str, float]]:
        _m = matrix
        rmse = {}

        # iterate over original matrix
        for outer, inner_dict in _m.items():
            keys = list(inner_dict.keys())
            scores = list(inner_dict.values())
            valid_scores = []
            valid_keys = []
            n_valid = 0

            for i, score in enumerate(scores):
                # case: valid score
                if score is not None and not np.isnan(score):
                    valid_keys.append(keys[i])
                    valid_scores.append(score)
                    n_valid += 1

            # dict is valid if greater than 1
            if n_valid > 1:
                inner = dict(zip(valid_keys, valid_scores))
                rmse[outer] = inner

        return rmse

    def calculate_pairwise_rmse(self, job_result: Dict, job_params: Dict) -> Dict:
        # get input data
        spec_data = job_result
        simulators = job_params['simulators']
        if job_params.get('expected_results') is not None:
            simulators.append('expected_results')
        n = len(simulators)

        # set up empty matrix
        rmse_matrix = np.zeros((n, n))

        # enumerate over i,j of simulators in a matrix
        for i, sim_i in enumerate(simulators):
            for j, sim_j in enumerate(simulators):
                if i != j:
                    mse_values = []
                    for observable, observable_data in spec_data.items():
                        if not isinstance(observable_data, str):
                            mse_data = observable_data['mse']
                            if sim_j in mse_data:
                                # mse_data[sim_j] is a dict containing MSEs with other simulators
                                for comparison_sim, mse_value in mse_data[sim_j].items():
                                    if comparison_sim == sim_i:
                                        mse_values.append(mse_value)
                    if mse_values:
                        mean_mse = sum(mse_values) / len(mse_values)
                        rmse_matrix[i, j] = math.sqrt(mean_mse)
                    else:
                        # TODO: make this more robust
                        rmse_matrix[i, j] = np.nan
                else:
                    rmse_matrix[i, j] = 0.0

        return pd.DataFrame(rmse_matrix, columns=simulators, index=simulators).to_dict()

    def select_observables(self, job_result: Dict, observables: List[str] = None) -> Dict:
        """Select data from the input data that is passed which should be formatted such that the data has mappings of observable names
            to dicts in which the keys are the simulator names and the values are arrays. The data must have content accessible at: `data['content']['results']`.
        """
        outputs = job_result.copy()
        result = {}
        data = job_result

        # case: results from sbml
        if isinstance(data, dict):
            for name, obs_data in data.items():
                if name in observables:
                    result[name] = obs_data
            outputs = result
        # case: results from omex
        elif isinstance(data, list):
            for i, datum in enumerate(data):
                name = datum['species_name']
                if name not in observables:
                    print(f'Name: {name} not in observables')
                    data.pop(i)
            outputs = data

        return outputs

    def run_comparison(
            self,
            path: str,
            simulators: List[str],
            out_dir: str,
            data_generator: Callable[[str, str, List[str]], Dict[str, Union[np.ndarray, List[float]]]],
            include_outputs: bool = True,
            truth_vals=None,
            rTol=None,
            aTol=None
    ) -> Dict:
        """Execute a Uniform Time Course comparison for ODE-based simulators from Biosimulators."""
        # download the omex file from GCS
        # source_blob_name = path.replace('gs://bio-check-requests-1', '')  # Assuming omex_fp is the blob name in GCS
        # local_omex_fp = os.path.join(out_dir, path.split('/')[-1])
        # download_blob(bucket_name=BUCKET_NAME, source_blob_name=path, destination_file_name=local_omex_fp)

        # download the report file from GCS if applicable
        # if ground_truth_report_path is not None:
        #     source_report_blob_name = ground_truth_report_path.replace('gs://bio-check-requests-1', '')
        #     # local_report_path = os.path.join(out_dir, source_report_blob_name.split('/')[-1])
        #     local_report_path = os.path.join(out_dir, ground_truth_report_path.split('/')[-1])
        #     truth_vals = read_report_outputs(ground_truth_report_path)
        # else:
        #     truth_vals = None

        results = {}

        # generate the data
        # output_data = generate_biosimulator_utc_outputs(omex_fp=path, output_root_dir=out_dir, simulators=simulators, alg_policy="same_framework")
        output_data = data_generator(path, out_dir, simulators)
        ground_truth_data = truth_vals.to_dict() if not isinstance(truth_vals, type(None)) else truth_vals

        # generate the species comparisons
        observable_names = []
        for simulator_name in output_data.keys():
            sim_data = output_data[simulator_name]
            if isinstance(sim_data, dict):
                for observable_name in sim_data.keys():
                    observable_names.append(observable_name)
        names = list(set(observable_names))

        for species in names:
            if not species == 'EmptySet':
                # TODO: reimplement this!
                ground_truth_data = None
                # if ground_truth:
                #     for data in ground_truth['data']:
                #         if data['dataset_label'] == species:
                #             ground_truth_data = data['data']
                # generate species comparison

                results[species] = self.generate_species_comparison(
                    output_data=output_data,
                    species_name=species,
                    simulators=simulators,
                    ground_truth=ground_truth_data,
                    rTol=rTol,
                    aTol=aTol
                )

        return results

    def generate_species_comparison(self, output_data, species_name, simulators, ground_truth=None, rTol=None, aTol=None):
        # extract valid comparison data
        stack = get_output_stack(output=output_data, spec_name=species_name)
        species_comparison_data = {}
        for simulator_name in stack.keys():
            row = stack[simulator_name]
            if row is not None:
                species_comparison_data[simulator_name] = row

        vals = list(species_comparison_data.values())
        valid_sims = list(species_comparison_data.keys())
        outputs = vals
        methods = ['mse', 'proximity']
        if len(outputs) > 1:
            # outputs = _get_output_stack(output_data, species_name)
            matrix_vals = list(map(
                lambda m: self.generate_species_comparison_matrix(outputs=outputs, simulators=valid_sims, method=m, ground_truth=ground_truth, rtol=rTol, atol=aTol).to_dict(),
                methods
            ))
        else:
            matrix_vals = list(map(
                lambda m: {},
                methods
            ))

        results = dict(zip(methods, matrix_vals))
        results['output_data'] = {}
        data = None
        for simulator_name in output_data.keys():
            sim_output = output_data[simulator_name]
            for spec_name, spec_output in sim_output.items():
                if spec_name == species_name:
                    data = output_data[simulator_name][spec_name]
                elif spec_name.lower() == 'error':
                    data = output_data[simulator_name]

                results['output_data'][simulator_name] = data.tolist() if isinstance(data, np.ndarray) else data
        return results

    def generate_species_comparison_matrix(
            self,
            outputs: Union[np.ndarray, List[np.ndarray]],
            simulators: List[str],
            method: Union[str, any] = 'proximity',
            rtol: float = None,
            atol: float = None,
            ground_truth: np.ndarray = None
    ) -> pd.DataFrame:
        """Generate a Mean Squared Error comparison matrix of arr1 and arr2, indexed by simulators by default,
            or an AllClose Tolerance routine result if `method` is set to `proximity`.

            Args:
                outputs: list of output arrays.
                simulators: list of simulator names.
                method: pass one of either: `mse` to perform a mean-squared error calculation
                    or `proximity` to perform a pair-wise proximity tolerance test using `np.allclose(outputs[i], outputs[i+1])`.
                rtol:`float`: relative tolerance for comparison if `proximity` is used.
                atol:`float`: absolute tolerance for comparison if `proximity` is used.
                ground_truth: If passed, this value is compared against each simulator in simulators. Currently, this
                    field is agnostic to any verified/validated source, and we trust that the user has verified it. Defaults
                    to `None`.

            Returns:
                Pandas dataframe representing a comparison matrix where `i` and `j` are both indexed by the
                    simulators involved. The aforementioned simulators involved will also include the `ground_truth` value
                    within the indices if one is passed.
        """
        # TODO: implement the ground truth
        _simulators = simulators.copy()
        _outputs = outputs.copy()
        if isinstance(_outputs, np.ndarray):
            _outputs = _outputs.tolist()
        if ground_truth is not None:
            _simulators.append('expected_results')
            _outputs.append(ground_truth)
        use_tol_method = method.lower() == 'proximity'
        matrix_dtype = np.float64 if not use_tol_method else bool
        num_simulators = len(_simulators)
        mse_matrix = np.zeros((num_simulators, num_simulators), dtype=matrix_dtype)
        # fill the matrices with the calculated values
        for i in range(len(_simulators)):
            for j in range(i, len(_simulators)):
                try:
                    output_i = _outputs[i]
                    output_j = _outputs[j]
                    method_type = method.lower()
                    if not isinstance(output_i, str) and not isinstance(output_j, str):
                        result = self.calculate_mse(output_i, output_j) if method_type == 'mse' else self.compare_arrays(arr1=output_i, arr2=output_j, rtol=rtol, atol=atol)
                        mse_matrix[i, j] = result
                except ValueError:
                    error = handle_sbml_exception()
                    mse_matrix[i, j] = error
                if i != j:
                    mse_matrix[j, i] = mse_matrix[i, j]
        return pd.DataFrame(mse_matrix, index=_simulators, columns=_simulators)

    def calculate_mse(self, a, b) -> np.float64:
        if isinstance(a, list):
            a = np.array(a)
        if isinstance(b, list):
            b = np.array(b)
        return np.mean((a - b) ** 2)

    def compare_arrays(self, arr1: np.ndarray, arr2: np.ndarray, atol=None, rtol=None) -> bool:
        """Original methodology copied from biosimulations runutils."""
        max1 = max(arr1)
        max2 = max(arr2)
        aTol = atol or max(1e-3, max1 * 1e-5, max2 * 1e-5)
        rTol = rtol or 1e-4
        return np.allclose(arr1, arr2, rtol=rTol, atol=aTol)
