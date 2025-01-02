from enum import Enum
from typing import Optional

from pydantic import BaseModel

from biosim_server.biosim1.models import Hdf5DataValues


class JobStatus(Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class VerificationRun(BaseModel):
    job_id: str
    timestamp: str
    status: str
    omex_path: str
    requested_simulators: list[str]
    include_outputs: Optional[bool] = True
    observables: Optional[list[str]] = None
    # expected_results: Optional[str] = None
    comparison_id: Optional[str] = None
    rTol: Optional[float] = None
    aTol: Optional[float] = None

class SimulatorRMSE(BaseModel):
    simulator1: str
    simulator2: str
    rmse_scores: dict[str, float]

class VerificationOutput(BaseModel):
    job_id: str
    timestamp: str
    status: str
    omex_path: Optional[str] = None
    requested_simulators: Optional[list[str]] = None
    observables: Optional[list[str]] = None
    sim_results: Optional[list[dict[str, Hdf5DataValues]]] = None
    compare_results: Optional[list[SimulatorRMSE]] = None
