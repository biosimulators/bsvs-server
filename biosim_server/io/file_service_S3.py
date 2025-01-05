import logging
import uuid
from temporalio import workflow
with workflow.unsafe.imports_passed_through():
    from datetime import datetime
from pathlib import Path
from typing import Optional

from typing_extensions import override

from biosim_server.io.file_service import FileService, ListingItem
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
    async def download_file(self, s3_path: str, file_path: Optional[Path]=None) -> tuple[str, str]:
        if file_path is None:
            file_path = Path(__file__).parent / ("temp_file_"+uuid.uuid4().hex)
        full_s3_path = await download_s3_file(s3_path, file_path)
        return full_s3_path, str(file_path)

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

    @override
    async def close(self) -> None:
        # nothing to close here
        pass
