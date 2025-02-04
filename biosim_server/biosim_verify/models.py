from typing import Optional

from pydantic import BaseModel


class ComparisonStatistics(BaseModel):
    dataset_name: str
    simulator_version_i: str  # version of simulator used for run i <simulator_name>:<version>
    simulator_version_j: str  # version of simulator used for run j <simulator_name>:<version>
    var_names: list[str]
    score: Optional[list[float]] = None
    is_close: Optional[list[bool]] = None
    error_message: Optional[str] = None


class CompareSettings(BaseModel):
    user_description: str
    include_outputs: bool
    rel_tol: float
    abs_tol_min: float
    abs_tol_scale: float
    observables: Optional[list[str]] = None

# class CompareReport(BaseModel):
#     omex_file: OmexFile
#     simulator1: BiosimulatorVersion
#     simulator2: BiosimulatorVersion
#     stats: ComparisonStatistics
#
# class SimulatorComparison(BaseModel):
#     simRun1: BiosimSimulationRun
#     simRun2: BiosimSimulationRun
#     equivalent: bool
