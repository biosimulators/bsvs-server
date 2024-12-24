import os
from dataclasses import asdict, dataclass
from enum import Enum
from typing import *

import numpy as np
from dotenv import load_dotenv
from pydantic import BaseModel as _BaseModel, ConfigDict


# for dev only
load_dotenv('../assets/dev/config/.env_dev')


DB_TYPE = "mongo"  # ie: postgres, etc
DB_NAME = "service_requests"
BUCKET_NAME = os.getenv("BUCKET_NAME")


# -- base models --

class BaseModel(_BaseModel):
    """Base Pydantic Model with custom app configuration"""
    model_config = ConfigDict(arbitrary_types_allowed=True)


@dataclass
class BaseClass:
    """Base Python Dataclass multipurpose class with custom app configuration."""
    def to_dict(self):
        return asdict(self)


class JobStatus(Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class DatabaseCollections(Enum):
    PENDING_JOBS = "PENDING_JOBS".lower()
    IN_PROGRESS_JOBS = "IN_PROGRESS_JOBS".lower()
    COMPLETED_JOBS = "COMPLETED_JOBS".lower()


class MultipleConnectorError(Exception):
    def __init__(self, message: str):
        self.message = message


# -- jobs --

class VerificationRun(BaseModel):
    job_id: str
    timestamp: str
    status: str
    path: str
    simulators: List[str]
    include_outputs: Optional[bool] = True
    selection_list: Optional[List[str]] = None
    # expected_results: Optional[str] = None
    comparison_id: Optional[str] = None
    rTol: Optional[float] = None
    aTol: Optional[float] = None


class OmexVerificationRun(VerificationRun):
    pass


# -- data --

# TODO: parse results and make object specs
class ObservableData(BaseModel):
    observable_name: str
    mse: Dict[str, Any]
    proximity: Dict[str, Any]
    output_data: Dict[str, Union[List[float], str]]


class SimulatorRMSE(BaseModel):
    simulator: str
    rmse_scores: Dict[str, float]


class Output(BaseModel):
    job_id: str
    timestamp: str
    status: str
    source: Optional[str] = None


class VerificationOutput(Output):
    """
    Return schema for get-verification-output.

    Parameters:
        job_id: str
        timestamp: str
        status: str --> may be COMPLETE, IN_PROGRESS, FAILED, or PENDING
        source: str
        requested_simulators: List[str]
        results: Optional[dict] = None TODO: parse this
    """
    requested_simulators: Optional[List[str]] = None
    results: Optional[Union[List[Union[ObservableData, SimulatorRMSE, Any]], Dict[str, Any]]] = None


@dataclass
class BiosimulationsReportOutput(BaseClass):
    dataset_label: str
    data: np.ndarray


@dataclass
class BiosimulationsRunOutputData(BaseClass):
    report_path: str
    data: List[BiosimulationsReportOutput]


# -- extras --

class DbClientResponse(BaseModel):
    message: str
    db_type: str  # ie: 'mongo', 'postgres', etc
    timestamp: str


class Simulator(BaseModel):
    name: str
    version: Optional[str] = None


class CompatibleSimulators(BaseModel):
    file: str
    simulators: List[Simulator]





