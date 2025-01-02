import os
from pathlib import Path

import pytest

from biosim_server.config import get_settings


@pytest.mark.asyncio
async def test_file_service_local(file_service_local):
    expected_file_content = b"Hello, World!"
    file_service = file_service_local
    s3_path = "some/s3/path/fname.txt"
    orig_file_path = Path("temp.txt")

    with open(orig_file_path, "wb") as f:
        f.write(expected_file_content)

    # upload the file
    absolute_s3_path = await file_service.upload_file(orig_file_path, s3_path)
    assert absolute_s3_path == str(file_service.BASE_DIR / s3_path)

    # download the file
    new_file_path = Path("temp2.txt")
    await file_service.download_file(s3_path, new_file_path)
    assert new_file_path.exists()
    with open(new_file_path, "rb") as f:
        content = f.read()
        assert content == expected_file_content

    os.remove(orig_file_path)
    os.remove(new_file_path)


@pytest.mark.skipif(len(get_settings().storage_secret) == 0,
                    reason="S3 config STORAGE_SECRET not supplied")
@pytest.mark.asyncio
async def test_file_service_s3(file_service_s3):
    expected_file_content = b"Hello, World!"
    file_service = file_service_s3
    s3_path = "some/s3/path/fname.txt"
    orig_file_path = Path("temp.txt")

    with open(orig_file_path, "wb") as f:
        f.write(expected_file_content)

    # upload the file
    absolute_s3_path = await file_service.upload_file(orig_file_path, s3_path)
    assert absolute_s3_path == str(file_service.BASE_DIR / s3_path)

    # download the file
    new_file_path = Path("temp2.txt")
    await file_service.download_file(s3_path, new_file_path)
    assert new_file_path.exists()
    with open(new_file_path, "rb") as f:
        content = f.read()
        assert content == expected_file_content

    os.remove(orig_file_path)
    os.remove(new_file_path)
