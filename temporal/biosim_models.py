from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional


class SimulationRunStatus(str, Enum):
    QUEUED = 'QUEUED',
    RUNNING = 'RUNNING',
    SKIPPED = 'SKIPPED',
    SUCCEEDED = 'SUCCEEDED',
    FAILED = 'FAILED',
    UNKNOWN = 'UNKNOWN'

    # add method to get status from string
    @classmethod
    def from_str(cls, status: str) -> 'SimulationRunStatus':
        switcher = {
            "QUEUED": cls.QUEUED,
            "RUNNING": cls.RUNNING,
            "SKIPPED": cls.SKIPPED,
            "SUCCEEDED": cls.SUCCEEDED,
            "FAILED": cls.FAILED,
            "UNKNOWN": cls.UNKNOWN
        }
        return switcher.get(status, cls.UNKNOWN)


@dataclass
class SimulationRunApiRequest:
    name: str  # what does this correspond to?
    simulator: str
    simulatorVersion: str
    maxTime: int  # in minutes
    # email: Optional[str] = None
    # cpus: Optional[int] = None
    # memory: Optional[int] = None (in GB)


@dataclass
class SourceOmex:
    name: str
    omex_file: Path


@dataclass
class Simulator(str, Enum):
    tellurium = "tellurium",
    copasi = "copasi",
    amici = "amici",
    vcell = "vcell",
    pysces = "pysces",
    libsbmlsim = "libsbmlsim"


@dataclass
class SimulationRun:
    simulator: Simulator
    simulator_version: str
    simulation_id: str
    project_id: str
    status: Optional[str] = "Unknown"


@dataclass
class SimulatorComparison:
    project_id: str
    simRun1: SimulationRun
    simRun2: SimulationRun
    equivalent: bool
