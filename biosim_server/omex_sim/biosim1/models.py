from dataclasses import dataclass
from enum import Enum, StrEnum
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


class BiosimSimulationRunStatus(StrEnum):
    QUEUED = 'QUEUED',
    RUNNING = 'RUNNING',
    SKIPPED = 'SKIPPED',
    SUCCEEDED = 'SUCCEEDED',
    FAILED = 'FAILED',
    UNKNOWN = 'UNKNOWN'


@dataclass
class SourceOmex:
    name: str
    omex_s3_file: str


@dataclass
class BiosimSimulatorSpec:
    simulator: str
    version: Optional[str] = None


@dataclass
class BiosimSimulationRunApiRequest:
    name: str  # what does this correspond to?
    simulator_spec: BiosimSimulatorSpec
    maxTime: int  # in minutes
    # email: Optional[str] = None
    # cpus: Optional[int] = None
    # memory: Optional[int] = None (in GB)


@dataclass
class BiosimSimulationRun:
    simulator_spec: BiosimSimulatorSpec
    simulation_id: str
    status: Optional[BiosimSimulationRunStatus] = BiosimSimulationRunStatus.UNKNOWN


@dataclass
class SimulatorComparison:
    simRun1: BiosimSimulationRun
    simRun2: BiosimSimulationRun
    equivalent: bool
