import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, UTC
from typing import *
from typing import List

import dotenv
import uvicorn
from fastapi import FastAPI, File, UploadFile, Query, APIRouter, Depends, HTTPException
from starlette.middleware.cors import CORSMiddleware

from archive.shared.data_model import DEV_ENV_PATH
from biosim_server.database.database_service import DatabaseService, DocumentNotFoundError
from biosim_server.database.models import VerificationRun, JobStatus, VerificationOutput
from biosim_server.dependencies import get_database_service, get_biosim_service, get_file_service, init_standalone
from biosim_server.log_config import setup_logging

logger = logging.getLogger(__name__)
setup_logging(logger)


# -- load dev env -- #
dotenv.load_dotenv(DEV_ENV_PATH)  # NOTE: create an env config at this filepath if dev


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
APP_TITLE = "bsvs-server"
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
APP_SERVERS: list[dict[str, str]] = [
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    # set up resources (e.g. create mongodb client)
    yield
    # clean up resources (e.g. shutdown mongodb client)


app = FastAPI(title=APP_TITLE, version=APP_VERSION, servers=APP_SERVERS, lifespan=lifespan)

# add origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=APP_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"])

# -- endpoint logic -- #

@app.get("/")
def root():
    return {
        'docs': 'https://biochecknet.biosimulations.org/docs'
    }


@app.post(
    "/verify",
    response_model=VerificationRun,
    name="Uniform Time Course Comparison from OMEX/COMBINE archive",
    operation_id="verify",
    tags=["Verification"],
    dependencies=[Depends(get_database_service), Depends(get_biosim_service), Depends(get_file_service)],
    summary="Compare UTC outputs from a deterministic SBML model within an OMEX/COMBINE archive.")
async def verify(
        uploaded_file: UploadFile = File(..., description="OMEX/COMBINE archive containing a deterministic SBML model"),
        simulators: List[str] = Query(default=["amici", "copasi", "pysces", "tellurium", "vcell"], description="List of simulators to compare"),
        include_outputs: bool = Query(default=True, description="Whether to include the output data on which the comparison is based."),
        observables: Optional[List[str]] = Query(default=None, description="List of observables to include in the return data."),
        comparison_id: Optional[str] = Query(default=None, description="Descriptive prefix to be added to this submission's job ID."),
        # expected_results: Optional[UploadFile] = File(default=None, description="reports.h5 file defining the expected results to be included in the comparison."),
        rTol: Optional[float] = Query(default=None, description="Relative tolerance to use for proximity comparison."),
        aTol: Optional[float] = Query(default=None, description="Absolute tolerance to use for proximity comparison.")
) -> VerificationRun:

    # TODO: this is a placeholder - needs an implementation

    timestamp = str(datetime.now(UTC))
    path = "path/to/omex"
    generated_job_id = "verification-" + str(uuid.uuid4())
    run = VerificationRun(
        job_id=generated_job_id,
        status=str(JobStatus.PENDING.value),
        omex_path=path,
        requested_simulators=simulators,
        timestamp=timestamp,
        include_outputs=include_outputs,
        rTol=rTol,
        aTol=aTol,
        observables=observables,
        # expected_results=report_location,
    )
    return run
    # uploaded_file.
    # get_file_service().upload_file(uploaded_file, uploaded_file.filename)
    # try:
    #     # request specific params
    #     if comparison_id is None:
    #         compare_id = "utc_comparison_omex"
    #     else:
    #         compare_id = comparison_id
    #     job_id = "verification-" + compare_id + "-" + str(uuid.uuid4())
    #     _time = db_connector.timestamp()
    #     upload_prefix, bucket_prefix = file_upload_prefix(job_id, BUCKET_NAME)
    #     save_dest = mkdtemp()
    #     fp = await save_uploaded_file(uploaded_file, save_dest)  # save uploaded file to ephemeral store
    #
    #     # Save uploaded omex file to Google Cloud Storage
    #     uploaded_file_location = None
    #     properly_formatted_omex = check_upload_file_extension(uploaded_file, 'uploaded_file', '.omex')
    #     if properly_formatted_omex:
    #         blob_dest = upload_prefix + fp.split("/")[-1]
    #         upload_blob(bucket_name=BUCKET_NAME, source_file_name=fp, destination_blob_name=blob_dest)
    #         uploaded_file_location = blob_dest
    #     # Save uploaded reports file to Google Cloud Storage if applicable
    #     # report_fp = None
    #     # report_blob_dest = None
    #     # if expected_results:
    #     #     # handle incorrect files upload
    #     #     properly_formatted_report = check_upload_file_extension(expected_results, 'expected_results', '.h5')
    #     #     if properly_formatted_report:
    #     #         report_fp = await save_uploaded_file(expected_results, save_dest)
    #     #         report_blob_dest = upload_prefix + report_fp.split("/")[-1]
    #     #     upload_blob(bucket_name=BUCKET_NAME, source_file_name=report_fp, destination_blob_name=report_blob_dest)
    #     # report_location = report_blob_dest
    #
    #     # instantiate new omex verification
    #     omex_verification = VerificationRun(
    #         status=JobStatus.PENDING.value,
    #         job_id=job_id,
    #         path=uploaded_file_location,
    #         simulators=simulators,
    #         timestamp=_time,
    #         include_outputs=include_outputs,
    #         rTol=rTol,
    #         aTol=aTol,
    #         selection_list=selection_list,
    #         # expected_results=report_location,
    #     )
    #
    #     # insert pending job with verification object fields
    #     pending_job_doc = await db_connector.insert_job_async(
    #         collection_name=DatabaseCollections.PENDING_JOBS.value,
    #         status=omex_verification.status,
    #         job_id=omex_verification.job_id,
    #         path=omex_verification.path,
    #         simulators=omex_verification.simulators,
    #         timestamp=omex_verification.timestamp,
    #         include_outputs=omex_verification.include_outputs,
    #         rTol=omex_verification.rTol,
    #         aTol=omex_verification.aTol,
    #         selection_list=omex_verification.selection_list,
    #         # expected_results=omex_verification.expected_results,
    #     )
    #
    #     # clean up local temp files
    #     os.remove(fp)
    #     # if report_fp:
    #     # os.remove(report_fp)
    #
    #     return omex_verification
    # except Exception as e:
    #     logger.error(str(e))
    #     raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/get-output/{job_id}",
    response_model=VerificationOutput,
    operation_id='get-output',
    tags=["Results"],
    dependencies=[Depends(get_database_service), Depends(get_biosim_service), Depends(get_file_service)],
    summary='Get the results of an existing verification run.')
async def get_output(job_id: str) -> VerificationOutput:
    logger.info(f"in get /get-output/{job_id}")
    database_service: DatabaseService | None = get_database_service()
    assert database_service is not None

    try:
        verification_run: VerificationRun = await database_service.get_verification_run(job_id)

        if verification_run is not None:
            return VerificationOutput(
                job_id=job_id,
                timestamp=verification_run.timestamp,
                status=verification_run.status,
                omex_path=verification_run.omex_path,
                requested_simulators=verification_run.requested_simulators,
                observables=verification_run.observables,
                sim_results=None
            )
    except DocumentNotFoundError as e1:
        msg = f"Job with id: {job_id} not found. Please check the job_id and try again."
        logger.warning(msg, exc_info=e1)
        raise HTTPException(status_code=404, detail=msg)
    except Exception as e2:
        exc_message = str(e2)
        msg = f"error retrieving verification job output with id: {job_id}: {exc_message}"
        logger.error(msg, exc_info=e2)
        raise HTTPException(status_code=404, detail=msg)

if __name__ == "__main__":
    init_standalone()
    uvicorn.run(app, host="0.0.0.0", port=8000)
    logger.info("Server started")


