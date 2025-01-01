# implementation of the LocalFileService class using local file system rather than S3
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import List

import aiofiles
from typing_extensions import override

from biosim_server.io.file_service import FileService
from biosim_server.io.model import ListingItem


def generate_fake_etag(file_path: Path) -> str:
    return file_path.absolute().as_uri()


class LocalFileService(FileService):
    # temporary base directory for the mock s3 file store
    BASE_DIR_PARENT = Path(__file__).parent.parent.parent / "local_data"
    BASE_DIR = BASE_DIR_PARENT / ("s3_" + uuid.uuid4().hex)

    s3_files_written: list[Path] = []

    def __init__(self):
        self.BASE_DIR.mkdir(parents=True, exist_ok=False)

    def cleanup(self):
        # remove all files in the mock s3 file store
        shutil.rmtree(self.BASE_DIR_PARENT)

    @override
    async def download_file(self, s3_path: str, file_path: Path) -> str:
        # copy file from mock s3 to local file system
        s3_file_path = self.BASE_DIR / s3_path
        local_file_path = Path(file_path)
        local_file_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(s3_file_path, mode='rb') as f:
            contents = await f.read()
            async with aiofiles.open(local_file_path, mode='wb') as f2:
                await f2.write(contents)
        return str(s3_file_path)

    @override
    async def upload_file(self, file_path: Path, s3_path: str) -> str:
        # copy file from local file_path to mock s3 using aoifiles
        local_file_path = Path(file_path)
        s3_file_path = self.BASE_DIR / s3_path
        s3_file_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(local_file_path, mode='rb') as f:
            contents = await f.read()
            async with aiofiles.open(s3_file_path, mode='wb') as f2:
                await f2.write(contents)
        self.s3_files_written.append(s3_file_path)
        return str(s3_file_path)

    @override
    async def upload_bytes(self, file_contents: bytes, s3_path: str) -> str:
        # write bytes to mock s3
        s3_file_path = self.BASE_DIR / s3_path
        s3_file_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(s3_file_path, mode='wb') as f:
            await f.write(file_contents)
        self.s3_files_written.append(s3_file_path)
        return str(s3_file_path)

    @override
    async def get_modified_date(self, s3_path: str) -> datetime:
        # get the modified date of the file in mock s3
        s3_file_path = self.BASE_DIR / s3_path
        return datetime.fromtimestamp(s3_file_path.stat().st_mtime)

    @override
    async def get_listing(self, s3_path: str) -> List[ListingItem]:
        # get the listing of the directory in mock s3
        s3_dir_path = self.BASE_DIR / s3_path
        return [ListingItem(Key=str(file.relative_to(self.BASE_DIR)), Size=file.stat().st_size,
                            LastModified=datetime.fromtimestamp(file.stat().st_mtime), ETag=generate_fake_etag(file))
                for file in s3_dir_path.rglob("*")]

    @override
    async def get_file_contents(self, s3_path: str) -> bytes:
        # get the file contents from mock s3
        s3_file_path = self.BASE_DIR / s3_path
        return s3_file_path.read_bytes()
