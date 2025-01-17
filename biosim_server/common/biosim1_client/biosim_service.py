import logging
from abc import ABC, abstractmethod

from biosim_server.common.biosim1_client.models import BiosimSimulationRun, HDF5File, Hdf5DataValues, BiosimSimulatorSpec

logger = logging.getLogger(__name__)

class BiosimService(ABC):

    @abstractmethod
    async def get_sim_run(self, simulation_run_id: str) -> BiosimSimulationRun:
        pass

    @abstractmethod
    async def run_biosim_sim(self, local_omex_path: str, omex_name: str, simulator_spec: BiosimSimulatorSpec) -> BiosimSimulationRun:
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
