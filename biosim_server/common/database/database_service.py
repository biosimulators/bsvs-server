from abc import abstractmethod, ABC

from biosim_server.common.database.data_models import OmexFile, BiosimulatorWorkflowRun


class DocumentNotFoundError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class DatabaseService(ABC):
    @abstractmethod
    async def insert_omex_file(self, omex_file: OmexFile) -> OmexFile:
        pass

    @abstractmethod
    async def get_omex_file(self, file_hash_md5: str) -> OmexFile | None:
        pass

    @abstractmethod
    async def delete_omex_file(self, database_id: str) -> None:
        pass

    @abstractmethod
    async def delete_all_omex_files(self) -> None:
        pass

    @abstractmethod
    async def list_omex_files(self) -> list[OmexFile]:
        pass

    @abstractmethod
    async def close(self) -> None:
        pass

    @abstractmethod
    async def insert_biosimulator_workflow_run(self, sim_workflow_run: BiosimulatorWorkflowRun) -> BiosimulatorWorkflowRun:
        pass

    @abstractmethod
    async def get_biosimulator_workflow_runs(self, file_hash_md5: str, image_digest: str, cache_buster: str) \
            -> list[BiosimulatorWorkflowRun]:
        pass

    @abstractmethod
    async def get_biosimulator_workflow_runs_by_biosim_runid(self, biosim_run_id: str) -> list[BiosimulatorWorkflowRun]:
        pass

    @abstractmethod
    async def delete_biosimulator_workflow_run(self, database_id: str) -> None:
        pass

    @abstractmethod
    async def delete_all_biosimulator_workflow_runs(self) -> None:
        pass

