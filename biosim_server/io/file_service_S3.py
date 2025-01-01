import logging
from datetime import datetime
from pathlib import Path

from typing_extensions import override

from biosim_server.io.file_service import FileService
from biosim_server.io.model import ListingItem
from biosim_server.io.s3_aiobotocore import (
    download_s3_file,
    get_s3_modified_date,
    get_listing_of_s3_path,
    upload_bytes_to_s3,
    upload_file_to_s3,
    get_s3_file_contents
)

logger = logging.getLogger(__name__)

class FileServiceS3(FileService):

    @override
    async def download_file(self, s3_path: str, file_path: Path) -> str:
        return await download_s3_file(s3_path, file_path)

    @override
    async def upload_file(self, file_path: Path, s3_path: str) -> str:
        return await upload_file_to_s3(file_path, s3_path)

    @override
    async def upload_bytes(self, file_contents: bytes, s3_path: str) -> str:
        return await upload_bytes_to_s3(file_contents, s3_path)

    @override
    async def get_modified_date(self, s3_path: str) -> datetime:
        return await get_s3_modified_date(s3_path)

    @override
    async def get_listing(self, s3_path: str) -> list[ListingItem]:
        return await get_listing_of_s3_path(s3_path)

    @override
    async def get_file_contents(self, s3_path: str) -> bytes:
        return await get_s3_file_contents(s3_path)
