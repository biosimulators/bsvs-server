from abc import abstractmethod, ABC
from functools import lru_cache

from biosim_server.common.database.data_models import OmexFile


class DocumentNotFoundError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class DatabaseService(ABC):
    @abstractmethod
    async def insert_omex_file(self, omex_file: OmexFile) -> None:
        pass

    # @lru_cache
    @abstractmethod
    async def get_omex_file(self, file_hash_md5: str) -> OmexFile | None:
        pass

    @abstractmethod
    async def delete_omex_file(self, file_hash_md5: str) -> None:
        pass

    @abstractmethod
    async def list_omex_files(self) -> list[OmexFile]:
        pass

    @abstractmethod
    async def close(self) -> None:
        pass

