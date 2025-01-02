import logging
from abc import ABC, abstractmethod

from biosim_server.biosim1.models import SourceOmex, Simulator, SimulationRun, HDF5File, Hdf5DataValues, \
    SimulationRunStatus

logger = logging.getLogger(__name__)

class BiosimService(ABC):

    @abstractmethod
    async def check_run_status(self, simulation_run_id: str) -> SimulationRunStatus:
        pass

    @abstractmethod
    async def run_project(self, source_omex: SourceOmex, simulator: Simulator, simulator_version: str) -> SimulationRun:
        pass

    @abstractmethod
    async def get_hdf5_metadata(self, simulation_run_id: str) -> HDF5File:
        pass

    @abstractmethod
    async def get_hdf5_data(self, simulation_run_id: str, dataset_name: str) -> Hdf5DataValues:
        pass
