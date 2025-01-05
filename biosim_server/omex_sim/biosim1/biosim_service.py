import logging
from abc import ABC, abstractmethod

from biosim_server.omex_sim.biosim1.models import SimulationRun, HDF5File, Hdf5DataValues, SimulationRunStatus, SimulatorSpec

logger = logging.getLogger(__name__)

class BiosimService(ABC):

    @abstractmethod
    async def check_run_status(self, simulation_run_id: str) -> SimulationRunStatus:
        pass

    @abstractmethod
    async def run_project(self, local_omex_path: str, omex_name: str, simulator_spec: SimulatorSpec) -> SimulationRun:
        pass

    @abstractmethod
    async def get_hdf5_metadata(self, simulation_run_id: str) -> HDF5File:
        pass

    @abstractmethod
    async def get_hdf5_data(self, simulation_run_id: str, dataset_name: str) -> Hdf5DataValues:
        pass

    @abstractmethod
    async def close(self) -> None:
        pass
