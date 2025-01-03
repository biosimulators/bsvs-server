import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, UTC
from pathlib import Path
from typing import *
from typing import List

import dotenv
import uvicorn
from fastapi import FastAPI, File, UploadFile, Query, APIRouter, Depends, HTTPException
from starlette.middleware.cors import CORSMiddleware

from archive.shared.data_model import DEV_ENV_PATH
from biosim_server.database.database_service import DatabaseService, DocumentNotFoundError
from biosim_server.database.models import VerificationRun, JobStatus, VerificationOutput
from biosim_server.dependencies import get_database_service, get_biosim_service, get_file_service, get_temporal_client, \
    init_standalone, shutdown_standalone
from biosim_server.log_config import setup_logging
from biosim_server.workflows.omex_verify_workflow import OmexVerifyWorkflow

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
    await init_standalone()
    yield
    await shutdown_standalone()


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
    dependencies=[Depends(get_database_service), Depends(get_temporal_client), Depends(get_file_service)],
    summary="Compare UTC outputs from a deterministic SBML model within an OMEX/COMBINE archive.")
async def verify(
        uploaded_file: UploadFile = File(..., description="OMEX/COMBINE archive containing a deterministic SBML model"),
        simulators: List[str] = Query(default=["amici", "copasi", "pysces", "tellurium", "vcell"],
                                      description="List of simulators to compare"),
        include_outputs: bool = Query(default=True,
                                      description="Whether to include the output data on which the comparison is based."),
        observables: Optional[List[str]] = Query(default=None,
                                                 description="List of observables to include in the return data."),
        comparison_id: Optional[str] = Query(default=None,
                                             description="Descriptive prefix to be added to this submission's job ID."),
        # expected_results: Optional[UploadFile] = File(default=None, description="reports.h5 file defining the expected results to be included in the comparison."),
        rTol: Optional[float] = Query(default=None, description="Relative tolerance to use for proximity comparison."),
        aTol: Optional[float] = Query(default=None, description="Absolute tolerance to use for proximity comparison.")
) -> VerificationRun:
    # save uploaded file to temporary file
    save_dest = Path(os.path.join(os.getcwd(), "temp"))
    save_dest.mkdir(parents=True, exist_ok=True)
    local_path: Path = await save_uploaded_file(uploaded_file, save_dest)

    # upload to cloud storage
    file_service = get_file_service()
    assert file_service is not None
    s3_path: str = await file_service.upload_file(local_path, local_path.name)
    logger.info(f"Uploaded file to S3 at {s3_path}")

    # remove temporary file
    local_path.unlink()

    timestamp = str(datetime.now(UTC))
    generated_job_id = "verification-" + str(uuid.uuid4())
    workflow_id = uuid.uuid4().hex
    run = VerificationRun(
        job_id=generated_job_id,
        status=str(JobStatus.PENDING.value),
        omex_path=s3_path,
        requested_simulators=simulators,
        observables=observables,
        comparison_id=comparison_id,
        timestamp=timestamp,
        include_outputs=include_outputs,
        rTol=rTol,
        aTol=aTol,
        workflow_id=workflow_id,
        # expected_results=report_location,
    )

    # save to database
    database_service = get_database_service()
    assert database_service is not None
    await database_service.insert_verification_run(run)
    logger.info(f"saved VerificationRun to database for Job_id {generated_job_id}")

    # invoke workflow
    logger.info(f"starting workflow with id {workflow_id}")
    temporal_client = get_temporal_client()
    _handle = await temporal_client.execute_workflow(
        OmexVerifyWorkflow.run,
        args=[s3_path, simulators],
        task_queue="verification_tasks",
        id=workflow_id,
    )
    logger.info(f"started workflow with id {workflow_id}")

    return run


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


async def save_uploaded_file(uploaded_file2: UploadFile, save_dest: Path) -> Path:
    """Write `fastapi.UploadFile` instance passed by api gateway user to `save_dest`."""
    filename = uploaded_file2.filename or (uuid.uuid4().hex + ".omex")
    file_path = save_dest / filename
    with open(file_path, 'wb') as file:
        contents = await uploaded_file2.read()
        file.write(contents)
    return file_path


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
    logger.info("Server started")
