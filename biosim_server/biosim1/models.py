from dataclasses import dataclass
from enum import Enum
from typing import Optional

from pydantic import BaseModel

ATTRIBUTE_VALUE_TYPE = int | float | str | bool | list[str] | list[int] | list[float] | list[bool]


class HDF5Attribute(BaseModel):
    key: str
    value: ATTRIBUTE_VALUE_TYPE


class HDF5Dataset(BaseModel):
    name: str
    shape: list[int]
    attributes: list[HDF5Attribute]


class HDF5Group(BaseModel):
    name: str
    attributes: list[HDF5Attribute]
    datasets: list[HDF5Dataset]


class HDF5File(BaseModel):
    filename: str
    id: str
    uri: str
    groups: list[HDF5Group]


@dataclass
class Hdf5DataValues:
    # simulation_run_id: str
    # dataset_name: str
    shape: list[int]
    values: list[float]


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
class SourceOmex:
    name: str
    omex_s3_file: str


@dataclass
class SimulatorSpec:
    simulator: str
    version: Optional[str] = None


@dataclass
class SimulationRunApiRequest:
    name: str  # what does this correspond to?
    simulator_spec: SimulatorSpec
    maxTime: int  # in minutes
    # email: Optional[str] = None
    # cpus: Optional[int] = None
    # memory: Optional[int] = None (in GB)


@dataclass
class SimulationRun:
    simulator_spec: SimulatorSpec
    simulation_id: str
    project_id: str
    status: Optional[str] = "Unknown"


@dataclass
class SimulatorComparison:
    project_id: str
    simRun1: SimulationRun
    simRun2: SimulationRun
    equivalent: bool
