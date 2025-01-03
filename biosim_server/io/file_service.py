from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel


class ListingItem(BaseModel):
    Key: str
    LastModified: datetime
    ETag: str
    Size: int


class FileService(ABC):

    @abstractmethod
    async def download_file(self, s3_path: str, file_path: Path) -> str:
        pass

    @abstractmethod
    async def upload_file(self, file_path: Path, s3_path: str) -> str:
        pass

    @abstractmethod
    async def upload_bytes(self, file_contents: bytes, s3_path: str) -> str:
        pass

    @abstractmethod
    async def get_modified_date(self, s3_path: str) -> datetime:
        pass

    @abstractmethod
    async def get_listing(self, s3_path: str) -> list[ListingItem]:
        pass

    @abstractmethod
    async def get_file_contents(self, s3_path: str) -> bytes:
        pass

    @abstractmethod
    async def close(self):
        pass