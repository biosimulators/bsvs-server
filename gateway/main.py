import os
import logging
import uuid
from typing import *
from tempfile import mkdtemp

import dotenv
import uvicorn
from fastapi import FastAPI, File, UploadFile, HTTPException, Query, APIRouter, Body
from fastapi.responses import FileResponse
from pydantic import BeforeValidator
from starlette.middleware.cors import CORSMiddleware

from shared.database import MongoDbConnector
from shared.io import save_uploaded_file, check_upload_file_extension, download_file_from_bucket
from shared.log_config import setup_logging
from shared.data_model import (
    VerificationOutput,
    OmexVerificationRun,
    DbClientResponse,
    CompatibleSimulators,
    Simulator
)

from gateway.compatible import COMPATIBLE_VERIFICATION_SIMULATORS


logger = logging.getLogger("verification-server.api.main.log")
setup_logging(logger)


# -- load dev env -- #

dotenv.load_dotenv("../assets/dev/config/.env_dev")  # NOTE: create an env config at this filepath if dev


# -- constraints -- #

version_path = os.path.join(
    os.path.dirname(__file__),
    ".VERSION"
)
if os.path.exists(version_path):
    with open(version_path, 'r') as f:
        APP_VERSION = f.read().strip()
else:
    APP_VERSION = "0.0.1"

MONGO_URI = os.getenv("MONGO_URI")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
APP_TITLE = "verification-server"
APP_ORIGINS = [
    'http://127.0.0.1:8000',
    'http://127.0.0.1:4200',
    'http://127.0.0.1:4201',
    'http://127.0.0.1:4202',
    'http://localhost:4200',
    'http://localhost:4201',
    'http://localhost:4202',
    'http://localhost:8000',
    'http://localhost:3001',
    'https://biosimulators.org',
    'https://www.biosimulators.org',
    'https://biosimulators.dev',
    'https://www.biosimulators.dev',
    'https://run.biosimulations.dev',
    'https://run.biosimulations.org',
    'https://biosimulations.dev',
    'https://biosimulations.org',
    'https://bio.libretexts.org',
    'https://biochecknet.biosimulations.org'
]
APP_SERVERS = [
    # {
    #     "url": "https://biochecknet.biosimulations.org",
    #     "description": "Production server"
    # },
    # {
    #     "url": "http://localhost:3001",
    #     "description": "Main Development server"
    # },
    # {
    #     "url": "http://localhost:8000",
    #     "description": "Alternate Development server"
    # }
]

# -- app components -- #

router = APIRouter()
app = FastAPI(title=APP_TITLE, version=APP_VERSION, servers=APP_SERVERS)

# add origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=APP_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"])

# add servers
# app.servers = APP_SERVERS


# -- mongo db -- #

db_connector = MongoDbConnector(connection_uri=MONGO_URI, database_id=DB_NAME)
app.mongo_client = db_connector.client

# It will be represented as a `str` on the model so that it can be serialized to JSON. Represents an ObjectId field in the database.
PyObjectId = Annotated[str, BeforeValidator(str)]


# -- initialization logic --

@app.on_event("startup")
def start_client() -> DbClientResponse:
    """TODO: generalize this to work with multiple client types. Currently using Mongo."""
    _time = db_connector.timestamp()
    try:
        app.mongo_client.admin.command('ping')
        msg = "Pinged your deployment. You successfully connected to MongoDB!"
    except Exception as e:
        msg = f"Failed to connect to MongoDB:\n{e}"
    return DbClientResponse(message=msg, db_type=DB_TYPE, timestamp=_time)


@app.on_event("shutdown")
def stop_mongo_client() -> DbClientResponse:
    _time = db_connector.timestamp()
    app.mongo_client.close()
    return DbClientResponse(message=f"{DB_TYPE} successfully closed!", db_type=DB_TYPE, timestamp=_time)


# -- endpoint logic -- #

@app.get("/")
def root():
    return {'root': 'https://biochecknet.biosimulations.org',
            'FOR MORE': 'https://biochecknet.biosimulations.org/docs'}


@app.post(
    "/verify",
    response_model=OmexVerificationRun,
    name="Uniform Time Course Comparison from OMEX/COMBINE archive",
    operation_id="verify",
    tags=["Verification"],
    summary="Compare UTC outputs from a deterministic SBML model within an OMEX/COMBINE archive.")
async def verify(
        uploaded_file: UploadFile = File(..., description="OMEX/COMBINE archive containing a deterministic SBML model"),
        simulators: List[str] = Query(default=["amici", "copasi", "pysces", "tellurium"], description="List of simulators to compare"),
        include_outputs: bool = Query(default=True, description="Whether to include the output data on which the comparison is based."),
        selection_list: Optional[List[str]] = Query(default=None, description="List of observables to include in the return data."),
        comparison_id: Optional[str] = Query(default=None, description="Descriptive prefix to be added to this submission's job ID."),
        # expected_results: Optional[UploadFile] = File(default=None, description="reports.h5 file defining the expected results to be included in the comparison."),
        rTol: Optional[float] = Query(default=None, description="Relative tolerance to use for proximity comparison."),
        aTol: Optional[float] = Query(default=None, description="Absolute tolerance to use for proximity comparison.")
) -> OmexVerificationRun:
    try:
        # request specific params
        if comparison_id is None:
            compare_id = "utc_comparison_omex"
        else:
            compare_id = comparison_id
        job_id = "verification-" + compare_id + "-" + str(uuid.uuid4())
        _time = db_connector.timestamp()
        upload_prefix, bucket_prefix = file_upload_prefix(job_id)
        save_dest = mkdtemp()
        fp = await save_uploaded_file(uploaded_file, save_dest)  # save uploaded file to ephemeral store

        # Save uploaded omex file to Google Cloud Storage
        uploaded_file_location = None
        properly_formatted_omex = check_upload_file_extension(uploaded_file, 'uploaded_file', '.omex')
        if properly_formatted_omex:
            blob_dest = upload_prefix + fp.split("/")[-1]
            upload_blob(bucket_name=BUCKET_NAME, source_file_name=fp, destination_blob_name=blob_dest)
            uploaded_file_location = blob_dest
        # Save uploaded reports file to Google Cloud Storage if applicable
        # report_fp = None
        # report_blob_dest = None
        # if expected_results:
        #     # handle incorrect files upload
        #     properly_formatted_report = check_upload_file_extension(expected_results, 'expected_results', '.h5')
        #     if properly_formatted_report:
        #         report_fp = await save_uploaded_file(expected_results, save_dest)
        #         report_blob_dest = upload_prefix + report_fp.split("/")[-1]
        #     upload_blob(bucket_name=BUCKET_NAME, source_file_name=report_fp, destination_blob_name=report_blob_dest)
        # report_location = report_blob_dest

        # instantiate new omex verification
        omex_verification = OmexVerificationRun(
            status=JobStatus.PENDING.value,
            job_id=job_id,
            path=uploaded_file_location,
            simulators=simulators,
            timestamp=_time,
            include_outputs=include_outputs,
            rTol=rTol,
            aTol=aTol,
            selection_list=selection_list,
            # expected_results=report_location,
        )

        # insert pending job with verification object fields
        pending_job_doc = await db_connector.insert_job_async(
            collection_name=DatabaseCollections.PENDING_JOBS.value,
            status=omex_verification.status,
            job_id=omex_verification.job_id,
            path=omex_verification.path,
            simulators=omex_verification.simulators,
            timestamp=omex_verification.timestamp,
            include_outputs=omex_verification.include_outputs,
            rTol=omex_verification.rTol,
            aTol=omex_verification.aTol,
            selection_list=omex_verification.selection_list,
            # expected_results=omex_verification.expected_results,
        )

        # clean up local temp files
        os.remove(fp)
        # if report_fp:
        # os.remove(report_fp)

        return omex_verification
    except Exception as e:
        logger.error(str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/get-output-file/{job_id}",
    operation_id='get-output-file',
    tags=["Results"],
    summary='Get the results of an existing simulation run from Smoldyn or Readdy as either a downloadable file or job progression status.'
)
async def get_output_file(job_id: str):
    # state-case: job is completed
    if not job_id.startswith("simulation-execution"):
        raise HTTPException(status_code=404, detail="This must be an output file job query starting with 'simulation-execution'.")

    job = await db_connector.read(collection_name="completed_jobs", job_id=job_id)
    if job is not None:
        # rm mongo index
        job.pop('_id', None)

        # parse filepath in bucket and create file response
        job_data = job
        if isinstance(job_data, dict):
            remote_fp = job_data.get("results").get("results_file")
            if remote_fp is not None:
                temp_dest = mkdtemp()
                local_fp = download_file_from_bucket(source_blob_path=remote_fp, out_dir=temp_dest, bucket_name=BUCKET_NAME)

                # return downloadable file blob
                return FileResponse(path=local_fp, media_type="application/octet-stream", filename=local_fp.split("/")[-1])  # TODO: return special smoldyn file instance

    # state-case: job has failed
    if job is None:
        job = await db_connector.read(collection_name="failed_jobs", job_id=job_id)

    # state-case: job is not in completed:
    if job is None:
        job = await db_connector.read(collection_name="in_progress_jobs", job_id=job_id)

    # state-case: job is not in progress:
    if job is None:
        job = await db_connector.read(collection_name="pending_jobs", job_id=job_id)

    # case: job is either failed, in prog, or pending
    if job is not None:
        # rm mongo index
        job.pop('_id', None)

        # specify source safely
        src = job.get('source', job.get('path'))
        if src is not None:
            source = src.split('/')[-1]
        else:
            source = None

        # return json job status
        return IncompleteJob(
            job_id=job_id,
            timestamp=job.get('timestamp'),
            status=job.get('status'),
            source=source
        )


@app.get(
    "/get-verification-output/{job_id}",
    response_model=VerificationOutput,
    operation_id='get-verification-output',
    tags=["Results"],
    summary='Get the results of an existing verification run.')
async def get_verification_output(job_id: str) -> VerificationOutput:
    if "verification" not in job_id:
        raise HTTPException(status_code=404, detail="This must be a verification job query.")

    # state-case: job is completed
    job = await db_connector.read(collection_name="completed_jobs", job_id=job_id)

    # state-case: job has failed
    if job is None:
        job = await db_connector.read(collection_name="failed_jobs", job_id=job_id)

    # state-case: job is not in completed:
    if job is None:
        job = await db_connector.read(collection_name="in_progress_jobs", job_id=job_id)

    # state-case: job is not in progress:
    if job is None:
        job = await db_connector.read(collection_name="pending_jobs", job_id=job_id)

    if job is not None:
        job.pop('_id', None)
        results = job.get('results')
        # data = []
        # if results is not None:
        #     for name, obs_data in results.items():
        #         if not name == "rmse":
        #             obs = ObservableData(observable_name=name, mse=obs_data['mse'], proximity=obs_data['proximity'], output_data=obs_data['output_data'])
        #             data.append(obs)
        #         else:
        #             for simulator_name, data_table in obs_data.items():
        #                 obs = SimulatorRMSE(simulator=simulator_name, rmse_scores=data_table)
        #                 data.append(obs)

        output = VerificationOutput(
            job_id=job_id,
            timestamp=job.get('timestamp'),
            status=job.get('status'),
            source=job.get('source', job.get('path')).split('/')[-1],
            # results=data,  # Change this to the results below if there is an issue
            results=results
        )
        requested_simulators = job.get('simulators', job.get('requested_simulators'))
        if requested_simulators is not None:
            output.requested_simulators = requested_simulators

        return output
    else:
        msg = f"Job with id: {job_id} not found. Please check the job_id and try again."
        logger.error(msg)
        raise HTTPException(status_code=404, detail=msg)


@app.post(
    "/get-compatible-for-verification",
    response_model=CompatibleSimulators,
    operation_id='get-compatible-for-verification',
    tags=["Files"],
    summary='Get the simulators that are compatible with either a given OMEX/COMBINE archive or SBML model simulation.')
async def get_compatible_for_verification(
        uploaded_file: UploadFile = File(..., description="Either a COMBINE/OMEX archive or SBML file to be simulated."),
        versions: bool = Query(default=False, description="Whether to include the simulator versions for each compatible simulator."),
) -> CompatibleSimulators:
    try:
        filename = uploaded_file.filename
        simulators = COMPATIBLE_VERIFICATION_SIMULATORS.copy()  # TODO: dynamically extract this!
        compatible_sims = []
        for data in simulators:
            name = data[0]
            version = data[1]
            sim = Simulator(name=name, version=version if versions is not False else None)
            compatible_sims.append(sim)

        return CompatibleSimulators(file=uploaded_file.filename, simulators=compatible_sims)
    except Exception as e:
        raise HTTPException(status_code=404, detail="Comparison not found")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)


